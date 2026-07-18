# tailor.py — pulls your real experience + a job ad, sends to Claude, returns tailored bullets.
import store
from ai import ask_claude
import json

def build_system():
    """Assemble the editor instructions from your saved style settings."""
    tone    = store.get_setting("style_tone", "Professional")
    length  = store.get_setting("style_length", "Medium")
    maxb     = store.get_setting("style_max_bullets", "4")
    metrics = store.get_setting("style_metrics", "yes") == "yes"
    custom  = store.get_setting("style_custom", "")

    rules = (
        "You are an expert resume editor. Using ONLY the candidate's real base resume and "
        "logged tasks, write tailored resume content for the job ad. You may reword, reorder, "
        "and emphasize real experience to match the ad's language, but NEVER invent employers, "
        "titles, dates, metrics, or skills the candidate does not have.\n\n"
        "PRESERVE ATTRIBUTION — as important as not inventing facts. Keep who did the work "
        "exactly as the source states it. If the source says the candidate's team did something, "
        "the bullet must say so ('Led the team that...', 'Through my team...') — never promote "
        "team work to first-person individual work. If the source says the candidate was a "
        "member of or contributor to something, never upgrade that to founder, owner, or sole "
        "leader. Never add adverbs the source does not support ('directly', 'personally', "
        "'single-handedly', 'hands-on'). Never add qualifiers that change what a number means "
        "(if the source says 'quarterly spend', do not write 'quarterly comp spend'). Never "
        "escalate a verb's strength: 'project managed', 'supported', 'contributed to', or "
        "'helped' must not become 'owned', 'led', 'drove', or 'built'. Keep the source's own "
        "words for roles and people — if the source says 'rep', write 'rep', never 'agent'. "
        "When in doubt about who did something or what a number counts, use the weaker "
        "claim.\n\n"
        f"STYLE: tone = {tone}; bullet length = {length}; up to {maxb} bullets per job. "
        "Start every bullet with a strong action verb. "
    )
    if metrics:
        rules += "Lead with quantified results (numbers, %, $) whenever the real task supports it. "
    if custom:
        rules += f"Extra instructions: {custom} "
    rules += (
        "\n\nSUMMARY RULES: the summary is the only prose not anchored to a specific logged "
        "task, so it is where false claims hide. Every factual claim in it — years of "
        "experience, industries, company stage, scale, scope — must be derivable from the "
        "candidate's stored jobs and tasks. Do NOT state a total years-of-experience number. "
        "Do NOT claim industry or company-stage experience (e.g. 'high-growth SaaS', "
        "'enterprise', 'startup') unless the logged data shows it. No unfalsifiable filler: "
        "never write 'proven track record', 'results-driven', 'seasoned', 'passionate about', "
        "'demonstrated ability', 'track record of success', 'brings a history of', 'a history "
        "of'. The rules above apply here too: no "
        "puffery adverbs in the summary ('hands-on', 'directly', 'personally', 'seasoned'), no "
        "verb escalation, keep the source's own vocabulary. Back every claim with a LOGGED TASK "
        "specifically — the base resume text is unverified legacy and does NOT count as backing; "
        "if a phrase appears only there and in no logged task, cut it. If a claim cannot be "
        "checked against a logged task, cut it."
        "\n\nOUTPUT: Markdown only — no '---' lines, no commentary. Start with a 2-3 line "
        "'## Summary'. Then, for each relevant job, output a line containing ONLY that job's "
        "tag exactly as given (e.g. '[[JOB:3]]') on its own line, followed by that job's "
        "bullets starting with '- '. Output jobs in reverse-chronological order — most recent "
        "first — regardless of relevance. Do NOT write company names, job titles, or dates "
        "yourself — only the [[JOB:id]] tag and the bullets. Skip jobs not relevant to this ad."
    )
    return rules

def build_candidate_profile():
    """Assemble the stored resume + work history + tasks into one text block."""
    lines = ["WORK HISTORY AND TASKS (real experience only):"]
    for job in store.list_jobs():
        lines.append(f"\n[[JOB:{job['id']}]] {job['employer']} — {job['role']}")
        for task in store.list_tasks(job["id"]):
            lines.append(f"- {task['text']}")
    return "\n".join(lines)

def tailor_resume(job_ad):
    prompt = f"JOB AD:\n{job_ad}\n\n{build_candidate_profile()}"
    return ask_claude(prompt, system=build_system(), model="claude-sonnet-4-6", max_tokens=1500)

ANALYZE_SYS = (
    "You are a precise resume-matching analyst. Compare the candidate's real resume and logged "
    "tasks to the job ad. Respond with ONLY valid JSON — no code fences, no commentary — in exactly "
    'this shape: {"score": <integer 0-100>, "matched": [<skills/keywords from the ad the candidate '
    'genuinely demonstrates>], "missing": [<important requirements in the ad NOT evidenced in the '
    'resume>], "gaps": [<short honest notes on real gaps>]}. '
    'Do not pad "matched" with things the resume does not actually show.'
)

def analyze_match(job_ad):
    """Compare the candidate to a job ad; return a dict with score, matched, missing, gaps."""
    prompt = f"JOB AD:\n{job_ad}\n\n{build_candidate_profile()}"
    raw = ask_claude(prompt, system=ANALYZE_SYS, model="claude-sonnet-4-6", max_tokens=800)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()   # strip any fences
    return json.loads(clean)   # turn the JSON text into a Python dict

BRAINDUMP_SYS = (
    "You turn a person's messy, plain-English description of work they did into clean, separate "
    "resume task entries. STRICT HONESTY: only rephrase what they actually wrote — never inflate, "
    "never invent metrics, employers, or skills they didn't state. "
    "PRESERVE ATTRIBUTION: keep who did the work exactly as stated. If they say their team did "
    "something, the entry must say so ('Led the team that...') — never rewrite team work as "
    "their own hands-on work. If they say they were a member or contributor, never upgrade it "
    "to founder or owner. Never add adverbs they didn't use ('directly', 'personally', "
    "'hands-on'). When unsure who did something, use the weaker claim. "
    "Split distinct accomplishments "
    "into separate entries. Start each with a strong action verb. Keep any numbers they gave "
    "exactly as given. Respond with ONLY a valid JSON array of strings, no fences, no commentary. "
    'Example: ["Centralized identity and access management for operations, consolidating '
    'permissioning under a single owned function", "Built a Jira workflow for structured '
    'access-change requests"]'
)

def braindump_to_tasks(dump_text):
    """Turn a messy description into a list of clean task strings."""
    raw = ask_claude(dump_text, system=BRAINDUMP_SYS, model="claude-sonnet-4-6", max_tokens=1000)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)
    if not isinstance(result, list):
        raise ValueError("Expected a list of tasks")
    return [str(t).strip() for t in result if str(t).strip()]