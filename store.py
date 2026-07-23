# store.py — the data-access layer. The ONLY file that talks to the database.
from db import get_connection   # reusing db.py — this is why we wrote that __main__ guard
import json

# --- tiny helpers so we don't repeat open/commit/close everywhere ---
def _write(query, params=()):
    """Run an INSERT/UPDATE/DELETE. Returns the new row's id (for inserts)."""
    conn = get_connection()
    cursor = conn.execute(query, params)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def _read(query, params=()):
    """Run a SELECT. Returns a list of rows."""
    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

# --- settings (base resume + style prefs live here as key/value) ---
def set_setting(key, value):
    _write(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
        (key, value),
    )

def get_setting(key, default=None):
    rows = _read("SELECT value FROM settings WHERE key = ?;", (key,))
    return rows[0]["value"] if rows else default

# --- work history ---
def add_job(employer, role="", start_date="", end_date="", location=""):
    return _write(
        "INSERT INTO jobs (employer, role, start_date, end_date, location) VALUES (?, ?, ?, ?, ?);",
        (employer, role, start_date, end_date, location),
    )

def list_jobs():
    return _read("SELECT * FROM jobs ORDER BY id;")

def delete_job(job_id):
    _write("DELETE FROM jobs WHERE id = ?;", (job_id,))

# --- task bank ---
def add_task(job_id, text, tag=""):
    return _write("INSERT INTO tasks (job_id, text, tag) VALUES (?, ?, ?);", (job_id, text, tag))

def set_task_tag(task_id, tag):
    _write("UPDATE tasks SET tag = ? WHERE id = ?;", (tag, task_id))

def update_task(task_id, text):
    _write("UPDATE tasks SET text = ? WHERE id = ?;", (text, task_id))

def set_task_group(task_ids, group_id):
    """Assign a set of tasks to a group (or pass group_id=None to ungroup them).
    A shared group_id means the tailor may compose these atoms into one bullet."""
    conn = get_connection()
    conn.executemany(
        "UPDATE tasks SET group_id = ? WHERE id = ?;",
        [(group_id, tid) for tid in task_ids],
    )
    conn.commit()
    conn.close()

def set_task_group_label(task_id, label):
    """Set or clear one task's group. Empty label = ungrouped. Tasks sharing a
    label are one sanctioned accomplishment. (Stored in group_id; SQLite doesn't
    enforce the INTEGER type, so text labels are fine.)"""
    _write("UPDATE tasks SET group_id = ? WHERE id = ?;",
           (label.strip() or None, task_id))

def next_group_id():
    """Return an unused group id (max existing + 1, starting at 1)."""
    rows = _read("SELECT MAX(group_id) AS m FROM tasks;")
    top = rows[0]["m"] if rows and rows[0]["m"] is not None else 0
    return top + 1

def list_task_groups(job_id):
    """Return {group_id: [task_row, ...]} for one job's GROUPED tasks only
    (ungrouped tasks are groups of one and handled separately by callers)."""
    groups = {}
    for t in _read("SELECT * FROM tasks WHERE job_id = ? AND group_id IS NOT NULL ORDER BY group_id, id;", (job_id,)):
        groups.setdefault(t["group_id"], []).append(t)
    return groups

def list_tasks(job_id=None):
    if job_id is None:
        return _read("SELECT * FROM tasks ORDER BY id;")
    return _read("SELECT * FROM tasks WHERE job_id = ? ORDER BY id;", (job_id,))

def delete_task(task_id):
    _write("DELETE FROM tasks WHERE id = ?;", (task_id,))

# --- applications (the job tracker) ---
def add_application(company, title, ad_text, status="Not applied",
                    date_applied="", got_response=0, notes="", url=""):
    return _write(
        "INSERT INTO applications "
        "(company, title, ad_text, status, date_applied, got_response, notes, url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (company, title, ad_text, status, date_applied, got_response, notes, url),
    )

def list_applications():
    return _read("SELECT * FROM applications ORDER BY id DESC;")

def set_application_status(app_id, status):
    _write("UPDATE applications SET status = ? WHERE id = ?;", (status, app_id))

def set_application_notes(app_id, notes):
    _write("UPDATE applications SET notes = ? WHERE id = ?;", (notes, app_id))

def set_application_company(app_id, company):
    _write("UPDATE applications SET company = ? WHERE id = ?;", (company, app_id))

def set_application_title(app_id, title):
    _write("UPDATE applications SET title = ? WHERE id = ?;", (title, app_id))

def set_application_date(app_id, date_applied):
    _write("UPDATE applications SET date_applied = ? WHERE id = ?;", (date_applied, app_id))    

def save_tailored_result(app_id, generated):
    _write("UPDATE applications SET generated = ? WHERE id = ?;", (generated, app_id))

def set_applied_snapshot(app_id, snapshot):
    """Freeze the resume text at the moment of applying. Never overwritten after."""
    _write("UPDATE applications SET applied_snapshot = ? WHERE id = ?;", (snapshot, app_id))

def delete_application(app_id):
    _write("DELETE FROM applications WHERE id = ?;", (app_id,))

def add_status_event(app_id, status, date=""):
    """Append one row to the status timeline. Empty date = dateless event."""
    return _write("INSERT INTO status_events (app_id, status, date) VALUES (?, ?, ?);",
                  (app_id, status, date or None))

def list_status_events(app_id):
    return _read("SELECT * FROM status_events WHERE app_id = ? ORDER BY id;", (app_id,))

def latest_event(app_id):
    rows = _read("SELECT * FROM status_events WHERE app_id = ? ORDER BY id DESC LIMIT 1;", (app_id,))
    return rows[0] if rows else None

def sync_applied_event_date(app_id, date):
    """Keep the 'Applied' timeline event in step when the user edits Date applied."""
    _write("UPDATE status_events SET date = ? WHERE app_id = ? AND status = 'Applied';",
           (date or None, app_id))

def update_job(job_id, employer, role, start_date, end_date, location="", seniority=""):
    _write(
        "UPDATE jobs SET employer = ?, role = ?, start_date = ?, end_date = ?, "
        "location = ?, seniority = ? WHERE id = ?;",
        (employer, role, start_date, end_date, location, seniority, job_id),
    )

def set_job_included(job_id, included):
    """Toggle whether a job appears on tailored resumes. Hidden jobs never enter
    the tailor's view at all — the model can't include what it can't see."""
    _write("UPDATE jobs SET include_on_resume = ? WHERE id = ?;",
           (1 if included else 0, job_id))

def save_analysis(app_id, score, matched, missing, gaps):
    _write(
        "UPDATE applications SET match_score = ?, matched = ?, missing = ?, gaps = ? WHERE id = ?;",
        (score, json.dumps(matched), json.dumps(missing), json.dumps(gaps), app_id),
    )

# --- quick self-test: runs only with `python store.py` ---
if __name__ == "__main__":
    set_setting("base_resume", "Jane Analyst — 6 years in BI and reporting...")
    print("Base resume saved, starts with:", get_setting("base_resume")[:28])

    job_id = add_job("Acme Corp", "Data Analyst", "2021", "2024")
    add_task(job_id, "Built the exec sales dashboard in SQL + Power BI")
    add_task(job_id, "Cut monthly close reporting time by 40%")

    print("Jobs:")
    for j in list_jobs():
        print(f"  [{j['id']}] {j['employer']} — {j['role']}")
    print("Tasks for that job:")
    for t in list_tasks(job_id):
        print(f"  [{t['id']}] {t['text']}")

    delete_job(job_id)   # FK cascade should delete its tasks too
    print("Remaining tasks after deleting the job:", len(list_tasks()))