# migrate.py — one-time: add the 'applied_snapshot' column to the applications table.
import store

conn = store.get_connection()
try:
    conn.execute("ALTER TABLE applications ADD COLUMN applied_snapshot TEXT;")
    conn.commit()
    print("Added 'applied_snapshot' column to applications.")
except Exception as e:
    print("Skipped (probably already added):", e)
conn.close()