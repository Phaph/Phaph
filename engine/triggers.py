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
                 "TotalDPS", "FullDPS", "IgniteChance", "ShockChance"]
# Meta gems that trigger socketed spells from energy, and what fills their energy.
METAS = {"Cast on Critical": "cast_on_crit", "Cast on Elemental Ailment": "cast_on_elemental_ailment"}
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
                 rules: dict | None = None, gem: str = "Cast on Critical") -> dict:
    """Estimate one Cast on X setup (Cast on Critical, or Cast on Elemental Ailment with gem=...). The build must
    already be loaded with its config for `mode`.

    Returns every step of the sum, so a player (or a test) can see where the number comes from."""
    r = rules or load_rules()
    coc = r[METAS.get(gem, "cast_on_crit")]
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
    # Hits per second, not casts: a skill that hits a target several times per cast (Spark's projectiles, a multi-hit
    # strike) fills energy several times per cast. PoB's DPS is average damage per use x uses x hits per use, so
    # DPS / average damage gives uses x hits per use. Fall back to the cast rate when PoB gives no average damage.
    uses = (a.get("Speed") or 0)
    if a.get("AverageDamage") and a.get("TotalDPS"):
        uses = max(uses, a["TotalDPS"] / a["AverageDamage"])
    crits_per_sec = uses * hit * crit
    avg_hit = (a.get("AverageDamage") or 0) / hit if hit else 0
    crit_hit = avg_hit / (1 + crit * (mult - 1)) * mult if avg_hit else 0

    ts = r["threshold_scaling"]
    if gem == "Cast on Elemental Ailment":
        # Energy per Ignite or Shock applied (freeze is left out: see trigger_rules.json). No threshold scaling.
        per_power = coc["energy_per_power"]
        # PoB's chance per hit for each (crits included), against the configured enemy's ailment threshold.
        ignites = uses * hit * (a.get("IgniteChance") or 0) / 100
        shocks = uses * hit * (a.get("ShockChance") or 0) / 100
        power = r["monster_power"]["unique_boss" if mode == "bossing" else "normal"]
        level = 1 + coc["energy_increased_per_level"] * (gem_level - 1) / 100
        energy_per_sec = (ignites * per_power["ignite"] + shocks * per_power["shock"]) * power * level
        crits_per_sec, energy_per_crit, threshold, ratio = ignites + shocks, (
            energy_per_sec / (ignites + shocks) if ignites + shocks else 0.0), None, 1.0
    elif mode == "bossing":
        power = r["monster_power"]["unique_boss"]
        threshold = a.get("EnemyAilmentThreshold") or 0
        ratio = min(ts["cap"], crit_hit / threshold) if threshold else ts["cap"]
    else:
        # Mapping: one normal monster per crit (conservative: area hits on a pack would gain more).
        power, threshold, ratio = r["monster_power"]["normal"], None, ts["mapping_ratio"]
    if gem != "Cast on Elemental Ailment":
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
        "mode": mode, "gem": gem, "estimate": True, "verified": verified(r),
        "attack": {"hits_per_sec": uses * hit, "crit_chance": crit, "crits_per_sec": crits_per_sec,
                   "crit_hit": crit_hit, "dps": attack_dps},
        "energy": {"monster_power": power, "enemy_threshold": threshold, "threshold_ratio": ratio,
                   "per_crit": energy_per_crit, "to_fire": energy_to_fire},
        "casts_per_sec": casts_per_sec, "spells": per_spell,
        "trigger_dps": trigger_dps, "total_dps": attack_dps + trigger_dps,
    }


# ---------- Picking a Cast on Critical setup for a build ----------
# "Totemable", "Trappable", "Mineable" mean a skill CAN be used that way, so they don't rule anything out (they once did,
# leaving 3 spells out of ~100). A spell must carry PoB's "Triggerable" type to sit in a Cast on X gem.
NOT_TRIGGERABLE = {"Buff", "Aura", "Herald", "Meta", "Triggered", "InbuiltTrigger", "Minion", "Channel", "OngoingSkill",
                   "Persistent", "AppliesCurse", "Shapeshift", "Movement", "Travel"}   # no random teleports


def spell_candidates(catalog: list[dict]) -> list[str]:
    """Spells that can sit in Cast on Critical: damaging spells that need no particular weapon."""
    out = set()
    for s in catalog:
        types = set(s["types"])
        if ("Spell" in types and "Triggerable" in types and not types & NOT_TRIGGERABLE and not s.get("weapons")
                and not s.get("from_item")):
            out.add(s["name"])
    return sorted(out)


def best_cast_on_crit(pob: PoB, attack_group: int, catalog: list[dict], mode: str = "mapping", slots: int = 5,
                      gem_level: int = 20, min_gain: float = 0.03, shortlist: int = 3, log=lambda *a: None,
                      gem: str = "Cast on Critical", extra_spells: int = 2) -> dict | None:
    """Try a Cast on X meta gem (Cast on Critical by default) with the spell that does the most damage per point of
    energy, with its best supports; then try a 2nd and 3rd spell in place of a support (a spell takes a socket), kept
    only when the estimate rises. A second spell helps when the first is held back by its cooldown.

    Keeps the setup in the build (a new skill group) and returns it with its estimate, or removes it and returns
    None when the attack can't feed it (no crits / no ignite or shock), it doesn't fit in spirit, or it adds less
    than `min_gain` of the attack's damage."""
    from optimize import optimise_supports

    pob.send("set_main", group=attack_group)
    a = pob.calc(["CritChance", "HitChance", "IgniteChance", "ShockChance"])
    if not a.get("HitChance"):
        return None
    if gem == "Cast on Critical" and not a.get("CritChance"):
        return None
    if gem == "Cast on Elemental Ailment" and not ((a.get("IgniteChance") or 0) + (a.get("ShockChance") or 0)):
        log(f"{gem}: the skill applies no ignite or shock")
        return None
    spells = spell_candidates(catalog)
    if not spells:
        return None
    info = pob.send("gem_info", names=spells)["gems"]
    spells = [s for s in spells if s in info and info[s]["cast_time"] > 0]
    group = pob.add_skill([spells[0]], main=False)["group"]

    def estimate(gems: list[str]) -> dict:
        pob.try_skill(group, [*gems, gem], ["TotalDPS"], keep_main=True)
        pob.send("set_main", group=attack_group)
        return cast_on_crit(pob, attack_group, group, mode=mode, gem_level=gem_level, gem=gem)
    try:
        # Damage per energy: per-cast damage over base cast time (energy to fire is 100 per second of it).
        ranked = []
        for s in spells:
            res = pob.try_skill(group, [s], ["TotalDPS", "Speed"])
            o = res["output"]
            per_cast = (o.get("TotalDPS") or 0) / o["Speed"] if o.get("Speed") else 0
            if per_cast > 0:
                ranked.append((per_cast / info[s]["cast_time"], s))
        ranked.sort(reverse=True)
        best = None
        for _, s in ranked[:shortlist]:
            # The spell itself takes one of the meta gem's sockets: the rest are for supports.
            res = optimise_supports(pob, group, s, slots=max(1, slots - 1), metric="per_cast", log=lambda *a: None)
            if not res:
                continue
            value = res[0].score / info[s]["cast_time"]
            if not best or value > best[0]:
                best = (value, s, res[0].supports)
        if not best:
            log(f"{gem}: no spell scored ({len(ranked)} ranked of {len(spells)})")
            raise LookupError
        _, spell, supports = best
        spell_list, supports = [spell], list(supports)
        est = estimate([*spell_list, *supports])
        if (pob.calc(["SpiritUnreserved"]).get("SpiritUnreserved") or 0) < 0:
            log(f"{gem}: not enough spirit")
            raise LookupError   # the meta gem reserves spirit the build doesn't have
        # More spells: each takes a socket, so try it in place of each support (or in a free socket).
        for _ in range(extra_spells):
            trial = None
            for _, c in ranked[:shortlist + 4]:
                if c in spell_list:
                    continue
                drops = [None] if len(spell_list) + len(supports) < slots else list(supports)
                for drop in drops:
                    sup = [x for x in supports if x != drop]
                    e = estimate([*spell_list, c, *sup])
                    if e["trigger_dps"] > (trial[0]["trigger_dps"] if trial else est["trigger_dps"] * 1.03):
                        trial = (e, c, sup)
            if not trial:
                break
            est, c, supports = trial
            spell_list.append(c)
            log(f"{gem}: + {c} ({est['trigger_dps']:,.0f} DPS)")
        est = estimate([*spell_list, *supports])   # leave the group holding the chosen setup
        gain = est["trigger_dps"] / max(est["attack"]["dps"], 1)
        log(f"{gem} + {', '.join(spell_list)}: {est['trigger_dps']:,.0f} DPS ({gain:+.1%}), {est['casts_per_sec']:.2f} casts/s")
        if gain < min_gain:
            raise LookupError
        return {"gem": gem, "spell": spell_list[0], "spells": spell_list, "supports": supports, "group": group,
                "gain": gain, mode: est}
    except LookupError:
        pob.send("remove_skill", group=group)
        pob.send("set_main", group=attack_group)
        return None


def best_triggers(pob: PoB, attack_group: int, catalog: list[dict], mode: str = "mapping", slots: int = 5,
                  log=lambda *a: None) -> list[dict]:
    """Every Cast on X meta gem worth running beside the attack: Cast on Critical, then Cast on Elemental Ailment.
    Each fills its own energy from the same hits, so both can run at once (spirit permitting)."""
    out = []
    for gem in METAS:
        t = best_cast_on_crit(pob, attack_group, catalog, mode=mode, slots=slots, log=log, gem=gem)
        if t:
            out.append(t)
    return out
