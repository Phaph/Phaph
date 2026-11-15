"""Support gem optimiser: beam search over support gems for one skill, scored by PoB."""
from __future__ import annotations

import re

import time
from dataclasses import dataclass, field

from pob import PoB

METRICS = {
    "hit": "TotalDPS",       # hit DPS only
    "total": "total",        # hits plus ailments and DoTs
    "combined": "CombinedDPS",  # PoB's combined number (skips DoT for some skills, e.g. Rake)
}


METRICS["mapping"] = "mapping"   # clear score: hit-weighted DPS x sqrt(area) x sqrt(projectiles)
CLEAR_FIELDS = ["AreaOfEffectMod", "ProjectileCount"]
DPS_FIELDS = ["TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "BleedDPS",
              "PoisonDPS", "IgniteDPS", "MinionBleedDPS", "MinionPoisonDPS", "MinionIgniteDPS"]

# PoB config for each mode. Bossing is PoB's default (pinnacle boss).
MODE_CONFIG = {
    "bossing": {"enemyIsBoss": "Pinnacle"},
    "mapping": {"enemyIsBoss": "None"},
}


# The guard against impossible numbers. When Path of Building's maths breaks (something divides by zero or grows
# without limit) a skill comes back infinite, not a number, or stuck at 2,147,483,647, the most a 32-bit counter
# holds; poe.ninja's "2 billion DPS" builds are this. No real build is near it, so such a number scores zero and
# can never win a search.
IMPOSSIBLE_DPS = 2.0e9
# One support gem multiplying damage by more than this is a calculation error, not a real interaction.
IMPOSSIBLE_SUPPORT_GAIN = 1000


def impossible(x) -> bool:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return True
    return x != x or x in (float("inf"), float("-inf")) or abs(x) >= IMPOSSIBLE_DPS


def _sane(v: float) -> float:
    return 0.0 if impossible(v) else v


def broken_numbers(out: dict) -> list[str]:
    """The damage fields in a PoB output that are impossible (see IMPOSSIBLE_DPS)."""
    return [k for k, v in out.items() if ("DPS" in k or k.endswith("Dot")) and isinstance(v, (int, float)) and impossible(v)]


def total_dps(out: dict) -> float:
    """All damage the build deals per second. PoB's Full DPS when available (every included
    skill, minion counts, damage over time); otherwise the main skill's hit + DoT + minion."""
    if out.get("FullDPS", 0) > 0:
        return _sane(out["FullDPS"])
    return _sane(out.get("TotalDPS", 0) + out.get("TotalDotDPS", 0)
                 + out.get("MinionDPS", 0) + out.get("MinionDotDPS", 0))


def clear_score(out: dict) -> float:
    """Rough map clear value. PoB has no clear speed stat, so: hits count fully, damage over
    time half (it ramps up), and bigger area / more projectiles reach more of the pack."""
    if out.get("FullDPS", 0) > 0:
        dps = out["FullDPS"] - 0.5 * out.get("FullDotDPS", 0)
    else:
        dps = (out.get("TotalDPS", 0) + 0.5 * out.get("TotalDotDPS", 0)
               + out.get("MinionDPS", 0) + 0.5 * out.get("MinionDotDPS", 0))
    area = max(out.get("AreaOfEffectMod", 1) or 1, 0.1)
    projectiles = max(out.get("ProjectileCount", 1) or 1, 1)
    return _sane(dps * area ** 0.5 * projectiles ** 0.5)


AILMENT_FIELD = {"bleed": "BleedDPS", "poison": "PoisonDPS", "ignite": "IgniteDPS"}
# The same ailments dealt by minions: PoB keeps minion damage in its own output (runner.lua exposes it as Minion*).
MINION_AILMENT_FIELDS = ["Minion" + f for f in AILMENT_FIELD.values()]


def ailment_dps(out: dict, ailment: str) -> float:
    """An ailment's damage per second from the player and their minions together."""
    f = AILMENT_FIELD[ailment]
    return (out.get(f, 0) or 0) + (out.get("Minion" + f, 0) or 0)


def hit_dps(out: dict) -> float:
    """Hit damage per second from the player and their minions."""
    return (out.get("TotalDPS", 0) or 0) + (out.get("MinionDPS", 0) or 0)


AILMENT_TARGET = 0.4   # an ailment build gets at least this share of its damage from the ailment (themes.py)


def ailment_score(out: dict, ailment: str) -> float:
    """An ailment build's score: the ailment counts fully, hits a quarter, and below AILMENT_TARGET of the damage the
    score falls in proportion. Without that last part a big enough hit build wins with no ailment at all (a crossbow
    "bleed" build that buys elemental damage), and the tree, gear and supports all follow the score away from it."""
    a, h = max(ailment_dps(out, ailment), 0), max(hit_dps(out), 0)
    share = a / (a + h) if a + h > 0 else 0.0
    return (a + 0.25 * h) * min(1.0, share / AILMENT_TARGET)


def area_factor(out: dict) -> float:
    return max(out.get("AreaOfEffectMod", 1) or 1, 0.1) ** 0.5 * max(out.get("ProjectileCount", 1) or 1, 1) ** 0.5


def metric_for(mode: str, ailment: str | None = None, goals=None) -> str:
    """The metric string every optimiser understands:
    "total", "mapping", "<ailment>" or "<ailment>+mapping" (e.g. "bleed+mapping"), plus "+<focus>" for each stat
    focus the player asked for (goals.FOCUS, e.g. "bleed+crit+speed")."""
    from goals import FOCUS
    mapping = mode == "mapping"
    if ailment in AILMENT_FIELD:
        m = f"{ailment}+mapping" if mapping else ailment
    else:
        m = "mapping" if mapping else "total"
    return m + "".join(f"+{g}" for g in (goals or ()) if g in FOCUS)


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
ELEMENT_TYPES = {"Fire", "Cold", "Lightning", "Chaos"}


def damage_types(types) -> set[str]:
    """A skill's damage types. Attacks with no element tag hit with the weapon's physical damage, so they count as
    physical (crossbow ammo, most bow and melee attacks carry no "Physical" tag in PoB)."""
    types = set(types)
    if "Attack" in types and not types & ELEMENT_TYPES:
        types.add("Physical")
    return types


def seed_ailment(pob: PoB, group: int, active: str, ailment: str | None, keep_main: bool = False) -> str | None:
    """Put the strongest compatible ailment support (e.g. Bleed IV) on the skill before gear and passives are chosen.
    Without it the skill has no ailment chance, its ailment damage is zero, and gear and tree would chase hit damage
    of any element (a crossbow bleed build would buy lightning). The support search later re-picks freely."""
    if ailment not in AILMENT_FIELD:
        return None
    compatible = pob.send("compatible_supports", group=group).get("supports") or []
    pattern = re.compile(rf"{ailment.capitalize()} (I|II|III|IV|V)")
    # The tier that gives the most ailment chance (Bleed IV, for one, applies no bleed by itself in PoB); ties go to
    # the higher tier.
    chance_field = ailment.capitalize() + "Chance"
    tried = []
    for n in (n for n in compatible if pattern.fullmatch(n)):
        out = pob.try_skill(group, [active, n], [chance_field], keep_main=keep_main)["output"]
        tried.append(((out.get(chance_field) or 0), ROMAN[n.split()[-1]], n))
    best = max(tried, default=None)
    if best and best[0] > 0:
        pob.try_skill(group, [active, best[2]], ["TotalDPS"], keep_main=keep_main)
        return best[2]
    pob.try_skill(group, [active], ["TotalDPS"], keep_main=keep_main)
    return None


def split_focus(field_name: str) -> tuple[str, list[str]]:
    """("bleed+mapping+crit") -> ("bleed+mapping", ["crit"])."""
    from goals import FOCUS
    parts = field_name.split("+")
    keep = [p for p in parts if p not in FOCUS] or ["total"]
    return "+".join(keep), [p for p in parts if p in FOCUS]


def score_of(out: dict, field_name: str) -> float:
    return _sane(_score_of(out, field_name))


def _score_of(out: dict, field_name: str) -> float:
    if field_name == "movement":
        # A movement skill: more uses per second, and cheaper to use. Damage doesn't matter here. Paying in life
        # (Bloodletting-style supports) is a cost too, not a saving.
        cost = sum(max(out.get(k, 0) or 0, 0) for k in ("ManaCost", "LifeCost", "ESCost"))
        return (out.get("Speed", 0) or 0) * 100 / (100 + cost)
    if field_name == "per_cast":
        # Damage per cast, for a spell fired by Cast on X: cast speed doesn't matter there, only how hard it hits.
        speed = out.get("Speed") or 0
        return (out.get("TotalDPS") or 0) / speed if speed > 0 else 0.0
    rest, focus = split_focus(field_name)
    if focus:
        from goals import focus_factor
        return _score_of(out, rest) * focus_factor(out, focus)
    if field_name == "total":
        return total_dps(out)
    if field_name == "mapping":
        return clear_score(out)
    parts = field_name.split("+")
    ailment = next((p for p in parts if p in AILMENT_FIELD), None)
    if ailment:
        base = ailment_score(out, ailment)
        return base * area_factor(out) if "mapping" in parts else base
    return out.get(field_name, 0)


@dataclass
class Result:
    supports: list[str]
    score: float
    output: dict = field(default_factory=dict)


def optimise_supports(
    pob: PoB,
    group: int,
    active: str,
    slots: int = 5,
    metric: str = "total",
    beam: int = 3,
    candidates: list[str] | None = None,
    min_gain: float = 0.005,
    top_k: int = 15,
    allow_conditional: bool = False,
    exclude: set[str] | None = None,
    shortlist: dict | None = None,
    keep_main: bool = False,
    log=print,
) -> list[Result]:
    """Find the support set that maximises `metric` for the skill in `group`.

    Rules respected: one gem per gem family (e.g. only one of Bleed I-IV),
    a support only counts if PoB says it actually supports the skill, and
    combos that trigger a PoB rule warning (e.g. lineage copy limit) are rejected.
    `exclude` holds supports already used elsewhere in the build.
    Conditional supports (Hit and Run, Glory gems, combo finishers...) are skipped
    unless allow_conditional, because PoB counts their bonus but not their downtime.
    Only the `top_k` best supports from screening go into the combination search.
    Pass the same `shortlist` dict to later calls for the same skill to skip the full screen
    and only re-check the 2 x top_k best supports from the first one.
    """
    field_name = METRICS.get(metric, metric)
    from goals import FOCUS_FIELDS
    fields = [*DPS_FIELDS, "CombinedDPS", "Life", "TotalEHP", *CLEAR_FIELDS, *FOCUS_FIELDS] \
        + (["Speed", "ManaCost", "LifeCost", "ESCost"] if field_name == "movement" else ["Speed"] if field_name == "per_cast" else
           [] if field_name in ("total", "mapping") or "+" in field_name or field_name in AILMENT_FIELD else [field_name])
    gems = pob.list_gems("support")
    family = {g["name"]: g.get("family") or g["name"] for g in gems}
    skip = set(exclude or ())
    if not allow_conditional:
        skip |= {g["name"] for g in gems if g.get("conditional")}
    pool = [n for n in (candidates or [g["name"] for g in gems]) if n not in skip]
    # PoB's own type rules rule out most supports for any given skill without a calculation.
    compatible = pob.send("compatible_supports", group=group).get("supports")
    if isinstance(compatible, list) and compatible:
        allowed = set(compatible)
        pool = [n for n in pool if n in allowed]
    shortlist_key = (active, metric)
    if shortlist is not None and shortlist_key in shortlist:
        pool = [n for n in shortlist[shortlist_key] if n not in skip]

    t0 = time.time()
    base = pob.try_skill(group, [active], fields, keep_main=keep_main)
    base_score = score_of(base["output"], field_name)
    log(f"Base {active}: {metric} DPS = {base_score:,.0f}")

    # Screen every support once on its own: drop ones that don't support the skill or add nothing.
    solo = {}
    for name in pool:
        res = pob.try_skill(group, [active, name], fields, keep_main=keep_main)
        if res["supported"].get(name):  # skip gems PoB says don't apply
            sc = score_of(res["output"], field_name)
            if base_score > 0 and sc > base_score * IMPOSSIBLE_SUPPORT_GAIN:
                log(f"  {name}: skipped, a {sc / base_score:,.0f}x jump is a calculation error")
                continue
            solo[name] = sc
    ranked = sorted((n for n, s in solo.items() if s > base_score * (1 + min_gain)), key=lambda n: -solo[n])
    if shortlist is not None and shortlist_key not in shortlist and ranked:
        shortlist[shortlist_key] = ranked[: top_k * 2]
    useful = ranked[:top_k]
    log(f"Screened {len(pool)} supports in {time.time() - t0:.1f}s, {len(useful)} add damage")
    for n in useful[:10]:
        log(f"  {n:<32} {solo[n] / max(base_score, 1e-9) - 1:+.0%}")

    frontier = [Result([], base_score, base["output"])]
    best = frontier[0]
    for depth in range(slots):
        scored: dict[tuple, Result] = {}
        for state in frontier:
            used_families = {family[s] for s in state.supports}
            for name in useful:
                if name in state.supports or family[name] in used_families:
                    continue
                combo = tuple(sorted(state.supports + [name]))
                if combo in scored:
                    continue
                res = pob.try_skill(group, [active, *combo], fields, keep_main=keep_main)
                if not all(res["supported"].get(s) for s in combo) or res.get("warnings"):
                    continue
                scored[combo] = Result(list(combo), score_of(res["output"], field_name), res["output"])
        if not scored:
            break
        frontier = sorted(scored.values(), key=lambda r: -r.score)[:beam]
        if frontier[0].score <= best.score * (1 + min_gain):
            break
        best = frontier[0]
        log(f"{depth + 1} supports: {best.score:,.0f} ({best.score / max(base_score, 1e-9):.2f}x) {best.supports}")

    # Leave the build holding the winning setup.
    pob.try_skill(group, [active, *best.supports], fields, keep_main=keep_main)
    log(f"Done in {time.time() - t0:.1f}s")
    return frontier
