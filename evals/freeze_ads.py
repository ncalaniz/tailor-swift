# freeze_ads.py — one-time: copy job ads out of the applications table into evals/ads/*.txt,
# so the eval suite runs off frozen files instead of live database state.
#
#   python evals/freeze_ads.py            # list what's available
#   python evals/freeze_ads.py 12 11 4    # freeze those application ids

import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import store

ADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads")

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "ad"

def main():
    ids = [int(a) for a in sys.argv[1:] if a.isdigit()]
    apps = store.list_applications()

    if not ids:
        print("Applications with ad text (pass the ids you want to freeze):\n")
        for a in apps:
            if (a["ad_text"] or "").strip():
                print(f"  {a['id']:>3}  {a['company']} — {a['title']}  ({len(a['ad_text'])} chars)")
        print("\nExample: python evals/freeze_ads.py 12 11 4")
        return

    os.makedirs(ADS_DIR, exist_ok=True)
    for a in apps:
        if a["id"] not in ids:
            continue
        if not (a["ad_text"] or "").strip():
            print(f"  #{a['id']} has no ad text — skipped")
            continue
        name = f"{slug(a['company'])}-{slug(a['title'])}.txt"
        path = os.path.join(ADS_DIR, name)
        open(path, "w", encoding="utf-8").write(a["ad_text"])
        print(f"  froze #{a['id']} -> evals/ads/{name}")

if __name__ == "__main__":
    main()
