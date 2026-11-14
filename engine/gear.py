"""Gear crafter: builds a rare item for every slot, scored by PoB for this exact build.

For each slot it picks the best base, then adds affixes one at a time (max 3 prefixes,
3 suffixes), each time choosing the affix that adds the most value:
    relative DPS gain + def_weight * relative EHP gain + res_weight * resistance deficit closed
The result is a per-slot shopping list: base type and affixes in priority order with
target values, which works as a trade search for players.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from goals import GOAL_FIELDS, goal_terms, weights as goal_weights
from optimize import CLEAR_FIELDS, DPS_FIELDS, clear_score, score_of, total_dps
from pob import PoB, PoBError

ARMOUR_SLOTS = {"Helmet": "Helmet", "Body Armour": "Body Armour", "Gloves": "Gloves", "Boots": "Boots"}
JEWELLERY_SLOTS = {"Amulet": "Amulet", "Ring 1": "Ring", "Ring 2": "Ring", "Belt": "Belt"}
RES_CAP = 75
SCORE_FIELDS = [*DPS_FIELDS, "TotalEHP", "Life", "FireResist", "ColdResist", "LightningResist",
                "ChaosResist", *CLEAR_FIELDS, *GOAL_FIELDS]
# Affix groups that never matter for a build score.
SKIP_GROUPS = {"ItemFoundRarityIncrease", "LocalAttributeRequirements", "LightRadius", "LocalLightRadius"}


@dataclass
class Stage:
    key: str
    name: str
    level: int          # character level for this stage
    item_level: int     # highest affix level available
    roll: float         # where in each affix's range the target value sits (0 = min, 1 = max)
    tier_drop: int      # tiers below the best available (budget)
    max_affixes: int    # how many good affixes a typical item has at this budget
    budget: str
    budget_key: str = "unlimited"


@dataclass(frozen=True)
class Budget:
    key: str
    label: str
    roll: float
    tier_drop: int
    max_affixes: int


# Ordered cheapest to most expensive. The player picks one up front; no stage goes above it.
BUDGETS = {
    "free": Budget("free", "Free, self-found", 0.35, 2, 3),
    "budget": Budget("budget", "Budget, up to ~5 divine", 0.5, 1, 4),
    "medium": Budget("medium", "Medium, ~5-30 divine", 0.6, 0, 5),
    "high": Budget("high", "High, ~30-100 divine", 0.8, 0, 6),
    "unlimited": Budget("unlimited", "No limit, 100+ divine", 0.95, 0, 6),
}
BUDGET_ORDER = list(BUDGETS)

# key: (name, character level, item level, the budget this stage would use with no cap)
STAGE_DEFS = {
    "leveling": ("Leveling (campaign)", 55, 55, "free"),
    "early": ("Early maps (league start)", 75, 70, "budget"),
    "mid": ("Mid maps", 90, 82, "medium"),
    "end": ("Endgame", 95, 82, "unlimited"),
}


def make_stage(key: str, budget: str = "unlimited") -> Stage:
    """A stage with its gear capped at the player's budget."""
    if budget not in BUDGETS:
        raise ValueError(f"budget must be one of {BUDGET_ORDER}")
    name, level, ilvl, natural = STAGE_DEFS[key]
    tier = BUDGETS[min(natural, budget, key=BUDGET_ORDER.index)]
    return Stage(key, name, level, ilvl, tier.roll, tier.tier_drop, tier.max_affixes, tier.label, tier.key)


STAGES = {k: make_stage(k) for k in STAGE_DEFS}


@dataclass
class SlotPlan:
    slot: str
    base: str
    affixes: list[str] = field(default_factory=list)   # in priority order, with target values
    raw: str = ""
    unique: str | None = None       # unique item name when a unique beats the crafted rare
    price_note: str | None = None   # e.g. "price unknown" until poe.ninja prices are loaded


def _value_at(text: str, roll: float) -> str:
    """'+(50-69) to maximum Life' at roll 0.5 -> '+60 to maximum Life'."""
    def sub(m):
        lo, hi = float(m.group(1)), float(m.group(2))
        v = lo + (hi - lo) * roll
        decimals = "." in m.group(1) or "." in m.group(2)
        return f"{v:.1f}" if decimals else str(int(round(v)))
    return re.sub(r"\((-?[\d.]+)-(-?[\d.]+)\)", sub, text)


def _res_deficit(out: dict) -> float:
    return sum(max(0, RES_CAP - out.get(k, -60)) for k in ("FireResist", "ColdResist", "LightningResist")) \
        + 0.5 * max(0, -out.get("ChaosResist", 0))


class Scorer:
    def __init__(self, def_weight: float = 0.4, res_weight: float = 0.006, mode: str = "bossing",
                 metric: str | None = None, goals=None):
        self.goal_w = goal_weights(goals)
        self.def_weight = def_weight * self.goal_w["def_mult"]
        self.res_weight = res_weight
        if metric:
            self.dps = lambda out: score_of(out, metric)
        else:
            self.dps = clear_score if mode == "mapping" else total_dps

    def __call__(self, out: dict, base: dict) -> float:
        d0 = max(self.dps(base), 1)
        e0 = max(base.get("TotalEHP", 0), 1)
        d = self.dps(out)
        return ((d - d0) / d0
                + self.def_weight * (out.get("TotalEHP", 0) - e0) / e0
                + self.res_weight * (_res_deficit(base) - _res_deficit(out))
                + goal_terms(out, base, self.goal_w))


def _item_raw(title: str, base: str, lines: list[str]) -> str:
    return "\n".join(["Rarity: Rare", title, base, *lines])


def _tier_choices(affixes: list[dict], stage: Stage, keep: set[str] = frozenset()) -> dict[str, dict]:
    """One affix per group: the best tier available at this stage, minus tier_drop.
    `keep` re-allows skipped groups (e.g. item rarity when the player wants more loot)."""
    by_group: dict[str, list[dict]] = {}
    for a in affixes:
        if a["group"] in SKIP_GROUPS - keep:
            continue
        by_group.setdefault(a["group"], []).append(a)
    chosen = {}
    for group, tiers in by_group.items():
        tiers.sort(key=lambda a: a["level"])
        chosen[group] = tiers[max(0, len(tiers) - 1 - stage.tier_drop)]
    return chosen


@dataclass
class _Work:
    """An item being crafted."""
    slot: str
    base: str
    title: str
    options: dict
    lines: list = field(default_factory=list)
    picked: list = field(default_factory=list)
    counts: dict = field(default_factory=lambda: {"Prefix": 0, "Suffix": 0})
    meta: list = field(default_factory=list)   # (group, affix, lines) per pick, in order
    unique: str | None = None
    unique_raw: str | None = None
    price_note: str | None = None

    def raw(self, extra: list[str] | None = None) -> str:
        if self.unique_raw:
            return self.unique_raw
        return _item_raw(self.title, self.base, self.lines + (extra or []))

    def has_room(self, stage: "Stage", kind: str) -> bool:
        if self.unique_raw:
            return False
        return len(self.picked) < stage.max_affixes and self.counts[kind] < 3


def _is_res_group(group: str) -> bool:
    return "Resist" in group and "Penetration" not in group and "Minion" not in group and "Allies" not in group


def _add(work: _Work, group: str, affix: dict, lines: list[str]) -> None:
    work.lines += lines
    work.picked.append(" / ".join(lines))
    work.counts[affix["type"]] += 1
    work.meta.append((group, affix, lines))
    work.options.pop(group, None)


def _remove(work: _Work, index: int) -> None:
    group, affix, lines = work.meta.pop(index)
    for line in lines:
        work.lines.remove(line)
    work.picked.pop(index)
    work.counts[affix["type"]] -= 1
    work.options[group] = affix


def _swap_for(work: _Work, stage: Stage, res_group: str) -> bool:
    """Make room for a resistance on a full item by dropping its lowest-priority
    non-resistance affix (picks are in priority order, so the last one)."""
    kind = work.options[res_group]["type"]
    for i in range(len(work.meta) - 1, -1, -1):
        group, affix, _ = work.meta[i]
        if _is_res_group(group):
            continue
        frees_kind = affix["type"] == kind or work.counts[kind] < 3
        frees_slot = len(work.picked) - 1 < stage.max_affixes
        if frees_kind and frees_slot:
            _remove(work, i)
            return True
    return False


def _try(pob: PoB, slot: str, raws: list[str]) -> list[dict | None]:
    """Score candidate items for a slot without equipping them (PoB's fast what-if calc)."""
    if not raws:
        return []
    res = pob.send("try_items", slot=slot, items=raws, fields=SCORE_FIELDS)["results"]
    return [None if (not isinstance(r, dict) or "error" in r) else r for r in res]


def _fill(pob: PoB, work: _Work, stage: Stage, score: Scorer, limit: int, allow, ) -> None:
    """Greedy: keep adding the affix with the best score until `limit` affixes or no gain."""
    current = pob.send("equip", slot=work.slot, raw=work.raw(), fields=SCORE_FIELDS)["output"]
    while len(work.picked) < limit:
        cands = []
        for group, a in work.options.items():
            if allow(group) and work.has_room(stage, a["type"]):
                cands.append((group, a, [_value_at(line, stage.roll) for line in a["lines"]]))
        outs = _try(pob, work.slot, [work.raw(c[2]) for c in cands])
        best, best_score = None, 0.0
        for cand, out in zip(cands, outs):
            if out is None:
                continue
            sc = score(out, current)
            if sc > best_score:
                best, best_score = cand, sc
        if not best:
            break
        _add(work, *best)
        # Equip the improved item so the next round's what-if calcs start from it.
        current = pob.send("equip", slot=work.slot, raw=work.raw(), fields=SCORE_FIELDS)["output"]


def _cap_resistances(pob: PoB, works: list[_Work], stage: Stage) -> None:
    """Add resistance affixes only where needed, on items that still have room."""
    keys = {"fire": "FireResist", "cold": "ColdResist", "lightning": "LightningResist", "chaos": "ChaosResist"}
    groups = {"fire": "FireResistance", "cold": "ColdResistance", "lightning": "LightningResistance",
              "chaos": "ChaosResistance"}
    targets = {"fire": RES_CAP, "cold": RES_CAP, "lightning": RES_CAP, "chaos": 0 if stage.key != "leveling" else -100}
    for _ in range(40):
        out = pob.calc(list(keys.values()))
        need = {e: targets[e] - out.get(k, -60) for e, k in keys.items() if out.get(k, -60) < targets[e]}
        if not need:
            return
        short = [e for e in need if e != "chaos"]
        pick = None
        # Most-needed element first; all-resistance affixes when two or more elements are short.
        for elem in sorted(need, key=need.get, reverse=True):
            choices = []
            for w in works:
                if len(short) >= 2 and "AllResistances" in w.options and w.has_room(stage, w.options["AllResistances"]["type"]):
                    choices.append((0, w, "AllResistances"))
                g = groups[elem]
                if g in w.options and w.has_room(stage, w.options[g]["type"]):
                    choices.append((1, w, g))
            if choices:
                choices.sort(key=lambda c: (c[0], len(c[1].picked)))
                pick = choices[0][1:]
                break
        if not pick:
            # Every item is full: trade a low-priority affix on an armour or jewellery piece.
            elem = next((e for e in sorted(need, key=need.get, reverse=True) if e != "chaos"), None)
            if elem is None:
                return
            g = groups[elem]
            for w in sorted((w for w in works if not w.slot.startswith("Weapon") and not w.unique and g in w.options),
                            key=lambda w: sum(_is_res_group(m[0]) for m in w.meta)):
                if _swap_for(w, stage, g):
                    pick = (w, g)
                    break
            if not pick:
                return
        w, g = pick
        a = w.options[g]
        _add(w, g, a, [_value_at(line, stage.roll) for line in a["lines"]])
        pob.send("equip", slot=w.slot, raw=w.raw(), fields=SCORE_FIELDS)


# Most a player at each budget would pay for one item, in divines.
BUDGET_DIVINES = {"free": 0, "budget": 5, "medium": 30, "high": 100, "unlimited": float("inf")}
SLOT_TYPES = {"Helmet": "Helmet", "Body Armour": "Body Armour", "Gloves": "Gloves", "Boots": "Boots",
              "Amulet": "Amulet", "Ring 1": "Ring", "Ring 2": "Ring", "Belt": "Belt"}
_PRICES: dict | None = None


def unique_prices() -> dict:
    """Unique prices in divines (engine/data/unique_prices.json, filled from poe.ninja)."""
    global _PRICES
    if _PRICES is None:
        import json
        from pathlib import Path
        try:
            _PRICES = json.loads((Path(__file__).parent / "data" / "unique_prices.json").read_text())
        except (OSError, ValueError):
            _PRICES = {}
    return _PRICES


def _unique_allowed(name: str, stage: Stage) -> tuple[bool, str | None]:
    cap = BUDGET_DIVINES.get(stage.budget_key, 0)
    price = unique_prices().get(name.split(",")[0])
    if price is not None:
        return price <= cap, f"~{price:g} div"
    # No price data: only suggest uniques where the budget clearly allows it, and say so.
    return cap >= 30, "price unknown"


def _consider_uniques(pob: PoB, works: list["_Work"], stage: Stage, score: "Scorer",
                      weapon_types: dict[str, tuple[str, str | None]], min_gain: float = 0.02) -> None:
    """Swap a crafted rare for a unique wherever a unique scores clearly better."""
    uniques = pob.list_uniques()
    used: set[str] = set()
    for w in works:
        if w.slot in weapon_types:
            wtype, wsub = weapon_types[w.slot]
            pool = [u for u in uniques if u["type"] == wtype and _sub_ok(u.get("subType"), wsub)]
        else:
            pool = [u for u in uniques if u["type"] == SLOT_TYPES.get(w.slot)]
        pool = [u for u in pool if (u.get("level") or 0) <= stage.level and u["name"] not in used]
        allowed = [(u, note) for u in pool for ok, note in [_unique_allowed(u["name"], stage)] if ok]
        if not allowed:
            continue
        current = pob.calc(SCORE_FIELDS)
        outs = _try(pob, w.slot, [u["raw"] for u, _ in allowed])
        best, best_score = None, min_gain
        for (u, note), out in zip(allowed, outs):
            if out is None:
                continue
            sc = score(out, current)
            if sc > best_score:
                best, best_score = (u, note), sc
        if best:
            u, note = best
            w.unique, w.unique_raw, w.price_note = u["name"], u["raw"], note
            used.add(u["name"])
            pob.send("equip", slot=w.slot, raw=u["raw"], fields=SCORE_FIELDS)


def _best_base(pob: PoB, slot: str, candidates: list[dict], stage: Stage, score: Scorer) -> str:
    """Try each candidate base bare (implicit + base defences only) and keep the best."""
    title = f"{stage.name} {slot}"
    ref = pob.calc(SCORE_FIELDS)
    outs = _try(pob, slot, [_item_raw(title, c["name"], []) for c in candidates])
    best, best_score = candidates[0]["name"], float("-inf")
    for c, out in zip(candidates, outs):
        if out is None:
            continue
        sc = score(out, ref)
        if sc > best_score:
            best, best_score = c["name"], sc
    return best


def _sub_ok(actual: str | None, wanted: str | None) -> bool:
    """wanted None: any subtype. "none": only bases without one (e.g. caster staves, not quarterstaves)."""
    if wanted is None:
        return True
    if wanted == "none":
        return not actual
    return actual == wanted


def _top_bases(bases: list[dict], item_type: str, sub_type: str | None = None, per_subtype: int = 1) -> list[dict]:
    """Highest-level base of each defence subtype (or of the given subtype)."""
    pool = [b for b in bases if b["type"] == item_type and (sub_type is None or b.get("subType") == sub_type)
            and not b["name"].startswith("Runeforged")]
    groups: dict[str, list[dict]] = {}
    for b in pool:
        groups.setdefault(b.get("subType") or "", []).append(b)
    out = []
    for items in groups.values():
        items.sort(key=lambda b: -b["level"])
        out += items[:per_subtype]
    return out


def craft_gear(
    pob: PoB,
    stage: Stage,
    weapon_type: str,
    weapon_subtype: str | None = None,
    dual_wield: bool = False,
    offhand_type: str | None = None,
    def_weight: float = 0.4,
    mode: str = "bossing",
    uniques: bool = True,
    metric: str | None = None,
    goals=None,
    log=print,
) -> list[SlotPlan]:
    """Craft every slot for a build already loaded in `pob` (class, level, skills set).

    1. Damage and defence affixes first, leaving room on armour and jewellery.
    2. Resistances only where still needed, on items with room.
    3. Fill any room left with the best remaining affixes.
    """
    score = Scorer(def_weight=def_weight, mode=mode, metric=metric, goals=goals)
    keep = {"ItemFoundRarityIncrease"} if goals and "rarity" in goals else set()
    bases = pob.send("bases", max_level=stage.item_level)["bases"]

    slot_bases: list[tuple[str, list[dict]]] = []
    weapon_slots = [("Weapon 1", weapon_type, weapon_subtype)]
    if dual_wield:
        weapon_slots.append(("Weapon 2", weapon_type, weapon_subtype))
    elif offhand_type:
        weapon_slots.append(("Weapon 2", offhand_type, None))
    for slot, wtype, wsub in weapon_slots:
        cands = sorted((b for b in bases if b["type"] == wtype and _sub_ok(b.get("subType"), wsub)
                        and not b["name"].startswith("Runeforged")), key=lambda b: -b["level"])[:6]
        if not cands:
            raise ValueError(f"No {wtype} bases up to item level {stage.item_level}")
        slot_bases.append((slot, cands))
    for slot, item_type in {**ARMOUR_SLOTS, **JEWELLERY_SLOTS}.items():
        per = 1 if item_type in ARMOUR_SLOTS.values() else 6
        cands = _top_bases(bases, item_type, per_subtype=per)
        if cands:
            slot_bases.append((slot, cands))

    works: list[_Work] = []
    for slot, cands in slot_bases:
        base = _best_base(pob, slot, cands, stage, score)
        affixes = pob.send("affixes", base=base, max_level=stage.item_level)["affixes"]
        works.append(_Work(slot, base, f"{stage.name} {slot}", _tier_choices(affixes, stage, keep)))

    no_res = Scorer(def_weight=def_weight, res_weight=0.0, mode=mode, metric=metric, goals=goals)
    for w in works:
        reserve = 0 if w.slot.startswith("Weapon") else 2
        _fill(pob, w, stage, no_res, stage.max_affixes - reserve, allow=lambda g: not _is_res_group(g))
    _cap_resistances(pob, works, stage)
    for w in works:
        _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)

    if uniques and BUDGET_DIVINES.get(stage.budget_key, 0) > 0:
        wt = {slot: (t, sub) for slot, t, sub in weapon_slots}
        _consider_uniques(pob, works, stage, score, wt)
        if any(w.unique for w in works):
            # A unique replaced a rare: its resistances and stats may be gone, so re-balance the rares.
            _cap_resistances(pob, works, stage)
            for w in works:
                _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)

    plans = []
    for w in works:
        if w.unique:
            log(f"  {w.slot:<12} UNIQUE {w.unique} ({w.price_note})")
            plans.append(SlotPlan(w.slot, w.unique.split(",")[-1].strip(), [], w.unique_raw, w.unique, w.price_note))
        else:
            log(f"  {w.slot:<12} {w.base:<28} " + "; ".join(w.picked))
            plans.append(SlotPlan(w.slot, w.base, w.picked, w.raw()))
    return plans


def craft_weapon(pob: PoB, stage: Stage, slot: str, weapon_type: str, weapon_subtype: str | None = None,
                 mode: str = "bossing", def_weight: float = 0.4, metric: str | None = None, log=print) -> SlotPlan:
    """Craft one weapon slot on its own, e.g. "Weapon 1 Swap" for a boss skill on weapon set 2.
    The skill that uses it must be the main skill while this runs."""
    score = Scorer(def_weight=def_weight, mode=mode, metric=metric)
    bases = pob.send("bases", max_level=stage.item_level)["bases"]
    cands = sorted((b for b in bases if b["type"] == weapon_type and _sub_ok(b.get("subType"), weapon_subtype)
                    and not b["name"].startswith("Runeforged")), key=lambda b: -b["level"])[:6]
    if not cands:
        raise ValueError(f"No {weapon_type} bases up to item level {stage.item_level}")
    base = _best_base(pob, slot, cands, stage, score)
    affixes = pob.send("affixes", base=base, max_level=stage.item_level)["affixes"]
    w = _Work(slot, base, f"{stage.name} {slot}", _tier_choices(affixes, stage))
    _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)
    log(f"  {slot:<12} {base:<28} " + "; ".join(w.picked))
    return SlotPlan(slot, base, w.picked, w.raw())
