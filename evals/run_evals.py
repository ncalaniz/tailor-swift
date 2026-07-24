# run_evals.py — the regression suite. For every saved job ad: tailor a resume, then run the
# deterministic checks against the task bank. Run this after ANY prompt change.
#
#   python evals/run_evals.py              # tailor fresh drafts (costs API calls) and check them
#   python evals/run_evals.py --cached     # re-check the drafts from the last run (free, instant)
#
# Exit code is 0 when nothing RED was found, 1 otherwise — so it can gate a commit later.

import sys, os, glob, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # import the app

import store
import tailor
import checks

HERE = os.path.dirname(os.path.abspath(__file__))
ADS_DIR = os.path.join(HERE, "ads")
OUT_DIR = os.path.join(HERE, "drafts")

def _employer_vocab():
    """Employer, role and location names — real facts that live outside task text."""
    bits = []
    for j in store.list_jobs():
        bits += [j["employer"] or "", j["role"] or "", (j["location"] or "")]
    return " ".join(bits)

def main():
    cached = "--cached" in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)
    ads = sorted(glob.glob(os.path.join(ADS_DIR, "*.txt")))
    if not ads:
        print(f"No ads found in {ADS_DIR}. Run: python evals/freeze_ads.py")
        return 1

    tasks = checks.load_bank(store)
    vocab = _employer_vocab()
    print(f"Bank: {len(tasks)} tasks across {len(store.list_jobs())} jobs")
    print(f"Ads:  {len(ads)}   mode: {'cached drafts' if cached else 'fresh tailor calls'}\n")

    total_red = total_amber = 0
    for path in ads:
        name = os.path.splitext(os.path.basename(path))[0]
        ad_text = open(path, encoding="utf-8").read()
        draft_path = os.path.join(OUT_DIR, name + ".md")

        if cached:
            if not os.path.exists(draft_path):
                print(f"--- {name}: no cached draft, skipping (run without --cached first)")
                continue
            draft = open(draft_path, encoding="utf-8").read()
        else:
            t0 = time.time()
            draft = tailor.tailor_resume(ad_text)
            open(draft_path, "w", encoding="utf-8").write(draft)
            print(f"    (tailored {name} in {time.time() - t0:.0f}s)")

        findings = checks.run_all(draft, tasks, ad_text, extra_vocab=vocab)
        reds = [f for f in findings if f[0] == "RED"]
        ambers = [f for f in findings if f[0] == "AMBER"]
        total_red += len(reds)
        total_amber += len(ambers)

        print(f"--- {name}: {len(reds)} RED, {len(ambers)} AMBER")
        for sev, cls, msg, bullet in reds + ambers:
            print(f"    [{sev} {cls}] {msg}")
            print(f"        in: {bullet[:110]}")
        print()

    print("=" * 70)
    print(f"TOTAL: {total_red} RED, {total_amber} AMBER across {len(ads)} ads")
    print("Drafts saved in evals/drafts/ — re-check them anytime with --cached")
    return 1 if total_red else 0

if __name__ == "__main__":
    sys.exit(main())
