# tailor.py — pulls your real experience + a job ad, sends to Claude, returns tailored bullets.
import store
from ai import ask_claude
import json

def build_system():
    """Assemble the editor instructions from your saved style settings."""
    tone    = store.get_setting("style_tone", "Professional")
    length  = store.get_setting("style_length", "Medium")
    maxb     = store.get_setting("style_max_bullets", "4")
    totalb   = store.get_setting("style_total_bullets", "18")
    metrics = store.get_setting("style_metrics", "yes") == "yes"
    custom  = store.get_setting("style_custom", "")

    rules = (
        "You are an expert resume editor. Using ONLY the candidate's real base resume and "
        "logged tasks, write tailored resume content for the job ad. You may reword, reorder, "
        "and emphasize real experience to match the ad's language, but NEVER invent employers, "
        "titles, dates, metrics, or skills the candidate does not have.\n\n"
        "PRESERVE ATTRIBUTION — as important as not inventing facts. Keep who did the work "
        "exactly as the source states it. If the source says the candidate's team did something, "
        "the bullet must say so ('Led the team that...', 'Through my team...') — never promote "
        "team work to first-person individual work. If the source says the candidate was a "
        "member of or contributor to something, never upgrade that to founder, owner, or sole "
        "leader. Never add adverbs the source does not support ('directly', 'personally', "
        "'single-handedly', 'hands-on'). Never add qualifiers that change what a number means "
        "(if the source says 'quarterly spend', do not write 'quarterly comp spend'). Never "
        "escalate a verb's strength: 'project managed', 'supported', 'contributed to', or "
        "'helped' must not become 'owned', 'led', 'drove', or 'built'. Keep the source's own "
        "words for roles and people — if the source says 'rep', write 'rep', never 'agent'. "
        "SCOPE, not just credit, can drift the same way: if the source says a task was done "
        "'across N employees' or 'affecting N employees' — describing the SCALE something "
        "touched — never convert that into 'led teams of N' or 'led N-person workforces', "
        "which claims DIRECT people-management of N. Only use direct-headcount language if the "
        "source explicitly states direct management of that many people. Scope inflation is "
        "the same class of lie as credit theft — reattributing what a number counts, not just "
        "who gets credit for it. "
        "NEVER COMBINE two distinct tasks into one bullet in a way that implies one caused the "
        "other's outcome, unless a task explicitly states that connection. If you join two real "
        "tasks with 'and', the result must not read as a single cause-and-effect story the "
        "source doesn't support — e.g. do not merge 'led an enablement initiative' with 'built "
        "a tool that cut time X to Y' into one bullet implying the initiative produced that "
        "result, when they are two separate accomplishments. When combining is genuinely useful, "
        "keep them as two bullets rather than inventing a causal link between them. Never drop a "
        "real number or usage stat from one task just because it got merged with another. "
        "When in doubt about who did something or what a number counts, use the weaker "
        "claim.\n\n"
        f"STYLE: tone = {tone}; bullet length = {length}; up to {maxb} bullets per job. "
        f"TOTAL BUDGET: the resume may contain AT MOST {totalb} experience bullets in total "
        "(the headline and the summary bullets do NOT count — only the per-job bullets). This "
        "is a HARD CEILING, not a number to approximate: do not exceed it, and do not land "
        "'close to' it on the high side. Count the per-job bullets before finishing; if the "
        f"total is above {totalb}, cut the least-relevant ones until it is not. "
        "Allocate the budget by RELEVANCE to THIS job ad: the jobs whose real tasks most match "
        "the ad get more bullets (up to the per-job cap), less-relevant jobs get fewer or drop "
        "to zero bullets (just their dateline). "
        f"If you have MORE than {totalb} genuinely relevant bullets, that is exactly when the "
        "Trimmed report below applies — keep the best, cut the rest to fit, and list the "
        "relevant ones you cut. This is a SELECTION task only: choose which real bullets to "
        "include, never merge, reorder, or re-title jobs to hit the number, and never invent or "
        "pad bullets to reach it. If the genuinely-relevant material is UNDER budget, stay "
        f"under — {totalb} is a ceiling, not a quota. "
        "Start every bullet with a strong action verb. "
    )
    if metrics:
        rules += "Lead with quantified results (numbers, %, $) whenever the real task supports it. "
    if custom:
        rules += f"Extra instructions: {custom} "
    rules += (
        "\n\nSUMMARY & HEADLINE RULES: the summary and headline are the only prose not "
        "anchored to a specific logged task, so they're where false claims hide. Every "
        "factual claim in either — years of "
        "experience, industries, company stage, scale, scope — must be derivable from the "
        "candidate's stored jobs and tasks. Do NOT state a total years-of-experience number. "
        "Do NOT claim industry or company-stage experience (e.g. 'high-growth SaaS', "
        "'enterprise', 'startup') unless the logged data shows it. No unfalsifiable filler: "
        "never write 'proven track record', 'results-driven', 'seasoned', 'passionate about', "
        "'demonstrated ability', 'track record of success', 'brings a history of', 'a history "
        "of'. The rules above apply here too: no "
        "puffery adverbs in the summary ('hands-on', 'directly', 'personally', 'seasoned'), no "
        "verb escalation, keep the source's own vocabulary. Back every claim with a LOGGED TASK "
        "specifically — the base resume text is unverified legacy and does NOT count as backing; "
        "if a phrase appears only there and in no logged task, cut it. If a claim cannot be "
        "checked against a logged task, cut it. "
        "CROSS-JOB SYNTHESIS: the summary is the one place required to compress the whole "
        "career into a few lines, which makes it the one place most likely to blend facts from "
        "DIFFERENT jobs or eras into a single claim. Two rules apply here, in addition to the "
        "ones above: (1) never combine tasks from different jobs into one bullet in a way that "
        "implies they were one continuous initiative or that one caused the other, unless a "
        "stored task explicitly says so; (2) attribution still applies when synthesizing across "
        "jobs — if the source tasks credit a team, PMO, or initiative for an outcome (e.g. "
        "scaling from N to M), the summary must preserve that, not compress it into personal "
        "leadership ('contributed to' or 'supported', not 'grew' or 'scaled'), even when the "
        "specific job that owns the credit gets summarized away for space."
        "\n\nOUTPUT: Markdown only — no '---' lines, no commentary. Start with a '## Headline' "
        "heading followed by ONE line (no bullet, no bold formatting) — a title plus one "
        "standout specialization or metric. The TITLE portion must be one of the candidate's "
        "ACTUAL STORED job titles, or a direct restatement of one — NEVER the job ad's own "
        "title for the role, even if it sounds close or more impressive. If the ad calls the "
        "role 'Director, Compliance Operations' and the candidate's stored title is 'Director "
        "of Operations', the headline title is 'Director of Operations' — do not adopt the "
        "ad's title as if it were the candidate's. "
        "The SPECIALIZATION phrase after the title gets the SAME task-backing test as every "
        "summary claim: it must be checkable against a SPECIFIC stored task where that subject "
        "is the task's PRIMARY focus, not a passing mention inside a task about something else. "
        "Do NOT use a connotation-loaded word ('compliance', 'compliance-enabling', 'security', "
        "'governance', 'audited', 'secured', 'directed') as a functional label for the "
        "specialization UNLESS a stored task is centrally about that discipline, not merely "
        "touching on it. A task that mentions 'agent policy compliance' as one clause inside a "
        "broader workforce-management task does NOT license 'compliance-enabling' as the "
        "candidate's headline specialty — that is the same overclaim as using the ad's own "
        "title, just moved one word to the right. When unsure, describe the work in the "
        "candidate's own plain operational language (e.g. 'workforce and access management "
        "systems') instead of borrowing the ad's functional framing. Then a '## Summary' heading "
        "followed by 3-4 bullet points (each starting with '- '), not a paragraph — "
        "one distinct, independently-checkable claim per bullet. Then, for each relevant "
        "job, output a line containing ONLY that job's tag exactly as given (e.g. "
        "'[[JOB:3]]') on its own line, followed by that job's "
        "bullets starting with '- '. Output jobs in reverse-chronological order — most recent "
        "first — regardless of relevance. Do NOT write company names, job titles, or dates "
        "yourself — only the [[JOB:id]] tag and the bullets. "
        "INCLUDE EVERY JOB — never fully omit one, even if none of its tasks are relevant to "
        "this ad. A missing job creates an unexplained gap in the employment timeline, which "
        "looks worse than an irrelevant one. If a job has nothing relevant to say, output ONLY "
        "its [[JOB:id]] tag with ZERO bullets beneath it — the employer, title, and dates still "
        "render from the database. Only write bullets for the tasks that are actually relevant; "
        "it's fine and expected for some jobs to have 0 bullets and others to have several."
        "\n\nTRIMMED REPORT: if — and ONLY if — you left out a bullet that IS genuinely relevant "
        "to this ad purely because the total budget was full (not bullets you skipped as "
        "irrelevant, which need no report), list them at the very END of your output under a "
        "heading exactly '## Trimmed for length'. Under it, one line per cut bullet in the form "
        "'[[JOB:id]] short description of the cut bullet' using the same job tag. This heading "
        "must come AFTER every job section. If you didn't cut anything relevant for space, omit "
        "the heading entirely — do not write it with 'none' or leave it empty."
    )
    return rules

def build_candidate_profile():
    """Assemble the stored resume + work history + tasks into one text block."""
    lines = ["WORK HISTORY AND TASKS (real experience only):"]
    for job in store.list_jobs():
        lines.append(f"\n[[JOB:{job['id']}]] {job['employer']} — {job['role']}")
        for task in store.list_tasks(job["id"]):
            lines.append(f"- {task['text']}")
    return "\n".join(lines)

def tailor_resume(job_ad):
    prompt = f"JOB AD:\n{job_ad}\n\n{build_candidate_profile()}"
    return ask_claude(prompt, system=build_system(), model="claude-sonnet-4-6", max_tokens=1500)

ANALYZE_SYS = (
    "You are a precise resume-matching analyst. Compare the candidate's real resume and logged "
    "tasks to the job ad. Respond with ONLY valid JSON — no code fences, no commentary — in exactly "
    'this shape: {"score": <integer 0-100>, "matched": [<skills/keywords from the ad the candidate '
    'genuinely demonstrates>], "missing": [<important requirements in the ad NOT evidenced in the '
    'resume>], "gaps": [{"gap": <short honest note on a real gap>, "ad_quote": <the exact phrase '
    'or sentence from the job ad that this gap responds to>}]}. '
    'Do not pad "matched" with things the resume does not actually show. '
    "The ad_quote MUST be copied VERBATIM from the job ad text — exact words, not a paraphrase "
    "or summary. If a gap doesn't map to one specific phrase in the ad, use the closest relevant "
    "sentence rather than inventing a quote. A made-up quote is a fabrication, same as any other "
    "invented fact — never do it. "
    "DISTINGUISH ILLUSTRATIVE EXAMPLES FROM NAMED REQUIREMENTS: when the ad gives a list after "
    "'such as', 'including', or 'e.g.' (e.g. 'tools such as Salesforce, Gainsight, and SQL'), "
    "treat every item in that list as ONE illustrative example of a broader category, not a "
    "separate required item — do not report a single example from an illustrative list as its "
    "own named gap. Only treat a specific tool/skill as a discrete requirement if the ad names "
    "it outside an illustrative list, or explicitly says 'required', 'must have', or similar. "
    "NEVER STATE A SENIORITY/LEVEL CLAIM THAT CONTRADICTS THE CANDIDATE'S STORED TITLE. If the "
    "candidate's real title is Director (or similar), never write a gap like 'leadership scope "
    "has been at operations and mid-manager level' — that reads as if their actual title were "
    "ignored. Instead, name the SPECIFIC scope difference: e.g. 'Director-level title, but "
    "scope was a single ops function rather than a multi-department org reporting to a "
    "C-suite exec.' A gap about org scope/scale is fine and often real — a gap that implies a "
    "lower job title than the candidate actually holds is not."
)

def analyze_match(job_ad):
    """Compare the candidate to a job ad; return a dict with score, matched, missing, gaps."""
    prompt = f"JOB AD:\n{job_ad}\n\n{build_candidate_profile()}"
    raw = ask_claude(prompt, system=ANALYZE_SYS, model="claude-sonnet-4-6", max_tokens=800)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()   # strip any fences
    return json.loads(clean)   # turn the JSON text into a Python dict

REALITY_SYS = (
    "You compare a candidate's resume database against an outside source they pasted (usually "
    "their LinkedIn profile). Your ONLY job is to find DISCREPANCIES in facts: employer names, "
    "job titles, start dates, end dates, and missing or extra jobs. Do not comment on wording, "
    "style, or accomplishments — facts only. Respond with ONLY a valid JSON array, no fences, "
    "no commentary. Each element: {\"field\": <what differs, e.g. 'ZipRecruiter — Director "
    "start date'>, \"bank_says\": <the database value>, \"source_says\": <the pasted source's "
    "value>, \"note\": <one short sentence on why it matters, e.g. 'a background check would "
    "surface this'>}. If a job appears in one place but not the other, report it with "
    "bank_says or source_says as 'missing'. If everything matches, return []. Never invent a "
    "discrepancy; when the pasted text is ambiguous, skip it rather than guess."
)

EXPORT_AUDIT_SYS = (
    "You are auditing a TAILORED RESUME DRAFT against the candidate's real task bank, looking "
    "for claims that overreach what the bank actually supports. This is NOT about inventing "
    "facts wholesale — the tailoring prompt already blocks that. You're looking for subtler "
    "drift: things that are technically true but misleading, or that quietly escalate beyond "
    "the source. Respond with ONLY a valid JSON array, no fences, no commentary. Each element: "
    '{"claim": <the exact phrase or sentence from the draft>, "issue_type": <one of '
    '"unbacked", "attribution", "blended", "connotation", "synonym", "summary_orphan">, "note": '
    '<one sentence on what\'s wrong>, "source_task": <the closest matching task from the bank, '
    'or null if none exists>}. If nothing is wrong, return [].\n\n'
    "CHECK FOR EACH TYPE:\n"
    "- unbacked: a claim (a number, a scope, a scale) that doesn't map to any task in the bank.\n"
    "- attribution: team work rewritten as first-person individual work, or a contributor role "
    "upgraded to owner/founder/sole leader.\n"
    "- blended: two distinct tasks combined into one bullet in a way that implies one caused "
    "the other's outcome, when the bank doesn't support that connection.\n"
    "- connotation: a word that is technically true and not escalated, but whose common meaning "
    "outruns the underlying task, so a reader would understand something bigger or different "
    "than what actually happened. Watch especially for: 'compliance', 'owned', 'led', 'audited', "
    "'secured', 'directed', 'governed'. Example: the bank says 'agents adhered to internal "
    "policy' and the draft says 'compliance' — technically defensible, but a reader in a "
    "regulated industry will hear regulatory/legal compliance, not internal policy adherence. "
    "For each connotation flag, name what a reader would likely assume vs. what the bank "
    "actually supports.\n"
    "- synonym: a word was swapped for a near-synonym that changes the reader's impression, "
    "even though both are 'true-ish'. Example: 'rep' (sales/quota-carrying) swapped for 'agent' "
    "(support/call-center) — same job, different signal to a reader. Watch for these swaps "
    "especially: rep/agent, manager/lead, owned/managed, built/implemented, director/head. Only "
    "flag a synonym swap if it actually changes what a reader would infer about the role.\n"
    "- summary_orphan: a claim in the '## Summary' or '## Headline' section that describes work "
    "(a project, an initiative, a specific accomplishment) which does NOT appear anywhere in "
    "the body bullets of THIS SAME DRAFT. This is different from 'unbacked' — the claim may be "
    "perfectly true and backed by a real task in the bank, but if that task's content was "
    "edited out of the body (e.g. the user manually trimmed a bullet), the summary now promises "
    "something a reader won't find any evidence for anywhere else in the document they're "
    "holding. Check every summary/headline claim against the BODY BULLETS of this draft "
    "specifically, not against the bank. If a summary claim's subject matter isn't echoed by at "
    "least one body bullet, flag it as summary_orphan.\n\n"
    "CHECK EVERY CATEGORY AGAINST EVERY CLAIM INDEPENDENTLY. A single claim can have more than "
    "one distinct problem at once — e.g. a claim can be BOTH attribution-inflated (team work "
    "claimed as individual) AND summary_orphan (its source bullet was removed from the body) "
    "at the same time. Do not stop checking a claim once you've found one issue with it — if "
    "it has two distinct problems, output two separate flags for it, one per issue_type. Do "
    "not silently drop the summary_orphan check just because a claim already has a different "
    "flag.\n\n"
    "Be precise and conservative — only flag real drift, not stylistic choices. You are the "
    "audit, not the editor: name the problem, do not rewrite the claim yourself."
)

def export_audit(tailored_text):
    """Trace every claim in a tailored draft back to the bank; flag drift the tailoring
    prompt's own rules might have missed. Returns a list of flag dicts."""
    prompt = f"TAILORED DRAFT:\n{tailored_text}\n\n{build_candidate_profile()}"
    raw = ask_claude(prompt, system=EXPORT_AUDIT_SYS, model="claude-sonnet-4-6", max_tokens=3000)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        raise ValueError("The audit response got cut off before finishing — try running it "
                         "again. If it keeps happening, the draft may have too much to check "
                         "in one pass.")
    if not isinstance(result, list):
        raise ValueError("Expected a list of flags")
    return result

BANK_LINT_TIER2_SYS = (
    "You are reviewing a candidate's ENTIRE task bank for wording problems — not comparing it "
    "to any specific job ad or tailored draft, just checking the bank against itself. Respond "
    "with ONLY a valid JSON array, no fences, no commentary. Each element: "
    '{"issue_type": <one of "near_duplicate", "contradictory", "vocabulary_drift", '
    '"connotation">, "tasks": [<the task text(s) involved, one or two entries>], "note": <one '
    "sentence on what's wrong and why it matters>}. If nothing is wrong, return [].\n\n"
    "CHECK FOR EACH TYPE:\n"
    "- near_duplicate: two tasks (possibly in different jobs) describing the same underlying "
    "work, where keeping both risks double-counting the same accomplishment as if it happened "
    "twice, or obscures which role actually owns it.\n"
    "- contradictory: two tasks describing the same project or number differently (e.g. "
    "'quarterly spend' in one task, 'quarterly comp spend' in another, for what looks like the "
    "same initiative) — the bank disagreeing with itself.\n"
    "- vocabulary_drift: the same role, entity, or concept called two different things across "
    "tasks in ways that could read as two different things to someone else (e.g. 'rep' in one "
    "task, 'agent' for what looks like the same role in another).\n"
    "- connotation: a word in a task that is technically true but whose common meaning outruns "
    "what the task actually describes, so a future reader (or a future tailored resume built "
    "from this task) would infer something bigger or different than what happened. Watch "
    "especially for: 'compliance', 'owned', 'led', 'audited', 'secured', 'directed', "
    "'governed'. Flag the word AND explain what a reader would likely over-infer.\n\n"
    "Be conservative — only flag real ambiguity, not stylistic variation. This is the source "
    "data a resume gets built from; catching an issue here prevents it from surfacing "
    "repeatedly in every future tailored draft instead of catching it once."
)

def bank_lint_tier2():
    """One model call reviewing the whole task bank for near-duplicates, contradictions,
    vocabulary drift, and connotation issues. Returns a list of flag dicts."""
    prompt = build_candidate_profile()
    raw = ask_claude(prompt, system=BANK_LINT_TIER2_SYS, model="claude-sonnet-4-6", max_tokens=2000)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        raise ValueError("The review response got cut off before finishing — try running it "
                         "again.")
    if not isinstance(result, list):
        raise ValueError("Expected a list of flags")
    return result

def reality_check(pasted_source):
    """Diff the stored jobs against pasted outside-source text (e.g. LinkedIn). Returns a list."""
    jobs_lines = ["DATABASE JOBS:"]
    for j in store.list_jobs():
        jobs_lines.append(
            f"- {j['employer']} — {j['role']} ({j['start_date'] or '?'} to {j['end_date'] or 'Present'})"
        )
    prompt = f"PASTED SOURCE:\n{pasted_source}\n\n" + "\n".join(jobs_lines)
    raw = ask_claude(prompt, system=REALITY_SYS, model="claude-sonnet-4-6", max_tokens=1000)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)
    if not isinstance(result, list):
        raise ValueError("Expected a list of discrepancies")
    return result

BRAINDUMP_SYS = (
    "You turn a person's messy, plain-English description of work they did into clean, separate "
    "resume task entries. STRICT HONESTY: only rephrase what they actually wrote — never inflate, "
    "never invent metrics, employers, or skills they didn't state. "
    "PRESERVE ATTRIBUTION: keep who did the work exactly as stated. If they say their team did "
    "something, the entry must say so ('Led the team that...') — never rewrite team work as "
    "their own hands-on work. If they say they were a member or contributor, never upgrade it "
    "to founder or owner. Never add adverbs they didn't use ('directly', 'personally', "
    "'hands-on'). SCOPE can drift the same way credit does: 'across N employees' or 'affecting "
    "N employees' describes SCALE, not direct headcount — never rephrase it as 'led N people' "
    "or 'managed a team of N' unless they said so explicitly. When unsure who did something or "
    "what a number counts, use the weaker claim. "
    "Split distinct accomplishments "
    "into separate entries. Start each with a strong action verb. Keep any numbers they gave "
    "exactly as given. Respond with ONLY a valid JSON array of strings, no fences, no commentary. "
    'Example: ["Centralized identity and access management for operations, consolidating '
    'permissioning under a single owned function", "Built a Jira workflow for structured '
    'access-change requests"]'
)

def braindump_to_tasks(dump_text):
    """Turn a messy description into a list of clean task strings."""
    raw = ask_claude(dump_text, system=BRAINDUMP_SYS, model="claude-sonnet-4-6", max_tokens=1000)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)
    if not isinstance(result, list):
        raise ValueError("Expected a list of tasks")
    return [str(t).strip() for t in result if str(t).strip()]