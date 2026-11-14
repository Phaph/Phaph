"""Build goals beyond damage. Players tick these when they create a build:

    movement  "Faster mapping": movement speed is worth real damage (time is money).
    rarity    "More loot": item rarity on gear and passives.
    tanky     "Tankier": effective HP counts for much more.

Each goal becomes a weight in every optimiser's score, so gear, passives and spirit trade
some damage for it. Weights are ours, not PoB's: e.g. with "movement", +10% movement speed is
worth about as much as +6% damage.
"""
from __future__ import annotations

GOAL_LABELS = {"movement": "Faster mapping (movement speed)", "rarity": "More loot (item rarity)",
               "tanky": "Tankier (more effective HP)"}
GOAL_FIELDS = ["EffectiveMovementSpeedMod", "EffectiveLootRarityMod"]


def weights(goals) -> dict:
    """Score weights for a set of goals: relative movement speed, relative loot rarity, and a
    multiplier on the defence weight."""
    g = set(goals or [])
    unknown = g - set(GOAL_LABELS)
    if unknown:
        raise ValueError(f"Unknown goals {sorted(unknown)}. Options: {sorted(GOAL_LABELS)}")
    return {
        "movement": 0.6 if "movement" in g else 0.0,
        "rarity": 0.15 if "rarity" in g else 0.0,
        "def_mult": 2.5 if "tanky" in g else 1.0,
    }


def goal_terms(out: dict, base: dict, w: dict) -> float:
    """Extra score for movement speed and rarity gained between `base` and `out`."""
    s = 0.0
    if w.get("movement"):
        m0 = max(base.get("EffectiveMovementSpeedMod", 1) or 1, 0.1)
        s += w["movement"] * (out.get("EffectiveMovementSpeedMod", m0) - m0) / m0
    if w.get("rarity"):
        r0 = max(base.get("EffectiveLootRarityMod", 1) or 1, 0.1)
        s += w["rarity"] * (out.get("EffectiveLootRarityMod", r0) - r0) / r0
    return s


# Movement skills: PoB can't score how they feel, so we recommend by rule. Skills that work
# with any weapon first, then ones the build's weapon can use.
def mobility_skills(catalog: list[dict], weapon_type: str | None, limit: int = 2) -> list[str]:
    picks = []
    for s in catalog:
        types = set(s["types"])
        if not types & {"Travel", "Movement"} or s.get("from_item"):
            continue
        if types & {"Triggered", "InbuiltTrigger"}:
            continue
        weapons = [w for w in s["weapons"] if w != "None"]
        if weapons and weapon_type not in weapons:
            continue
        # Prefer weapon-free skills and dodge-style movement, which work in every build.
        rank = (0 if not weapons else 1, 0 if "DodgeReplacement" in types else 1, s["name"])
        picks.append((rank, s["name"]))
    seen, out = set(), []
    for _, name in sorted(picks):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out[:limit]
