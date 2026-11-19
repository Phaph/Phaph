"""Combo finder, step 2: score setup + payoff pairs, starting with Armour Broken (bossing, pinnacle boss).

Step 1 (condition_scan.py) found the payoffs: skills that gain far more than usual when the enemy is in one state.
This step pairs each payoff with the skills that put the enemy in that state, and scores the pair as it plays:

  Armour Broken. A boss has armour A (PoB's pinnacle boss: about 8,000). Each hit of a setup skill breaks
  B_hit = flat break + X% of the hit's physical damage (Armour Break supports, some skills), x Armour Demolisher's more.
  Hits per second h = uses per second x hit chance. Time to Fully Break: T = A / (B_hit x h).
  Fully Broken lasts 12 s (armour 0, +20% physical damage taken from hits), then the armour comes back.
  One cycle: T seconds of the setup skill (its own damage, boss unbroken), then 12 s of the payoff (broken):
      combo DPS = (T x setup DPS + 12 x payoff DPS when broken) / (T + 12)      uptime = 12 / (T + 12)
  A setup on another weapon type sits on weapon set 2: +1 s per cycle for the two swaps.
  "Self" is the payoff breaking armour itself, with Armour Break / Armour Demolisher in place of its weakest supports.

  Edge = combo DPS / the better of the two skills alone - 1 (only combos with an edge are kept): worth playing.
  Gain = combo DPS / payoff alone - 1. A Breaker lead when the edge is far beyond the ~+20-45% PoB gives a payoff
  for "always broken".

PoB doesn't model the time to break (it only ticks "Is the enemy Armour Broken?"), so T and the uptime are our own
estimates from PoB's per-hit numbers (runner `armour_break`); the cycle model is conservative (no partial-break damage
before Fully Broken, no hits per use beyond 1).

  python combo_scan.py run [--workers 2] [--out data/breaker/combos.json] [--only Skill,Skill]   (resumable)
  python combo_scan.py report data/breaker/combos.json
  python combo_scan.py ailments [--workers 2] [--out data/breaker/combos_ailments.json] [--only ...]   (resumable)
  python combo_scan.py ailments-report data/breaker/combos_ailments.json
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "combos.json"
COND = "conditionEnemyArmourBroken"
FULLY_BROKEN_S = 12.0       # how long Fully Broken Armour lasts (PoB's tooltip, game text)
SWAP_S = 1.0                # two weapon swaps per cycle when the setup needs the other weapon set
BREAK_SUPPORTS = ["Armour Break III", "Armour Demolisher II"]
MIN_PAYOFF = 0.10           # a skill is a payoff when Armour Broken is worth +10% or more to it
PCT_HIT = {                 # which hit damage each "% of damage dealt as Armour Break" stat reads
    "WsArmourBreakPhysPct": ("Physical",),
    "WsArmourBreakAllPct": ("Physical", "Fire", "Cold", "Lightning", "Chaos"),
    "WsArmourBreakChaosPct": ("Chaos",),
    "WsArmourBreakFirePct": ("Fire",),
}


def break_rate(ab: dict, hit_chance: float) -> tuple[float, float]:
    """(armour broken per hit, per second) from the runner's armour_break reply."""
    if ab.get("cannot") and not ab.get("flat"):
        return 0.0, 0.0
    per_hit = ab.get("flat") or 0.0
    for stat, v in (ab.get("pct") or {}).items():
        per_hit += v / 100 * sum(ab.get(t + "HitAverage") or 0 for t in PCT_HIT.get(stat, ()))
    per_hit *= ab.get("more") or 1.0
    return per_hit, per_hit * (ab.get("speed") or 0) * min(hit_chance or 100, 100) / 100


def measure(p, group: int, gems: list[str]) -> dict:
    """Damage unbroken and broken, and how fast this gem setup breaks armour."""
    from generate import FIELDS
    from optimize import total_dps
    p.set_config(**{COND: False})
    out = p.try_skill(group, gems, FIELDS + ["HitChance"])["output"]
    dps_u = total_dps(out)
    ab = p.send("armour_break")
    per_hit, rate = break_rate(ab, out.get("HitChance") or 100)
    p.set_config(**{COND: True})
    dps_b = total_dps(p.calc(FIELDS))
    p.set_config(**{COND: False})
    return {"gems": gems, "dps": round(dps_u), "dps_broken": round(dps_b), "break_hit": round(per_hit),
            "break_s": round(rate), "armour": round(ab.get("enemy_armour") or 0),
            "phys_hit": round(ab.get("PhysicalHitAverage") or 0), "speed": round(ab.get("speed") or 0, 2)}


def cycle(setup_dps: float, setup_rate: float, payoff_broken: float, armour: float, swap: bool) -> dict | None:
    if setup_rate <= 0:
        return None
    t = armour / setup_rate + (SWAP_S if swap else 0.0)
    dps = (t * setup_dps + FULLY_BROKEN_S * payoff_broken) / (t + FULLY_BROKEN_S)
    return {"dps": round(dps), "time_to_break": round(t, 2), "uptime": round(FULLY_BROKEN_S / (t + FULLY_BROKEN_S), 3)}


def with_break_supports(p, group: int, skill: str, supports: list[str], key) -> dict:
    """Swap the weakest supports for Armour Break / Armour Demolisher, one at a time, keeping each swap that improves
    key(measure); returns the best measure (or the plain one if no swap helps)."""
    best = measure(p, group, [skill, *supports])
    for extra in BREAK_SUPPORTS:
        if extra in best["gems"]:
            continue
        cur = best
        for i in range(1, len(cur["gems"])):
            gems = cur["gems"][:i] + cur["gems"][i + 1:] + [extra]
            try:
                m = measure(p, group, gems)
            except Exception:  # noqa: BLE001 - a support that doesn't fit this skill
                continue
            if key(m) > key(best):
                best = m
        if len(cur["gems"]) < 6:   # a free slot: just add it
            try:
                m = measure(p, group, cur["gems"] + [extra])
                if key(m) > key(best):
                    best = m
            except Exception:  # noqa: BLE001
                pass
    return best


def self_score(m: dict) -> float:
    c = cycle(m["dps"], m["break_s"], m["dps_broken"], m["armour"], False)
    return c["dps"] if c else m["dps"]


def run(workers: int, out: Path, only: set[str] | None = None) -> None:
    import generate as g
    from gear import make_stage
    from pob import PoB

    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
    skills = g.main_skills(catalog, {})
    if only:
        skills = [s for s in skills if s["name"] in only]
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"skills": {}}
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{len(skills)} skills, {len(todo)} to measure, {workers} workers", flush=True)
    stage = make_stage("mid")
    lock = threading.Lock()

    def one(s):
        is_minion = "Minion" in s["types"]
        w, sub, off = (g.weapon_options(s, {}) or [(None, None, None)])[0]
        c = g.Candidate(s["name"], w, sub, off, g.DEFAULT_CLASS.get("Minion" if is_minion else
                        "Spell" if "Spell" in s["types"] else "", "Mercenary"), is_minion=is_minion,
                        totem=s.get("totem"))
        c = g.evaluate(c, stage, {}, tree=False)
        rec = {"weapon": g.weapon_key(w, sub), "class": c.cls, "minion": is_minion, "error": c.error}
        if not c.error:
            p = g._pob()
            try:
                group = next(x["group"] for x in p.send("groups")["groups"] if x["main"])
                plain = measure(p, group, [s["name"], *c.supports])
                rec["plain"] = plain
                gain = plain["dps_broken"] / plain["dps"] - 1 if plain["dps"] else 0
                rec["gain_broken"] = round(gain, 3)
                if not is_minion and (gain >= MIN_PAYOFF or plain["phys_hit"] > 0 or plain["break_s"] > 0):
                    # As a setup: break as fast as possible. As a payoff: best self-break cycle.
                    rec["setup"] = with_break_supports(p, group, s["name"], c.supports, key=lambda m: m["break_s"])
                    if gain >= MIN_PAYOFF:
                        rec["self"] = with_break_supports(p, group, s["name"], c.supports, key=self_score)
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        pl, su = rec.get("plain") or {}, rec.get("setup") or {}
        print(f"  {s['name']:<28} {pl.get('dps', 0):>10,}  broken {rec.get('gain_broken', 0):+.0%}  "
              f"breaks {su.get('break_s', pl.get('break_s', 0)):,}/s  {rec.get('error') or ''}", flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report(done), flush=True)


def combos(d: dict) -> list[dict]:
    """Every payoff with its best setup (another skill, or itself), scored by the cycle model.
    A combo only counts when it beats both skills used alone: a slow setup whose own damage carries the "combo" is
    just the stronger skill. edge = combo DPS / the better skill alone - 1."""
    sk = {n: r for n, r in d["skills"].items() if not r.get("error") and r.get("plain")}
    setups = {n: r["setup"] for n, r in sk.items() if (r.get("setup") or {}).get("break_s", 0) > 0}
    rows = []
    for n, r in sk.items():
        pl = r["plain"]
        if r.get("gain_broken", 0) < MIN_PAYOFF or not pl["dps"]:
            continue
        options = []
        if r.get("self") and (c := cycle(r["self"]["dps"], r["self"]["break_s"], r["self"]["dps_broken"],
                                         r["self"]["armour"], False)):
            options.append({"setup": "(itself)", "gems": r["self"]["gems"], "setup_alone": 0, **c})
        for sn, su in setups.items():
            if sn == n:
                continue
            swap = sk[sn]["weapon"] != r["weapon"]
            if c := cycle(su["dps"], su["break_s"], pl["dps_broken"], su["armour"] or pl["armour"], swap):
                options.append({"setup": sn, "gems": su["gems"], "swap": swap,
                                "setup_alone": sk[sn]["plain"]["dps"], **c})
        for o in options:
            o["edge"] = round(o["dps"] / max(pl["dps"], o["setup_alone"]) - 1, 3)
        options = [o for o in options if o["edge"] > 0]
        if not options:
            continue
        best = max(options, key=lambda o: o["edge"])
        rows.append({"payoff": n, "weapon": r["weapon"], "alone": pl["dps"], "broken_always": pl["dps_broken"],
                     "gain_if_always": r["gain_broken"], **best, "gain": round(best["dps"] / pl["dps"] - 1, 3),
                     "runners_up": sorted(options, key=lambda o: -o["edge"])[1:4]})
    return sorted(rows, key=lambda x: -x["edge"])


def report(d: dict, top: int = 40) -> str:
    rows = combos(d)
    setups = sorted(((n, r["setup"]) for n, r in d["skills"].items() if (r.get("setup") or {}).get("break_s", 0) > 0),
                    key=lambda x: -x[1]["break_s"])
    out = [f"{len(d['skills'])} skills measured; {len(setups)} can break armour; {len(rows)} payoffs (Armour Broken "
           f"worth {MIN_PAYOFF:.0%}+), vs pinnacle boss. Time to break and uptime are our estimates.",
           "Fastest armour breakers (with Armour Break / Demolisher supports where they help):"]
    for n, s in setups[:12]:
        out.append(f"  {n:<26} {s['break_s']:>7,}/s  ({s['break_hit']:,}/hit x {s['speed']}/s; boss armour "
                   f"{s['armour']:,} -> {s['armour'] / max(s['break_s'], 1):.1f} s)  [{', '.join(s['gems'][1:])}]")
    out.append("Payoff + best setup that beats both alone (edge = vs the better skill alone; gain = vs the payoff "
               "alone; 'always' = PoB's 100%-uptime assumption):")
    for r in rows[:top]:
        swap = " [weapon set 2]" if r.get("swap") else ""
        out.append(f"  edge {r['edge']:+5.0%}  gain {r['gain']:+5.0%} (always {r['gain_if_always']:+.0%})  "
                   f"{r['payoff']:<22} <- {r['setup']}{swap}: {r['alone']:,} -> {r['dps']:,}, "
                   f"break {r['time_to_break']} s, up {r['uptime']:.0%}")
    return "\n".join(out)


# ---------- Ailment families (Shocked, Poisoned, Ignited, Chilled, Bleeding) ----------
# Setup: a skill that applies the ailment. Expected time to apply it once T = 1 / (chance per hit x hits per second);
# it then lasts its duration D. The same cycle as Armour Broken: T s of the setup, then D s of the payoff.
# A payoff that applies the ailment itself keeps it up min(1, applications per second x D) of the time.
# Against a pinnacle boss ailment chances are low (bosses have high ailment thresholds), so most uptimes are small:
# that's the real game, and what makes a dedicated applier a combo.
AILMENTS = {"Shock": ["conditionEnemyShocked"], "Poison": ["conditionEnemyPoisoned"],
            "Ignite": ["conditionEnemyIgnited", "conditionEnemyBurning"], "Chill": ["conditionEnemyChilled"],
            "Bleed": ["conditionEnemyBleeding"]}
AILMENT_OUT = ENGINE / "data" / "breaker" / "combos_ailments.json"
# Supports that raise the chance to apply each ailment: an applier gets them in place of its weakest supports.
AILMENT_SUPPORTS = {"Shock": ["Shock", "Overcharge"], "Poison": ["Poison III", "Deadly Poison II"],
                    "Ignite": ["Ignite III"], "Bleed": ["Bleed IV"], "Chill": []}


def _apply_rate(p, a: str) -> tuple[float, float]:
    r = p.send("ailment_rates")
    x = (r.get("ailments") or {}).get(a) or {}
    per_s = (x.get("chance") or 0) / 100 * (r.get("speed") or 0) * min(r.get("hit_chance") or 100, 100) / 100
    return per_s, x.get("duration") or 0


def best_applier(p, group: int, gems: list[str], a: str) -> dict:
    """The fastest way this skill applies ailment a: its own supports, or with the ailment's supports swapped in for
    the weakest ones (one at a time, kept when they raise applications per second)."""
    from generate import FIELDS
    from optimize import total_dps
    best_gems = list(gems)
    best_rate, dur = _apply_rate(p, a)
    for extra in AILMENT_SUPPORTS.get(a, []):
        cur = list(best_gems)
        trials = [cur[:i] + cur[i + 1:] + [extra] for i in range(1, len(cur))] + ([cur + [extra]] if len(cur) < 6 else [])
        for g2 in trials:
            try:
                p.try_skill(group, g2, ["TotalDPS"])
            except Exception:  # noqa: BLE001 - a support that doesn't fit this skill
                continue
            rate, d = _apply_rate(p, a)
            if rate > best_rate:
                best_gems, best_rate, dur = g2, rate, d
    p.try_skill(group, best_gems, ["TotalDPS"])
    dps = total_dps(p.calc(FIELDS))
    p.try_skill(group, gems, ["TotalDPS"])
    return {"gems": best_gems, "per_s": round(best_rate, 4), "duration": round(dur, 2), "dps": round(dps)}


def measure_ailments(p) -> dict:
    from generate import FIELDS
    from optimize import total_dps
    off = {v: False for vs in AILMENTS.values() for v in vs}
    p.set_config(**off)
    base = total_dps(p.calc(FIELDS))
    rates = p.send("ailment_rates")
    rec = {"dps": round(base), "ailments": {}}
    for a, vars_ in AILMENTS.items():
        p.set_config(**{v: True for v in vars_})
        on = total_dps(p.calc(FIELDS))
        p.set_config(**off)
        r = (rates.get("ailments") or {}).get(a) or {}
        per_s = (r.get("chance") or 0) / 100 * (rates.get("speed") or 0) * min(rates.get("hit_chance") or 100, 100) / 100
        rec["ailments"][a] = {"dps_on": round(on), "gain": round(on / base - 1, 3) if base else 0.0,
                              "per_s": round(per_s, 4), "duration": round(r.get("duration") or 0, 2)}
    # As a setup: the fastest applier variant of this skill for each ailment.
    g = next((x for x in p.send("groups")["groups"] if x["main"]), None)
    if g:
        gems = [n for n in g["gems"] if n]
        for a in AILMENTS:
            if AILMENT_SUPPORTS.get(a):
                rec["ailments"][a]["applier"] = best_applier(p, g["group"], gems, a)
    return rec


def run_ailments(workers: int, out: Path, only: set[str] | None = None) -> None:
    import generate as g
    from gear import make_stage
    from pob import PoB

    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
    skills = [s for s in g.main_skills(catalog, {}) if not only or s["name"] in only]
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"skills": {}}
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{len(skills)} skills, {len(todo)} to measure (ailments), {workers} workers", flush=True)
    stage = make_stage("mid")
    lock = threading.Lock()

    def one(s):
        is_minion = "Minion" in s["types"]
        w, sub, off = (g.weapon_options(s, {}) or [(None, None, None)])[0]
        c = g.Candidate(s["name"], w, sub, off, g.DEFAULT_CLASS.get("Minion" if is_minion else
                        "Spell" if "Spell" in s["types"] else "", "Mercenary"), is_minion=is_minion, totem=s.get("totem"))
        c = g.evaluate(c, stage, {}, tree=False)
        rec = {"weapon": g.weapon_key(w, sub), "minion": is_minion, "error": c.error}
        if not c.error:
            try:
                rec.update(measure_ailments(g._pob()))
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        best = max((rec.get("ailments") or {}).items(), key=lambda kv: kv[1]["gain"], default=(None, {}))
        print(f"  {s['name']:<28} {rec.get('dps', 0):>10,}  best payoff {best[0]} {best[1].get('gain', 0):+.0%}  "
              f"{rec.get('error') or ''}", flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report_ailments(done), flush=True)


def ailment_combos(d: dict, min_gain: float = 0.30) -> list[dict]:
    """Payoffs that gain far more than usual from one ailment, with their best applier (or themselves)."""
    sk = {n: r for n, r in d["skills"].items() if not r.get("error") and r.get("ailments") and r.get("dps")}
    usual = {}
    for a in AILMENTS:
        vals = sorted(r["ailments"][a]["gain"] for r in sk.values())
        usual[a] = vals[len(vals) // 2] if vals else 0.0
    rows = []
    for n, r in sk.items():
        for a, x in r["ailments"].items():
            if x["gain"] < min_gain or x["gain"] - usual[a] < 0.15:
                continue
            options = []
            for own in (x, x.get("applier")):   # its own supports, or with the ailment's supports swapped in
                if not own or own["per_s"] <= 0:
                    continue
                up = min(1.0, own["per_s"] * own["duration"])
                base = own.get("dps", r["dps"])
                options.append({"setup": "(itself)", "gems": own.get("gems"), "uptime": round(up, 3),
                                "time_to_apply": round(1 / own["per_s"], 2),
                                "dps": round(base * (1 + x["gain"] * up)), "setup_alone": 0})
            for sn, sr in sk.items():
                y = sr["ailments"][a].get("applier") or sr["ailments"][a]
                if sn == n or sr.get("minion") or y["per_s"] <= 0:
                    continue
                t = 1 / y["per_s"] + (SWAP_S if sr["weapon"] != r["weapon"] else 0.0)
                dur = y["duration"]
                dps = (t * y.get("dps", sr["dps"]) + dur * x["dps_on"]) / (t + dur)
                options.append({"setup": sn, "gems": y.get("gems"), "swap": sr["weapon"] != r["weapon"],
                                "uptime": round(dur / (t + dur), 3), "time_to_apply": round(t, 2), "dps": round(dps),
                                "setup_alone": sr["dps"]})
            for o in options:
                o["edge"] = round(o["dps"] / max(r["dps"], o["setup_alone"]) - 1, 3)
            options = [o for o in options if o["edge"] >= 0.01]
            best = max(options, key=lambda o: o["edge"], default=None)
            rows.append({"payoff": n, "ailment": a, "gain_if_always": x["gain"], "usual": round(usual[a], 3),
                         "alone": r["dps"], **(best or {"setup": None, "edge": 0.0})})
    return sorted(rows, key=lambda r: -r["edge"])


def report_ailments(d: dict, top: int = 30) -> str:
    rows = ailment_combos(d)
    out = [f"{len(d['skills'])} skills measured for ailments vs a pinnacle boss. Payoffs (gain if always on, well above "
           f"the usual) and their best applier (our cycle estimate):"]
    for r in rows[:top]:
        if r.get("setup"):
            swap = " [weapon set 2]" if r.get("swap") else ""
            out.append(f"  edge {r['edge']:+5.0%}  {r['payoff']:<22} vs {r['ailment']:<6} (always {r['gain_if_always']:+.0%}, "
                       f"usual {r['usual']:+.0%}) <- {r['setup']}{swap}: apply every {r['time_to_apply']} s, up {r['uptime']:.0%}")
        else:
            out.append(f"  no combo  {r['payoff']:<22} vs {r['ailment']:<6} (always {r['gain_if_always']:+.0%}): nothing applies it "
                       f"often enough on a pinnacle boss")
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 2
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        run(workers, out, only)
    elif cmd == "report":
        print(report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    elif cmd == "ailments":
        workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 2
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else AILMENT_OUT
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        run_ailments(workers, out, only)
    elif cmd == "ailments-report":
        print(report_ailments(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
