"""Does the search's ranking survive full builds? (task 35)

For each ascendancy in a blind-test result (data/breaker/blind*.json), the search's top N skills (one row per skill)
are built as full guides at one stage (Uber Endgame by default) and re-ranked by boss DPS. Reports, per ascendancy,
the search's order vs the full-build order and how much the search's #1 gives away. Resumable.

  python tools/rank_check.py run data/breaker/blind_2026-11-21.5.json --only Deadeye,Lich,Titan --top 3 \
      [--stage end] [--out data/breaker/rank_check.json]
  python tools/rank_check.py report data/breaker/rank_check.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "data" / "breaker" / "rank_check.json"


def run(blind: Path, only: set[str] | None, top: int, stage: str, out: Path) -> None:
    from guide import build_stage
    d = json.loads(blind.read_text(encoding="utf-8"))
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"stage": stage, "ascendancies": {}}
    for asc, rec in d["ascendancies"].items():
        if only and asc not in only:
            continue
        rows, seen = [], set()
        for r in rec.get("ranked") or []:
            if r["skill"] not in seen:
                seen.add(r["skill"])
                rows.append(r)
            if len(rows) >= top:
                break
        res = done["ascendancies"].setdefault(asc, {"class": rec["class"], "skills": {}})
        for i, r in enumerate(rows, 1):
            if r["skill"] in res["skills"]:
                continue
            spec = {"name": f"{r['skill']} {asc}", "class": rec["class"], "ascendancy": asc, "skill": r["skill"],
                    "weapon_type": r["weapon_type"], "weapon_subtype": r.get("weapon_subtype"), "support_slots": 5}
            t0 = time.time()
            try:
                g = build_stage(spec, stage)
                res["skills"][r["skill"]] = {"search_rank": i, "search_score": r["score"], "boss_dps": round(g.boss_dps),
                                             "dps": round(g.dps), "seconds": round(time.time() - t0)}
            except Exception as e:  # noqa: BLE001
                res["skills"][r["skill"]] = {"search_rank": i, "error": f"{type(e).__name__}: {e}"}
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"{asc} #{i} {r['skill']}: {res['skills'][r['skill']].get('boss_dps') or res['skills'][r['skill']].get('error')}", flush=True)
    print(report(done), flush=True)


def report(d: dict) -> str:
    lines = [f"Search order vs full builds ({d.get('stage')} stage, boss DPS):"]
    flips = n = 0
    for asc, rec in d["ascendancies"].items():
        sk = {k: v for k, v in rec["skills"].items() if v.get("boss_dps")}
        if len(sk) < 2:
            continue
        n += 1
        by_search = sorted(sk, key=lambda k: sk[k]["search_rank"])
        by_full = sorted(sk, key=lambda k: -sk[k]["boss_dps"])
        lost = 1 - sk[by_search[0]]["boss_dps"] / sk[by_full[0]]["boss_dps"]
        flips += by_search[0] != by_full[0]
        lines.append(f"  {asc:<22} search: {' > '.join(by_search)} | full: {' > '.join(by_full)}"
                     + (f"  (search's #1 gives away {lost:.0%})" if lost > 0 else "  (same #1)"))
    lines.insert(1, f"  The search's #1 is the best full build in {n - flips} of {n} ascendancies.")
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(Path(a[1]), set(a[a.index("--only") + 1].split(",")) if "--only" in a else None,
            int(a[a.index("--top") + 1]) if "--top" in a else 3, a[a.index("--stage") + 1] if "--stage" in a else "end",
            Path(a[a.index("--out") + 1]) if "--out" in a else OUT)
    elif a and a[0] == "report":
        print(report(json.loads(Path(a[1] if len(a) > 1 else OUT).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
