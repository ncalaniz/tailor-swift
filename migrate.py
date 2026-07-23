# migrate.py — one-off schema migrations for changes init_db() can't make.
# init_db() only CREATEs missing tables; it never ALTERs an existing one.
# Adding a column to a table that already has data is what this file is for.
# Every migration here is guarded so re-running the whole file is harmless.
from db import get_connection


def _column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r["name"] == column for r in rows)


def migrate():
    conn = get_connection()

    # --- SANCTIONED-GROUPING: tasks can belong to a group of sibling atoms ---
    # NULL group_id = ungrouped = a group of one. A shared integer = one
    # sanctioned accomplishment the tailor may compose within (never across).
    if not _column_exists(conn, "tasks", "group_id"):
        conn.execute("ALTER TABLE tasks ADD COLUMN group_id INTEGER DEFAULT NULL;")
        print("Added tasks.group_id")
    else:
        print("tasks.group_id already present — skipping")

    # --- JOB-TOGGLE: per-job "show on resumes" flag (1 = show, 0 = hide) ---
    if not _column_exists(conn, "jobs", "include_on_resume"):
        conn.execute("ALTER TABLE jobs ADD COLUMN include_on_resume INTEGER DEFAULT 1;")
        print("Added jobs.include_on_resume")
    else:
        print("jobs.include_on_resume already present — skipping")

# --- TRACKER-TABLE: status timeline + backfill ---
    have = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='status_events';").fetchall()
    if not have:
        conn.execute("""CREATE TABLE status_events (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            date   TEXT,
            FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE
        );""")
        # Backfill so no history is lost: every dated application seeds an 'Applied'
        # event; non-Applied current statuses seed a DATELESS event (we don't know
        # when the change happened — a wrong date is worse than no date).
        for a in conn.execute("SELECT id, status, date_applied FROM applications;").fetchall():
            if a["date_applied"]:
                conn.execute("INSERT INTO status_events (app_id, status, date) VALUES (?, 'Applied', ?);",
                             (a["id"], a["date_applied"]))
            if a["status"] and a["status"] not in ("Not applied", "Applied"):
                conn.execute("INSERT INTO status_events (app_id, status, date) VALUES (?, ?, NULL);",
                             (a["id"], a["status"]))
        print("Created status_events + backfilled from existing applications")
    else:
        print("status_events already present — skipping")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()