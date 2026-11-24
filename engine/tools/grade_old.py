"""Grade the old-patch scans against data/breaker/answer_key.json, by the key's own rules (default thresholds, no tuning).

  python tools/grade_old.py        prints found / missed per case, and how many rows each scan flags

False alarms need a person: a flagged piece counts as real if the next major patch's notes cut it. Until those are read
(old/verdicts.json: {"<tag>": {"<piece>": true/false}}), flagged pieces are "unjudged", not false alarms.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
B = ENGINE / "data" / "breaker"


def flagged(tag: str, det: str) -> list[tuple[str, str, float]] | None:
    """[(piece, skill or condition, gain)] best first, or None when the scan hasn't finished."""
    f = B / "old" / f"{tag}_{det}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    # Both scans cover the same skills: a scan with fewer than the condition scan's is still running.
    cond = json.loads((B / "old" / f"{tag}_condition.json").read_text(encoding="utf-8"))["skills"]
    log = Path.home() / "old_patch.log"
    finished = log.exists() and f"{tag} {det} done" in log.read_text()
    if not finished or len(d["skills"]) < len(cond):
        return None
    if det == "condition":
        from condition_scan import payoffs
        return [(n, c, v) for n, c, v, _ in payoffs(d)]
    from matrix_scan import outliers
    # an outlier row is (skill, "kind:piece", gain, above usual): either name may be a case's hit piece
    return [(a if not str(a).split(":")[0] in ("unique", "keystone") else a.split(":", 1)[1], b, v)
            for a, b, v, _ in outliers(d)]


def main() -> None:
    key = json.loads((B / "answer_key.json").read_text(encoding="utf-8"))
    vf = B / "old" / "verdicts.json"
    verdicts = json.loads(vf.read_text(encoding="utf-8")) if vf.exists() else {}
    found = graded = 0
    for c in key["cases"]:
        rows = flagged(c["tag"], c["detector"])
        if rows is None:
            print(f"  {c['id']:<5} {c['name']:<40} not scanned yet")
            continue
        graded += 1
        hit = next(((i, r) for i, r in enumerate(rows, 1)
                    if any(h == str(x).split(":", 1)[-1] for h in c["hit"] for x in r[:2])), None)
        found += bool(hit)
        print(f"  {c['id']:<5} {c['name']:<40} " + (f"FOUND, row {hit[0]} of {len(rows)} ({hit[1][0]} / {hit[1][1]} +{hit[1][2]:.0%})"
              if hit else f"missed ({len(rows)} rows flagged)") + ("" if c.get("blind", True) else "  [not blind]"))
    print(f"found {found} of {graded} graded ({len(key['cases'])} cases)")
    for tag in sorted({c["tag"] for c in key["cases"]}):
        for det in ("condition", "matrix"):
            rows = flagged(tag, det)
            if rows is not None:
                pieces = {r[0] for r in rows}
                v = verdicts.get(tag, {})
                if det == "condition":
                    from condition_scan import payoffs
                    d = json.loads((B / "old" / f"{tag}_condition.json").read_text(encoding="utf-8"))
                    print(f"  {tag} strict (+60% above usual): {sorted({n for n, c, g, above in payoffs(d) if above >= 0.6})}")
                print(f"  {tag} {det}: {len(rows)} rows, {len(pieces)} pieces: {sum(v.get(p) is True for p in pieces)} real, "
                      f"{sum(v.get(p) is False for p in pieces)} false alarms, {sum(p not in v for p in pieces)} unjudged")


if __name__ == "__main__":
    main()
