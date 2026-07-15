# tracker.py — show everything in your job tracker.
import store

apps = store.list_applications()
if not apps:
    print("No applications tracked yet.")
for a in apps:
    applied = f" — applied {a['date_applied']}" if a['date_applied'] else ""
    saved = " — tailored resume saved" if a['generated'] else ""
    print(f"#{a['id']}  {a['company']} — {a['title']}  [{a['status']}]{applied}{saved}")