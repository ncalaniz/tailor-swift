# Tailor Swift — To-Do

## CONTEXT FOR A NEW CHAT (paste this file to bring Claude up to speed)
**What this is:** Tailor Swift — a local Streamlit app I built that tailors my resume to job ads
using the Claude API, tracks applications, and exports PDF/Word. Repo (public):
https://github.com/ncalaniz/tailor-swift — Claude can read files via
`https://raw.githubusercontent.com/ncalaniz/tailor-swift/main/FILENAME.py` if I paste that URL.

**Who I am / how to work with me:** Nick, Atlanta. Career: ops/RevOps leadership (StubHub,
ZipRecruiter). This is my FIRST software project — started with barely any Python, ~8-12 hrs of
build time so far spread over weeks. I know SQL at a "pull data and build dashboards" level, not
deep. Windows, VS Code, PowerShell, venv at `.venv`, run with `streamlit run app.py` or the
"Tailor Swift" desktop shortcut (start.bat).

**How I want you to talk to me:** Concise and direct. No compliments, praise, or encouragement.
Don't restate my reasoning back to me. Skip preamble — just give the answer. DO keep plain
explanations of new concepts (I'm learning), stated once without build-up. BE EXPLICIT about
exactly what to change and where (search for X, replace these N lines with this) — vague
"update the handler" instructions cost us hours.

**Architecture (important):** `db.py` (SQLite schema) / `store.py` (data-access layer, the ONLY
file touching SQL) / `ai.py` (Claude API wrapper) / `tailor.py` (prompts: tailoring, match
analysis, brain-dump parsing) / `export.py` (PDF via fpdf2 + Word via python-docx) / `app.py`
(all Streamlit UI, 4 tabs: Tailor, Applications, Profile, Setup) / `migrate.py` (one-off ALTER
TABLE migrations) / helpers: seed.py, tracker.py, debug.py / `.streamlit/config.toml` (theme).

**Core design principle — non-negotiable:** FACTS come from the database, PROSE comes from the
model. Employers/titles/dates/education are stored data and rendered by export.py; the model
only writes bullet text and picks which real tasks are relevant. It emits `[[JOB:id]]` tags,
never company names. Honesty guardrails in every prompt: rephrase only what's real, never
invent or inflate. The review-before-save step exists because *I* am the final honesty check.

---

Active work at the top, full checkbox history at the bottom. :3

## ▶ NEXT UP — Group 2 remainder: B (intake overhaul + retire base resume) — ~1.5-2 hrs
- B. Onboarding + RETIRE the base resume. Three parts:
  (1) INTAKE: first-run user pastes/uploads resume -> model parses into contact, jobs, tasks,
      education -> user reviews/confirms -> saved into structured stores.
  (2) RETIREMENT: once structured data exists, the base-resume section disappears from the UI.
  (3) CORRECTNESS: build_candidate_profile() still sends the stale base-resume blob to the model
      on every tailor — stop; rely on structured data only. Replace its one remaining job
      (professional identity framing) with an editable "Professional summary" field in Setup,
      seeded at intake. This IS the new-user experience — required before sharing.
  (B2 is DONE — see checkbox history. B reuses its "messy text -> structured, reviewed" pattern
  at full-resume scale instead of one job's brain-dump.)
- Personal motivation: my bank holds a small slice of my career; B2 already helps with this —
  B extends the same ease to full onboarding.

## THEN — Group 3: Application workflow polish — ~1.5-2 hrs
- [x] H. DONE — clean display numbers: newest application at TOP with the HIGHEST number
      (list stays ORDER BY id DESC; numbering counts down via `total = len(apps)` +
      `n = total - i`). Oldest = #1 forever, at the bottom. Real db ids still used for all ops.
- F. Edit the tailored draft before downloading (text area pre-filled + save) — fix wording,
  cut fluff, VERIFY every number before it becomes a PDF. ~30 min.
- G. Cover letter generator (one button, same stored data; esp. for stretch roles — address
  gaps honestly instead of disguising them). ~45 min.
- I. Date-applied tracking (store fn + st.date_input; auto-fill today when status -> "Applied").
  ~20-30 min.

## THEN — PRIORITY: USE IT. Apply to a run of real jobs.
Not a coding task. Real usage decides everything below. While using: read every number/claim
before sending — the tool drafts, I verify. (Called out once already for building instead of
applying; Group 3 ends, applications begin.)

## THEN — README + send to first friend (as a PAIR, ~30-45 min) + N-v1 feedback button
Rule: write the README the day before sending the first friend the link. It documents the
CONTRACT (install/run), not the code. Contents: what it is, clone, venv,
`pip install -r requirements.txt`, own Anthropic API key in `.env` (exact line format),
`streamlit run app.py`, data stays local, AI costs pennies on their own key.
N-v1 (~5 min, same day): `st.link_button("🐞 Report a bug / request a feature",
"https://github.com/ncalaniz/tailor-swift/issues/new")` — GitHub Issues gives threading,
image-paste, zero attachment risk. Repo: https://github.com/ncalaniz/tailor-swift

## BACKLOG — pull as real usage demands
- C-revisited. Task tags with PURPOSE (column + inline boxes already exist, unused). Tags =
  SKILL THEMES (leadership, analytics/reporting, vendor management, process/PMO,
  compensation/incentives, access/IAM, cost savings, team development). Point: the bank becomes
  an INVENTORY — see instantly whether a theme an ad wants is deep or thin. Build: in-UI
  tagging guidance, suggested-tags dropdown-with-add, sort/filter/group; maybe analysis shows
  ad's themes vs. bank coverage. ~45-60 min. After real usage clarifies taxonomy.
- L. "Earlier career" brief-mention mode. ~45 min. Detail last 10-15 yrs; older-but-relevant
  jobs render as ONE line ("Earlier career: Project Manager, [Telecom Co], 2008-2011"), no
  bullets. Per-job flag or age cutoff + prompt awareness + compact render path. (Telecom PM
  into the archive; Uber year excluded — 1-yr gap 15 yrs back is a non-issue.)
- E8. Mirror layout upgrades in Word (.docx) so both formats match. ~20 min.
- D. Steadier + self-explaining match score (temperature, reason line). ~30 min.
  Reminder: MISSING/GAPS list is the real signal, not the number.
- K-big. Full UI reorganization — deferred until a RUN of real applications shows which
  features I touch constantly vs. rarely. What sparked it: app layout reflects build order,
  not usage (four instances already fixed/specced: opened-on-Setup, WorkHistory/TaskBank split,
  lingering base resume, "Which job?" dropdown). Revisit: which tabs earn their place, what's
  the true home screen.
- N-v2. In-app email feedback form — ONLY if non-GitHub users appear. Security design: images
  ONLY, validated + re-encoded via PIL; never arbitrary attachments (renamed files + my inbox
  = me as the attack surface). Needs an email service; real work.

## LAST — M. Monetization experiment (for the EXPERIENCE, not the expected outcome)
Signal ladder — ratchet investment up only when the previous rung's signal is REAL:
Rung 1 — SELF: use it through my job hunt. Signal: it materially helped. Cost: paid.
Rung 2 — FRIENDS (3-5): README + link, own API keys. Signal: still using it UNPROMPTED in
  week 3; ask what they'd miss if it vanished. Cost: README + support.
Rung 3 — STRANGERS: post free/open-source (r/jobs, HN Show). Signal: installs, issues filed,
  feature asks, anyone says "I'd pay for hosted." Cost: polish + a weekend.
Rung 4 — PAID TEST: only if strangers pull. Smallest paid thing (hosted, waitlist + price).
  Signal: anyone pays. Requires the big build (hosting, accounts, per-user data, payments,
  margin over API costs) and the rename (Tailor Swift dies at commercialization).
Positioning if it gets there: NOT "AI resume writer #400" — honest architecture: facts from
the DB (can't hallucinate employers/dates), career-long task bank, gap-detection that surfaces
forgotten real experience, analyze-first triage. "The tool that never lies on your resume and
remembers your whole career." Story: built it job hunting, it got me hired, friends wouldn't
give it back. Rule: no rung-skipping.

## SHARING PLAN (decided; GitHub DONE)
- Repo live: https://github.com/ncalaniz/tailor-swift (.env/app.db/.venv correctly excluded).
- Friends clone + bring their OWN API key + own local db. I do NOT host or share my key.
- Git rhythm after each session: `git add .` -> `git commit -m "what changed"` -> `git push`.
- Claude can read repo files if I paste the direct file URL in chat.
- Optional cleanup: job_ad.txt is in the repo (harmless; can remove).

---
# ✅ DONE — in the order I did it :3
- [x] Set up the dev environment: Python, VS Code, venv, pip, first script
- [x] Designed the database schema; built db.py (SQLite, 4 tables, FK cascades)
- [x] Built store.py — the data-access layer (parameterized queries)
- [x] Got an API key, secured it in .env + .gitignore; first Claude call from ai.py
- [x] Built tailor.py — the tailoring engine with the honesty system prompt
- [x] Application tracker: add/list/status/notes/delete + tailored results saved
- [x] Built the Streamlit interface (app.py) with warm theme; learned the rerun model
- [x] Desktop shortcut (start.bat) to launch with a double-click
- [x] Editable work history (update_job + expander UI)
- [x] Word (.docx) download via python-docx
- [x] PDF download via fpdf2 (after the Word-license discovery — PDF is better for applying anyway)
- [x] Setup tab: contact details + writing-style controls; tailor reads style from settings
- [x] Contact header stamped on exports; killed stray "---" lines
- [x] Caching added to exports (later removed — see below)
- [x] Keyword match score + gap check (the interview-getter) — and it caught real experience
      I was underselling (change mgmt, C-suite, IAM)
- [x] View the job ad from each application
- [x] Job posting URL: first migration (ALTER TABLE), field + clickable link
- [x] Quick-add real experience to the Task Bank from the analysis screen
- [x] Quick-add splits on newlines — one line = one task
- [x] Big reorg (A1/A2): Tailor + Applications split; analyze-first linear flow;
      "Not a fit — skip" -> Passed status; style moved next to tailoring
- [x] Removed @st.cache_data from exports (the stale-PDF trap)
- [x] Fixed "Open in Tailor tab" two-click bug (st.rerun after session_state)
- [x] PDF: fixed mid-word breaks + contact cutoff (root cause: multi_cell cursor —
      new_x=LMARGIN everywhere)
- [x] E1: job dates in headings; rebuilt headings to come from the DB via [[JOB:id]] tags —
      the model can't touch facts (employers/titles/dates)
- [x] E1b: preview renders tags as readable headings
- [x] E2: education stored (with format guidance for double majors)
- [x] E3: Education section rendered in PDF + Word
- [x] E6: section headers with horizontal rules (Summary / Experience / Education)
- [x] E4: dates right-aligned on the heading line (measured cells)
- [x] E5: job locations — migration, UI field, italic right-aligned render
- [x] E7: reverse-chronological job order GUARANTEED at export (collect-sort-draw) +
      long-title collision guard
- [x] Git installed; .gitignore verified; repo pushed public — github.com/ncalaniz/tailor-swift
- [x] K: dynamic tab order — returning users land on Tailor; new users get Setup + hint
- [x] J: renamed to Tailor Swift 🧵 — "Please Hire Me" -> "Please Hire Nick"
- [x] A3: merged Work History + Task Bank — per-job expanders with task counts, scoped
      add box, "Which job?" dropdown eliminated, Task Bank tab dissolved
- [x] B2: brain-dump -> multiple polished tasks, with review-before-save. Hardest bug hunt
      yet (3 sessions): root cause was a plain st.button silently misbehaving inside st.form
      (buttons can't nest in forms); the "clear this box after save" fix was made bulletproof
      via KEY-VERSIONING (new widget key each time) instead of fighting session_state timing.
      Confirmed the honesty guardrail holds even against absurd test input.
- [x] H: application display numbers — newest on top with the highest number, oldest = #1

---
## Handy reminders (hard-won)
- Run the app from ONE place at a time. Nuclear reset: `taskkill /F /IM python.exe`, relaunch.
- Debug by testing the function in plain Python to isolate code vs. stale app.
- A colon line (`if`/`with`/`for`/`def`) ALWAYS needs an indented line under it.
- Existing-database changes = a migration (ALTER TABLE), run once. Keep migration scripts.
- After installs or edits to imported files: full restart.
- Function return-shape changes: update the function AND every caller in the same edit.
- Adding an OPTIONAL parameter (tag="") is the safe kind of change — old callers keep working.
- "None" on screen = a function fell through without a `return`.
- Text input -> variable -> must be PASSED into the store call, or it's never saved.
- After pasting new code, Ctrl+F for a distinctive string from it to confirm it landed.
- `st.button` CANNOT live inside `st.form` — only `st.form_submit_button` can. Weird/inconsistent
  button behavior inside a form block = check for this first.
- To reliably clear a widget's value, don't fight session_state timing — give the widget a NEW
  key (e.g. a counter suffix). A widget with a fresh key has no memory of old state, guaranteed.
- When behavior doesn't match the code you're reading, PUSH TO GITHUB and have Claude read the
  actual file via the raw.githubusercontent.com URL — faster than repeated screenshots, and
  proves whether editor/disk/repo actually agree.

**Where I left off:** A3, B2, and H done and pushed. Currently working Group 3 — next up is
**I** (date-applied tracking), then F (edit draft before download), then G (cover letters).
Then B (the big intake overhaul), then actually applying to jobs.
