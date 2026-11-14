"""Support gem optimiser: beam search over support gems for one skill, scored by PoB."""
from __future__ import annotations

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


def total_dps(out: dict) -> float:
    """All damage the build deals per second. PoB's Full DPS when available (every included
    skill, minion counts, damage over time); otherwise the main skill's hit + DoT + minion."""
    if out.get("FullDPS", 0) > 0:
        return out["FullDPS"]
    return (out.get("TotalDPS", 0) + out.get("TotalDotDPS", 0)
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
    return dps * area ** 0.5 * projectiles ** 0.5


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


def area_factor(out: dict) -> float:
    return max(out.get("AreaOfEffectMod", 1) or 1, 0.1) ** 0.5 * max(out.get("ProjectileCount", 1) or 1, 1) ** 0.5


def metric_for(mode: str, ailment: str | None = None) -> str:
    """The metric string every optimiser understands:
    "total", "mapping", "<ailment>" or "<ailment>+mapping" (e.g. "bleed+mapping")."""
    mapping = mode == "mapping"
    if ailment in AILMENT_FIELD:
        return f"{ailment}+mapping" if mapping else ailment
    return "mapping" if mapping else "total"


def score_of(out: dict, field_name: str) -> float:
    if field_name == "movement":
        # A movement skill: more uses per second, and cheaper to use. Damage doesn't matter here. Paying in life
        # (Bloodletting-style supports) is a cost too, not a saving.
        cost = sum(max(out.get(k, 0) or 0, 0) for k in ("ManaCost", "LifeCost", "ESCost"))
        return (out.get("Speed", 0) or 0) * 100 / (100 + cost)
    if field_name == "total":
        return total_dps(out)
    if field_name == "mapping":
        return clear_score(out)
    parts = field_name.split("+")
    ailment = next((p for p in parts if p in AILMENT_FIELD), None)
    if ailment:
        # An ailment build lives on its ailment: it counts fully, hits a quarter.
        base = ailment_dps(out, ailment) + 0.25 * hit_dps(out)
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
    fields = [*DPS_FIELDS, "CombinedDPS", "Life", "TotalEHP", *CLEAR_FIELDS] \
        + (["Speed", "ManaCost", "LifeCost", "ESCost"] if field_name == "movement" else
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
            solo[name] = score_of(res["output"], field_name)
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
