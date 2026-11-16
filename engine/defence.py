"""Defence: persistent buffs that keep the character alive (Wind Dancer, Scavenged Plating, Iron Ward...).

The spirit pass (spirit.py) fills spirit with whatever adds the most, and damage buffs nearly always win, so
real builds' defensive buffs never made it in. This pass runs after it: each defensive buff is tried with the
spirit left over, or in place of one of the chosen spirit skills, and kept when the effective HP it adds is
worth more than the damage it costs (DEF_WEIGHT: +10% EHP is worth 5% damage; a "tanky" prompt weighs it more).

Only what PoB can measure counts. Buffs whose effect PoB doesn't model (e.g. Time of Need's recovery)
show no gain and are not added.
"""
from __future__ import annotations

from optimize import CLEAR_FIELDS, DPS_FIELDS, score_of
from pob import PoB, PoBError

FIELDS = [*DPS_FIELDS, *CLEAR_FIELDS, "TotalEHP", "SpiritUnreserved", "ArmourBreakPerHit"]
DEF_WEIGHT = 0.5
MIN_EHP = 0.01   # a defensive buff has to add at least 1% effective HP
NOT_DEFENCE = {"Herald", "Aura", "Minion", "Meta", "Attack", "Damage"}
# Stacks PoB only counts when told how many are up (config var, value; PoB caps it at the skill's own limit).
STACKS = {"Wind Dancer": ("windDancerStacks", 99), "Scavenged Plating": ("scavengedPlatingStacks", 99)}


def defence_candidates(catalog: list[dict]) -> list[str]:
    names = set()
    for s in catalog:
        types = set(s["types"])
        if ("Persistent" in types and "Buff" in types and s.get("spirit") and not types & NOT_DEFENCE
                and not s.get("from_item")):
            names.add(s["name"])
    return sorted(names)


def _stacks_config(name: str, out0: dict) -> dict:
    if name not in STACKS:
        return {}
    if name == "Scavenged Plating" and not out0.get("ArmourBreakPerHit"):
        return {}   # its stacks come from breaking armour
    var, n = STACKS[name]
    return {var: n}


def optimise_defence(pob: PoB, catalog: list[dict], spirit: list[str], metric: str, def_mult: float = 1.0,
                     limit: int = 2, min_gain: float = 0.02, log=print) -> tuple[list[str], list[dict]]:
    """Returns (spirit skills still in the build, defensive buffs added: {"skill", "ehp", "dps", "replaced"})."""
    w = DEF_WEIGHT * def_mult
    spirit = list(spirit)
    added: list[dict] = []
    for _ in range(limit):
        out0 = pob.calc(FIELDS)
        d0, e0 = max(score_of(out0, metric), 1), max(out0.get("TotalEHP") or 0, 1)
        groups = {g["gems"][0]: g["group"] for g in pob.send("groups")["groups"] if g["gems"]}
        best, best_val = None, min_gain
        for cand in defence_candidates(catalog):
            if cand in groups:
                continue
            cfg = _stacks_config(cand, out0)
            if cfg:
                pob.set_config(**cfg)
            # With spare spirit: a new group. Otherwise: in place of one damage buff (never one already added here).
            options = [None] + [r for r in spirit if r in groups and r not in {a["skill"] for a in added}]
            for replace in options:
                try:
                    if replace is None:
                        g = pob.add_skill([cand], main=False)["group"]
                        res = {"output": pob.calc(FIELDS), "warnings": []}
                        pob.remove_skill(g)
                    else:
                        res = pob.try_skill(groups[replace], [cand], FIELDS, keep_main=True)
                        pob.try_skill(groups[replace], [replace], FIELDS, keep_main=True)
                except PoBError:
                    continue
                o = res["output"]
                if o.get("SpiritUnreserved", -1) < 0 or res.get("warnings"):
                    continue
                dps, ehp = (score_of(o, metric) - d0) / d0, (o.get("TotalEHP") or 0 - e0) / e0
                val = dps + w * ehp
                if ehp >= MIN_EHP and val > best_val:
                    best, best_val = {"skill": cand, "ehp": ehp, "dps": dps, "replaced": replace, "config": cfg}, val
            if cfg:
                pob.set_config(**{k: 0 for k in cfg})
        if not best:
            break
        if best["config"]:
            pob.set_config(**best["config"])
        if best["replaced"]:
            pob.try_skill(groups[best["replaced"]], [best["skill"]], FIELDS, keep_main=True)
            spirit.remove(best["replaced"])
        else:
            pob.add_skill([best["skill"]], main=False)
        best.pop("config")
        added.append(best)
        log(f"  defence: + {best['skill']} (EHP {best['ehp']:+.0%}, damage {best['dps']:+.0%}"
            + (f", replaces {best['replaced']})" if best["replaced"] else ")"))
    return spirit, added
