# migrate.py — one-time: rename application status values to actor-clear names.
import store

conn = store.get_connection()
renames = {
    "Rejected": "Rejected by them",
    "Offer": "Offer received",
    "Ghosted": "No response",
    "Passed": "I passed",
}
try:
    for old, new in renames.items():
        conn.execute("UPDATE applications SET status = ? WHERE status = ?;", (new, old))
    conn.commit()
    print("Renamed status values:", renames)
except Exception as e:
    print("Migration failed:", e)
conn.close()