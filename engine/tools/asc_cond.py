"""Conditional ascendancy passives (task 48): which notable pays only, or far more, while a condition is up?

The per-ascendancy condition scan takes passives on their plain gain, so one that needs a condition (Titan: 25% more
against Heavy Stunned) is never in and its condition reads 0. Here every notable of an ascendancy (with its path) is
tried on each skill's round-1 build, alone, under each condition PoB offers for the enemy or the player.

  interaction = damage with both / without either, over (notable alone x condition alone)

Scores are search-style and a condition is only a switch here: a row is a question (can the build keep it up?), not a find.

  python tools/asc_cond.py run --class Warrior --ascendancy Titan --out data/breaker/asc_cond/Titan.json [--workers 6] [--only "Spark,Comet"]
  python tools/asc_cond.py report data/breaker/asc_cond [--top 40]
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
MIN_INTERACTION = 0.03
MIN_DPS = 20_000


def all_conditions(text: str) -> list[str]:
    """Every on/off condition in PoB's config, enemy's and player's."""
    found = re.findall(r'var = "(condition[A-Z][A-Za-z]+)", type = "check"', text)
    return sorted(set(found) - {"conditionEnemyRareOrUnique"})


def interaction(base: float, node: float, cond: float, both: float) -> float:
    return 0.0 if min(base, node, cond) <= 0 else both * base / (node * cond) - 1


def run(workers: int, out: Path, cls: str, asc: str, only: set[str] | None = None) -> None:
    import generate as g
    from condition_scan import code_stamp
    from gear import make_stage
    from optimize import total_dps
    from pob import POB_SRC, PoB

    conds = all_conditions((POB_SRC / "Modules" / "ConfigOptions.lua").read_text(encoding="utf-8", errors="ignore"))
    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        classes = p.list_classes()
    g._ALL_ASCS[:] = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    skills = [s for s in g.main_skills(catalog, {}) if not only or s["name"] in only]
    stamp = code_stamp()
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"code": stamp, "skills": {}}
    if done["code"] != stamp:
        sys.exit(f"{out} was scanned with other engine code ({done['code']}, now {stamp}): move it away first")
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{asc}: {len(todo)} of {len(skills)} skills, {len(conds)} conditions", flush=True)
    stage, lock = make_stage("mid"), threading.Lock()

    def one(s):
        w, sub, off = (g.weapon_options(s, {}) or [(None, None, None)])[0]
        c = g.evaluate(g.Candidate(s["name"], w, sub, off, cls, asc, is_minion="Minion" in s["types"], totem=s.get("totem")),
                       stage, {}, tree=False)
        rec = {"error": c.error, "plain": {}, "inter": []}
        if not c.error:
            p = g._pob()
            try:
                tries = lambda **k: p.send("asc_tries", fields=g.FIELDS, **k)
                r = tries(all=True)
                base = total_dps(r["base"])
                node = {x["id"]: (x["name"], total_dps(x["output"])) for x in r["rows"]}
                rec["dps"], all0 = round(base), total_dps(r["all"])
                if base > 0:
                    rec["plain"] = {n: round(d / base - 1, 3) for n, d in node.values()}
                    auto = p.send("get_config", keys=conds).get("values") or {}
                    for cond in conds:
                        if auto.get(cond):
                            continue   # the build already assumes it
                        p.set_config(**{cond: True})
                        try:
                            # one calculation says whether any notable cares (choice options aren't in it)
                            q = tries(all=True, only_all=True)
                            b = total_dps(q["base"])
                            if abs(interaction(base, all0, b, total_dps(q["all"]))) < 0.005:
                                continue
                            q = tries()
                            for x in q["rows"]:
                                n, d = node[x["id"]]
                                i = interaction(base, d, b, total_dps(x["output"]))
                                if i >= MIN_INTERACTION:
                                    rec["inter"].append([n, cond.removeprefix("condition"), round(i, 3), round(total_dps(x["output"]) / base - 1, 3)])
                        finally:
                            p.set_config(**{cond: False})
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        top = sorted(rec["inter"], key=lambda x: -x[2])[:3]
        print(f"  {s['name']:<28} {rec.get('dps', 0):>10,}  " + ", ".join(f"{n} / {k} +{v:.0%}" for n, k, v, _ in top)
              + (rec["error"] or ""), flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)


def pays(plain: float, v: float, both: float) -> bool:
    """Does notable + condition beat the better of the two alone? A condition that costs the build damage (player
    Frozen / Chilled: about x0.2) times a notable that cancels it ("speed unaffected by Slows") reads as a big
    interaction although both together are no better than the notable alone (Pathfinder, 2026-11-27)."""
    d, bb = 1 + plain, 1 + both
    c = bb / (d * (1 + v))   # the condition alone, from the interaction
    return bb >= max(d, c, 1.0) * (1 + MIN_INTERACTION)


def specific(scans: dict[str, dict]) -> list[tuple]:
    """(interaction beyond the pair's usual, skill, ascendancy, notable, condition, interaction, gain of both), and the
    pair's usual (median over the ascendancy's skills, skills it does nothing for count 0) in front of it."""
    out = []
    for asc, d in scans.items():
        ok = {s: r for s, r in d["skills"].items() if not r.get("error") and r.get("dps", 0) >= MIN_DPS}
        pairs: dict[tuple, dict] = {}
        for s, r in ok.items():
            for n, c, v, both in r["inter"]:
                if not pays(r.get("plain", {}).get(n, 0.0), v, both):
                    continue
                pairs.setdefault((n, c), {})[s] = (v, both)
        for (n, c), rows in pairs.items():
            usual = statistics.median([v for v, _ in rows.values()] + [0.0] * (len(ok) - len(rows)))
            out += [(v - usual, s, asc, n, c, v, both) for s, (v, both) in rows.items()]
    return sorted(out, key=lambda x: -x[0])


def report(scans: dict[str, dict], top: int = 40) -> str:
    rows = specific(scans)
    general: dict[tuple, list] = {}
    for _, s, a, n, c, v, _ in rows:
        general.setdefault((a, n, c), []).append(v)
    lines = [f"{len(scans)} ascendancies: {', '.join(scans)}", "", "Notable x condition, per ascendancy (median interaction, skills it touches):"]
    lines += [f"  {statistics.median(v):+5.0%} {len(v):>4} skills  {a:<20} {n} / {c}"
              for (a, n, c), v in sorted(general.items(), key=lambda kv: -statistics.median(kv[1]))[:top]]
    lines += ["", "Skills that gain beyond what the pair usually gives (both up vs neither in brackets):"]
    lines += [f"  {x:+5.0%}  {s:<26} {a:<20} {n} / {c}: {v:+.0%} ({both:+.0%})" for x, s, a, n, c, v, both in rows[:top]]
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if a[:1] == ["run"]:
        run(int(opt("--workers", 6)), Path(opt("--out")), opt("--class"), opt("--ascendancy"),
            set(opt("--only").split(",")) if opt("--only") else None)
    elif a[:1] == ["report"]:
        print(report({f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(Path(a[1]).glob("*.json"))}, int(opt("--top", 40))))
    else:
        print(__doc__)
