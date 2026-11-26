"""Task 40: did the next patch cut a flagged skill? Same rule as the 0.1 verdicts (verdicts.json _how):
real = base damage at gem level 20 down 20%+ (attack multiplier or any spell part), or a constant multiplier cut
(printed, read by a person). Minion skills have no numbers of their own here: unjudged.

  python3 tools/old_skill_verdicts.py <tag> [skill ...]     default: the skills flagged by that tag's condition scan
"""
from __future__ import annotations

import re
import sys

from old_verdicts import NEXT, POB


def skills(tag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    hidden: dict[str, str] = {}
    for f in (POB / tag / "src" / "Data" / "Skills").glob("*.lua"):
        if f.name in ("spectre.lua", "minion.lua"):
            continue
        for b in re.split(r"(?m)^(?=skills\[)", f.read_text(encoding="utf-8")):
            m = re.match(r'skills\["\w+"\] = \{\s*name = "([^"]+)"', b)
            if m and "support = true" not in b[:400]:
                # hidden blocks are kept as a fallback: since 0.4 some player skills are hidden variants
                # (skills["SiegeCascadePlayer"]); a visible block of the same name wins
                if "hidden = true" not in b[:300]:
                    out[m.group(1)] = b
                else:
                    hidden.setdefault(m.group(1), b)
    return {**hidden, **out}


def numbers(block: str) -> tuple[dict[str, float], dict[str, float]]:
    """(damage at level 20 by stat set and stat, constant stats)"""
    dmg: dict[str, float] = {}
    head, *sets = re.split(r"\n\t\t\[\d+\] = \{\n\t\t\tlabel", block)
    m = re.search(r"\[20\] = \{[^\n]*?baseMultiplier = ([\d.]+)", head)
    if m:
        dmg["attack"] = float(m.group(1))
    const: dict[str, float] = {}
    for i, s in enumerate(sets):
        for k, v in re.findall(r'\{ "([^"]+)", (-?[\d.]+) \}', s):
            const[f"{i}:{k}"] = float(v)
        st, lv = re.search(r"\n\t\t\tstats = \{(.*?)\n\t\t\t\}", s, re.S), re.search(r"\[20\] = \{([^\n]*)", s)
        if not (st and lv):
            continue
        m = re.search(r"baseMultiplier = ([\d.]+)", lv.group(1))
        if m:
            dmg[f"{i}:attack"] = float(m.group(1))
        vals = [float(x) for x in re.findall(r"(-?[\d.]+)\s*,", re.split(r"\w+ = ", lv.group(1))[0])]
        for k, v in zip(re.findall(r'"([^"]+)"', st.group(1)), vals):
            (dmg if re.search(r"base_\w*damage", k) else const)[f"{i}:{k}"] = v
    return {k: v for k, v in dmg.items() if v}, const


def main() -> None:
    tag, names = sys.argv[1], sys.argv[2:]
    if not names:
        from grade_old import flagged
        names = sorted({r[0] for r in flagged(tag, "condition") or []})
    a, b = skills(tag), skills(NEXT[tag])
    for n in names:
        if n not in a or n not in b:
            print(f"{n}: not found ({'gone next patch' if n in a else 'not in this patch' if n in b else 'in neither'})")
            continue
        (da, ca), (db, cb) = numbers(a[n]), numbers(b[n])
        ratio = {k: round(db[k] / da[k], 2) for k in da if k in db}
        word = "unjudged" if not ratio else "CUT" if min(ratio.values()) <= 0.8 else "not cut"
        changed = {k: (ca[k], cb.get(k)) for k in ca if ca[k] != cb.get(k)}
        print(f"{n}: {word} {sorted(set(ratio.values()))}" + (f"  const {changed}" if changed else ""))


if __name__ == "__main__":
    main()
