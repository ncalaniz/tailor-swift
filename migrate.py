# migrate.py — one-time: add the 'location' column to the jobs table.
import store

conn = store.get_connection()
try:
    conn.execute("ALTER TABLE tasks ADD COLUMN tag TEXT DEFAULT '';")
    conn.commit()
    print("Added 'tag' column to jobs.")
except Exception as e:
    print("Skipped (probably already added):", e)
conn.close()