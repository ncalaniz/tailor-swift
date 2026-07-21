# migrate.py — one-time: add the per-job seniority column (item 5 / seniority-aware compression).
# Run once with: python migrate.py
import store

conn = store.get_connection()
try:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs);")}
    if "seniority" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN seniority TEXT DEFAULT '';")
        conn.commit()
        print("Added jobs.seniority column.")
    else:
        print("jobs.seniority already exists — nothing to do.")
except Exception as e:
    print("Migration failed:", e)
conn.close()