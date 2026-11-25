"""Task 42: how much does a full Uber Endgame build depend on the order choices are made in?

The same spec is built with the gear slots crafted in different orders (as is, reversed, rotated by two, armour and jewellery each) and nothing
else changed. The spread between them is optimiser luck: a lead smaller than that isn't a finding.

  python tools/path_luck.py run [--workers 3] --finalists data/breaker/finalists_offhand.json --extra data/breaker/finalists.json --out data/breaker/path_luck.json
  python tools/path_luck.py report data/breaker/path_luck.json
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
PICKS = [("Bow", "Rain of Arrows"), ("Bow", "Ice Shot"), ("Staff", "Bonestorm"), ("Crossbow", "Rapid Shot")]
ORDERS = ("as is", "reversed", "rotated")


def build(spec: dict, order: str, stage: str = "end") -> dict:
    import gear
    for d in (gear.ARMOUR_SLOTS, gear.JEWELLERY_SLOTS):
        items = list(d.items())
        items = {"as is": items, "reversed": items[::-1], "rotated": items[2:] + items[:2]}[order]
        d.clear()
        d.update(items)
    from guide import build_stage
    t0 = time.time()
    g = build_stage(spec, stage)
    return {"boss_dps": round(g.boss_dps), "dps": round(g.dps), "code": g.code, "sources": g.sources, "boss_sources": g.boss_sources,
            "seconds": round(time.time() - t0),
            "supports": g.supports, "notes": g.notes}


def best_of(spec: dict, orders: int = 3, stage: str = "end", workers: int = 1) -> dict:
    """The spec built in several slot orders, each in its own process (an order changes module state): the best boss
    damage, plus {"orders": {order: boss dps or error}}. All failed: RuntimeError."""
    got = {}
    with ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn"), max_tasks_per_child=1) as pool:
        jobs = {o: pool.submit(build, spec, o, stage) for o in ORDERS[:orders]}
        for o, j in jobs.items():
            try:
                got[o] = j.result()
            except Exception as e:  # noqa: BLE001
                got[o] = {"error": f"{type(e).__name__}: {e}"}
    ok = [r for r in got.values() if r.get("boss_dps")]
    if not ok:
        raise RuntimeError("; ".join(r.get("error", "no boss dps") for r in got.values()))
    return {**max(ok, key=lambda r: r["boss_dps"]), "seconds": sum(r["seconds"] for r in ok),
            "orders": {o: r.get("boss_dps") or r.get("error") for o, r in got.items()}}


def run(workers: int, files: list[Path], out: Path) -> None:
    specs: dict[str, dict] = {}
    for f in files:
        for w, rec in json.loads(f.read_text(encoding="utf-8"))["weapons"].items():
            for r in rec.get("search") or []:
                if (w, r["skill"]) in PICKS:
                    specs.setdefault(f"{w}: {r['skill']}", r["spec"])
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    with ProcessPoolExecutor(workers, max_tasks_per_child=1) as pool:
        jobs = {pool.submit(build, s, o): (k, o) for o in ORDERS for k, s in specs.items() if o not in done.get(k, {})}
        for j in as_completed(jobs):
            k, o = jobs[j]
            try:
                done.setdefault(k, {})[o] = j.result()
            except Exception as e:  # noqa: BLE001
                done.setdefault(k, {})[o] = {"error": f"{type(e).__name__}: {e}"}
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
            print(k, o, done[k][o].get("boss_dps"), done[k][o].get("error", ""), flush=True)
    print(report(done), flush=True)


def report(d: dict) -> str:
    lines = []
    for k, r in d.items():
        v = {o: x["boss_dps"] for o, x in r.items() if x.get("boss_dps")}
        if v:
            lines.append(f"{k:<24} {max(v.values()) / min(v.values()) - 1:+6.0%} spread  " + ", ".join(f"{o} {x:,}" for o, x in v.items()))
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(int(a[a.index("--workers") + 1]) if "--workers" in a else 3,
            [Path(a[a.index(x) + 1]) for x in ("--finalists", "--extra") if x in a], Path(a[a.index("--out") + 1]))
    elif a and a[0] == "report":
        print(report(json.loads(Path(a[1]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
