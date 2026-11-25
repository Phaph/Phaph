"""Cross-class reading of the per-ascendancy condition scans (task 37): what does one ascendancy do for a skill that the others don't?

For each skill (scanned on every ascendancy, any weapon): ascendancies whose damage, or gain from a condition, stands
out from the median ascendancy. Scores are search-style, so each row is a question for a full build, not a finding.
Only complete scans should be read; a skill needs results on at least MIN_ASC ascendancies.

  python tools/asc_read.py data/breaker/conditions_asc [--top 30] [--skip Infernalist,Titan]
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

MIN_ASC = 5
MIN_DPS = 20_000   # weaker rows (a spectre at 2 dps) give huge ratios that mean nothing


def load(folder: Path, skip: set[str] = frozenset()) -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8"))["skills"] for f in sorted(folder.glob("*.json"))
            if f.stem not in skip}


def outliers(scans: dict[str, dict], min_asc: int = MIN_ASC) -> tuple[list[tuple], list[tuple]]:
    """([(ratio, skill, ascendancy, dps, median)], [(extra gain, skill, condition, ascendancy, gain, median gain)])."""
    base, gains = [], []
    for skill in sorted({s for d in scans.values() for s in d}):
        rows = {a: d[skill] for a, d in scans.items() if skill in d and not d[skill].get("error") and d[skill].get("dps")}
        if len(rows) < min_asc:
            continue
        med = statistics.median(r["dps"] for r in rows.values())
        base += [(r["dps"] / med, skill, a, r["dps"], med) for a, r in rows.items() if r["dps"] >= MIN_DPS]
        for cond in {c for r in rows.values() for c in r["gains"]}:
            g = {a: r["gains"].get(cond, 0.0) for a, r in rows.items()}   # gains lists only what changes something
            m = statistics.median(g.values())
            gains += [(x - m, skill, cond, a, x, m) for a, x in g.items() if rows[a]["dps"] >= MIN_DPS]
    return sorted(base, reverse=True), sorted(gains, reverse=True)


def report(scans: dict[str, dict], top: int = 30, min_asc: int = MIN_ASC) -> str:
    base, gains = outliers(scans, min_asc)
    lines = [f"{len(scans)} ascendancies: {', '.join(scans)}", "", "Damage vs the median ascendancy, same skill:"]
    lines += [f"  x{r:5.2f}  {s:<26} {a:<22} {d:>10,.0f} (median {m:,.0f})" for r, s, a, d, m in base[:top]]
    lines += ["", "Gain from a condition vs the median ascendancy:"]
    lines += [f"  {x:+5.0%}  {s:<26} {c:<26} {a:<22} {g:+.0%} (median {m:+.0%})" for x, s, c, a, g, m in gains[:top]]
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    else:
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        print(report(load(Path(a[0]), set(opt("--skip", "").split(","))), int(opt("--top", 30)), int(opt("--min", MIN_ASC))))
