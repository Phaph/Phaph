"""Cast on X (meta gem) damage, which Path of Building does not model.

PoB scores a spell socketed in Cast on Critical as if you cast it yourself, and has no energy system. This
module adds the energy maths on top of PoB's own numbers:

    crits per second    = attack rate x chance to hit x crit chance            (PoB, the attack)
    energy per crit     = monster power x (1 + gem level bonus) x threshold ratio
    threshold ratio     = crit damage / enemy ailment threshold, at most the cap  (PoB gives both numbers)
    energy to fire      = 100 per second of base cast time, summed over the socketed spells
    casts per second    = crits per second x energy per crit / energy to fire  (cooldowns still apply)
    trigger damage      = casts per second x each spell's damage per cast x 20% less (PoB, the spell)

Every number that isn't PoB's lives in engine/data/trigger_rules.json with its source and a "verified" flag, so an
in-game check (tools/trigger_check.py) can correct it without touching code. Results are Whetstone's estimate,
not Path of Building's, and are labelled that way.
"""
from __future__ import annotations

import json
from pathlib import Path

from pob import PoB

RULES_FILE = Path(__file__).parent / "data" / "trigger_rules.json"
ATTACK_FIELDS = ["Speed", "HitChance", "CritChance", "CritMultiplier", "AverageDamage", "EnemyAilmentThreshold",
                 "TotalDPS", "FullDPS"]
SPELL_FIELDS = ["TotalDPS", "Speed", "AverageDamage", "TotalDotDPS"]


def load_rules() -> dict:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def verified(rules: dict | None = None) -> bool:
    """True only once every rule the estimate depends on has been checked in game."""
    r = rules or load_rules()
    return all(r[k].get("verified") for k in ("monster_power", "threshold_scaling", "cast_on_crit"))


def find_groups(pob: PoB, gem: str = "Cast on Critical") -> tuple[int | None, list[int]]:
    """The Cast on X group, and the other groups (candidates for the attack that feeds it)."""
    groups = pob.send("groups")["groups"]
    coc = next((g["group"] for g in groups if gem in g["gems"]), None)
    return coc, [g["group"] for g in groups if g["group"] != coc and g["gems"]]


def cast_on_crit(pob: PoB, attack_group: int, coc_group: int, mode: str = "bossing", gem_level: int = 20,
                 rules: dict | None = None) -> dict:
    """Estimate one Cast on Critical setup. The build must already be loaded with its config for `mode`.

    Returns every step of the sum, so a player (or a test) can see where the number comes from."""
    r = rules or load_rules()
    coc = r["cast_on_crit"]
    groups = {g["group"]: g for g in pob.send("groups")["groups"]}
    names = groups[coc_group]["gems"]
    info = pob.send("gem_info", names=names)["gems"]
    # PoB orders a group's active skills by gem order with supports left out; the meta gem is the first.
    actives = [n for n in names if n in info and not info[n]["support"]]
    spells = [n for n in actives if n != coc["gem"] and "Spell" in info[n]["types"]]

    pob.send("set_main", group=attack_group)
    a = pob.calc(ATTACK_FIELDS)
    hit = (a.get("HitChance") or 0) / 100
    crit = (a.get("CritChance") or 0) / 100
    mult = a.get("CritMultiplier") or 1
    crits_per_sec = (a.get("Speed") or 0) * hit * crit
    avg_hit = (a.get("AverageDamage") or 0) / hit if hit else 0
    crit_hit = avg_hit / (1 + crit * (mult - 1)) * mult if avg_hit else 0

    ts = r["threshold_scaling"]
    if mode == "bossing":
        power = r["monster_power"]["unique_boss"]
        threshold = a.get("EnemyAilmentThreshold") or 0
        ratio = min(ts["cap"], crit_hit / threshold) if threshold else ts["cap"]
    else:
        # Mapping: one normal monster per crit (conservative: area hits on a pack would gain more).
        power, threshold, ratio = r["monster_power"]["normal"], None, ts["mapping_ratio"]
    energy_per_crit = coc["energy_per_power"] * power * (1 + coc["energy_increased_per_level"] * (gem_level - 1) / 100) * ratio
    energy_to_fire = sum(info[s]["cast_time"] * coc["max_energy_per_second_of_cast_time"] for s in spells)
    casts_per_sec = crits_per_sec * energy_per_crit / energy_to_fire if energy_to_fire else 0.0

    per_spell, trigger_dps = [], 0.0
    more = 1 + coc["triggered_damage_more"] / 100
    for s in spells:
        pob.send("set_main", group=coc_group, skill=actives.index(s) + 1)
        o = pob.calc(SPELL_FIELDS)
        per_cast = (o.get("TotalDPS") or 0) / o["Speed"] if o.get("Speed") else (o.get("AverageDamage") or 0)
        per_cast *= more
        cd = info[s].get("cooldown")
        rate = min(casts_per_sec, 1 / cd) if cd else casts_per_sec
        trigger_dps += rate * per_cast
        per_spell.append({"spell": s, "base_cast_time": info[s]["cast_time"], "cooldown": cd,
                          "damage_per_cast": per_cast, "casts_per_sec": rate, "dps": rate * per_cast})
    pob.send("set_main", group=attack_group)
    attack_dps = a.get("FullDPS") or a.get("TotalDPS") or 0
    return {
        "mode": mode, "estimate": True, "verified": verified(r),
        "attack": {"hits_per_sec": (a.get("Speed") or 0) * hit, "crit_chance": crit, "crits_per_sec": crits_per_sec,
                   "crit_hit": crit_hit, "dps": attack_dps},
        "energy": {"monster_power": power, "enemy_threshold": threshold, "threshold_ratio": ratio,
                   "per_crit": energy_per_crit, "to_fire": energy_to_fire},
        "casts_per_sec": casts_per_sec, "spells": per_spell,
        "trigger_dps": trigger_dps, "total_dps": attack_dps + trigger_dps,
    }
