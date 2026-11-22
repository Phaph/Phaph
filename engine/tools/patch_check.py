"""Patch-notes practice: grade a changes file against PoB's real update.

  PATCH_FILE=data/patches/0_5_1.json POB_VENDOR=<old PoB> python tools/patch_check.py dump --file data/patches/0_5_1.json --out a.json
  POB_VENDOR=<new PoB> python tools/patch_check.py dump --file data/patches/0_5_1.json --out b.json
  python tools/patch_check.py compare a.json b.json
Each gem in the file: its supported skill types, constant stats, crit / cooldown / damage multiplier at levels 1 and
20, in the patched old game (a) and the real new one (b). Same = we read that note line the way PoB did.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))


def dump(file: str, out: str) -> None:
    from pob import PoB
    keys = [c.get("id") or c.get("gem") for c in json.loads(Path(file).read_text(encoding="utf-8"))["changes"]
            if c.get("id") or c.get("gem")]
    with PoB() as p:
        d = p.send("gem_dump", keys=keys)["gems"]
        Path(out).write_text(json.dumps({"version": p.version, "patched": p.patched, "gems": d}, indent=1), encoding="utf-8")


def compare(a: str, b: str) -> str:
    A, B = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    lines = [f"Patched PoB {A['version']} ({len(A['patched'])} changes applied) vs real PoB {B['version']}:"]
    same = 0
    for k in A["gems"]:
        ga, gb = A["gems"][k], B["gems"].get(k)
        if not gb:
            lines.append(f"  {k}: not in the new PoB")
            continue
        diffs = [f for f in ("require", "constant", "crit", "cooldown", "base_multiplier") if ga.get(f) != gb.get(f)]
        if diffs:
            lines.append(f"  DIFF {k}: " + "; ".join(f"{f}: ours {ga.get(f)} vs PoB {gb.get(f)}" for f in diffs))
        else:
            same += 1
            lines.append(f"  same {k}")
    lines.insert(1, f"  {same} of {len(A['gems'])} gems match exactly")
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "dump":
        dump(a[a.index("--file") + 1], a[a.index("--out") + 1])
    elif a and a[0] == "compare":
        print(compare(a[1], a[2]))
    else:
        print(__doc__)
