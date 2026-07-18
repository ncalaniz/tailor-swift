# lint.py — deterministic integrity checks on the task bank. No API calls, no prose.
# The counterpart to "facts come from the DB": something that asks whether the DB is any good.
# It only INSPECTS and FLAGS — it never edits. I stay the honesty check.
import re
import datetime
import store

# Tier-1 catches only what regex/logic can prove. Semantic stuff (near-duplicates,
# contradictory numbers, vocabulary drift) is tier 2 — a model call — and lives elsewhere.

PLACEHOLDERS = ["xxx", "tbd", "???", "[insert]", "lorem", "fixme", "placeholder"]

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _label(job):
    """A human-readable name for a job row."""
    emp = (job["employer"] or "").strip() or "Untitled"
    role = (job["role"] or "").strip()
    return f"{emp} — {role}" if role else emp


def _parse_month_year(text):
    """Tolerant parse of a free-text date. Returns a comparable (year, month) tuple,
    or None if it can't be parsed. Dates are intentionally free text, so unparseable
    means STAY SILENT — never nag about a format that's allowed."""
    if not text:
        return None
    t = text.strip().lower()
    if t in ("present", "current", "now"):
        return (9999, 12)          # sorts after any real date
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{4})$", t)   # "Jan 2019", "September 2020"
    if m and m.group(1) in _MONTHS:
        return (int(m.group(2)), _MONTHS[m.group(1)])
    m = re.match(r"(\d{4})$", t)                          # bare year "2019"
    if m:
        return (int(m.group(1)), 1)
    return None                                          # unparseable -> silent


def _has_placeholder(text):
    low = text.lower()
    return any(p in low for p in PLACEHOLDERS)


def check_bank():
    """Return a list of (severity, message) tuples. severity is 'warn' or 'info'.
    Empty list means the bank passed every deterministic check."""
    flags = []
    jobs = store.list_jobs()

    # --- per-task checks: placeholders, empty rows, exact-duplicate text ---
    seen = {}   # normalized task text -> label where first seen
    for job in jobs:
        label = _label(job)
        for t in store.list_tasks(job["id"]):
            text = (t["text"] or "").strip()
            if not text:
                flags.append(("warn", f"{label}: an empty task row — delete it or fill it in."))
                continue
            if _has_placeholder(text):
                flags.append(("warn", f'{label}: placeholder text in a task — "{text[:60]}"'))
            key = text.lower()
            if key in seen:
                flags.append(("warn",
                              f'Duplicate task text in {seen[key]} and {label}: "{text[:60]}"'))
            else:
                seen[key] = label

    # --- per-job date checks ---
    now = (datetime.date.today().year, datetime.date.today().month)
    for job in jobs:
        label = _label(job)
        s = _parse_month_year(job["start_date"])
        e = _parse_month_year(job["end_date"])
        if s and e and e < s:
            flags.append(("warn", f"{label}: end date is before start date."))
        if s and s != (9999, 12) and s > now:
            flags.append(("warn", f"{label}: start date is in the future."))

    # --- overlapping roles at the SAME employer ---
    by_emp = {}
    for job in jobs:
        by_emp.setdefault((job["employer"] or "").strip().lower(), []).append(job)
    for group in by_emp.values():
        spans = []
        for j in group:
            s = _parse_month_year(j["start_date"])
            e = _parse_month_year(j["end_date"])
            if s and e:
                spans.append((s, e, j))
        for i in range(len(spans)):
            for k in range(i + 1, len(spans)):
                (s1, e1, j1), (s2, e2, j2) = spans[i], spans[k]
                if s1 <= e2 and s2 <= e1:               # the spans overlap
                    identical = (s1 == s2 and e1 == e2)
                    sev = "warn" if identical else "info"
                    extra = " (identical spans — almost certainly a typo)" if identical else ""
                    flags.append((sev,
                                  f"{j1['employer']}: '{j1['role']}' and '{j2['role']}' "
                                  f"overlap in time{extra}."))
    return flags