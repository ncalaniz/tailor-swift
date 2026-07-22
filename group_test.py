# group_test.py — mark the five RBAC atoms as ONE sanctioned group, so the
# tailor may compose them into a single bullet. Idempotent-ish: re-running
# just re-stamps the same group id.
import store

RBAC_TASKS = [20, 21, 22, 24, 25]

gid = store.next_group_id()
store.set_task_group(RBAC_TASKS, gid)
print(f"Grouped tasks {RBAC_TASKS} as group {gid}")

# verify
for t in store.list_tasks():
    if t["id"] in RBAC_TASKS:
        print(f"  [{t['id']}] group={t['group_id']}  {t['text'][:70]}")