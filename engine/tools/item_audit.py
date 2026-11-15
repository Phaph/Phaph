"""Audit fresh builds: is every item real, does it carry stats, and can the character actually use the build?

  STRICT_ITEMS=1 python engine/tools/item_audit.py [--only 1,3]

Builds every spec below (all four stages) from scratch, with strict crafting (an item the game couldn't make stops
the build), then checks each item:
  real       passes the crafting rules (strict mode; gear.item_problems)
  has stats  a rare has affixes, a unique lists its mods, a jewel isn't blank
  readable   Path of Building reads the item text back and finds every affix listed
and each stage:
  attributes Str / Dex / Int meet what the gear and gems require
  gems       no gem above the level the character's level allows
  uniques    no unique twice (several are "limited to 1")
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("STRICT_ITEMS", "1")

from guide import build_guide  # noqa: E402
from pob import PoB  # noqa: E402

SPECS = [
    {"class": "Monk", "ascendancy": "Invoker", "skill": "Tempest Flurry", "weapon_type": "Staff", "weapon_subtype": "Warstaff", "budget": "high"},
    {"class": "Sorceress", "ascendancy": "Stormweaver", "skill": "Spark", "weapon_type": "Wand", "budget": "unlimited", "with_skills": ["Cast on Critical"]},
    {"class": "Witch", "ascendancy": "Infernalist", "skill": "Skeletal Storm Mage", "weapon_type": "Sceptre", "budget": "medium"},
    {"class": "Ranger", "ascendancy": "Deadeye", "skill": "Lightning Arrow", "weapon_type": "Bow", "budget": "budget"},
    {"class": "Mercenary", "ascendancy": "Witchhunter", "skill": "Explosive Shot", "weapon_type": "Crossbow", "budget": "high"},
    {"class": "Huntress", "ascendancy": "Amazon", "skill": "Twister", "weapon_type": "Spear", "offhand_type": "Shield", "budget": "unlimited"},
    {"class": "Warrior", "ascendancy": "Titan", "skill": "Boneshatter", "weapon_type": "Two Hand Mace", "budget": "free"},
    {"class": "Witch", "ascendancy": "Lich", "skill": "Hexblast", "weapon_type": "Staff", "weapon_subtype": "none", "budget": "unlimited"},
]
ATTR = [("Str", "ReqStr"), ("Dex", "ReqDex"), ("Int", "ReqInt")]


def audit_stage(pob: PoB, g) -> dict:
    issues = {"real": [], "stats": [], "readable": [], "attributes": [], "gems": [], "uniques": []}
    items = list(g.gear) + list(g.jewels or [])
    names = [p.unique.split(",")[0] for p in items if p.unique]
    for n in {x for x in names if names.count(x) > 1}:
        issues["uniques"].append(f"{n} twice")
    for p in items:
        label = f"{p.slot} {p.unique or p.base}"
        if p.unique:
            if not p.mods:
                issues["stats"].append(f"{label}: unique shows no mods")
        elif not p.affixes:
            issues["stats"].append(f"{label}: rare with no affixes")
        try:
            res = pob.send("item_lines", raw=p.raw)
            lines = set(res.get("implicits") or []) | set(res.get("explicits") or [])
            if not lines:
                issues["readable"].append(f"{label}: Path of Building reads no mods")
            missing = [a for a in p.affixes for part in a.split(" / ") if part not in lines]
            if missing:
                issues["readable"].append(f"{label}: not read back: {missing[:2]}")
        except Exception as e:  # noqa: BLE001
            issues["readable"].append(f"{label}: {e}")
    pob.load_code(g.code)
    out = pob.calc([f for pair in ATTR for f in pair])
    for have, need in ATTR:
        if (out.get(have) or 0) < (out.get(need) or 0):
            issues["attributes"].append(f"{have} {out.get(have, 0):.0f} < {out.get(need, 0):.0f} needed")
    over = {}
    for grp in pob.send("groups")["groups"]:
        for name, lv in zip(grp["gems"], grp.get("levels") or []):
            if (lv.get("req") or 0) > g.level:
                over[name] = (lv.get("level"), lv.get("req"))
    if over:
        issues["gems"].append(f"{len(over)} gems need a higher character level than {g.level}, e.g. "
                              + ", ".join(f"{n} level {lv} (needs {req})" for n, (lv, req) in list(over.items())[:3]))
    return issues


def run(i: int, spec: dict) -> list[str]:
    name = f"#{i} {spec['skill']} {spec['ascendancy']} ({spec['budget']})"
    t = time.time()
    try:
        guides = build_guide(spec, ["leveling", "early", "mid", "end"], log=lambda *a: None)
    except AssertionError as e:
        return [f"{name}: ILLEGAL ITEM: {e}"]
    except Exception as e:  # noqa: BLE001
        return [f"{name}: build failed: {type(e).__name__}: {e}"]
    rows = [f"{name}: built in {time.time() - t:.0f}s"]
    with PoB() as pob:
        for g in guides:
            iss = audit_stage(pob, g)
            bad = {k: v for k, v in iss.items() if v}
            n_items = len(g.gear) + len(g.jewels or [])
            rows.append(f"   {g.stage:<9} {n_items:>2} items  " + ("all checks pass" if not bad else
                        " | ".join(f"{k}: {'; '.join(v)}" for k, v in bad.items())))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma separated spec numbers")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    picks = [(i, s) for i, s in enumerate(SPECS, 1) if not a.only or str(i) in a.only.split(",")]
    with ThreadPoolExecutor(a.workers) as ex:
        for rows in ex.map(lambda x: run(*x), picks):
            print("\n".join(rows), flush=True)


if __name__ == "__main__":
    main()
