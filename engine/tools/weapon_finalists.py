"""Lodestone's cross-class ranking (NIGHT_TASKS 38): the search's scores can't be compared across weapon kinds (its
error is per skill, x0.41 Rapid Shot to x1.83 Bonestorm vs full builds), so for each weapon type the search
shortlists its best TOP skill + ascendancy pairs (any class may use the weapon: picking a weapon lifts the class
lock), and the finalists are ranked by full Uber Endgame builds. The answer to "what is the strongest build in the
game", with every weapon given a fair chance. Weekly (server free time or the PC). Resumable.

  python tools/weapon_finalists.py run [--only Bow,Staff] [--top 2] [--workers 6] [--builds 3] [--orders 3] [--out data/breaker/finalists.json]
  python tools/weapon_finalists.py report data/breaker/finalists.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tools"))
OUT = ENGINE / "data" / "breaker" / "finalists.json"
WEAPONS = ["Bow", "Crossbow", "Spear", "Quarterstaff", "Staff", "Wand", "Sceptre", "Talisman", "One Hand Mace",
           "Two Hand Mace", "Claw", "Dagger", "One Hand Sword", "Two Hand Sword", "One Hand Axe", "Two Hand Axe", "Flail"]


def run(only: set[str] | None, top: int, workers: int, out: Path, builds: int = 3, orders: int = 3) -> None:
    """Each weapon's search uses `workers` processes; its finalists' full builds (one process each, the slow part) go to
    a pool of `builds` and run beside the next weapon's search."""
    import multiprocessing as mp
    import threading
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
    from generate import generate, plan_build
    from path_luck import ORDERS, build as path_build
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"weapons": {}}
    lock = threading.Lock()

    def save():
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")

    def build(w, rec, key, spec):
        """The same spec in several gear slot orders, the best kept: one order is luck (task 42, up to x4 between them)."""
        with ProcessPoolExecutor(1, mp_context=mp.get_context("spawn"), max_tasks_per_child=1) as one:   # an order changes module state: its own process
            got = {}
            for o in ORDERS[:orders]:
                try:
                    got[o] = one.submit(path_build, spec, o).result()
                except Exception as e:  # noqa: BLE001
                    got[o] = {"error": f"{type(e).__name__}: {e}"}
        ok = [r for r in got.values() if r.get("boss_dps")]
        if ok:
            res = {**max(ok, key=lambda r: r["boss_dps"]), "orders": {o: r.get("boss_dps") or r["error"] for o, r in got.items()},
                   "seconds": sum(r["seconds"] for r in ok)}
        else:
            res = next(iter(got.values()))
        with lock:
            rec["finalists"][key] = res
            save()
        print(f"  {w}: {key}: {res.get('boss_dps') or res.get('error')} ({res.get('seconds', 0)}s)", flush=True)

    pool = ThreadPoolExecutor(max_workers=builds)
    for w in WEAPONS:
        if only and w not in only:
            continue
        with lock:
            rec = done["weapons"].setdefault(w, {"finalists": {}})
        if "search" not in rec:
            t0 = time.time()
            found: dict = {}   # into rec under the lock: a build may be saving `done` meanwhile
            try:
                # PoB has no "Quarterstaff" type: it's a Staff with the Warstaff subtype. Search Staff, keep one kind.
                pob_w = "Staff" if w == "Quarterstaff" else w
                req = {"weapons": [pob_w], "_class_unlocked": True}
                if w == "Quarterstaff":   # staff spells outscore every attack, so a plain Staff search ranked none
                    req["kinds"] = ["Attack"]
                res = generate(req, workers=workers, log=lambda *a: None)
                rows, seen = [], set()
                for r in res["ranked"]:
                    if pob_w == "Staff" and (r.get("weapon_subtype") == "Warstaff") != (w == "Quarterstaff"):
                        continue
                    if r.get("weapon_type") != pob_w:   # no skill uses this weapon: the search dropped the weapon (Claw)
                        continue
                    key = r["skill"]   # different skills (each on its best ascendancy): two Rapid Shots waste a build
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)
                    if len(rows) >= top:
                        break
                found["search"] = [{"skill": r["skill"], "ascendancy": r["ascendancy"], "score": round(r["score"]),
                                  "spec": plan_build(res, ascendancy=r["ascendancy"], skill=r["skill"])["spec"]}
                                 for r in rows]
            except Exception as e:  # noqa: BLE001
                found["search"] = []
                found["error"] = f"{type(e).__name__}: {e}"
            found["search_seconds"] = round(time.time() - t0)
            with lock:
                rec.update(found)
                save()
            print(f"{w}: search {rec['search_seconds']}s -> {[(r['skill'], r['ascendancy']) for r in rec['search']]}"
                  f"{' ' + rec['error'] if rec.get('error') else ''}", flush=True)
        for f in rec["search"]:
            key = f"{f['skill']} | {f['ascendancy']}"
            if key in rec["finalists"]:
                continue
            pool.submit(build, w, rec, key, f["spec"])
    pool.shutdown(wait=True)
    print(report(done), flush=True)


def report(d: dict) -> str:
    rows = []
    for w, rec in d["weapons"].items():
        for key, f in rec.get("finalists", {}).items():
            if f.get("boss_dps"):
                other = [x for x in f.get("boss_sources") or [] if x["name"] != key.split(" | ")[0]
                         and not x["name"].startswith("Best ") and x["share"] >= 0.1]
                v = [x for x in (f.get("orders") or {}).values() if isinstance(x, int)]
                luck = f"  best of {len(v)} orders, worst {min(v):,}" if v else "  ONE order: luck up to x4"
                rows.append((f["boss_dps"], f["dps"], w, luck,
                             key + "".join(f" [{x['name']} {x['share']:.0%}]" for x in other)))
    rows.sort(reverse=True)
    out = ["Cross-class ranking: each weapon type's best search finalists as full Uber Endgame builds (boss DPS, map DPS):"]
    for i, (b, m, w, luck, key) in enumerate(rows, 1):
        out.append(f"  {i:>2}. {key:<44} {w:<15} boss {b:>12,}  map {m:>12,}{luck}")
    return "\n".join(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(set(a[a.index("--only") + 1].split(",")) if "--only" in a else None,
            int(a[a.index("--top") + 1]) if "--top" in a else 2,
            int(a[a.index("--workers") + 1]) if "--workers" in a else 4,
            Path(a[a.index("--out") + 1]) if "--out" in a else OUT,
            int(a[a.index("--builds") + 1]) if "--builds" in a else 3,
            int(a[a.index("--orders") + 1]) if "--orders" in a else 3)
    elif a and a[0] == "report":
        print(report(json.loads(Path(a[1] if len(a) > 1 else OUT).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
