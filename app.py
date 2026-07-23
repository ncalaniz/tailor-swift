# CHECKPOINT-ALPHA
# app.py — a local visual interface for your resume studio.
# Run it with:  streamlit run app.py
import streamlit as st
import json
import datetime
import store
from tailor import braindump_to_tasks, tailor_resume, analyze_match, reality_check, export_audit, bank_lint_tier2, coach_review_task, coach_apply_answers
from export import build_docx, build_pdf, _year_of, _month_of
from lint import check_bank
import re

@st.cache_data(show_spinner=False)
def _cached_docx(text):
    return _safe_export(build_docx, text)

@st.cache_data(show_spinner=False)
def _cached_pdf(text):
    return _safe_export(build_pdf, text)

def _safe_export(build_fn, text):
    """Run a build_docx/build_pdf call; never let a bad export crash the page.
    Returns (bytes_or_None, error_message_or_None)."""
    try:
        return build_fn(text), None
    except Exception as e:
        return None, str(e)

def _sort_draft_text(text):
    """Reorder [[JOB:id]] sections in raw tailored text to reverse-chronological order,
    same sort key as export.py/_preview — but keeps the tags intact (doesn't convert to
    headers). Run ONCE right after a fresh tailor/re-tailor, not on every rerun."""
    from export import _year_of, _month_of

    def _sort_key(job_id):
        for j in store.list_jobs():
            if j["id"] == job_id:
                end = (j["end_date"] or "").strip().lower()
                if not end or end == "present":
                    return (0, "")
                return (1, (_year_of(end) * -1, _month_of(end) * -1))
        return (2, 0)

    lines = text.split("\n")
    preamble = []
    sections = []
    current = None
    for raw in lines:
        m = re.match(r"^\[\[JOB:(\d+)\]\]\s*$", raw.strip())
        if m:
            current = [raw]
            sections.append((int(m.group(1)), current))
            continue
        (current if current is not None else preamble).append(raw)

    sections.sort(key=lambda s: _sort_key(s[0]))
    out = preamble[:]
    for _, block_lines in sections:
        out.extend(block_lines)
    return "\n".join(out)

def _preview(text):
    """Turn [[JOB:id]] tags into readable headings for on-screen preview, in the same
    reverse-chronological order the actual PDF/Word exports use."""
    from export import _job_heading_parts, _year_of, _month_of

    def _sort_key(job_id):
        for j in store.list_jobs():
            if j["id"] == job_id:
                end = (j["end_date"] or "").strip().lower()
                if not end or end == "present":
                    return (0, "")
                return (1, (_year_of(end) * -1, _month_of(end) * -1))
        return (2, 0)

    # parse line-by-line into preamble + per-job line lists, same approach build_pdf uses
    preamble_lines = []
    sections = []       # list of (job_id, [lines])
    current = None
    for raw in text.split("\n"):
        m = re.match(r"^\[\[JOB:(\d+)\]\]\s*$", raw.strip())
        if m:
            current = []
            sections.append((int(m.group(1)), current))
            continue
        (current if current is not None else preamble_lines).append(raw)

    sections.sort(key=lambda s: _sort_key(s[0]))

    def repl(job_id):
        title, dates, loc = _job_heading_parts(job_id)
        h = title + (f" ({dates})" if dates else "")
        return f"### {h}" if h else ""

    out_lines = list(preamble_lines)
    for job_id, lines in sections:
        out_lines.append(repl(job_id))
        out_lines.extend(lines)

    return "\n".join(out_lines)

def md_safe(text):
    """Escape $ so st.markdown doesn't swallow money figures as LaTeX math."""
    return (text or "").replace("$", "\\$")

def _dejob(text):
    """Swap any leaked JOB:id tag (from build_candidate_profile's [[JOB:id]] format)
    for the real 'Employer — Role' heading, so lint/audit notes read for a human.
    Catches [[JOB:3]], JOB:3, and JOB 3 alike."""
    from export import _job_heading_parts
    if not text:
        return text
    def _swap(m):
        try:
            title, _dates, _loc = _job_heading_parts(int(m.group(1)))
            return title or m.group(0)
        except Exception:
            return m.group(0)
    return re.sub(r"\[?\[?JOB[:\s]\s*(\d+)\]?\]?", _swap, text)

_MONTH_OK = {"jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",
             "january","february","march","april","june","july","august","september",
             "october","november","december"}

def _date_warning(text):
    """Deterministic sanity check for job dates like 'Apr 2023' / 'Present' / ''.
    Returns a warning string, or '' if the date looks fine. The 'Apt 2016' guard."""
    t = (text or "").strip()
    if not t or t.lower() == "present":
        return ""
    parts = t.split()
    if len(parts) != 2:
        return f"⚠ '{t}' — expected 'Mon YYYY' or 'Present'"
    mon, yr = parts
    if mon.lower().rstrip(".") not in _MONTH_OK:
        return f"⚠ '{mon}' isn't a month"
    if not (yr.isdigit() and len(yr) == 4 and 1950 <= int(yr) <= 2100):
        return f"⚠ '{yr}' isn't a plausible year"
    return ""

def _split_trimmed(text):
    """Separate the '## Trimmed for length' report from the actual resume text.
    Returns (resume_text, [trimmed_line, ...]). The trimmed lines are the cut-bullet
    descriptions with the leading '- '/tag left as-is for display. Called before the
    draft box and before every export so trimmed content is never rendered INTO the
    resume it was cut from."""
    lines = (text or "").split("\n")
    for i, raw in enumerate(lines):
        if raw.strip().lower() == "## trimmed for length":
            resume = "\n".join(lines[:i]).rstrip()
            trimmed = [l.strip() for l in lines[i + 1:] if l.strip()]
            return resume, trimmed
    return text, []

def _parse_draft_sections(text):
    """Split a resume draft into (preamble_lines, [(job_id, [body_lines])]) using the same
    [[JOB:id]] regex the preview and exporters use. Lets the editor show real headings as
    read-only labels while keeping the tags out of the user's hands."""
    preamble, sections, current = [], [], None
    for raw in text.split("\n"):
        m = re.match(r"^\[\[JOB:(\d+)\]\]\s*$", raw.strip())
        if m:
            current = []
            sections.append((int(m.group(1)), current))
        else:
            (current if current is not None else preamble).append(raw)
    return preamble, sections

def _reassemble_draft(preamble, sections):
    """Rebuild the tag-bearing string that export / audit / the P7 report all expect.
    Byte-identical in structure to what tailor_resume produced, so nothing downstream
    can tell the draft was edited section-by-section instead of in one box."""
    out = list(preamble)
    for job_id, lines in sections:
        out.append(f"[[JOB:{job_id}]]")
        out.extend(lines)
    return "\n".join(out)

def _structured_draft_editor(app_id, resume_text, edver):
    """Item 3 / option (c): headings render as read-only labels (facts from the DB), only
    the bullets are editable (prose). Returns the reassembled draft string. Makes the
    facts-vs-prose split visible instead of explained by a caption the tags kept undermining."""
    from export import _job_heading_parts
    preamble, sections = _parse_draft_sections(resume_text)

    # preamble (headline + summary) stays a normal editable text box — no tags in it
    pre_text = "\n".join(preamble).strip()
    new_pre = st.text_area("Headline & summary", value=pre_text,
                           key=f"edpre{app_id}_{edver}", height=180)

    new_sections = []
    for job_id, lines in sections:
        title, dates, _loc = _job_heading_parts(job_id)
        heading = title + (f" ({dates})" if dates else "")
        st.markdown(f"**{md_safe(heading)}**  ·  *from your profile — not editable here*")
        body = "\n".join(lines).strip()
        new_body = st.text_area(f"bullets for {heading}", value=body,
                                key=f"edjob{app_id}_{job_id}_{edver}", height=140,
                                label_visibility="collapsed")
        new_sections.append((job_id, new_body.split("\n")))

    return _reassemble_draft(new_pre.split("\n"), new_sections)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
STATUSES = ["Not applied", "Applied", "Interviewing", "Offer received", "Hired",
           "Rejected by them", "No response", "I passed"]


def _parse_list(text):
    """Turn stored JSON text back into a Python list (safely)."""
    try:
        return json.loads(text) if text else []
    except Exception:
        return []

def _coach_widget(job):
    """TASK-QUALITY-COACH on-demand surface: review one job's tasks for weakness,
    show a no-invention Tier-1 rewrite the user can accept, and a Tier-2
    'go further' path that asks for missing facts then folds ONLY those in."""
    jid = job["id"]
    seniority = job["seniority"] if "seniority" in job.keys() else ""
    with st.expander("✨ Coach my tasks — flag weak ones and help me strengthen them"):
        st.caption("Reviews this job's tasks for the three things that make a bullet weak: no "
                   "numbers, too junior for the role, or no outcome. Suggests a stronger version "
                   "using ONLY what's already there — and if that's not enough, asks you for the "
                   "missing facts. Never invents. Suggestions only; nothing changes unless you accept.")
        if st.button("Review this job's tasks", key=f"coach_run{jid}"):
            reviews = {}
            with st.spinner("Coaching..."):
                for t in store.list_tasks(jid):
                    try:
                        reviews[t["id"]] = coach_review_task(t["text"], seniority)
                    except Exception as e:
                        reviews[t["id"]] = {"error": str(e)}
            st.session_state[f"coach_reviews{jid}"] = reviews

        reviews = st.session_state.get(f"coach_reviews{jid}", {})
        if not reviews:
            return
        # re-fetch tasks so text is current after any accepts
        cur = {t["id"]: t for t in store.list_tasks(jid)}
        weak_found = False
        for tid, rev in reviews.items():
            if tid not in cur:
                continue
            if rev.get("error"):
                st.error(f"Couldn't review one task: {rev['error']}")
                continue
            if not rev.get("weak"):
                continue
            weak_found = True
            task = cur[tid]
            axes = ", ".join(rev.get("axes", [])) or "weak"
            st.markdown(f"**Weak task** ({axes}):")
            st.caption(md_safe(task["text"]))
            if st.button("🗑 Delete this task instead", key=f"coach_del{tid}"):
                store.delete_task(tid)
                st.session_state.setdefault("open_jobs", set()).add(jid)
                st.rerun()
            tier1 = rev.get("tier1", "").strip()
            note = rev.get("tier1_note", "").strip()
            if tier1 and tier1 != task["text"]:
                st.markdown(f"**Suggested (using only what's here):** {md_safe(tier1)}")
                if note:
                    st.caption(md_safe(note))
                if st.button("Accept this rewrite", key=f"coach_accept{tid}"):
                    store.update_task(tid, tier1)
                    st.session_state.setdefault("open_jobs", set()).add(jid)
                    st.rerun()
            else:
                st.caption(note or "Can't strengthen this without more detail — see the questions below.")
            qs = rev.get("questions", [])
            if qs:
                with st.expander("Go further — answer what you know, skip the rest"):
                    st.caption("These only ask you to add facts you already have. Anything you "
                               "answer gets folded in; anything you skip is left out — nothing invented.")
                    for q in qs:
                        st.markdown(f"- {md_safe(q)}")
                    ans = st.text_area("Your answers", key=f"coach_ans{tid}",
                                       placeholder="e.g. the contract was ~$2M/year and renewal avoided a mid-quarter migration")
                    if st.button("Strengthen with these details", key=f"coach_apply{tid}"):
                        if ans.strip():
                            with st.spinner("Rewriting with your facts..."):
                                try:
                                    stronger = coach_apply_answers(task["text"], ans.strip())
                                    st.session_state[f"coach_pending{tid}"] = stronger
                                except Exception as e:
                                    st.error(f"Rewrite failed: {e}")
                    pending = st.session_state.get(f"coach_pending{tid}")
                    if pending:
                        st.markdown(f"**Strengthened:** {md_safe(pending)}")
                        st.caption("Check every fact here traces to something you said. Accept only if true.")
                        if st.button("Accept strengthened version", key=f"coach_acceptv2{tid}"):
                            store.update_task(tid, pending)
                            st.session_state.pop(f"coach_pending{tid}", None)
                            st.session_state.setdefault("open_jobs", set()).add(jid)
                            st.rerun()
            st.divider()
        if not weak_found:
            st.success("No weak tasks found for this job — these all earn their place.")

def _braindump_widget(job_id, key_ns):
    """Reusable 'describe what you did, I'll draft tasks' flow. key_ns keeps widget keys
    unique when the same flow is used from more than one screen (Profile, Tailor gap-fill)."""
    st.markdown("**✨ Or describe what you did, and I'll draft the tasks**")
    st.caption("Write in plain words — a paragraph, a story, however it comes out. "
               "It gets split into separate polished entries that you review before "
               "saving. Only what you actually say gets used — nothing is invented.")

    dump_counter = st.session_state.get(f"dumpgen_{key_ns}{job_id}", 0)
    dump = st.text_area("What did you do at this job?",
                        key=f"dump_{key_ns}{job_id}_{dump_counter}",
                        placeholder="e.g. I ran the team that owned provisioning...")
    if st.button("Draft tasks from this", key=f"dumpbtn_{key_ns}{job_id}"):
        st.session_state.setdefault("open_jobs", set()).add(job_id)
        if dump.strip():
            with st.spinner("Turning your words into task entries..."):
                try:
                    _tasks, _questions = braindump_to_tasks(dump)
                    st.session_state[f"drafts_{key_ns}{job_id}"] = _tasks
                    st.session_state[f"dumpq_{key_ns}{job_id}"] = _questions
                except Exception as e:
                    st.error(f"Couldn't parse that — try again. ({e})")
        else:
            st.warning("Write something first.")

    _questions = st.session_state.get(f"dumpq_{key_ns}{job_id}", [])
    if _questions:
        with st.container():
            st.markdown("**A few things you could make more specific** — optional; answer any that "
                        "you know, or skip:")
            st.caption("These only ask you to put numbers on work you already described — answer "
                       "in your own words below and I'll fold them in. Nothing is added unless you "
                       "say it.")
            for q in _questions:
                st.markdown("- " + md_safe(q))
            _ans = st.text_area("Answers (optional)", key=f"dumpans_{key_ns}{job_id}",
                                placeholder="e.g. the incentive spend was about $1M across 20 teams")
            if st.button("Add these details", key=f"dumpansbtn_{key_ns}{job_id}") and _ans.strip():
                st.session_state.setdefault("open_jobs", set()).add(job_id)
                with st.spinner("Folding in your answers..."):
                    try:
                        _combined = (dump + "\n\nAdditional detail: " + _ans).strip()
                        _tasks2, _q2 = braindump_to_tasks(_combined)
                        st.session_state[f"drafts_{key_ns}{job_id}"] = _tasks2
                        st.session_state[f"dumpq_{key_ns}{job_id}"] = _q2
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't parse that — try again. ({e})")

    drafts = st.session_state.get(f"drafts_{key_ns}{job_id}", [])
    if drafts:
        st.markdown("**Review before saving** — edit anything, untick what's wrong:")
        keep, edited = [], []
        for i, d in enumerate(drafts):
            cols = st.columns([0.5, 6])
            k = cols[0].checkbox(" ", value=True, key=f"keep_{key_ns}{job_id}_{i}",
                                label_visibility="collapsed")
            e = cols[1].text_area(" ", value=d, key=f"edit_{key_ns}{job_id}_{i}",
                                  label_visibility="collapsed", height=68)
            keep.append(k); edited.append(e)
        if st.button("Save selected to this job", key=f"dumpsave_{key_ns}{job_id}"):
            st.session_state.setdefault("open_jobs", set()).add(job_id)
            n = 0
            for k, e in zip(keep, edited):
                if k and e.strip():
                    store.add_task(job_id, e.strip()); n += 1
            st.session_state.pop(f"drafts_{key_ns}{job_id}", None)
            st.session_state.pop(f"dumpq_{key_ns}{job_id}", None)
            st.session_state[f"dumpgen_{key_ns}{job_id}"] = dump_counter + 1
            st.success(f"Saved {n} tasks."); st.rerun()

def _parse_date(text):
    """Turn stored ISO text ('2026-07-17') into a date object. Empty/bad -> None."""
    try:
        return datetime.date.fromisoformat(text) if text else None
    except Exception:
        return None

def _get_app(app_id):
    """Fetch a single application by id from the stored list."""
    return next((x for x in store.list_applications() if x["id"] == app_id), None)


def _run_analysis(app_id, ad_text):
    """Analyze fit and save it. Returns True on success."""
    try:
        r = analyze_match(ad_text)
        store.save_analysis(app_id, r["score"], r["matched"], r["missing"], r["gaps"])
        return True
    except Exception as e:
        st.error(f"Analysis failed — try again. ({e})")
        return False


def style_controls():
    """The 'how the resume is written' settings — now lives next to tailoring."""
    with st.expander("Writing style (applies to every tailored resume)"):
        tones = ["Punchy", "Professional", "Formal", "Conversational"]
        lengths = ["Short", "Medium", "Detailed"]
        tone = st.selectbox("Tone", tones,
                            index=tones.index(store.get_setting("style_tone", "Professional")))
        length = st.selectbox("Bullet length", lengths,
                              index=lengths.index(store.get_setting("style_length", "Medium")))
        max_bullets = st.slider("Max bullets per job", 2, 8,
                                int(store.get_setting("style_max_bullets", "4")))
        total_bullets = st.slider("Total bullets across resume", 10, 30,
                                  int(store.get_setting("style_total_bullets", "18")),
                                  help="Overall budget. The model spends it on the jobs most "
                                       "relevant to each ad; less-relevant jobs get fewer bullets "
                                       "or just their dateline. The per-job cap above still applies.")
        metrics = st.checkbox("Emphasize numbers/metrics where the real task supports it",
                              value=store.get_setting("style_metrics", "yes") == "yes")
        custom = st.text_area("Extra instructions (optional)",
                              value=store.get_setting("style_custom", ""),
                              placeholder="e.g. lead with the outcome, avoid buzzwords")
        if st.button("Save writing style"):
            for key, val in {
                "style_tone": tone, "style_length": length,
                "style_max_bullets": str(max_bullets),
                "style_total_bullets": str(total_bullets),
                "style_metrics": "yes" if metrics else "no", "style_custom": custom,
            }.items():
                store.set_setting(key, val)
            st.success("Saved.")


st.set_page_config(page_title="Tailor Swift", page_icon="🧵", layout="wide")
_name = store.get_setting("name", "").strip()
_first = _name.split()[0] if _name else ""
st.title(f"Please Hire {_first}" if _first else "Please Hire Me")
st.caption("Tailor Swift — resumes built on your real experience.")

_setup_done = bool(_name and store.get_setting("base_resume", "").strip())
if _setup_done:
    tailor_tab, apps_tab, profile_tab, setup_tab = st.tabs(
        ["Tailor", "Applications", "Work History", "Resume Basics"]
    )
else:
    st.info("👋 New here? Start in Resume Basics, then add your work history and tasks under Work History.")
    setup_tab, profile_tab, tailor_tab, apps_tab = st.tabs(
        ["Resume Basics", "Work History", "Tailor", "Applications"]
    )

# ================= Setup (contact details only) =================
with setup_tab:
    st.subheader("Your contact details")
    st.caption("These appear at the top of every resume you export.")
    name = st.text_input("Full name", value=store.get_setting("name", ""))
    c = st.columns(2)
    email = c[0].text_input("Email", value=store.get_setting("email", ""))
    phone = c[1].text_input("Phone", value=store.get_setting("phone", ""))
    c2 = st.columns(2)
    location = c2[0].text_input("Location", value=store.get_setting("location", ""))
    linkedin = c2[1].text_input("LinkedIn / website", value=store.get_setting("linkedin", ""))
    if st.button("Save contact details"):
        for key, val in {"name": name, "email": email, "phone": phone,
                         "location": location, "linkedin": linkedin}.items():
            store.set_setting(key, val)
        st.success("Saved.")
    st.divider()
    st.subheader("Education")
    st.caption("Shows up in a dedicated section on your resume.")

    edu = json.loads(store.get_setting("education", "[]") or "[]")

    for i, e in enumerate(edu):
        with st.expander(f"{e.get('school', 'School')} — {e.get('degree', '')}"):
            c = st.columns(2)
            school = c[0].text_input("School", value=e.get("school", ""), key=f"edusch{i}")
            degree = c[1].text_input("Degree", value=e.get("degree", ""),
                                     placeholder="e.g. B.A. in English & Philosophy", key=f"edudeg{i}")
            c2 = st.columns(2)
            loc = c2[0].text_input("Location", value=e.get("location", ""), key=f"eduloc{i}")
            year = c2[1].text_input("Grad year", value=e.get("year", ""), key=f"eduyr{i}")
            b = st.columns(2)
            if b[0].button("Save", key=f"edusave{i}"):
                edu[i] = {"school": school, "degree": degree, "location": loc, "year": year}
                store.set_setting("education", json.dumps(edu))
                st.success("Saved."); st.rerun()
            if b[1].button("Delete", key=f"edudel{i}"):
                edu.pop(i)
                store.set_setting("education", json.dumps(edu))
                st.rerun()

    with st.form("add_edu", clear_on_submit=True):
        st.write("Add education")
        st.caption("Format: degree type + field(s), e.g. 'B.A. in English & Philosophy' or "
                   "'B.S. in Computer Science'. Double majors go on one line.")
        c = st.columns(2)
        new_school = c[0].text_input("School")
        new_degree = c[1].text_input("Degree", placeholder="e.g. B.A. in English & Philosophy")
        c2 = st.columns(2)
        new_loc = c2[0].text_input("Location")
        new_year = c2[1].text_input("Grad year")
        if st.form_submit_button("Add") and new_school:
            edu.append({"school": new_school, "degree": new_degree,
                        "location": new_loc, "year": new_year})
            store.set_setting("education", json.dumps(edu))
            st.rerun()

    st.divider()
    st.subheader("Skills & technologies")
    st.caption("Rendered as its own section on your resume. One per line.")
    skills = json.loads(store.get_setting("skills", "[]") or "[]")
    skills_text = st.text_area("Skills", value="\n".join(skills), height=120,
                               label_visibility="collapsed",
                               placeholder="e.g. Salesforce\nSQL\nXactly\nHex\nJira")
    if st.button("Save skills"):
        new_skills = [s.strip() for s in skills_text.split("\n") if s.strip()]
        store.set_setting("skills", json.dumps(new_skills))
        st.success("Saved.")

# ================= Profile (base resume + work history) =================
with profile_tab:
    _bank_flags = check_bank()
    if _bank_flags:
        with st.expander(f"⚠ Bank check — {len(_bank_flags)} thing(s) worth a look"):
            st.caption("Deterministic checks on your stored data. Flags only — nothing is changed.")
            for _sev, _msg in _bank_flags:
                (st.warning if _sev == "warn" else st.info)(_msg)

    with st.expander("🔎 Bank review — wording issues across your whole task bank"):
        st.caption("One model call, on demand — reviews every task for near-duplicates, "
                   "contradictory numbers, vocabulary drift, and connotation issues (a true "
                   "word whose common meaning outruns the task). Catches these once, at the "
                   "source, instead of the same issue resurfacing in every future tailored "
                   "draft. Flags only, nothing changes automatically.")
        if st.button("Run bank review", key="banklint2_run"):
            with st.spinner("Reviewing your task bank..."):
                try:
                    st.session_state["banklint2_flags"] = bank_lint_tier2()
                except Exception as e:
                    st.error(f"Review failed: {e}")
        _bl2_flags = st.session_state.get("banklint2_flags", [])
        if _bl2_flags:
            for _f in _bl2_flags:
                st.warning(
                    f"**[{_f.get('issue_type', '?')}]**\n\n"
                    f"{md_safe(_dejob(_f.get('note', '')))}\n\n"
                    + "\n\n".join(f"- {md_safe(_dejob(t))}" for t in _f.get("tasks", []))
                )
        elif "banklint2_flags" in st.session_state:
            st.success("No wording issues found across your task bank.")

    with st.expander("🔎 Reality check — compare your bank against LinkedIn"):
        st.caption("Paste your LinkedIn Experience section (select it on your profile page, "
                   "copy, paste here). One model call compares employers, titles, and dates "
                   "against your stored jobs and flags anything that doesn't match. Flags only "
                   "— nothing is changed. Catches the errors that look right: a plausible-but-"
                   "wrong date is invisible to every other check in the app.")
        _rc_src = st.text_area("LinkedIn Experience text", height=180, key="rc_src",
                               label_visibility="collapsed",
                               placeholder="Director of Operations\nStubHub · Full-time\nApr 2023 - Present\n...")
        if st.button("Run reality check", key="rc_run"):
            if not _rc_src.strip():
                st.warning("Paste your LinkedIn Experience text first.")
            else:
                try:
                    st.session_state["rc_flags"] = reality_check(_rc_src)
                except Exception as e:
                    st.error(f"Reality check failed: {e}")

        _dismissed = json.loads(store.get_setting("dismissed_reality_flags", "[]") or "[]")
        _rc_flags = st.session_state.get("rc_flags", [])
        _active = [f for f in _rc_flags if f.get("field", "") not in _dismissed]
        _hidden = [f for f in _rc_flags if f.get("field", "") in _dismissed]

        if _rc_flags and not _active:
            st.success("No open discrepancies — your bank matches the pasted source.")
        for _i, _f in enumerate(_active):
            wc = st.columns([5, 1])
            wc[0].warning(
                f"**{_f.get('field', '?')}** — bank says: {_f.get('bank_says', '?')} · "
                f"source says: {_f.get('source_says', '?')}\n\n{_f.get('note', '')}"
            )
            if wc[1].button("Known", key=f"dismiss_rc_{_i}",
                            help="Mark as an intentional difference — hide on future runs"):
                _dismissed.append(_f.get("field", ""))
                store.set_setting("dismissed_reality_flags", json.dumps(_dismissed))
                st.rerun()

        if _hidden:
            with st.expander(f"{len(_hidden)} known/dismissed difference(s) — click to review"):
                for _i, _f in enumerate(_hidden):
                    hc = st.columns([5, 1])
                    hc[0].caption(
                        f"**{_f.get('field', '?')}** — bank: {_f.get('bank_says', '?')} · "
                        f"source: {_f.get('source_says', '?')}"
                    )
                    if hc[1].button("Un-dismiss", key=f"undismiss_rc_{_i}"):
                        _dismissed.remove(_f.get("field", ""))
                        store.set_setting("dismissed_reality_flags", json.dumps(_dismissed))
                        st.rerun()

    st.subheader("Base resume")
    resume_text = st.text_area("Base resume", value=store.get_setting("base_resume", ""),
                               height=220, label_visibility="collapsed")
    if st.button("Save base resume"):
        store.set_setting("base_resume", resume_text)
        st.success("Saved.")

    st.subheader("Work history & accomplishments")
    st.caption("Each job holds its own tasks. Expand a job to edit it, see its tasks, or add more.")

    def _job_sort_key(j):
        end = (j["end_date"] or "").strip().lower()
        if not end or end == "present":
            return (0, "")  # current job(s): always first
        return (1, (_year_of(end) * -1, _month_of(end) * -1))  # newest first

    for job in sorted(store.list_jobs(), key=_job_sort_key):
        tasks = store.list_tasks(job["id"])
        _dates = f"{job['start_date']} – {job['end_date']}" if job["start_date"] else ""
        _loc = f" · {job['location']}" if job["location"] else ""
        _hidden = ("include_on_resume" in job.keys() and not job["include_on_resume"])
        _hide_tag = "   🚫 hidden from resumes" if _hidden else ""
        with st.expander(f"{job['employer']} — {job['role']}  ({_dates}{_loc} · {len(tasks)} tasks){_hide_tag}",
                         expanded=(job["id"] in st.session_state.get("open_jobs", set()))):
            # --- job details ---
            c = st.columns(5)
            employer = c[0].text_input("Employer", value=job["employer"] or "", key=f"emp{job['id']}")
            role = c[1].text_input("Role", value=job["role"] or "", key=f"role{job['id']}")
            start = c[2].text_input("Start", value=job["start_date"] or "", key=f"start{job['id']}")
            end = c[3].text_input("End", value=job["end_date"] or "", key=f"end{job['id']}")
            loc = c[4].text_input("Location", value=job["location"] or "", key=f"loc{job['id']}")
            for _w in (_date_warning(start), _date_warning(end)):
                if _w:
                    st.caption(_w)
            _levels = ["", "IC", "Manager", "Director", "Executive"]
            _cur_sen = job["seniority"] if "seniority" in job.keys() else ""
            seniority = st.selectbox(
                "Seniority at this job", _levels,
                index=_levels.index(_cur_sen) if _cur_sen in _levels else 0,
                key=f"sen{job['id']}",
                help="Sets how much this job gets compressed when tailoring — a Director role "
                     "reads as a few bullets about owning the function; an IC role gets the "
                     "detailed play-by-play. Leave blank to let the model judge from the title.")
            b = st.columns(2)
            _cur_inc = (("include_on_resume" not in job.keys()) or bool(job["include_on_resume"]))
            new_inc = st.checkbox(
                "Include this job on resumes", value=_cur_inc, key=f"inc{job['id']}",
                help="Off = this job never reaches the tailor at all — no heading, no bullets, "
                     "nothing. Use it for old roles that just take up space. Note the tradeoff: "
                     "hiding a job in the MIDDLE of your history leaves a visible date gap a reader "
                     "will notice and wonder about. Hiding your OLDEST roles just makes the resume "
                     "start later, which reads fine. Hidden jobs stay in your bank and still get "
                     "checked by Bank Lint — they're only hidden from resumes.")
            if new_inc != _cur_inc:
                store.set_job_included(job["id"], new_inc)
                st.session_state.setdefault("open_jobs", set()).add(job["id"])
                st.rerun()

            b = st.columns(2)
            if b[0].button("Save changes", key=f"savejob{job['id']}"):
                st.session_state.setdefault("open_jobs", set()).add(job["id"])
                store.update_job(job["id"], employer, role, start, end, loc, seniority)
                st.success("Updated."); st.rerun()
            _job_dirty = (employer != (job["employer"] or "") or role != (job["role"] or "") or
                         start != (job["start_date"] or "") or end != (job["end_date"] or "") or
                         loc != (job["location"] or "") or seniority != _cur_sen)
            if _job_dirty:
                b[0].caption("⚠ Unsaved — press Enter alone doesn't save these fields.")
            if b[1].button("Delete job (and its tasks)", key=f"deljob{job['id']}"):
                store.delete_job(job["id"])
                st.session_state.setdefault("open_jobs", set()).discard(job["id"])
                st.rerun()

            st.divider()

            # --- tasks, grouped by tag ---
            if tasks:
                if True:
                    for t in tasks:
                        cols = st.columns([5, 1.2, 0.6])
                        new_text = cols[0].text_area("task", value=t["text"],
                                                     key=f"task{t['id']}", label_visibility="collapsed",
                                                     height=68)
                        if not new_text.strip():
                            cols[0].caption("⚠ Can't be empty — use ✕ to delete instead.")
                        elif new_text.strip() != t["text"]:
                            st.session_state.setdefault("open_jobs", set()).add(job["id"])
                            store.update_task(t["id"], new_text.strip()); st.rerun()
                        _cur_grp = str(t["group_id"]) if ("group_id" in t.keys() and t["group_id"] is not None) else ""
                        new_grp = cols[1].text_input("group", value=_cur_grp,
                                                     key=f"grp{t['id']}", label_visibility="collapsed",
                                                     placeholder="group",
                                                     help="Type the same group name on 2+ tasks to mark "
                                                          "them as ONE accomplishment the tailor may "
                                                          "compose into a single bullet. Leave empty = "
                                                          "standalone.")
                        if new_grp.strip() != _cur_grp:
                            st.session_state.setdefault("open_jobs", set()).add(job["id"])
                            store.set_task_group_label(t["id"], new_grp); st.rerun()
                        if cols[2].button("✕", key=f"deltask{t['id']}"):
                            st.session_state.setdefault("open_jobs", set()).add(job["id"])
                            store.delete_task(t["id"]); st.rerun()

            # --- add tasks, scoped to THIS job ---
            with st.form(f"addtask{job['id']}", clear_on_submit=True):
                new_tasks = st.text_area("Add accomplishments", key=f"newtask{job['id']}",
                    help="Each line becomes its own accomplishment. Hit Enter between them.")
                new_grp = st.text_input("Group for these (optional — same group name = one accomplishment)", key=f"newgrp{job['id']}")
                if st.form_submit_button("Add") and new_tasks.strip():
                    st.session_state.setdefault("open_jobs", set()).add(job["id"])
                    for ln in [x.strip() for x in new_tasks.split("\n") if x.strip()]:
                        _tid = store.add_task(job["id"], ln)
                        if new_grp.strip():
                            store.set_task_group_label(_tid, new_grp)
                    st.rerun()

            _coach_widget(job)
            _braindump_widget(job["id"], "profile_")

    with st.form("add_job", clear_on_submit=True):
        st.write("Add a job")
        c = st.columns(5)
        employer = c[0].text_input("Employer"); role = c[1].text_input("Role")
        start = c[2].text_input("Start"); end = c[3].text_input("End")
        location = c[4].text_input("Location")
        if st.form_submit_button("Add job") and employer:
            store.add_job(employer, role, start, end, location); st.rerun()


# ================= Tailor (work one job, in order) =================
with tailor_tab:
    style_controls()
    st.divider()

    active_id = st.session_state.get("active_app")

    # ----- No active job: paste a new one -----
    if not active_id:
        _just_applied = st.session_state.pop("just_applied", None)
        if _just_applied:
            st.success(f"Marked as applied — {_just_applied}. Find it anytime in the "
                       f"Applications tab. Ready for the next one.")
        st.subheader("Work a new job")
        st.caption("Paste a job, analyze your fit first, then decide whether to tailor or pass.")
        with st.form("new_job", clear_on_submit=True):
            c = st.columns(2)
            company = c[0].text_input("Company")
            title = c[1].text_input("Role title")
            url = st.text_input("Job posting URL (optional)")
            ad = st.text_area("Paste the job ad", height=220)
            go = st.form_submit_button("Analyze fit")
        if go and ad.strip():
            app_id = store.add_application(company=company, title=title, ad_text=ad, url=url)
            with st.spinner("Analyzing your fit for this job..."):
                _run_analysis(app_id, ad)
            st.session_state["active_app"] = app_id
            st.rerun()

    # ----- Active job: the linear workflow -----
    else:
        a = _get_app(active_id)
        if a is None:
            st.session_state.pop("active_app", None)
            st.rerun()

        top = st.columns([4, 1])
        top[0].subheader(f"{a['company'] or 'Untitled'} — {a['title'] or ''}")
        if top[1].button("Work a different job"):
            st.session_state.pop("active_app", None)
            st.rerun()

        # Step 1 — fit
        st.markdown("### 1. Fit")
        if a["match_score"] is not None:
            st.metric("Match score", f"{a['match_score']} / 100")
            with st.expander("What does this score mean?"):
                st.caption("A rough rule of thumb, not a gate — the score reflects keyword and "
                           "experience overlap, and a low one can mean 'wrong function entirely' "
                           "or just 'missing a few keywords'. Read it alongside the real gaps below, "
                           "which tell you WHICH kind it is.")
                st.markdown(
                    "- **Under 40** — usually skip, unless you have a specific reason to reach.\n"
                    "- **40s–60s** — apply if you want it and can address the gaps head-on "
                    "(cover letter, direct experience you can point to).\n"
                    "- **65+** — strong match; the overlap is real."
                )
            matched, missing, gaps = (_parse_list(a["matched"]),
                                      _parse_list(a["missing"]), _parse_list(a["gaps"]))
            if matched:
                with st.expander(f"Keywords you already hit ({len(matched)})"):
                    st.markdown(", ".join(md_safe(m) for m in matched))
            if gaps:
                st.markdown("**Real gaps to consider:**")
                for g in gaps:
                    if isinstance(g, dict):
                        st.markdown(f"- {md_safe(g.get('gap', ''))}")
                        if g.get("ad_quote"):
                            st.caption(f"↳ ad says: \u201c{md_safe(g['ad_quote'])}\u201d")
                    else:
                        # old-shape data from before this change — plain string, no quote yet
                        st.markdown(f"- {md_safe(g)}")
            if st.button("Re-analyze fit (after adding experience)"):
                with st.spinner("Re-analyzing..."):
                    if _run_analysis(a["id"], a["ad_text"]):
                        st.rerun()
        else:
            if st.button("Analyze fit"):
                with st.spinner("Analyzing..."):
                    if _run_analysis(a["id"], a["ad_text"]):
                        st.rerun()

        # Step 2 — add real experience for a gap
        st.markdown("### 2. Fill a real gap (optional)")
        with st.expander("Add real experience to your Task Bank"):
            st.caption("If a gap is something you've actually done, add it in your own true "
                       "words — don't just echo the keyword.")
            add_labels = {f"{j['employer']} — {j['role']}": j["id"] for j in store.list_jobs()}
            if add_labels:
                pick = st.selectbox("Add to which job?", list(add_labels.keys()), key="tailor_addjob")
                _braindump_widget(add_labels[pick], "tailor_")
            else:
                st.info("Add a job under Work History first.")

        # Step 3 — decide
        st.markdown("### 3. Decide")
        d = st.columns(2)
        if d[0].button("Tailor / Re-tailor resume", type="primary"):
            with st.spinner("Writing your tailored resume..."):
                result = tailor_resume(a["ad_text"])
                st.session_state.pop(f"audit{a['id']}", None)
                result, _trimmed = _split_trimmed(result)
                result = _sort_draft_text(result)
                if _trimmed:
                    result = result.rstrip() + "\n\n## Trimmed for length\n" + "\n".join(_trimmed)
                store.save_tailored_result(a["id"], result)
            st.session_state[f"edver{a['id']}"] = st.session_state.get(f"edver{a['id']}", 0) + 1
            st.rerun()
        if d[1].button("Not a fit — skip"):
            store.set_application_status(a["id"], "I passed")
            st.session_state.pop("active_app", None)
            st.rerun()

        # Step 4 — draft + downloads
        if a["generated"]:
            st.markdown("### 4. Review and edit your tailored resume")
            st.caption("Read every line before it becomes a PDF. Verify every number against "
                       "what actually happened. Job headings come straight from your profile and "
                       "aren't editable here — edit them under the Profile tab.")

            _resume_only, _trimmed = _split_trimmed(a["generated"])
            _edver = st.session_state.get(f"edver{a['id']}", 0)
            draft = _structured_draft_editor(a["id"], _resume_only, _edver)
            if _trimmed:
                with st.expander(f"✂ Trimmed for length ({len(_trimmed)}) — relevant bullets cut to fit the budget"):
                    st.caption("These were relevant but didn't fit your total-bullet budget. "
                               "Raise the budget under Writing style, or paste one back into the "
                               "draft above if it belongs.")
                    for t in _trimmed:
                        st.markdown("- " + md_safe(re.sub(r"^\[\[JOB:\d+\]\]\s*", "", t).lstrip("- ")))

            s = st.columns([1, 3])
            if s[0].button("Save edits"):
                store.save_tailored_result(a["id"], draft)
                st.session_state[f"saved{a['id']}"] = True
                st.rerun()
            if st.session_state.pop(f"saved{a['id']}", False):
                s[1].success("Saved.")
            def _norm_ws(t):
                # compare on content, not incidental blank lines: reassembly strips
                # whitespace the raw model draft had, so a raw != reassembled diff is
                # not a real edit. Collapse each line's trailing space + drop blank lines.
                return "\n".join(ln.rstrip() for ln in (t or "").split("\n") if ln.strip())
            if _norm_ws(draft) != _norm_ws(a["generated"]):
                s[1].caption("⚠ Unsaved edits — downloads below use what's in the box.")

            # --- P7: report which jobs were included vs silently skipped ---
            _inc_ids = {int(m) for m in re.findall(r"\[\[JOB:(\d+)\]\]", draft)}
            _jobs = store.list_jobs()
            _lbl = lambda j: f"{j['employer']} — {j['role']}" if j["role"] else j["employer"]
            _hid = lambda j: ("include_on_resume" in j.keys() and not j["include_on_resume"])
            _in = [_lbl(j) for j in _jobs if j["id"] in _inc_ids]
            _out = [_lbl(j) for j in _jobs if j["id"] not in _inc_ids and not _hid(j)]
            _off = [_lbl(j) for j in _jobs if j["id"] not in _inc_ids and _hid(j)]
            _bullets = lambda items: "\n".join("- " + md_safe(x) for x in items)
            if _in:
                st.caption("In this resume:")
                st.markdown(_bullets(_in))
            else:
                st.caption("In this resume: none")
            if _out:
                st.warning("Left out of this resume — if any belong here, they were skipped as "
                           "'not relevant', so check that's right:")
                st.markdown(_bullets(_out))
            if _off:
                st.caption("Hidden by you (not an error — toggle back on in Work History): "
                           + ", ".join(_off))

            with st.expander("🔎 Export audit — trace every claim back to the bank"):
                st.caption("One model call, on demand — traces each claim in the draft against "
                           "your task bank. Catches connotation drift and synonym swaps the "
                           "tailoring prompt's own rules can miss. Flags only, nothing changes "
                           "automatically.")
                if st.button("Run export audit", key=f"auditrun{a['id']}"):
                    with st.spinner("Tracing claims against your task bank..."):
                        try:
                            st.session_state[f"audit{a['id']}"] = export_audit(draft)
                        except Exception as e:
                            st.error(f"Audit failed: {e}")
                _audit_flags = st.session_state.get(f"audit{a['id']}", [])
                if _audit_flags:
                    for _f in _audit_flags:
                        st.warning(
                            f"**[{_f.get('issue_type', '?')}]** {md_safe(_dejob(_f.get('claim', '')))}\n\n"
                            f"{md_safe(_dejob(_f.get('note', '')))}\n\n"
                            f"Source task: {md_safe(_dejob(_f.get('source_task') or 'none found'))}"
                        )
                elif f"audit{a['id']}" in st.session_state:
                    st.success("No drift found — every claim traces back to the bank.")

            st.markdown("**Preview**")
            st.markdown(_preview(md_safe(draft)))

            fname = f"Resume - {a['company'] or 'role'} - {a['title'] or ''}".strip().replace("/", "-")
            docx_bytes, docx_err = _cached_docx(draft)
            pdf_bytes, pdf_err = _cached_pdf(draft)
            dl = st.columns(2)
            if docx_bytes is not None:
                dl[0].download_button("⬇ Word (.docx)", data=docx_bytes,
                                      file_name=fname + ".docx", mime=DOCX_MIME, key="dl_active")
            else:
                dl[0].error(f"Word export failed: {docx_err}")
            if pdf_bytes is not None:
                dl[1].download_button("⬇ PDF", data=pdf_bytes,
                                      file_name=fname + ".pdf", mime=PDF_MIME, key="pdf_active")
            else:
                dl[1].error(f"PDF export failed: {pdf_err}")
            if st.button("Mark as applied"):
                store.save_tailored_result(a["id"], draft)
                store.set_applied_snapshot(a["id"], draft)
                store.set_application_status(a["id"], "Applied")
                store.set_application_date(a["id"], datetime.date.today().isoformat())
                st.session_state[f"stver{a['id']}"] = st.session_state.get(f"stver{a['id']}", 0) + 1
                st.session_state[f"dtver{a['id']}"] = st.session_state.get(f"dtver{a['id']}", 0) + 1
                st.session_state["just_applied"] = f"{a['company'] or 'that role'} — {a['title'] or ''}"
                st.session_state.pop("active_app", None)
                st.rerun()

# ================= Applications (the tracker) =================
with apps_tab:
    st.subheader("Your applications")
    apps = store.list_applications()
    if not apps:
        st.info("No applications yet. Start one in the Tailor tab.")
    total = len(apps)
    for i, a in enumerate(apps):
        n = total - i
        score = f" · match {a['match_score']}" if a["match_score"] is not None else ""
        when = f" · applied {a['date_applied']}" if a["date_applied"] else ""
        header = f"#{n}  {a['company'] or '—'} — {a['title'] or ''}   [{a['status']}]{score}{when}"
        with st.expander(header):
            c = st.columns(2)
            idx = STATUSES.index(a["status"]) if a["status"] in STATUSES else 0
            _stver = st.session_state.get(f"stver{a['id']}", 0)
            new_status = c[0].selectbox("Status", STATUSES, index=idx, key=f"st{a['id']}_{_stver}")
            if new_status != a["status"]:
                store.set_application_status(a["id"], new_status)
                if new_status == "Applied" and not a["date_applied"]:
                    store.set_application_date(a["id"], datetime.date.today().isoformat())
                    st.session_state[f"dtver{a['id']}"] = st.session_state.get(f"dtver{a['id']}", 0) + 1
                st.rerun()

            _dtver = st.session_state.get(f"dtver{a['id']}", 0)
            new_date = c[1].date_input("Date applied", value=_parse_date(a["date_applied"]),
                                       format="YYYY-MM-DD", key=f"dt{a['id']}_{_dtver}")
            new_date_text = new_date.isoformat() if new_date else ""
            if new_date_text != (a["date_applied"] or ""):
                store.set_application_date(a["id"], new_date_text)
                st.rerun()

            with st.expander("Update company / title"):
                st.caption("For aggregators (Ladders, etc.) where the real employer only shows "
                           "up after you apply.")
                ec = st.columns(2)
                new_company = ec[0].text_input("Company", value=a["company"] or "",
                                                key=f"co{a['id']}")
                new_title = ec[1].text_input("Title", value=a["title"] or "",
                                              key=f"ti{a['id']}")
                if st.button("Save company / title", key=f"savect{a['id']}"):
                    if new_company != (a["company"] or ""):
                        store.set_application_company(a["id"], new_company)
                    if new_title != (a["title"] or ""):
                        store.set_application_title(a["id"], new_title)
                    st.rerun()

            if st.button("Open in Tailor tab", key=f"open{a['id']}"):
                st.session_state["active_app"] = a["id"]
                st.rerun()

            if a["ad_text"]:
                with st.expander("View the job ad"):
                    if a["url"]:
                        st.markdown(f"[Open original posting]({a['url']})")
                    st.text(a["ad_text"])

            _record = a["applied_snapshot"] or a["generated"]
            if a["applied_snapshot"]:
                st.caption("📌 Frozen at the moment you applied — this is what you actually sent, "
                           "even if the draft has changed since.")
                with st.expander("What I actually applied with"):
                    st.text(a["applied_snapshot"])
            if _record:
                fname = f"Resume - {a['company'] or 'role'} - {a['title'] or ''}".strip().replace("/", "-")
                if not st.session_state.get(f"prep{a['id']}"):
                    if st.button("Prepare downloads", key=f"prepbtn{a['id']}"):
                        st.session_state[f"prep{a['id']}"] = True
                        st.rerun()
                else:
                    docx_bytes, docx_err = _cached_docx(_record)
                    pdf_bytes, pdf_err = _cached_pdf(_record)
                    dl = st.columns(2)
                    if docx_bytes is not None:
                        dl[0].download_button("⬇ Word", data=docx_bytes,
                                              file_name=f"{fname}.docx", key=f"dx{a['id']}")
                    else:
                        dl[0].error(f"Word export failed: {docx_err}")
                    if pdf_bytes is not None:
                        dl[1].download_button("⬇ PDF", data=pdf_bytes,
                                              file_name=f"{fname}.pdf", key=f"pf{a['id']}")
                    else:
                        dl[1].error(f"PDF export failed: {pdf_err}")

            notes = st.text_area("Notes", value=a["notes"] or "", key=f"nt{a['id']}")
            if st.button("Save notes", key=f"sn{a['id']}"):
                store.set_application_notes(a["id"], notes); st.success("Saved.")

            if st.button("Delete", key=f"da{a['id']}"):
                store.delete_application(a["id"]); st.rerun()