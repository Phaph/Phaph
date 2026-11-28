"""Compare two blind-test result files, top N per ascendancy (boss DPS).

python3 engine/tools/blind_diff.py OLD.json NEW.json [N]
Prints old vs new top N, and how often each skill / weapon is #1 in each file.
"""
import json
import sys
from collections import Counter


def load(path):
    return json.load(open(path))["ascendancies"]


def top(rows, n):
    return ", ".join(f"{r['skill']}/{r['weapon_type']} {r['boss'] / 1e6:.2f}M" for r in rows[:n])


def main():
    old, new = load(sys.argv[1]), load(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    firsts = {"old": Counter(), "new": Counter()}
    for asc, v in new.items():
        ro, rn = old.get(asc, {}).get("ranked", []), v["ranked"]
        print(asc)
        print("  old:", top(ro, n))
        print("  new:", top(rn, n))
        if ro:
            firsts["old"][ro[0]["skill"]] += 1
        if rn:
            firsts["new"][rn[0]["skill"]] += 1
    print(f"\n{len(new)} ascendancies in new; #1 old: {dict(firsts['old'])}; #1 new: {dict(firsts['new'])}")


if __name__ == "__main__":
    main()
