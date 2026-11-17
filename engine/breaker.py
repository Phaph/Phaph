"""The Breaker: looks for builds that multiply instead of add (see BREAKER.md).

Scaler scan: on a finished build, add more of one stat at a time through PoB's custom modifiers and measure how damage
responds. Elasticity = how much damage grows per unit of stat growth: ln(D'/D) / ln(S'/S). Around 0-1 is normal; above 1
means damage grows faster than the stat (a stat that feeds damage several ways, like mana for an Archmage build): the
shape of the builds GGG ends up nerfing.

    python breaker.py scan <PoB code file>       one build
    python breaker.py scan --jobs /data/jobs.sqlite3 --out data/breaker/scan.json   every saved guide (end stage)

Interaction finder: on each saved build (one per skill + ascendancy), try every piece alone (a support added to the main
skill, a keystone's or a unique's mods as custom modifiers), then pairs of the pieces that matter. Synergy =
(1 + gain(a+b)) / ((1 + gain(a)) (1 + gain(b))); above 1 the pair does more together than apart.

    python breaker.py pairs --jobs /data/jobs.sqlite3 --out data/breaker/pairs.json [--limit N]   resumable
    python breaker.py report data/breaker/pairs.json                                             top outliers
"""
from __future__ import annotations

import itertools
import json
import math
import re
import sqlite3
import sys
from pathlib import Path

from optimize import total_dps
from pob import PoB, PoBError

DMG = ["TotalDPS", "TotalDotDPS", "FullDPS", "FullDotDPS", "CombinedDPS", "MinionDPS", "MinionDotDPS", "BleedDPS",
       "PoisonDPS", "IgniteDPS"]
# stat: (PoB output that measures it, custom mod with {n}, how {n} is chosen: "flat" = a share of the current value)
SCALERS = {
    "mana": ("Mana", "+{n} to maximum Mana", "flat"),
    "life": ("Life", "+{n} to maximum Life", "flat"),
    "energy shield": ("EnergyShield", "+{n} to maximum Energy Shield", "flat"),
    "strength": ("Str", "+{n} to Strength", "flat"),
    "dexterity": ("Dex", "+{n} to Dexterity", "flat"),
    "intelligence": ("Int", "+{n} to Intelligence", "flat"),
    "spirit": ("Spirit", "+{n} to Spirit", "flat"),
    "armour": ("Armour", "+{n} to Armour", "flat"),
    "evasion": ("Evasion", "+{n} to Evasion Rating", "flat"),
    "crit chance": ("CritChance", "{n}% increased Critical Hit Chance", "inc"),
    "speed": ("Speed", "{n}% increased Skill Speed", "inc"),
    # Minion builds: the player's own stats barely touch minion damage, so they need their own scalers. These read the
    # main skill's minion (the scan makes the build's biggest damage source the main skill).
    "minion damage": ("MinionAverageDamage", "Minions deal {n}% increased Damage", "inc"),
    "minion speed": ("MinionSpeed", "Minions have {n}% increased Attack and Cast Speed", "inc"),
    "minion count": ("MinionCount", None, "count"),   # +n to every minion limit (raw mods), then Full DPS recounts
}
STEPS = (0.5, 1.0)   # add 50% and 100% of the stat's current value (or that much "increased")
RED_FLAG = 1.15   # speed alone scales damage about 1:1, so the bar is clearly above that


def _dmg(pob: PoB) -> float:
    return total_dps(pob.calc(DMG))


def dominant_group(pob: PoB) -> int | None:
    """Make the skill group that deals the most damage the main skill, and return it.

    Stats like speed are read from the main skill, but damage is the whole build's (Full DPS). When another group deals
    most of the damage, the main skill's speed can move far less than the damage does, which once read as elasticity
    3.4 on a build where nothing multiplied (Whirling Assault Martial Artist, see BREAKER.md)."""
    best, best_d = None, 0.0
    for g in pob.send("groups")["groups"]:
        try:
            pob.send("set_main", group=g["group"])
            o = pob.calc(["TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS"])
        except PoBError:
            continue
        d = sum(o.get(k) or 0 for k in ("TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS"))
        if d > best_d:
            best, best_d = g["group"], d
    if best:
        pob.send("set_main", group=best)
    return best


def _apply(pob: PoB, mod: str | None, kind: str, n: int, limits: list[str]) -> None:
    if kind == "count":   # PoB has no mod text for most minion limits, so raise every limit stat directly
        pob.send("set_custom_mods", text="", raw=[{"name": l, "type": "BASE", "value": n} for l in limits])
        pob.send("sync_minion_counts")
    else:
        pob.send("set_custom_mods", text=mod.format(n=n))


def _clear(pob: PoB, kind: str) -> None:
    pob.send("set_custom_mods", text="")
    if kind == "count":
        pob.send("sync_minion_counts")


def boss(pob: PoB) -> None:
    """Score against a pinnacle boss. Against normal monsters PoB counts culling as a damage multiplier (35% cull =
    x1.54, and "100% increased Culling Strike Threshold" read as x2.2 damage), which drowns every real signal."""
    pob.send("set_config", values={"enemyIsBoss": "Pinnacle"})


def scan(pob: PoB) -> dict:
    """Elasticity of damage to each stat for the build loaded in `pob`."""
    pob.send("set_custom_mods", text="")
    boss(pob)
    main = dominant_group(pob)
    d0 = _dmg(pob)
    mc = pob.send("minion_count")
    base = pob.calc([f for f, _, _ in SCALERS.values()])
    base["MinionCount"] = mc["count"]
    out = {"dps": d0, "main_group": main, "stats": {}}
    if d0 <= 0:
        return out
    for name, (field, mod, kind) in SCALERS.items():
        s0 = base.get(field) or 0
        rows = []
        for step in STEPS:
            n = round(max(s0, 1) * step) if kind in ("flat", "count") else round(step * 100)
            _apply(pob, mod, kind, n, mc["limits"])
            o = pob.calc([field, *DMG])
            if kind == "count":
                o[field] = pob.send("minion_count")["count"]
            s1, d1 = o.get(field) or 0, total_dps(o)
            if s0 > 0 and s1 > s0 and d1 > 0:
                rows.append({"add": n, "stat": round(s1, 1), "dps": round(d1), "elasticity": round(math.log(d1 / d0) / math.log(s1 / s0), 3)})
        _clear(pob, kind)
        if rows:
            out["stats"][name] = {"base": round(s0, 1), "steps": rows, "elasticity": max(r["elasticity"] for r in rows)}
    out["red_flags"] = sorted((k for k, v in out["stats"].items() if v["elasticity"] > RED_FLAG),
                              key=lambda k: -out["stats"][k]["elasticity"])
    return out


def scan_jobs(db: str, out_path: Path) -> None:
    """Scan every saved guide's endgame build (players' builds and tests), resumable."""
    done = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    rows = sqlite3.connect(db).execute("select id, result from jobs where kind='guide' and status='done'").fetchall()
    pob = PoB()
    try:
        for job_id, result in rows:
            if job_id in done or not result:
                continue
            r = json.loads(result)
            end = next((s for s in r.get("stages") or [] if s.get("stage") == "end"), None)
            if not end or not end.get("code"):
                continue
            try:
                pob.load_code(end["code"])
                res = scan(pob)
            except PoBError as e:   # one build that crashes PoB must not stop the scan: restart and skip it
                print(f"skipped {job_id[:8]}: {e}", flush=True)
                pob.close() if pob.proc.poll() is None else None
                pob = PoB()
                continue
            spec = r.get("spec") or {}
            done[job_id] = {"skill": spec.get("skill"), "ascendancy": spec.get("ascendancy"), **res}
            print(f"{spec.get('skill')} {spec.get('ascendancy')}: {res['dps']:,.0f} dps, red flags {res.get('red_flags')}", flush=True)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(done, indent=1), encoding="utf-8")
    finally:
        pob.close()


# ---------- interaction finder ----------
UNIQUE_TYPES = {"Amulet", "Ring", "Belt", "Body Armour", "Helmet", "Gloves", "Boots", "Jewel"}   # no weapons: their
# local mods ("Adds X to Y") would read as global ones in the custom modifier box
POOL = 30          # pairs are tried among this many pieces with the biggest single gain, plus every keystone
SYNERGY_FLAG = 1.10
_RANGE = re.compile(r"\((-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)\)")


def _top_roll(line: str) -> str:
    return _RANGE.sub(lambda m: m.group(2), line.replace("\n", " "))


def pieces(pob: PoB) -> list[dict]:
    """Every keystone and every non-weapon unique as custom modifier text (uniques at their top rolls)."""
    out = [{"kind": "keystone", "name": k["name"], "mods": ""} for k in pob.list_keystones()]   # applied as nodes
    seen = set()
    for u in pob.send("list_uniques")["uniques"]:
        name = u["name"].split(",")[0]
        if u.get("type") not in UNIQUE_TYPES or name in seen:
            continue
        seen.add(name)
        try:
            lines = pob.send("item_lines", raw=u["raw"])
        except PoBError:
            continue
        mods = [_top_roll(l) for l in (lines.get("implicits") or []) + (lines.get("explicits") or [])
                if not l.startswith("Grants Skill")]
        if mods:
            out.append({"kind": "unique", "name": name, "slot": u["type"], "mods": "\n".join(mods)})
    return out


class Bench:
    """One build with its biggest damage source as the main skill; applies any set of pieces and returns the gain."""

    def __init__(self, pob: PoB):
        self.pob = pob
        boss(pob)
        self.group = dominant_group(pob)
        g = next(x for x in pob.send("groups")["groups"] if x["group"] == self.group)
        self.gems = [n for n in g["gems"] if n]
        self.supports = [s["name"] for s in pob.send("fitting_supports", group=self.group)["supports"]
                         if s["name"] not in self.gems]
        self.base = self._dmg([])

    def _dmg(self, ps: list[dict]) -> float:
        text = "\n".join(p["mods"] for p in ps if p["kind"] == "unique")
        self.pob.send("set_custom_mods", text=text, nodes=[p["name"] for p in ps if p["kind"] == "keystone"])
        gems = self.gems + [p["name"] for p in ps if p["kind"] == "support"]
        try:
            o = self.pob.try_skill(self.group, gems, DMG)["output"]
        finally:
            self.pob.send("set_custom_mods", text="")
        return total_dps(o)

    def gain(self, ps: list[dict]) -> float:
        return self._dmg(ps) / self.base - 1 if self.base > 0 else 0.0


def _can_pair(a: dict, b: dict) -> bool:
    if a["kind"] == "unique" and b["kind"] == "unique" and a["slot"] == b["slot"]:
        return a["slot"] in ("Ring", "Jewel")   # two rings fit; one-slot items don't
    return True


def pairs_build(pob: PoB, catalogue: list[dict]) -> dict:
    bench = Bench(pob)
    if bench.base <= 0:
        return {"dps": 0, "singles": {}, "pairs": []}
    ps = catalogue + [{"kind": "support", "name": n} for n in bench.supports]
    singles = {}
    for p in ps:
        try:
            singles[p["name"]] = round(bench.gain([p]), 4)
        except PoBError:
            pass
    ps = [p for p in ps if p["name"] in singles]
    ranked = sorted((p for p in ps if p["kind"] != "keystone"), key=lambda p: -singles[p["name"]])[:POOL]
    pool = ranked + [p for p in ps if p["kind"] == "keystone"]
    rows = []
    for a, b in itertools.combinations(pool, 2):
        if not _can_pair(a, b):
            continue
        try:
            g = bench.gain([a, b])
        except PoBError:
            continue
        ga, gb = singles[a["name"]], singles[b["name"]]
        if 1 + ga <= 0 or 1 + gb <= 0:
            continue
        syn = (1 + g) / ((1 + ga) * (1 + gb))
        rows.append({"a": a["name"], "ka": a["kind"], "b": b["name"], "kb": b["kind"], "gain_a": ga, "gain_b": gb,
                     "gain_ab": round(g, 4), "synergy": round(syn, 4)})
    rows.sort(key=lambda r: -r["synergy"])
    return {"dps": bench.base, "main_group": bench.group, "main_gems": bench.gems, "tried": len(rows),
            "singles": dict(sorted(singles.items(), key=lambda kv: -kv[1])[:40]),
            "pairs": rows[:60] + [r for r in rows[60:] if r["synergy"] < 0.8][:20]}


def pairs_jobs(db: str, out_path: Path, limit: int | None = None) -> None:
    """Interaction finder over the saved guides' endgame builds, one per skill + ascendancy, resumable."""
    done = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    rows = sqlite3.connect(db).execute("select id, result from jobs where kind='guide' and status='done'").fetchall()
    pob = PoB()
    catalogue = None
    seen = {(v.get("skill"), v.get("ascendancy")) for v in done.values()}
    n = 0
    try:
        for job_id, result in rows:
            if limit is not None and n >= limit:
                break
            if job_id in done or not result:
                continue
            r = json.loads(result)
            spec = r.get("spec") or {}
            key = (spec.get("skill"), spec.get("ascendancy"))
            end = next((s for s in r.get("stages") or [] if s.get("stage") == "end"), None)
            if key in seen or not end or not end.get("code"):
                continue
            seen.add(key)
            try:
                if catalogue is None:
                    pob.send("new")
                    catalogue = pieces(pob)
                pob.load_code(end["code"])
                res = pairs_build(pob, catalogue)
            except PoBError as e:   # one build that crashes PoB must not stop the run: restart and skip it
                print(f"skipped {job_id[:8]}: {e}", flush=True)
                pob.close() if pob.proc.poll() is None else None
                pob = PoB()
                continue
            n += 1
            done[job_id] = {"skill": key[0], "ascendancy": key[1], **res}
            top = res["pairs"][0] if res["pairs"] else None
            print(f"{key[0]} {key[1]}: {res['dps']:,.0f} dps, {res.get('tried', 0)} pairs, top "
                  f"{top and (top['a'], top['b'], top['synergy'])}", flush=True)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(done, indent=1), encoding="utf-8")
    finally:
        pob.close()


def report(path: Path, n: int = 25) -> list[dict]:
    """The strongest pairs across every build: synergy above SYNERGY_FLAG and the pair worth 10%+ damage."""
    done = json.loads(path.read_text(encoding="utf-8"))
    rows = [{"build": f"{v['skill']} {v['ascendancy']}", **r} for v in done.values() for r in v.get("pairs", [])
            if r["synergy"] >= SYNERGY_FLAG and r["gain_ab"] >= 0.10]
    rows.sort(key=lambda r: -r["synergy"])
    return rows[:n]


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "scan" and sys.argv[2] == "--jobs":
        scan_jobs(sys.argv[3], Path(sys.argv[sys.argv.index("--out") + 1]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "pairs" and sys.argv[2] == "--jobs":
        lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        pairs_jobs(sys.argv[3], Path(sys.argv[sys.argv.index("--out") + 1]), lim)
    elif len(sys.argv) == 3 and sys.argv[1] == "report":
        for r in report(Path(sys.argv[2])):
            print(f"{r['synergy']:.2f}  {r['build']}: {r['a']} ({r['ka']}, {r['gain_a']:+.0%}) + {r['b']} ({r['kb']}, "
                  f"{r['gain_b']:+.0%}) = {r['gain_ab']:+.0%}")
    elif len(sys.argv) == 3 and sys.argv[1] == "scan":
        with PoB() as p:
            p.load_code(Path(sys.argv[2]).read_text().strip())
            print(json.dumps(scan(p), indent=1))
    else:
        print(__doc__)
