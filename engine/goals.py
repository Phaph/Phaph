"""Build goals beyond damage. Players tick these when they create a build:

    movement  "Faster mapping": movement speed is worth real damage (time is money).
    rarity    "More loot": item rarity on gear and passives.
    tanky     "Tankier": effective HP counts for much more.
    crit      "Critical hits": a crit build. It changes the build's metric (optimize.metric_for), so the
              skill pick, supports, tree, gear and jewels all value crit chance on top of its damage.

Each goal becomes a weight in every optimiser's score, so gear, passives and spirit trade
some damage for it. Weights are ours, not PoB's: e.g. with "movement", +10% movement speed is
worth about as much as +6% damage.
"""
from __future__ import annotations

# Stat focuses: "crit", "cast speed", "energy shield"... The player wants the build built around that stat, so it
# becomes part of the build's metric (optimize.metric_for "+<key>"): every optimiser scores
# damage x (1 + stat / scale), capped at x2. runner.lua has the same table for the passive tree.
# key: (PoB output fields (the highest counts), scale, label, minimum the finished build should reach or None)
FOCUS = {
    "crit": (["CritChance"], 100, "Critical hits (crit chance)", 40),
    "speed": (["Speed"], 6, "Attack / cast speed", None),
    "block": (["BlockChance", "SpellBlockChance"], 75, "Block chance", 30),
    "es": (["EnergyShield"], 8000, "Energy shield", 1000),
    "life": (["Life"], 6000, "Life", None),
    "armour": (["Armour"], 30000, "Armour", 3000),
    "evasion": (["Evasion"], 30000, "Evasion", 3000),
    "leech": (["LifeLeechRate"], 1500, "Life leech", None),
    "regen": (["LifeRegen"], 500, "Life regeneration", None),
    "mana": (["Mana"], 4000, "Mana", None),
    "str": (["Str"], 400, "Strength", None),
    "dex": (["Dex"], 400, "Dexterity", None),
    "int": (["Int"], 400, "Intelligence", None),
    "spirit": (["Spirit"], 400, "Spirit", None),
}
FOCUS_FIELDS = sorted({f for fields, *_ in FOCUS.values() for f in fields})
GOAL_LABELS = {"movement": "Faster mapping (movement speed)", "rarity": "More loot (item rarity)",
               "tanky": "Tankier (more effective HP)", **{k: v[2] for k, v in FOCUS.items()}}
GOAL_FIELDS = ["EffectiveMovementSpeedMod", "EffectiveLootRarityMod", *FOCUS_FIELDS]


def focus_value(out: dict, key: str) -> float:
    return max((out.get(f) or 0) for f in FOCUS[key][0])


def focus_factor(out: dict, keys) -> float:
    """Damage multiplier for a build's stat focuses: 1 + stat / scale each, capped at x2."""
    m = 1.0
    for k in keys:
        if k in FOCUS:
            m *= 1 + min(max(focus_value(out, k), 0), FOCUS[k][1]) / FOCUS[k][1]
    return m


def weights(goals) -> dict:
    """Score weights for a set of goals: relative movement speed, relative loot rarity, and a
    multiplier on the defence weight."""
    g = set(goals or [])
    unknown = g - set(GOAL_LABELS)
    if unknown:
        raise ValueError(f"Unknown goals {sorted(unknown)}. Options: {sorted(GOAL_LABELS)}")
    return {
        "movement": 0.6 if "movement" in g else 0.0,
        "rarity": 0.4 if "rarity" in g else 0.0,   # asked for loot: +15% rarity is worth about +6% damage
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
def mobility_skills(catalog: list[dict], weapon_type: str | None, limit: int = 2,
                    offhand_type: str | None = None) -> list[str]:
    picks = []
    for s in catalog:
        types = set(s["types"])
        if not types & {"Travel", "Movement"} or s.get("from_item"):
            continue
        if types & {"RequiresShield", "RequiresBuckler"} and offhand_type != "Shield":
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
