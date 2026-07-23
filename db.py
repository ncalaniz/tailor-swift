# db.py — creates and connects to the SQLite database for the app.
import sqlite3

DB_FILE = "app.db"   # the whole database is this one file, in this folder

# Every statement uses IF NOT EXISTS, so running this repeatedly is harmless.
SCHEMA = """
-- Base resume + style preferences, stored as simple key/value rows.
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Work history. Each row is a job that tailored bullets get grouped under.
CREATE TABLE IF NOT EXISTS jobs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    employer   TEXT NOT NULL,
    role       TEXT,
    start_date TEXT,
    end_date   TEXT,
    location   TEXT,
    seniority  TEXT DEFAULT '',
    include_on_resume INTEGER DEFAULT 1   -- 0 = user hid this job from resumes
);

-- Accomplishment bank. Each task is tied to one job (its resume section).
CREATE TABLE IF NOT EXISTS tasks (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id   INTEGER NOT NULL,
    text     TEXT NOT NULL,
    tag      TEXT DEFAULT '',
    group_id TEXT DEFAULT NULL,   -- shared label = one sanctioned accomplishment
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Application tracker. One row per job ad you feed in.
CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company      TEXT,
    title        TEXT,
    ad_text      TEXT,
    status       TEXT DEFAULT 'Not applied',
    date_applied TEXT,
    got_response INTEGER DEFAULT 0,     -- SQLite has no boolean: 0 = no, 1 = yes
    notes        TEXT,
    match_score  INTEGER,
    matched      TEXT,                  -- JSON list stored as text
    missing      TEXT,
    gaps         TEXT,
    generated    TEXT,
    applied_snapshot TEXT,
    created_at   TEXT DEFAULT (date('now'))
);
"""

def get_connection():
    """Open a connection to the database file."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")   # SQLite ships with FKs OFF — turn them on
    conn.row_factory = sqlite3.Row              # read columns by name, like a dict
    return conn

def init_db():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

# This block runs only when you execute `python db.py` directly,
# not when another file imports db.py (which later stages will do).
if __name__ == "__main__":
    init_db()
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    ).fetchall()
    conn.close()
    print("Database ready:", DB_FILE)
    print("Tables created:", ", ".join(row["name"] for row in tables))