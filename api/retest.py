"""After a game patch: re-test the old patch's best builds on the new one.

Run inside the engine container once PoB has the new patch (see LAUNCH_1.0.md):
    docker exec phaph-app-1 python -m api.retest            # top 200 winners of the newest older patch
    docker exec phaph-app-1 python -m api.retest --top 50 --from 0_5

Old builds are never changed or deleted. Each winner is built again on the new patch, the same quick way the search
scores candidates, and saved to the `seeds` table: the new patch's searches start from them (api/learn.head_starts),
and the report (/data/retest_<old>_to_<new>.json) lists who was buffed and who was nerfed, for the Breaker.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from api.learn import BUILD_KEYS, SEEDS, THEME_LISTS, THEME_ONE  # noqa: E402


def old_winners(db: sqlite3.Connection, old: str, top: int) -> list[dict]:
    """The strongest distinct builds of the old patch's searches, most often near the top first."""
    seen: dict[tuple, dict] = {}
    count = Counter()
    for row in db.execute("SELECT result FROM jobs WHERE kind='generate' AND status='done' AND game_patch=?", (old,)):
        try:
            res = json.loads(row[0])["result"]
        except (ValueError, KeyError, TypeError):
            continue
        req = res.get("request") or {}
        if req.get("random"):
            continue
        theme = {k: req[k] for k in (*THEME_LISTS, *THEME_ONE) if req.get(k)}
        for r in (res.get("ranked") or [])[:3]:
            key = (r.get("skill"), r.get("ascendancy"), r.get("weapon_type"))
            count[key] += 1
            if key not in seen or (r.get("score") or 0) > seen[key]["old_score"]:
                seen[key] = {"build": {k: r.get(k) for k in BUILD_KEYS}, "theme": theme, "old_score": r.get("score") or 0}
    ranked = sorted(seen, key=lambda k: (-count[k], -seen[k]["old_score"]))
    return [seen[k] for k in ranked[:top]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--from", dest="old", default=None, help="old game patch (default: newest one before this)")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("GENERATE_WORKERS", "4")))
    ap.add_argument("--db", default=os.environ.get("JOBS_DB", "/data/jobs.sqlite3"))
    args = ap.parse_args()

    import generate as g
    from gear import make_stage
    from pob import PoB

    with PoB() as p:
        new = p.patch
    db = sqlite3.connect(args.db)
    db.executescript(SEEDS)
    old = args.old or next((r[0] for r in db.execute(
        "SELECT game_patch FROM jobs WHERE game_patch IS NOT NULL AND game_patch != ? GROUP BY game_patch "
        "ORDER BY MAX(created) DESC LIMIT 1", (new,))), None)
    if not old or old == new:
        print(f"No older patch to re-test (PoB is on {new}).")
        return
    todo = old_winners(db, old, args.top)
    print(f"Re-testing {len(todo)} builds from patch {old} on {new} with {args.workers} workers")
    stage = make_stage("mid")
    mine: list = []

    def one(w):
        b = w["build"]
        c = g.Candidate(b["skill"], b["weapon_type"], b.get("weapon_subtype"), b.get("offhand_type"), b["cls"],
                        b.get("ascendancy"), totem=b.get("totem"))
        return w, g.evaluate(c, stage, w["theme"], tree=True)

    t0 = time.time()
    out = []
    try:
        with ThreadPoolExecutor(args.workers, initializer=g._bind, initargs=(mine,)) as pool:
            for w, c in pool.map(one, todo):
                if c.error or c.score <= 0:
                    out.append({**w["build"], "old_score": w["old_score"], "new_score": 0, "change": None,
                                "error": c.error or "no damage"})
                    continue
                db.execute("INSERT INTO seeds (game_patch, theme, build, score, old_patch, old_score, created) "
                           "VALUES (?,?,?,?,?,?,?)", (new, json.dumps(w["theme"]), json.dumps(w["build"]), c.score,
                                                      old, w["old_score"], time.time()))
                out.append({**w["build"], "old_score": w["old_score"], "new_score": c.score,
                            "change": c.score / w["old_score"] if w["old_score"] else None})
        db.commit()
    finally:
        g._close_all(mine)
    out.sort(key=lambda r: -(r["change"] or 0))
    report = {"from": old, "to": new, "seconds": round(time.time() - t0), "builds": out,
              "buffed": [r for r in out if (r["change"] or 0) >= 1.25],
              "nerfed": [r for r in out if r["change"] is not None and r["change"] <= 0.8],
              "broken": [r for r in out if r["change"] is None]}
    path = Path(args.db).with_name(f"retest_{old}_to_{new}.json")
    path.write_text(json.dumps(report, indent=1))
    print(f"Done in {report['seconds']}s: {len(report['buffed'])} buffed, {len(report['nerfed'])} nerfed, "
          f"{len(report['broken'])} no longer build. Report: {path}")
    for r in report["buffed"][:10]:
        print(f"  +{r['change'] - 1:6.0%}  {r['skill']} {r['ascendancy']} {r['weapon_type']}")


if __name__ == "__main__":
    main()
