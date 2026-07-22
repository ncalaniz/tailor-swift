# list_tasks.py — read-only, shows task ids so we can pick two to group
import store
for j in store.list_jobs():
    if "stubhub" in (j["employer"] or "").lower():
        print(f"JOB {j['id']}: {j['employer']} — {j['role']}")
        for t in store.list_tasks(j["id"]):
            gid = t["group_id"] if "group_id" in t.keys() else None
            print(f"  [{t['id']}] (group={gid}) {t['text'][:90]}")