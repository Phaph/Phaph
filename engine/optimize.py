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


def total_dps(out: dict) -> float:
    """Hit DPS plus damage over time (bleed, ignite, poison, DoT skills)."""
    return out.get("TotalDPS", 0) + out.get("TotalDotDPS", 0)


def score_of(out: dict, field_name: str) -> float:
    return total_dps(out) if field_name == "total" else out.get(field_name, 0)


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
    log=print,
) -> list[Result]:
    """Find the support set that maximises `metric` for the skill in `group`.

    Rules respected: one gem per gem family (e.g. only one of Bleed I-IV),
    a support only counts if PoB says it actually supports the skill.
    """
    field_name = METRICS.get(metric, metric)
    fields = ["TotalDPS", "TotalDotDPS", "CombinedDPS", "Life", "TotalEHP"] + ([] if field_name == "total" else [field_name])
    gems = pob.list_gems("support")
    family = {g["name"]: g.get("family") or g["name"] for g in gems}
    pool = candidates or [g["name"] for g in gems]

    t0 = time.time()
    base = pob.try_skill(group, [active], fields)
    base_score = score_of(base["output"], field_name)
    log(f"Base {active}: {metric} DPS = {base_score:,.0f}")

    # Screen every support once on its own: drop ones that don't support the skill or add nothing.
    solo = {}
    for name in pool:
        res = pob.try_skill(group, [active, name], fields)
        if res["supported"].get(name):  # skip gems PoB says don't apply
            solo[name] = score_of(res["output"], field_name)
    useful = sorted((n for n, s in solo.items() if s > base_score * (1 + min_gain)), key=lambda n: -solo[n])
    log(f"Screened {len(pool)} supports in {time.time() - t0:.1f}s, {len(useful)} add damage")
    for n in useful[:10]:
        log(f"  {n:<32} {solo[n] / base_score - 1:+.0%}")

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
                res = pob.try_skill(group, [active, *combo], fields)
                if not all(res["supported"].get(s) for s in combo):
                    continue
                scored[combo] = Result(list(combo), score_of(res["output"], field_name), res["output"])
        if not scored:
            break
        frontier = sorted(scored.values(), key=lambda r: -r.score)[:beam]
        if frontier[0].score <= best.score * (1 + min_gain):
            break
        best = frontier[0]
        log(f"{depth + 1} supports: {best.score:,.0f} ({best.score / base_score:.2f}x) {best.supports}")

    # Leave the build holding the winning setup.
    pob.try_skill(group, [active, *best.supports], fields)
    log(f"Done in {time.time() - t0:.1f}s")
    return frontier
