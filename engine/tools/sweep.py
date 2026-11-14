"""Smoke test: build one stage for every ascendancy with a typical skill and weapon.
Reports crashes, zero damage and uncapped resistances. Takes a few minutes.

  python3 tools/sweep.py [--stage early] [--budget budget]
"""
import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guide import build_stage  # noqa: E402

# (class, ascendancy, skill, weapon type, weapon subtype)
SPECS = [
    ("Monk", "Invoker", "Tempest Flurry", "Staff", "Warstaff"),
    ("Monk", "Acolyte of Chayula", "Falling Thunder", "Staff", "Warstaff"),
    ("Monk", "Martial Artist", "Tempest Flurry", "Staff", "Warstaff"),
    ("Witch", "Infernalist", "Fireball", "Wand", None),
    ("Witch", "Blood Mage", "Skeletal Storm Mage", "Sceptre", None),
    ("Witch", "Lich", "Chaos Bolt", "Wand", None),
    ("Witch", "Abyssal Lich", "Raise Zombie", "Sceptre", None),
    ("Ranger", "Deadeye", "Lightning Arrow", "Bow", None),
    ("Ranger", "Pathfinder", "Tornado Shot", "Bow", None),
    ("Warrior", "Titan", "Boneshatter", "Two Hand Mace", None),
    ("Warrior", "Warbringer", "Rolling Slam", "Two Hand Mace", None),
    ("Warrior", "Smith of Kitava", "Volcanic Fissure", "Two Hand Mace", None),
    ("Sorceress", "Stormweaver", "Spark", "Wand", None),
    ("Sorceress", "Chronomancer", "Arc", "Wand", None),
    ("Sorceress", "Disciple of Varashta", "Lightning Bolt", "Wand", None),
    ("Huntress", "Amazon", "Rake", "Spear", None),
    ("Huntress", "Ritualist", "Lightning Spear", "Spear", None),
    ("Huntress", "Spirit Walker", "Twister", "Spear", None),
    ("Mercenary", "Witchhunter", "Explosive Shot", "Crossbow", None),
    ("Mercenary", "Tactician", "Armour Piercing Rounds", "Crossbow", None),
    ("Mercenary", "Gemling Legionnaire", "Permafrost Bolts", "Crossbow", None),
    ("Druid", "Shaman", "Volcano", "Talisman", None),
    ("Druid", "Oracle", "Maul", "Talisman", None),
]


RESULTS: list[dict] = []


def run(spec, stage, budget):
    cls, asc, skill, wtype, wsub = spec
    t = time.time()
    try:
        g = build_stage({"class": cls, "ascendancy": asc, "skill": skill, "weapon_type": wtype,
                         "weapon_subtype": wsub, "budget": budget}, stage)
        RESULTS.append({"ascendancy": asc, "skill": skill, "damage": g.boss_dps or g.dps, "clear": g.clear,
                        "toughness": g.stats.get("TotalEHP", 0), "mapping_dps": g.dps})
        s = g.stats
        res = [s.get(k, 0) for k in ("FireResist", "ColdResist", "LightningResist")]
        flags = []
        if g.dps <= 0:
            flags.append("ZERO DPS")
        if min(res) < 75 and stage != "leveling":
            flags.append(f"res {res}")
        if not g.supports:
            flags.append("no supports")
        return f"{'FAIL' if 'ZERO DPS' in flags else 'ok  '} {asc:<22} {skill:<24} {g.dps:>10,.0f} dps  {time.time() - t:5.0f}s  {' '.join(flags)}"
    except Exception as e:  # noqa: BLE001
        return f"ERR  {asc:<22} {skill:<24} {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="early")
    ap.add_argument("--budget", default="budget")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--calibrate", help="write rating calibration JSON to this path")
    a = ap.parse_args()
    with ThreadPoolExecutor(a.workers) as ex:
        for line in ex.map(lambda s: run(s, a.stage, a.budget), SPECS):
            print(line, flush=True)
    if a.calibrate:
        out = {"source": f"tools/sweep.py --stage {a.stage} --budget {a.budget}", "builds": RESULTS,
               "metrics": {k: sorted(r[k] for r in RESULTS) for k in ("damage", "clear", "toughness")}}
        Path(a.calibrate).write_text(json.dumps(out, indent=1))
        print(f"Calibration from {len(RESULTS)} builds written to {a.calibrate}")


if __name__ == "__main__":
    main()
