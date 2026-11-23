"""Lodestone's cross-class ranking (NIGHT_TASKS 38): the search's scores can't be compared across weapon kinds (its
error is per skill, x0.41 Rapid Shot to x1.83 Bonestorm vs full builds), so for each weapon type the search
shortlists its best TOP skill + ascendancy pairs (any class may use the weapon: picking a weapon lifts the class
lock), and the finalists are ranked by full Uber Endgame builds. The answer to "what is the strongest build in the
game", with every weapon given a fair chance. Weekly (server free time or the PC). Resumable.

  python tools/weapon_finalists.py run [--only Bow,Staff] [--top 2] [--workers 6] [--out data/breaker/finalists.json]
  python tools/weapon_finalists.py report data/breaker/finalists.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "data" / "breaker" / "finalists.json"
WEAPONS = ["Bow", "Crossbow", "Spear", "Quarterstaff", "Staff", "Wand", "Sceptre", "Talisman", "One Hand Mace",
           "Two Hand Mace", "Claw", "Dagger", "One Hand Sword", "Two Hand Sword", "One Hand Axe", "Two Hand Axe", "Flail"]


def run(only: set[str] | None, top: int, workers: int, out: Path) -> None:
    from generate import generate, plan_build
    from guide import build_stage
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"weapons": {}}
    for w in WEAPONS:
        if only and w not in only:
            continue
        rec = done["weapons"].setdefault(w, {"finalists": {}})
        if "search" not in rec:
            t0 = time.time()
            try:
                # PoB has no "Quarterstaff" type: it's a Staff with the Warstaff subtype. Search Staff, keep one kind.
                pob_w = "Staff" if w == "Quarterstaff" else w
                res = generate({"weapons": [pob_w], "_class_unlocked": True}, workers=workers, log=lambda *a: None)
                rows, seen = [], set()
                for r in res["ranked"]:
                    if pob_w == "Staff" and (r.get("weapon_subtype") == "Warstaff") != (w == "Quarterstaff"):
                        continue
                    key = (r["skill"], r["ascendancy"])
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)
                    if len(rows) >= top:
                        break
                rec["search"] = [{"skill": r["skill"], "ascendancy": r["ascendancy"], "score": round(r["score"]),
                                  "spec": plan_build(res, ascendancy=r["ascendancy"], skill=r["skill"])["spec"]}
                                 for r in rows]
            except Exception as e:  # noqa: BLE001
                rec["search"] = []
                rec["error"] = f"{type(e).__name__}: {e}"
            rec["search_seconds"] = round(time.time() - t0)
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"{w}: search {rec['search_seconds']}s -> {[(r['skill'], r['ascendancy']) for r in rec['search']]}"
                  f"{' ' + rec['error'] if rec.get('error') else ''}", flush=True)
        for f in rec["search"]:
            key = f"{f['skill']} | {f['ascendancy']}"
            if key in rec["finalists"]:
                continue
            t0 = time.time()
            try:
                g = build_stage(f["spec"], "end")
                rec["finalists"][key] = {"boss_dps": round(g.boss_dps), "dps": round(g.dps), "code": g.code,
                                         "seconds": round(time.time() - t0)}
            except Exception as e:  # noqa: BLE001
                rec["finalists"][key] = {"error": f"{type(e).__name__}: {e}"}
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  {key}: {rec['finalists'][key].get('boss_dps') or rec['finalists'][key].get('error')}", flush=True)
    print(report(done), flush=True)


def report(d: dict) -> str:
    rows = []
    for w, rec in d["weapons"].items():
        for key, f in rec.get("finalists", {}).items():
            if f.get("boss_dps"):
                rows.append((f["boss_dps"], f["dps"], w, key))
    rows.sort(reverse=True)
    out = ["Cross-class ranking: each weapon type's best search finalists as full Uber Endgame builds (boss DPS, map DPS):"]
    for i, (b, m, w, key) in enumerate(rows, 1):
        out.append(f"  {i:>2}. {key:<44} {w:<15} boss {b:>12,}  map {m:>12,}")
    return "\n".join(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(set(a[a.index("--only") + 1].split(",")) if "--only" in a else None,
            int(a[a.index("--top") + 1]) if "--top" in a else 2,
            int(a[a.index("--workers") + 1]) if "--workers" in a else 4,
            Path(a[a.index("--out") + 1]) if "--out" in a else OUT)
    elif a and a[0] == "report":
        print(report(json.loads(Path(a[1] if len(a) > 1 else OUT).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
