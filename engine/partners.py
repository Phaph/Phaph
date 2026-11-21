"""Partner combos: a skill whose damage depends on another skill being used first, scored as the player plays it.

Path of Building can show the payoff (a config box such as "# of Whirlwind Stages") but never sets it, so the payoff
skill was scored as if used alone and ranked far below where the ladder plays it (blind test, 2026-11-21: Twister
6.4k alone, ~4x that through a 3-stage whirlwind; Whirling Slash + Twister is the ladder's top Huntress pair).

A rule: the payoff skill, the setup skill (same weapon, added to the build only while measuring), the PoB config
var that holds the setup's stages, and the most stages one setup builds. One cycle = n setup uses, then one payoff
use that consumes them:

    cycle DPS = (n x setup damage per use + payoff damage per use at n stages) / (n / setup speed + 1 / payoff speed)

The best n (0 = payoff alone) wins; the payoff's DPS fields are scaled by cycle DPS / alone DPS. Conservative: the
setup gets the payoff's supports (no search of its own), only one payoff use per setup cycle, no elemental ground (Twister's
cold/fire/lightning bonus needs ground the build makes).
"""
from __future__ import annotations

PARTNERS = {
    # Whirling Slash: each slash adds a stage to its whirlwind, up to 3 (sandstorm_swipe_max_stages). Twister passing
    # through consumes it: Damage MORE per WhirlwindStages (PoB config whirlwindStages).
    "Twister": {"setup": "Whirling Slash", "var": "whirlwindStages", "max": 3},
}
DPS_FIELDS = ("TotalDPS", "CombinedDPS", "TotalDotDPS", "FullDPS", "FullDotDPS", "WithBleedDPS", "WithPoisonDPS",
              "WithIgniteDPS", "BleedDPS", "PoisonDPS", "IgniteDPS")


def _dps(out: dict) -> float:
    from optimize import total_dps
    return total_dps(out)


def cycle_dps(n: int, setup_dps: float, setup_speed: float, payoff_dps: float, payoff_speed: float) -> float:
    """DPS of n setup uses then one payoff use (payoff_dps measured at n stages)."""
    if n == 0:
        return payoff_dps
    if setup_speed <= 0 or payoff_speed <= 0:
        return 0.0
    damage = n * setup_dps / setup_speed + payoff_dps / payoff_speed
    return damage / (n / setup_speed + 1 / payoff_speed)


def apply_partner(p, skill: str, group: int, out: dict, fields: list[str],
                  supports: list[str] | None = None) -> tuple[dict, dict | None]:
    """(out with the payoff's DPS fields scaled to the best cycle, the partner note or None).

    supports: the payoff's own supports, also put on the setup (both use the same weapon; PoB ignores the ones that
    can't support it). Players support their setup skill too (attack speed), so a bare setup skill read far too slow.
    Leaves the build as it found it: the setup group is removed and the config var cleared."""
    rule = PARTNERS.get(skill)
    if not rule:
        return out, None
    alone = _dps(out)
    speed = out.get("Speed") or 0
    if alone <= 0 or speed <= 0:
        return out, None
    staged = {}
    try:
        for n in range(1, rule["max"] + 1):
            p.set_config(**{rule["var"]: n})
            staged[n] = _dps(p.calc(fields))
    finally:
        p.set_config(**{rule["var"]: 0})
    sg = p.add_skill([rule["setup"], *(supports or [])], main=False)["group"]
    try:
        p.send("set_main", group=sg)
        so = p.calc(fields)
        s_dps, s_speed = _dps(so), so.get("Speed") or 0
    finally:
        p.send("set_main", group=group)
        p.remove_skill(sg)
    import os
    if os.environ.get("PARTNER_DEBUG"):
        print(f"partner {skill}: alone {alone:.0f} @ {speed:.2f}/s, staged {staged}, setup {s_dps:.0f} @ {s_speed:.2f}/s")
    best_n, best = 0, alone
    for n, d in staged.items():
        c = cycle_dps(n, s_dps, s_speed, d, speed)
        if c > best:
            best_n, best = n, c
    if best_n == 0:
        return out, None
    f = best / alone
    scaled = dict(out)
    for k in DPS_FIELDS:
        if isinstance(scaled.get(k), (int, float)):
            scaled[k] = scaled[k] * f
    note = {"setup": rule["setup"], "stages": best_n, "factor": round(f, 3),
            "why": f"{best_n} {rule['setup']} use(s) build the whirlwind, then {skill} consumes it "
                   f"(x{staged[best_n] / alone:.2f} per use; x{f:.2f} DPS over the whole cycle)"}
    return scaled, note


# Infusions (task 21, 2026-11-21). Some spells have an infused version (a PoB stat set such as Ice Nova's
# "Cold-Infused", or Arc's config box) that needs an Infusion of their element, which a generator skill leaves behind:
# Frost Bomb one Cold Infusion per use (6 s cooldown), Orb of Storms one Lightning Infusion when the orb expires
# (12 s). One cycle of T seconds (the generator's cooldown or duration): one generator cast, one infused cast, plain
# casts the rest of the time:
#     cycle DPS = (infused damage per cast + (T - 2 / cast rate) x cast rate x plain damage per cast) / T
# Conservative: the generator's own damage and Frost Bomb's Exposure count as nothing here; one infusion per period.
# Fire infusions (Comet, Ball Lightning) come from Living Bomb / Siphon Elements / Verisium, which need kills,
# ailments or Ward: not modelled yet.
INFUSIONS = {
    "Ice Nova": {"element": "cold", "part": 2},
    "Arc": {"element": "lightning", "config": "arcLightningInfused"},
}
GENERATORS = {"cold": ["Frost Bomb"], "lightning": ["Orb of Storms"]}


def infusion_cycle(infused_dps: float, plain_dps: float, speed: float, period: float) -> float:
    if speed <= 0 or period <= 0:
        return plain_dps
    plain_casts = max(period - 2 / speed, 0) * speed
    return (infused_dps / speed + plain_casts * plain_dps / speed) / period


def apply_infusion(p, skill: str, group: int, out: dict, fields: list[str]) -> tuple[dict, dict | None]:
    rule = INFUSIONS.get(skill)
    if not rule:
        return out, None
    alone, speed = _dps(out), out.get("Speed") or 0
    if alone <= 0 or speed <= 0:
        return out, None
    try:
        if rule.get("part"):
            p.send("set_part", group=group, part=rule["part"])
        else:
            p.set_config(**{rule["config"]: True})
        infused = _dps(p.calc(fields))
    finally:
        if rule.get("part"):
            p.send("set_part", group=group, part=1)
        else:
            p.set_config(**{rule["config"]: False})
    best, best_gen, best_T = alone, None, None
    for gen in GENERATORS.get(rule["element"], []):
        gg = p.add_skill([gen], main=False)["group"]
        try:
            p.send("set_main", group=gg)
            go = p.calc(["Cooldown", "Duration"])
        finally:
            p.send("set_main", group=group)
            p.remove_skill(gg)
        period = go.get("Cooldown") or go.get("Duration") or 0
        c = infusion_cycle(infused, alone, speed, period)
        if c > best:
            best, best_gen, best_T = c, gen, period
    if not best_gen:
        return out, None
    f = best / alone
    scaled = {k: (v * f if k in DPS_FIELDS and isinstance(v, (int, float)) else v) for k, v in out.items()}
    return scaled, {"setup": best_gen, "factor": round(f, 3), "infused": round(infused / alone, 2),
                    "why": f"{best_gen} leaves a {rule['element'].title()} Infusion every {best_T:.1f} s; one "
                           f"{skill} cast in each cycle is infused (x{infused / alone:.2f}), x{f:.2f} DPS overall"}
