# seed.py — run ONCE to put your real experience into the database.
import store

store.set_setting("base_resume",
    "Nick Alaniz, OPERATIONS EXECUTIVE | WORKFORCE STRATEGY | VENDOR GOVERNANCE | BUSINESS TRANSFORMATION, Workforce, Performance, and Revenue Operations leader specializing in scaling global support organizations through data-driven decision making, performance management systems, and operational design. Proven track record of reducing costs, improving service levels, and building accountability frameworks across in-house and BPO environments.")

job_id = store.add_job("StubHub", "Director Of Operations", "2023", "present")
store.add_task(job_id, "Led workforce strategy, performance management, and compliance across 3,000+ employees and 14 international sites")
store.add_task(job_id, "Increased service levels from ~60% to ~90% within 6 months by redesigning workforce planning, queue management, and performance accountability systems")
store.add_task(job_id, "Maintained flat fixed costs while supporting ~50%+ increase in order volume through headcount optimization and vendor strategy")

print("Seeded. Jobs now in the database:")
for j in store.list_jobs():
    print(f"  [{j['id']}] {j['employer']} — {j['role']}")