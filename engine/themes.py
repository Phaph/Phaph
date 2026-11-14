"""Theme checks: does the finished build still deliver what the player asked for?

The theme drives every optimiser (optimize.metric_for), but the result is still checked:
a "bleed" build whose damage mostly isn't bleed has failed its brief, however strong it is.
"""
from __future__ import annotations

from optimize import AILMENT_FIELD, total_dps

AILMENT_MIN_SHARE = 0.4   # at least 40% of damage from the theme's ailment


def check(spec: dict, stats: dict, catalog: list[dict]) -> list[str]:
    issues = []
    ailment = spec.get("ailment")
    total = max(total_dps(stats), 1)
    if ailment in AILMENT_FIELD:
        share = stats.get(AILMENT_FIELD[ailment], 0) / total
        if share < AILMENT_MIN_SHARE:
            issues.append(f"Only {share:.0%} of damage is {ailment}; a {ailment} build should be at least "
                          f"{AILMENT_MIN_SHARE:.0%}.")
    skills = {s["name"]: set(s["types"]) for s in catalog}
    types = skills.get(spec["skill"], set())
    for d in spec.get("damage") or []:
        if d.capitalize() not in types:
            issues.append(f"{spec['skill']} is not a {d} skill.")
    for k in spec.get("kinds") or []:
        if k.lower() == "minion" and "Minion" not in types:
            issues.append(f"{spec['skill']} is not a minion skill.")
    return issues
