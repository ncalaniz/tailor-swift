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

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()