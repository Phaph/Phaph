"""Blind test (Breaker roadmap, week 1): can the engine find what poe.ninja's ladder plays without seeing it?

The search runs once per ascendancy ("<Ascendancy> build", the A-to-Z prompt), off-meta OFF and no head starts, so
nothing from poe.ninja reaches it (poe.ninja data only enters through the off-meta toggle and the build page's
popularity line). Its ranked skills are then compared with the ladder:

  1. Ladder skills found: of poe.ninja's most played main skills, how many the search ranks in the top 5 of some
     ascendancy (recall), and where each one lands.
  2. Ascendancies: does our best score per ascendancy line up with how many players each one has (Spearman)?
  3. The other way: skills we rank top 3 somewhere that almost nobody plays. Each is either a Breaker lead (strong,
     undiscovered) or a modelling bug (like Hexblast before its usage limit). Both are worth knowing.

Truth: data/meta_usage.json (overall shares). When data/meta_pairs.json exists ({ascendancy: {skill: share within
it}}, fetched on the PC, where poe.ninja isn't blocked) the report also checks each ascendancy's own top skills.
If the search can't find today's strong builds, it won't find tomorrow's.

  python tools/blind_test.py run [--workers 3] [--only Infernalist,Titan] [--out data/breaker/blind.json]  (resumable)
  python tools/blind_test.py report data/breaker/blind.json
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "data" / "breaker" / "blind.json"
TOP_KEEP = 15
LADDER_TOP = 20      # poe.ninja's most played main skills checked
FOUND_RANK = 5       # "found" = in the top 5 of some ascendancy
UNPLAYED = 0.01      # under 1% of the ladder


def run(workers: int, out: Path, only: set[str] | None) -> None:
    from generate import generate, main_skills
    from pob import PoB
    from prompt import parse_prompt

    with PoB() as p:
        classes = p.list_classes()
        catalog_list = p.send("skill_catalog")["skills"]
    # parse_prompt's catalog shape (same as tools/check_prompt.py). It was a {name: skill} map until 2026-11-21,
    # so no ascendancy was ever read and all 23 searches were the same all-class search (Deadeye Rain of Arrows).
    catalog = {"skills": [s["name"] for s in catalog_list], "classes": classes, "weapon_types": {},
               "helper_skills": [s["name"] for s in catalog_list
                                 if set(s["types"]) & {"Buff", "Aura", "Herald", "Meta"}]}
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"ascendancies": {}}
    done["main_skills"] = sorted(s["name"] for s in main_skills(catalog_list, {}))   # damage skills the search can pick
    pairs = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    todo = [(c, a) for c, a in pairs if a not in done["ascendancies"] and (not only or a in only)]
    print(f"{len(pairs)} ascendancies, {len(todo)} to search, {workers} workers", flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    for cls, asc in todo:
        t0 = time.time()
        rec: dict = {"class": cls}
        try:
            req = dict(parse_prompt(f"{asc} build", catalog)["request"])
            req.pop("off_meta", None)
            if req.get("ascendancy") != asc:
                raise ValueError(f"prompt read {req.get('ascendancy')!r}, not {asc!r}")
            rec["request"] = req
            result = generate(req, workers=workers, log=lambda *a: None)
            rec["ranked"] = [{k: c.get(k) for k in ("skill", "weapon_type", "weapon_subtype", "ascendancy", "score",
                                                     "dps", "boss", "clear", "supports", "relative")}
                             for c in result["ranked"][:TOP_KEEP]]
            rec["relaxed"] = result.get("relaxed") or []
            wrong = {c["ascendancy"] for c in rec["ranked"]} - {asc}
            if wrong:
                raise ValueError(f"search for {asc} ranked other ascendancies: {sorted(wrong)}")
        except Exception as e:  # noqa: BLE001 - one ascendancy must not stop the run
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["trace"] = traceback.format_exc()[-1500:]
        rec["seconds"] = round(time.time() - t0)
        done["ascendancies"][asc] = rec
        done["updated"] = time.strftime("%Y-%m-%d %H:%M")
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        top = ", ".join(f"{r['skill']} ({r['weapon_type']})" for r in rec.get("ranked", [])[:3])
        print(f"  {asc:<24} {rec['seconds']:>5}s  {top or rec.get('error')}", flush=True)
    print(report(done), flush=True)


def _spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for k, i in enumerate(order):
            r[i] = k
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    if n < 3:
        return float("nan")
    return 1 - 6 * sum((a - b) ** 2 for a, b in zip(rx, ry)) / (n * (n * n - 1))


def report(d: dict, meta: dict | None = None, pairs: dict | None = None) -> str:
    if meta is None:
        meta = json.loads((ENGINE / "data" / "meta_usage.json").read_text(encoding="utf-8"))
    if pairs is None and (ENGINE / "data" / "meta_pairs.json").exists():
        pairs = json.loads((ENGINE / "data" / "meta_pairs.json").read_text(encoding="utf-8"))
    asc_ok = {a: r for a, r in d["ascendancies"].items() if r.get("ranked")}
    main = set(d.get("main_skills") or [])
    ladder = [(s, v) for s, v in meta["skill"].items() if not main or s in main][:LADDER_TOP]
    # where each skill lands: best rank over all ascendancies (1 = picked)
    where: dict[str, tuple[int, str]] = {}
    for a, r in asc_ok.items():
        seen = []
        for c in r["ranked"]:
            if c["skill"] in seen:
                continue
            seen.append(c["skill"])
            rank = len(seen)
            if c["skill"] not in where or rank < where[c["skill"]][0]:
                where[c["skill"]] = (rank, a)
    found = [s for s, _ in ladder if s in where and where[s][0] <= FOUND_RANK]
    out = [f"Blind test: {len(asc_ok)} of {len(d['ascendancies'])} ascendancies searched (no poe.ninja input). "
           f"Ladder: {meta.get('league')} ({meta.get('characters', 0):,} characters, fetched {meta.get('fetched', '?')[:10]}).",
           f"1. Ladder's top {len(ladder)} main skills found in some ascendancy's top {FOUND_RANK}: "
           f"{len(found)}/{len(ladder)} ({len(found) / max(len(ladder), 1):.0%})"]
    for s, v in ladder:
        w = where.get(s)
        out.append(f"   {'FOUND ' if s in found else '      '}{s:<26} {v:>5.1%} of ladder   "
                   + (f"our rank {w[0]} on {w[1]}" if w else "not in any top 15"))
    # 2. ascendancy strength vs players
    rows = [(a, max(c["score"] or 0 for c in r["ranked"]), meta["ascendancy"].get(a, 0.0)) for a, r in asc_ok.items()]
    if rows:
        rho = _spearman([x[1] for x in rows], [x[2] for x in rows])
        out.append(f"2. Ascendancies, our best score vs share of players: Spearman {rho:+.2f} (1 = same order, 0 = unrelated)")
        for a, sc, sh in sorted(rows, key=lambda x: -x[1]):
            top = asc_ok[a]["ranked"][0]
            out.append(f"   {a:<24} score {sc:>12,.0f}  ladder {sh:>5.1%}   picks {top['skill']} ({top['weapon_type']})")
    # 3. strong but unplayed
    out.append(f"3. Ranked top 3 by us, played by under {UNPLAYED:.0%} of the ladder (lead or modelling bug):")
    odd = sorted({(s, w) for s, w in where.items() if w[0] <= 3 and meta["skill"].get(s, 0) < UNPLAYED},
                 key=lambda x: x[1][0])
    for s, (rank, a) in odd:
        out.append(f"   {s:<26} rank {rank} on {a:<22} ladder {meta['skill'].get(s, 0):.2%}")
    if pairs:
        hits = tot = 0
        out.append(f"4. Per ascendancy (poe.ninja top 3 main skills each, found in our top {FOUND_RANK}):")
        for a, r in asc_ok.items():
            ours = list(dict.fromkeys(c["skill"] for c in r["ranked"]))[:FOUND_RANK]
            theirs = [s for s in (pairs.get(a) or {}) if not main or s in main][:3]
            h = [s for s in theirs if s in ours]
            hits, tot = hits + len(h), tot + len(theirs)
            out.append(f"   {a:<24} {len(h)}/{len(theirs)}  ladder: {', '.join(theirs)} | ours: {', '.join(ours)}")
        out.append(f"   total {hits}/{tot} ({hits / max(tot, 1):.0%})")
    errs = [a for a, r in d["ascendancies"].items() if r.get("error")]
    if errs:
        out.append("Failed: " + ", ".join(f"{a} ({d['ascendancies'][a]['error'][:80]})" for a in errs))
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 3
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        run(workers, out, only)
    elif cmd == "report":
        print(report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
