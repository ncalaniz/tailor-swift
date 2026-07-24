# test_checks.py — prove the checkers fire on the REAL failures from the 7/24 real-ad runs,
# and stay quiet on the drafts that were actually fine. Run: python test_checks.py
import checks

TASKS = [
    {"id": 1, "job_id": 1, "group": None,
     "text": "Led workforce management, performance management, and monitoring of agent adherence to internal policy across 3,000+ employees and 14 international sites."},
    {"id": 2, "job_id": 1, "group": None,
     "text": "Increased service levels from ~60% to ~90% within 6 months by redesigning workforce planning, queue management, and BPO partner accountability systems"},
    {"id": 3, "job_id": 1, "group": "SLAs",
     "text": "Maintained flat fixed costs while supporting ~50%+ increase in order volume through headcount optimization"},
    {"id": 4, "job_id": 1, "group": "SLAs",
     "text": "Delivered ~$240K+ in annualized cost savings across tooling, vendor allocation, and workforce restructuring"},
    {"id": 5, "job_id": 2, "group": None,
     "text": "Led implementation of the Xactly incentive management platform, migrating comp plans for 350 employees and $465M in quarterly spend from manual, error-prone worksheets."},
    {"id": 6, "job_id": 2, "group": None,
     "text": "Instituted PMO (Project Management Office), project management framework, and JIRA workflow to drive transformation within Revenue Operations with an emphasis on enforcing internal policy adherence across the team."},
]

AD = ("Operations Process Excellence Director. Deep knowledge of Opportunity-to-Cash processes. "
      "Experience with NetSuite and ServiceNow preferred. Own the O2C roadmap and KPI framework.")

CASES = [
    ("WELD of tasks 1+2 (NWN, real)", "blend",
     "[[JOB:1]]\n- Owned service-level and cost performance across 3,000+ employees and 14 international sites, increasing service levels from ~60% to ~90% within 6 months by redesigning workforce planning, queue management, and performance accountability systems"),
    ("VERB escalation Led->Owned (real)", "verb_escalation",
     "[[JOB:1]]\n- Owned workforce management, performance management, and monitoring of agent adherence to internal policy across 3,000+ employees and 14 international sites."),
    ("DROPPED qualifier 'internal' (real)", "dropped_qualifier",
     "[[JOB:2]]\n- Instituted PMO, project management framework, and Jira workflow to drive transformation within Revenue Operations with an emphasis on enforcing policy adherence across the team."),
    ("AD VOCAB in summary (real, NWN O2C)", "ad_vocab",
     "## Summary\n- Built and managed the O2C-adjacent process optimization roadmap at ZipRecruiter\n\n[[JOB:2]]\n- Led implementation of the Xactly incentive management platform, migrating comp plans for 350 employees and $465M in quarterly spend from manual, error-prone worksheets."),
    ("PERIOD drift quarterly->annual (proactive)", "period_drift",
     "[[JOB:2]]\n- Led implementation of the Xactly incentive management platform, migrating comp plans for 350 employees and $465M in annual spend from manual, error-prone worksheets."),
    ("HEDGE dropped ~$240K+ -> $240K (proactive)", "number_hedge",
     "[[JOB:1]]\n- Delivered $240K in annualized cost savings across tooling, vendor allocation, and workforce restructuring"),
    ("ENTITY swap Xactly->NetSuite (proactive)", "entity",
     "[[JOB:2]]\n- Led implementation of the NetSuite incentive management platform, migrating comp plans for 350 employees and $465M in quarterly spend from manual, error-prone worksheets."),
    ("CROSS-JOB leakage (proactive)", "cross_job",
     "[[JOB:1]]\n- Led implementation of the Xactly incentive management platform, migrating comp plans for 350 employees and $465M in quarterly spend from manual, error-prone worksheets."),
    ("UNBACKED bullet (real class)", "unbacked",
     "[[JOB:1]]\n- Designed and led the company's global transformation office across every business unit"),
]

# Regression cases: every false positive the live run produced becomes a permanent test.
FP_TASKS = TASKS + [
    {"id": 7, "job_id": 2, "group": None,
     "text": "Built and scaled reporting infrastructure for service levels, attrition, and agent performance, enabling data-driven decision-making across revenue leadership"},
    {"id": 11, "job_id": 1, "group": None,
     "text": "Built an AI-powered dashboard (Hex) that lets users input a transaction ID and get an automated summary of account activity, cutting investigation and documentation time from up to 3+ hours to approximately 5 minutes for complex cases."},
    {"id": 9, "job_id": 3, "group": None,
     "text": "Partnered with CRM team to design Salesforce solutions supporting the full customer journey, spanning new business, account management, retention, and reactivation."},
    {"id": 10, "job_id": 11, "group": None,
     "text": "Partnered with the management team on account-screening priorities and departmental objectives"},
    {"id": 8, "job_id": 2, "group": None,
     "text": "Key reporting point of contact with the Customer Success team responsible for providing insights and recommendations leveraging Sisense/SQL across six Customer Success divisions."},
]

CLEAN = [
    ("verbatim task, correct job", "[[JOB:1]]\n- Increased service levels from ~60% to ~90% within 6 months by redesigning workforce planning, queue management, and BPO partner accountability systems"),
    ("FP: 'Scale' when the bank says 'scaled' (live run 7/24)", "## Summary\n- Revenue and Customer Experience Operations at Scale\n\n[[JOB:2]]\n- Built and scaled reporting infrastructure for service levels, attrition, and agent performance, enabling data-driven decision-making across revenue leadership"),
    ("FP: 'Sisense' when the bank says 'Sisense/SQL' (live run 7/24)", "[[JOB:2]]\n- Key reporting point of contact with the Customer Success team responsible for providing insights and recommendations leveraging Sisense and SQL across six Customer Success divisions."),
    ("FP: generic-word overlap is not a blend (#29+#90, live run 7/24)", "[[JOB:3]]\n- Partnered with CRM team to design Salesforce solutions supporting the full customer journey, spanning new business, account management, retention, and reactivation."),
    ("FP: 'AI-powered' when the bank says it too (live run 7/24)", "[[JOB:1]]\n- Built an AI-powered dashboard (Hex) that lets users input a transaction ID and get an automated summary of account activity, cutting investigation and documentation time from up to 3+ hours to approximately 5 minutes for complex cases."),
    ("SANCTIONED group compose (tasks 3+4)", "[[JOB:1]]\n- Maintained flat fixed costs while supporting ~50%+ increase in order volume through headcount optimization, delivering ~$240K+ in annualized cost savings across tooling, vendor allocation, and workforce restructuring"),
]

def main():
    print("=" * 78)
    print("MUST FIRE")
    print("=" * 78)
    failed = 0
    for name, expect, draft in CASES:
        classes = {c for _, c, _, _ in checks.run_all(draft, TASKS, AD)}
        ok = expect in classes
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        print(f"      expected [{expect}]   got {sorted(classes) or 'nothing'}")

    print()
    print("=" * 78)
    print("MUST STAY QUIET")
    print("=" * 78)
    for name, draft in CLEAN:
        found = checks.run_all(draft, FP_TASKS, AD)
        ok = not found
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        for sev, cls, msg, _ in found:
            print(f"      false positive: [{cls}] {msg}")

    print()
    print(f"{'ALL GOOD' if not failed else str(failed) + ' PROBLEM(S)'}")

if __name__ == "__main__":
    main()
