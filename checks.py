# checks.py — deterministic faithfulness checks: given the task bank and a tailored draft,
# find the failure classes we can catch with plain code (no API calls, instant, free).
#
# Error classes come from the FRANK summarization-faithfulness typology, mapped onto this app
# (see TASK_SPEC.md's failure map). The model-graded audit stays for judgment calls like
# connotation; everything in here is a fact you can check by string comparison.
#
# Designed to be importable by BOTH the eval suite and (later) the app itself.

import re

# --- text helpers -----------------------------------------------------------------

STOP = set("""a an the and or but of to in on at for with by from as is are was were be been
being this that these those it its their his her our your my we i you they he she them us
which who whom whose what when where why how all any both each few more most other some such
no nor not only own same so than too very can will just should now into out up down over under
again further then once here there than while during before after above below between through
key new used using use also across within per plan plans planning""".split())

def _words(text):
    """Lowercased word list, punctuation stripped (keeps % $ inside numbers)."""
    return re.findall(r"[a-z0-9][a-z0-9%$\.,+~/-]*", (text or "").lower())

def _stem(w):
    """Crude suffix stripper so 'scaled', 'scaling' and 'scalable' all match 'scale'.
    Not linguistics — just enough that a word's own tenses stop looking like new words."""
    w = w.strip(".,")
    for suf in ("ization", "izations", "ations", "ation", "ising", "izing", "ables", "able",
                "ings", "ing", "ers", "er", "ies", "ied", "ed", "es", "s", "ly", "al"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)].rstrip("e")
    return w.rstrip("e")

def _split_compounds(words):
    """'sisense/sql' -> 'sisense', 'sql'; 'rules-of-engagement' -> its parts."""
    out = []
    for w in words:
        out += [p for p in re.split(r"[/\-]", w) if p]
    return out

def _content(text):
    """Meaning-carrying word STEMS: no stopwords, nothing shorter than 3 characters,
    compounds split, tenses folded together."""
    return {_stem(w) for w in _split_compounds(_words(text))
            if w not in STOP and len(w) > 2 and _stem(w)}

def _distinct(text):
    """Content stems MINUS generic business vocabulary. Words like 'team', 'account' and
    'management' appear in half the bank, so sharing them is not evidence that two records are
    the same record — only distinctive words are. (Same intuition as IDF weighting in search:
    rare words carry signal, common words carry noise.)"""
    return _content(text) - GENERIC

def coverage(task_text, bullet_text):
    """What fraction of the TASK's DISTINCTIVE words show up in the bullet? 1.0 = fully used."""
    t = _distinct(task_text)
    if not t:
        t = _content(task_text)             # task is entirely generic; fall back
    if not t:
        return 0.0
    return len(t & _content(bullet_text)) / len(t)

def shared_distinct(task_text, bullet_text):
    """How many distinctive words the two actually share — the absolute-evidence floor."""
    return len(_distinct(task_text) & _content(bullet_text))

# --- draft parsing ----------------------------------------------------------------

def parse_draft(draft):
    """Split a tailored draft into (preamble_lines, [(job_id, [bullets]), ...]).
    Preamble = everything before the first [[JOB:id]] tag: headline + summary."""
    preamble, sections, current = [], [], None
    for raw in (draft or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\[\[JOB:(\d+)\]\]", line)
        if m:
            current = []
            sections.append((int(m.group(1)), current))
            continue
        if line.startswith("## Trimmed for length"):
            current = None                      # trimmed report isn't resume content
            continue
        text = line[2:].strip() if line[:2] in ("- ", "* ") else line
        if line.startswith("#"):
            continue                            # headings render from the DB, not the model
        (current if current is not None else preamble).append(text)
    return preamble, sections

# --- the bank ---------------------------------------------------------------------

def load_bank(store):
    """Read the bank into plain dicts so checks never touch the database directly.
    Returns [{id, job_id, text, group}], including hidden jobs (a hidden job's task
    appearing in a draft is itself a finding)."""
    tasks = []
    for job in store.list_jobs():
        for t in store.list_tasks(job["id"]):
            gid = t["group_id"] if "group_id" in t.keys() else None
            tasks.append({"id": t["id"], "job_id": job["id"], "text": t["text"], "group": gid})
    return tasks

MIN_SHARED = 3          # a match needs this many distinctive words in common, not just a ratio

def matches(bullet, tasks, threshold=0.5):
    """Tasks this bullet draws on, best first. A task counts as 'used' only when BOTH
    (a) `threshold` of its distinctive words appear in the bullet, and (b) at least
    MIN_SHARED distinctive words are actually shared (short tasks need all they have).
    Without (b), two records that share only boilerplate look like one record."""
    out = []
    for t in tasks:
        score = coverage(t["text"], bullet)
        if score < threshold:
            continue
        need = min(MIN_SHARED, len(_distinct(t["text"])) or 1)
        if shared_distinct(t["text"], bullet) < need:
            continue
        out.append((score, t))
    return sorted(out, key=lambda x: -x[0])

# --- individual checks ------------------------------------------------------------
# Every check returns a list of findings: (severity, class, message).
# severity: "RED" = would block sending. "AMBER" = look at it.

PERIODS = ["annual", "annualized", "annually", "quarterly", "monthly", "weekly", "daily", "yearly"]
HEDGES = ("~", "about", "approximately", "over", "under", "nearly", "roughly")
QUALIFIERS = ["internal", "existing", "interim", "pilot", "partial", "temporary", "proposed",
              "adjacent", "draft", "planned"]
# Words too generic to be evidence of ad-borrowing on their own. Domain terms, acronyms and
# proper nouns are NOT in here on purpose — those are exactly what we want flagged.
GENERIC = set("""scale scaled scaling team teams process processes operations operational
business company companies leader leadership manage managed management system systems data
support supported improve improved improvement performance quality strategy strategic customer
customers experience organization organizational function functions program programs project
projects work working role roles level levels report reports reporting build built building
drive driven driving deliver delivered lead led partner partnered cross functional""".split())
GENERIC = {_stem(w) for w in GENERIC}   # stored as stems, since that's what _content produces

STRONG_VERBS = ["owned", "drove", "spearheaded", "architected", "transformed", "pioneered",
                "founded", "created", "established", "directed", "orchestrated", "championed"]

def check_blends(bullet, hits):
    """Two or more DIFFERENT tasks fused into one bullet without a shared group label."""
    out = []
    if len(hits) >= 2:
        groups = {t["group"] for _, t in hits}
        if not (len(groups) == 1 and None not in groups):
            names = " | ".join(f"#{t['id']} {t['text'][:45]}..." for _, t in hits[:3])
            out.append(("RED", "blend", f"draws on {len(hits)} ungrouped tasks: {names}"))
    return out

def check_cross_job(bullet, hits, section_job_id):
    """A bullet sitting under one employer that's actually sourced from a different job."""
    out = []
    for score, t in hits:
        if t["job_id"] != section_job_id:
            out.append(("RED", "cross_job",
                        f"bullet under job {section_job_id} matches task #{t['id']} "
                        f"from job {t['job_id']} (coverage {score:.0%})"))
    return out

def _numbers(text):
    """Numeric tokens with their hedge marker attached: '~60%', '$465m', '3,000+'."""
    found = set()
    for m in re.finditer(r"(~?\$?\d[\d,\.]*\s?(?:%|k|m|b|bn)?\+?)", (text or "").lower()):
        tok = m.group(1).replace(" ", "").rstrip(".,")
        if tok not in {".", ","}:
            found.add(tok)
    return found

def check_numbers(bullet, hits):
    """Circumstance errors: a figure that isn't in the source, or lost its hedge/period."""
    out = []
    if not hits:
        return out
    src = " ".join(t["text"] for _, t in hits).lower()
    src_nums = _numbers(src)
    for n in _numbers(bullet):
        if n in src_nums:
            continue
        bare = n.lstrip("~").rstrip("+")
        if any(bare == s.lstrip("~").rstrip("+") for s in src_nums):
            out.append(("RED", "number_hedge",
                        f"'{n}' drops or changes the source's approximation marker"))
        else:
            out.append(("RED", "number_unbacked", f"'{n}' does not appear in the source task(s)"))
    b_periods = [p for p in PERIODS if re.search(rf"\b{p}\b", bullet.lower())]
    s_periods = [p for p in PERIODS if re.search(rf"\b{p}\b", src)]
    for p in b_periods:
        if s_periods and p not in s_periods:
            out.append(("RED", "period_drift",
                        f"draft says '{p}' but the source says '{s_periods[0]}'"))
    return out

def check_proper_nouns(bullet, bank_vocab):
    """Entity errors: a capitalised name (system, vendor, employer) that's nowhere in the bank.
    The dangerous variant is swapping the user's real tool for one the job ad asked for."""
    out = []
    # Skip words that are capitalised only because they START a sentence — otherwise every
    # bullet's opening verb reads as a mysterious proper noun.
    body = re.sub(r"(^|[.;:]\s+)([A-Z])", lambda m: m.group(1) + m.group(2).lower(), bullet.strip())
    for word in re.findall(r"\b([A-Z][A-Za-z0-9&\.\-]{2,})", body):
        key = _stem(word.lower())
        # Compounds ('AI-powered', 'Sisense/SQL') are known if every meaningful part is known.
        # Parts under 3 characters never enter the vocabulary at all, so they prove nothing.
        parts = [_stem(x) for x in re.split(r"[/\-]", word.lower()) if len(x) > 2]
        known = (key in bank_vocab or word.lower().strip(".") in bank_vocab or key in GENERIC
                 or (parts and all(p in bank_vocab or p in GENERIC for p in parts)))
        if known or key in STOP or (key.isupper() and len(key) <= 3):
            continue
        out.append(("AMBER", "entity",
                    f"'{word}' does not appear anywhere in the bank — invented or ad-borrowed?"))
    return out

def check_qualifiers(bullet, hits):
    """A truth-critical qualifier present in the source but dropped in the draft."""
    out = []
    for _, t in hits:
        for q in QUALIFIERS:
            if re.search(rf"\b{q}\b", t["text"].lower()) and not re.search(rf"\b{q}\b", bullet.lower()):
                out.append(("RED", "dropped_qualifier",
                            f"source task #{t['id']} says '{q}'; the draft dropped it"))
    return out

def check_verbs(bullet, hits):
    """Predicate errors: the draft opens with a stronger verb than its source task."""
    out = []
    if not hits:
        return out
    b_verb = (_words(bullet) or [""])[0].strip(".,")
    if b_verb not in STRONG_VERBS:
        return out
    for _, t in hits:
        s_verb = (_words(t["text"]) or [""])[0].strip(".,")
        if s_verb != b_verb and not re.search(rf"\b{b_verb}\b", t["text"].lower()):
            out.append(("RED", "verb_escalation",
                        f"draft opens '{b_verb}'; source task #{t['id']} opens '{s_verb}'"))
    return out

def check_unbacked(bullet, hits):
    """Out-of-source errors: a bullet no task supports."""
    if hits:
        return []
    return [("RED", "unbacked", "no bank task covers this bullet")]

def check_ad_vocab(preamble, bank_vocab, ad_text):
    """Ad-vocabulary injection: words in the headline/summary that come from the JOB AD
    and appear nowhere in the bank. This is the O2C failure, caught deterministically."""
    out = []
    ad_words = _content(ad_text)
    acronyms = {a.lower() for a in re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", " ".join(preamble))}
    for line in preamble:
        for w in _content(line):
            if w in bank_vocab or w in GENERIC:
                continue
            if w in ad_words or w in acronyms:
                out.append(("RED", "ad_vocab",
                            f"headline/summary uses '{w}' — it's in the job ad, not the bank"))
    return out

# --- the runner -------------------------------------------------------------------

def run_all(draft, tasks, ad_text="", extra_vocab=""):
    """Run every check over one draft. Returns a list of findings:
    (severity, class, message, bullet_text).
    extra_vocab: employer/role/location names — they're real bank facts that live in the
    jobs table rather than task text, so without them every employer reads as invented."""
    bank_vocab = _content(" ".join(t["text"] for t in tasks) + " " + extra_vocab)
    preamble, sections = parse_draft(draft)
    findings = []

    for sev, cls, msg in check_ad_vocab(preamble, bank_vocab, ad_text):
        findings.append((sev, cls, msg, "(headline/summary)"))

    # Summary bullets are claims too: check them against the bank, minus job-placement checks.
    for line in preamble:
        hits = matches(line, tasks)
        for sev, cls, msg in (check_blends(line, hits) + check_numbers(line, hits)
                              + check_qualifiers(line, hits) + check_verbs(line, hits)
                              + check_proper_nouns(line, bank_vocab)):
            findings.append((sev, cls, msg, line))

    for job_id, bullets in sections:
        for b in bullets:
            hits = matches(b, tasks)
            for sev, cls, msg in (check_unbacked(b, hits) + check_blends(b, hits)
                                  + check_cross_job(b, hits, job_id) + check_numbers(b, hits)
                                  + check_qualifiers(b, hits) + check_verbs(b, hits)
                                  + check_proper_nouns(b, bank_vocab)):
                findings.append((sev, cls, msg, b))

    # A word already reported as ad-vocabulary shouldn't also be reported as a mystery entity.
    flagged_words = {m.split("'")[1].lower() for s, c, m, b in findings
                     if c == "ad_vocab" and "'" in m}
    findings = [f for f in findings
                if not (f[1] == "entity" and f[2].split("'")[1].lower() in flagged_words)]

    seen, unique = set(), []          # same finding twice is noise, not two problems
    for f in findings:
        key = (f[1], f[2], f[3][:60])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique

# =====================================================================================
# BANK-SIDE CHECKS — these run over the TASK BANK itself, before any resume exists.
# Same idea as the draft checks: whatever plain code can settle, code settles. The coach
# then spends model calls only on genuine judgment (altitude, outcome, vagueness).
# Rule numbers refer to TASK_SPEC.md.
# =====================================================================================

# Words that signal a record leaning on something outside itself (spec rule 8).
DEPENDENT = ["this project", "that project", "the above", "as mentioned", "same as",
             "this effort", "this work", "these teams", "also,", "additionally"]

# Attribution markers: any one of these makes who-did-what explicit (spec rule 4).
ATTRIB = ["team", "teams", "partnered", "partnership", "with the", "personally", "owned",
          "own ", "founding member", "alongside", "collaborat", "we ", "supported", "helped",
          "contributed", "as part of", "jointly", "my ", "reports"]

# Verbs that are genuinely ambiguous about solo-vs-team when they open a record. Leadership
# verbs (led, managed, directed, oversaw) already carry attribution, so they're not here —
# flagging those would fire on most of a healthy bank, and a coach that flags everything is
# a coach nobody reads.
AMBIGUOUS_VERBS = ["built", "developed", "created", "designed", "implemented", "launched",
                   "established", "renegotiated", "negotiated", "delivered", "produced",
                   "automated", "migrated", "consolidated", "instituted", "introduced"]

def weld_risk(tasks, min_shared=3):
    """Spec rule 3 (distinctiveness). Pairs of tasks at the SAME job that share enough
    distinctive vocabulary that a summarizer will read them as one story — the deterministic
    version of 'these two are going to blend.' Ungrouped pairs only: tasks that already share
    a group label are sanctioned to combine, so overlap there is fine and expected.
    Returns [(shared_count, [w1, w2, ...], task_a, task_b), ...], worst first."""
    out = []
    for i, a in enumerate(tasks):
        for b in tasks[i + 1:]:
            if a["job_id"] != b["job_id"]:
                continue
            if a["group"] and b["group"] and a["group"] == b["group"]:
                continue                      # sanctioned pair — combining is allowed
            shared = _distinct(a["text"]) & _distinct(b["text"])
            if len(shared) >= min_shared:
                out.append((len(shared), sorted(shared), a, b))
    return sorted(out, key=lambda x: -x[0])

def spelling_drift(tasks):
    """Spec rule 10 (canonical names). The same word written more than one way across the bank
    ('JIRA' vs 'Jira'), which quietly breaks every check that compares strings. Differences in
    only the first letter are ignored — that's just sentence capitalisation.
    Returns {lowercase_word: [surface forms]}."""
    forms = {}
    for t in tasks:
        for w in re.findall(r"\b[A-Za-z][A-Za-z0-9&\.]{2,}\b", t["text"]):
            if w.lower() in STOP:
                continue
            forms.setdefault(w.lower(), set()).add(w)
    drift = {}
    for key, variants in forms.items():
        if len(variants) < 2:
            continue
        if len({v[1:] for v in variants}) > 1:      # differ beyond the first letter
            drift[key] = sorted(variants)
    return drift

def spec_scan(task_text):
    """Per-task spec violations that plain code can settle. Returns [(rule, message)].
    Deliberately narrow: only things a string can prove, so the model never gets asked."""
    out = []
    low = task_text.lower()

    for phrase in DEPENDENT:                                    # rule 8
        if phrase in low:
            out.append(("rule8_self_contained",
                        f"'{phrase.strip()}' points at something outside this task — "
                        "the tailor sees tasks one at a time and in any order"))
            break

    first = (_words(task_text) or [""])[0].strip(".,")           # rule 4
    if first in AMBIGUOUS_VERBS and not any(m in low for m in ATTRIB):
        out.append(("rule4_attribution",
                    f"opens with '{first}' and names no team or partner — solo work or a team "
                    "effort? An ambiguous verb gets rendered as sole credit"))

    for q in QUALIFIERS:                                        # rule 5
        if re.search(rf"\b{q}\b", low):
            out.append(("rule5_fragile_qualifier",
                        f"'{q}' is load-bearing and lives in a droppable modifier — it gets "
                        "trimmed in compression; restate it in the noun or verb"))
            break

    for m in re.finditer(r"\$[\d,\.]+\s?[kmb]?", low):          # rule 9
        window = low[max(0, m.start() - 60):m.end() + 60]
        if not any(p in window for p in PERIODS) and "spend" not in window and "budget" not in window:
            out.append(("rule9_number_period",
                        f"'{m.group(0)}' has no timeframe — a figure with no period gets "
                        "re-scaled (quarterly silently becomes annual)"))
            break
    return out
