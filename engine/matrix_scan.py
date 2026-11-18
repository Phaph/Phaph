"""Unique x skill and keystone x skill matrix: which unique or keystone is far better on one skill than on the rest.

The pair scan (breaker.py pairs) tries every unique and keystone, but only on the ~31 saved builds' skills, and only the
30 best singles go into pairs. A unique that is ordinary on most skills and broken on one particular skill (a classic
broken-build shape, research/broken_builds.md group I) is invisible there. This scan builds every main-capable skill
the quick round-1 way and measures each non-weapon unique (top rolls) and each keystone on it alone, against a
pinnacle boss, reusing breaker.Bench. A gain far above what that piece usually gives is flagged: an interaction.

Weapon uniques are not in it yet: their local mods ("Adds X to Y") would apply globally through the custom modifier box.

  python matrix_scan.py run [--workers 6] [--out data/breaker/matrix.json]   (resumable)
  python matrix_scan.py report data/breaker/matrix.json
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "matrix.json"
KEEP = 0.05   # store gains of at least +5%


def run(workers: int, out: Path) -> None:
    import generate as g
    from breaker import Bench, pieces
    from gear import make_stage
    from pob import PoB, PoBError

    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        p.new()
        catalogue = pieces(p)
    skills = g.main_skills(catalog, {})
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"skills": {}}
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{len(skills)} skills x {len(catalogue)} uniques/keystones, {len(todo)} skills to go, {workers} workers",
          flush=True)
    stage = make_stage("end")
    lock = threading.Lock()

    def one(s):
        w, sub, off = (g.weapon_options(s, {}) or [(None, None, None)])[0]
        c = g.Candidate(s["name"], w, sub, off, g.DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else
                        "Spell" if "Spell" in s["types"] else "", "Mercenary"), is_minion="Minion" in s["types"],
                        totem=s.get("totem"))
        c = g.evaluate(c, stage, {}, tree=False)
        rec = {"weapon": g.weapon_key(w, sub), "error": c.error, "gains": {}}
        if not c.error:
            try:
                bench = Bench(g._pob())
                rec["dps"] = round(bench.base)
                if bench.base > 0:
                    for piece in catalogue:
                        try:
                            v = bench.gain([piece])
                        except PoBError:
                            continue
                        if v >= KEEP:
                            rec["gains"][f"{piece['kind']}:{piece['name']}"] = round(v, 3)
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        top = sorted(rec["gains"].items(), key=lambda kv: -kv[1])[:3]
        print(f"  {s['name']:<28} " + ", ".join(f"{k.split(':', 1)[1]} +{v:.0%}" for k, v in top), flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report(done), flush=True)


def outliers(d: dict, margin: float = 0.25, floor: float = 0.30) -> list[tuple[str, str, float, float]]:
    """(skill, piece, gain, gain above that piece's usual) where a piece helps one skill far more than it usually
    helps (median over every scanned skill, skills under +5% counting as no gain)."""
    n_ok = sum(1 for r in d["skills"].values() if not r.get("error"))
    by_piece: dict[str, list[float]] = {}
    for r in d["skills"].values():
        for k, v in (r.get("gains") or {}).items():
            by_piece.setdefault(k, []).append(v)
    usual = {}
    for k, vals in by_piece.items():
        vals = sorted(vals + [0.0] * max(n_ok - len(vals), 0))
        usual[k] = vals[len(vals) // 2]
    rows = [(n, k, v, v - usual[k]) for n, r in d["skills"].items() for k, v in (r.get("gains") or {}).items()
            if v >= floor and v - usual[k] >= margin]
    return sorted(rows, key=lambda x: -x[3])


def report(d: dict, top: int = 40) -> str:
    rows = outliers(d)
    out = [f"{len(d['skills'])} skills scanned. Interactions: a unique or keystone worth far more on one skill than "
           f"usual ({len(rows)} found):"]
    out += [f"  +{v:>6.0%} (usual +{v - x:.0%})  {k.split(':', 1)[1]:<28} on {n}  [{k.split(':')[0]}]"
            for n, k, v, x in rows[:top]]
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        run(int(arg("--workers") or 6), Path(arg("--out")) if arg("--out") else OUT)
    elif cmd == "report":
        print(report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
