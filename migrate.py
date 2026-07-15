# migrate.py — one-time: add the 'location' column to the jobs table.
import store

conn = store.get_connection()
try:
    conn.execute("ALTER TABLE jobs ADD COLUMN location TEXT;")
    conn.commit()
    print("Added 'location' column to jobs.")
except Exception as e:
    print("Skipped (probably already added):", e)
conn.close()