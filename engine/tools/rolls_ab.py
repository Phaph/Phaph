"""Task 57: the same specs built for Uber Endgame with gear.TYPICAL_ROLLS off and on ("as is" slot order; --orders "as is,reversed,rotated" adds the other orders of task 42).
Answers: with a typical roll, do Mageblood / Megalomaniac stay in the build, and what do boss damage and EHP become?

  python tools/rolls_ab.py run --workers 2 --finalists data/breaker/finalists_offhand.json --extra data/breaker/finalists.json --out /s/rolls_ab.json
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tools"))
from path_luck import PICKS  # noqa: E402


def build(spec: dict, typical: bool, order: str = "as is") -> dict:
    import gear
    gear.TYPICAL_ROLLS = typical
    if order != "as is":   # task 42's slot orders, so a roll's effect can be told apart from path luck
        for d in (gear.ARMOUR_SLOTS, gear.JEWELLERY_SLOTS):
            items = list(d.items())
            items = {"reversed": items[::-1], "rotated": items[2:] + items[:2]}[order]
            d.clear()
            d.update(items)
    from guide import build_stage
    t0 = time.time()
    g = build_stage(spec, "end")
    worn = [p.unique for p in g.gear if p.unique]
    rolled = {p.unique: {"variants": p.variants, "hunt": p.hunt} for p in g.gear if p.unique and p.variants}
    return {"boss_dps": round(g.boss_dps), "dps": round(g.dps), "ehp": round((g.stats or {}).get("TotalEHP") or 0),
            "uniques": worn, "rolled": rolled, "seconds": round(time.time() - t0)}


def run(workers: int, files: list[Path], out: Path, orders: tuple[str, ...] = ("as is",)) -> None:
    specs: dict[str, dict] = {}
    for f in files:
        for w, rec in json.loads(f.read_text(encoding="utf-8"))["weapons"].items():
            for r in rec.get("search") or []:
                if (w, r["skill"]) in PICKS:
                    specs.setdefault(f"{w}: {r['skill']}", r["spec"])
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    with ProcessPoolExecutor(workers, max_tasks_per_child=1) as pool:
        modes = [(t, o, m if o == "as is" else f"{m} {o}") for t, m in ((False, "best"), (True, "typical")) for o in orders]
        jobs = {pool.submit(build, s, t, o): (k, m) for t, o, m in modes
                for k, s in specs.items() if m not in done.get(k, {})}
        for j in as_completed(jobs):
            k, m = jobs[j]
            try:
                done.setdefault(k, {})[m] = j.result()
            except Exception as e:  # noqa: BLE001
                done.setdefault(k, {})[m] = {"error": f"{type(e).__name__}: {e}"}
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
            r = done[k][m]
            print(k, m, r.get("boss_dps"), r.get("ehp"), [u for u in r.get("uniques", []) if u.split(",")[0] in ("Mageblood", "Megalomaniac")],
                  r.get("error", ""), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    run(int(a[a.index("--workers") + 1]) if "--workers" in a else 2,
        [Path(a[a.index(x) + 1]) for x in ("--finalists", "--extra") if x in a], Path(a[a.index("--out") + 1]),
        tuple(a[a.index("--orders") + 1].split(",")) if "--orders" in a else ("as is",))
