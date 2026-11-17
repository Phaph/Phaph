"""The Breaker: looks for builds that multiply instead of add (see BREAKER.md).

Scaler scan: on a finished build, add more of one stat at a time through PoB's custom modifiers and measure how damage
responds. Elasticity = how much damage grows per unit of stat growth: ln(D'/D) / ln(S'/S). Around 0-1 is normal; above 1
means damage grows faster than the stat (a stat that feeds damage several ways, like mana for an Archmage build): the
shape of the builds GGG ends up nerfing.

    python breaker.py scan <PoB code file>       one build
    python breaker.py scan --jobs /data/jobs.sqlite3 --out data/breaker/scan.json   every saved guide (end stage)
"""
from __future__ import annotations

import json
import math
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
}
STEPS = (0.5, 1.0)   # add 50% and 100% of the stat's current value (or that much "increased")
RED_FLAG = 1.15   # speed alone scales damage about 1:1, so the bar is clearly above that


def _dmg(pob: PoB) -> float:
    return total_dps(pob.calc(DMG))


def scan(pob: PoB) -> dict:
    """Elasticity of damage to each stat for the build loaded in `pob`."""
    pob.send("set_custom_mods", text="")
    d0 = _dmg(pob)
    base = pob.calc([f for f, _, _ in SCALERS.values()])
    out = {"dps": d0, "stats": {}}
    if d0 <= 0:
        return out
    for name, (field, mod, kind) in SCALERS.items():
        s0 = base.get(field) or 0
        rows = []
        for step in STEPS:
            n = round(max(s0, 1) * step) if kind == "flat" else round(step * 100)
            pob.send("set_custom_mods", text=mod.format(n=n))
            o = pob.calc([field, *DMG])
            s1, d1 = o.get(field) or 0, total_dps(o)
            if s0 > 0 and s1 > s0 and d1 > 0:
                rows.append({"add": n, "stat": round(s1, 1), "dps": round(d1), "elasticity": round(math.log(d1 / d0) / math.log(s1 / s0), 3)})
        pob.send("set_custom_mods", text="")
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


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "scan" and sys.argv[2] == "--jobs":
        scan_jobs(sys.argv[3], Path(sys.argv[sys.argv.index("--out") + 1]))
    elif len(sys.argv) == 3 and sys.argv[1] == "scan":
        with PoB() as p:
            p.load_code(Path(sys.argv[2]).read_text().strip())
            print(json.dumps(scan(p), indent=1))
    else:
        print(__doc__)
