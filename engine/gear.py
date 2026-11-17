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
from meta import meta_factor
from pob import PoB, PoBError

ARMOUR_SLOTS = {"Helmet": "Helmet", "Body Armour": "Body Armour", "Gloves": "Gloves", "Boots": "Boots"}
JEWELLERY_SLOTS = {"Amulet": "Amulet", "Ring 1": "Ring", "Ring 2": "Ring", "Belt": "Belt"}
RES_CAP = 75
SCORE_FIELDS = [*DPS_FIELDS, "TotalEHP", "Life", "FireResist", "ColdResist", "LightningResist",
                "ChaosResist", *CLEAR_FIELDS, *GOAL_FIELDS, "Str", "Dex", "Int", "ReqStr", "ReqDex", "ReqInt"]
# Affix groups that never matter for a build score.
SKIP_GROUPS = {"ItemFoundRarityIncrease", "LocalAttributeRequirements", "LightRadius", "LocalLightRadius"}


@dataclass
class Stage:
    key: str
    name: str
    level: int          # character level for this stage
    item_level: int     # highest affix level available
    roll: float         # where in each affix's range the target value sits (0 = min, 1 = max)
    tier_drop: int      # tiers below the best available
    max_affixes: int    # how many good affixes a typical item has at this stage
    top_mods: int = 0   # how many of an item's affixes can be the best tier; the rest sit tier_drop tiers lower
    uniques: str = "all"        # which uniques a player realistically has: none / common / most / all (UNIQUE_ACCESS)
    sockets: int = 5            # support sockets per skill gem (2 base; Lesser / Greater / Perfect Jeweller's Orb)
    points: int | None = None   # passive points (None: PoB's count for the level, every quest done)
    ascendancy_points: int = 8
    res_target: int = 75        # elemental resistance the gear aims for
    chaos_target: int = 0
    focus: str = "mapping"      # what gear and passives are built for first: mapping, or bossing (pinnacle bosses)
    def_mult: float = 1.0       # toughness weight on top of the build's own
    jewel_affixes: int = 3      # good affixes on a rare jewel (0: no jewels at this stage)
    light: bool = False         # campaign: one tree pass, no jewels, no boss or trigger setups, so it builds fast

    @property
    def campaign(self) -> bool:
        return self.key in CAMPAIGN


# Seven stages, as a player meets them. What the player realistically has at each one decides the gear: self-found
# rares with two or three mods in the acts, easy uniques once maps start, most uniques by mid endgame, and
# best-in-slot items against the pinnacle bosses. Support sockets: every skill gem starts with 2; a Lesser Jeweller's
# Orb (campaign) sets 3, a Greater (early endgame) 4, a Perfect 5. Passive points in the acts are level - 1 plus the
# quest points a player has picked up by then; ascendancy points come from the trials (2 per trial).
STAGE_DEFS = {
    "act1": Stage("act1", "Act 1", 12, 12, 0.3, 1, 2, uniques="none", sockets=2, points=13, ascendancy_points=0,
                  res_target=30, chaos_target=-100, jewel_affixes=0, light=True),
    "act2": Stage("act2", "Act 2", 25, 25, 0.35, 1, 3, uniques="none", sockets=3, points=29, ascendancy_points=2,
                  res_target=45, chaos_target=-100, jewel_affixes=0, light=True),
    "act34": Stage("act34", "Acts 3–4", 45, 45, 0.4, 1, 3, uniques="none", sockets=3, points=56,
                   ascendancy_points=4, res_target=60, chaos_target=-100, jewel_affixes=0, light=True),
    "interludes": Stage("interludes", "Interludes", 60, 62, 0.45, 1, 3, uniques="common", sockets=3, points=79,
                        ascendancy_points=4, res_target=75, chaos_target=-100, jewel_affixes=0, light=True),
    "early": Stage("early", "Early Endgame", 72, 75, 0.5, 1, 4, uniques="common", sockets=4, ascendancy_points=6,
                   jewel_affixes=2),
    "mid": Stage("mid", "Mid Endgame", 86, 81, 0.65, 1, 5, top_mods=2, uniques="most", jewel_affixes=3),
    "end": Stage("end", "Uber Endgame", 95, 82, 0.9, 1, 6, top_mods=4, uniques="all", chaos_target=30,
                 focus="bossing", def_mult=1.5, jewel_affixes=4),
}
CAMPAIGN = ("act1", "act2", "act34", "interludes")


def make_stage(key: str) -> Stage:
    """The stage's settings (a copy, so a build can't change the shared table)."""
    from dataclasses import replace
    if key not in STAGE_DEFS:
        raise ValueError(f"stage must be one of {list(STAGE_DEFS)}")
    return replace(STAGE_DEFS[key])


STAGES = {k: make_stage(k) for k in STAGE_DEFS}


@dataclass
class SlotPlan:
    slot: str
    base: str
    affixes: list[str] = field(default_factory=list)   # in priority order, with target values
    raw: str = ""
    unique: str | None = None       # unique item name when a unique beats the crafted rare
    # Per affix, same order: {"tier": 1 = best roll in the game, "of": tiers that exist, "type": Prefix/Suffix}
    affix_info: list[dict] = field(default_factory=list)
    trade_url: str | None = None    # official trade search for this base + affixes (or this unique)
    implicits: list[str] = field(default_factory=list)   # the base's own modifiers, shown above the affixes
    mods: list[str] = field(default_factory=list)        # a unique's own mods, its chosen variants applied
    variants: list[str] = field(default_factory=list)    # a unique's chosen variants (e.g. Mageblood's Legacy effects)


def _value_at(text: str, roll: float) -> str:
    """'+(50-69) to maximum Life' at roll 0.5 -> '+60 to maximum Life'."""
    def sub(m):
        lo, hi = float(m.group(1)), float(m.group(2))
        v = lo + (hi - lo) * roll
        decimals = "." in m.group(1) or "." in m.group(2)
        return f"{v:.1f}" if decimals else str(int(round(v)))
    return re.sub(r"\((-?[\d.]+)-(-?[\d.]+)\)", sub, text)


def _attr_deficit(out: dict) -> float:
    """Attribute points the gear and gems need that the character doesn't have."""
    return sum(max(0.0, (out.get(need) or 0) - (out.get(have) or 0))
               for have, need in (("Str", "ReqStr"), ("Dex", "ReqDex"), ("Int", "ReqInt")))


def _res_deficit(out: dict) -> float:
    return sum(max(0, RES_CAP - out.get(k, -60)) for k in ("FireResist", "ColdResist", "LightningResist")) \
        + 0.5 * max(0, -out.get("ChaosResist", 0))


class Scorer:
    def __init__(self, def_weight: float = 0.4, res_weight: float = 0.006, mode: str = "bossing",
                 metric: str | None = None, goals=None, attr_weight: float | None = None):
        if attr_weight is not None:
            self.attr_weight = attr_weight
        self.goal_w = goal_weights(goals)
        self.def_weight = def_weight * self.goal_w["def_mult"]
        self.res_weight = res_weight
        if metric:
            self.dps = lambda out: score_of(out, metric)
        else:
            self.dps = clear_score if mode == "mapping" else total_dps

    # Per attribute point a requirement is short by. Off by default: before the passive tree exists every build is
    # short, and the tree's attribute passives fix most of it. The final gear pass (guide.py) turns it on.
    attr_weight = 0.0

    def __call__(self, out: dict, base: dict) -> float:
        d0 = max(self.dps(base) or 0, 1)
        e0 = max(base.get("TotalEHP") or 0, 1)
        d = self.dps(out) or 0
        return ((d - d0) / d0
                + self.def_weight * ((out.get("TotalEHP") or 0) - e0) / e0
                + self.res_weight * (_res_deficit(base) - _res_deficit(out))
                + self.attr_weight * (_attr_deficit(base) - _attr_deficit(out))
                + goal_terms(out, base, self.goal_w))


def _item_raw(title: str, base: str, lines: list[str], implicits=()) -> str:
    # PoB only applies a base's implicit when the item text lists it, under "Implicits: n".
    head = ["Rarity: Rare", title, base] + ([f"Implicits: {len(implicits)}", *implicits] if implicits else [])
    return "\n".join([*head, *lines])


_AVAILABILITY: dict | None = None


def base_available(name: str) -> bool:
    """False for a base the current league's trade site has no listings of (data/base_availability.json, filled by
    tools/fetch_bases.py): players can't find it, so we never tell them to buy it. Unknown bases count as available."""
    global _AVAILABILITY
    if _AVAILABILITY is None:
        import json
        from pathlib import Path
        try:
            _AVAILABILITY = json.loads((Path(__file__).parent / "data" / "base_availability.json").read_text(encoding="utf-8")).get("bases", {})
        except (OSError, ValueError):
            _AVAILABILITY = {}
    return _AVAILABILITY.get(name, 1) > 0


def base_usable(base: dict) -> bool:
    """A base the crafter may use: a normal drop (not a Demigod / not-for-sale special base), with a crafter-safe
    implicit, and listed in the current league."""
    if set(base.get("tags") or []) & {"not_for_sale", "demigods"}:
        return False
    return base_implicits(base, 0.5) is not None and base_available(base["name"])


def base_implicits(base: dict, roll: float) -> list[str] | None:
    """A base's implicit lines at this roll, or None for a base the crafter can't promise: one whose implicit is
    random (amulets that grant one of many skills) or that removes affix slots ("-1 Prefix Modifier allowed")."""
    text = base.get("implicit") or ""
    if "{variant" in text or "Modifier allowed" in text:
        return None
    return [_value_at(line, roll) for line in text.split("\n") if line.strip()]


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
        idx = max(0, len(tiers) - 1 - stage.tier_drop)
        chosen[group] = {**tiers[idx], "_tier": len(tiers) - idx, "_tiers": len(tiers)}
        if idx < len(tiers) - 1:
            # The best tier too, offered while the item still has a top-tier slot left (stage.top_mods).
            chosen[group]["_best"] = {**tiers[-1], "_tier": 1, "_tiers": len(tiers), "_is_top": True}
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
    max_total: int | None = None    # affix cap for this item (jewels); None: the stage's
    max_kind: int = 3               # prefixes (or suffixes) at most
    implicits: tuple = ()           # the base's implicit lines, at this stage's roll
    base_tags: frozenset | None = None   # the base's item tags (None: no tag rules, e.g. jewels)

    def top_used(self) -> int:
        return sum(1 for _, a, _ in self.meta if a.get("_is_top"))

    def tags(self) -> set:
        """The item's tags now: the base's, plus any its mods added (which block other mods, as in game)."""
        out = set(self.base_tags or ())
        for _, a, _ in self.meta:
            out |= set(a.get("adds") or ())
        return out

    def allows(self, affix: dict) -> bool:
        """Can this affix roll on the item as it is now? The first of the mod's weight tags the item has decides.
        Never two mods with the same stat (a rarity prefix and a rarity suffix, say): the game won't allow it."""
        st = tuple(affix.get("stats") or ())
        if st and any(tuple(a.get("stats") or ()) == st for _, a, _ in self.meta):
            return False
        if self.base_tags is None or "wk" not in affix:
            return True
        tags = self.tags()
        for key, val in zip(affix["wk"], affix["wv"]):
            if key in tags:
                return val > 0
        return False

    def raw(self, extra: list[str] | None = None) -> str:
        if self.unique_raw:
            return self.unique_raw
        return _item_raw(self.title, self.base, self.lines + (extra or []), self.implicits)

    def has_room(self, stage: "Stage", kind: str) -> bool:
        if self.unique_raw:
            return False
        total = stage.max_affixes if self.max_total is None else self.max_total
        return len(self.picked) < total and self.counts[kind] < self.max_kind


# ---------- The game's crafting rules, checked on every finished rare ----------
STRICT_ITEMS = __import__("os").environ.get("STRICT_ITEMS") == "1"   # tests: a broken rule fails loudly


def _allowed_with(affix: dict, tags: set) -> bool:
    for key, val in zip(affix.get("wk") or (), affix.get("wv") or ()):
        if key in tags:
            return val > 0
    return "wk" not in affix   # no weight data (older callers): nothing to check


def item_problems(w: "_Work", item_level: int = 100) -> list[str]:
    """Everything about a crafted rare the game wouldn't allow. Empty means it can really exist."""
    if w.unique_raw:
        return []
    out = []
    kinds = {"Prefix": 0, "Suffix": 0}
    for _, a, _ in w.meta:
        kinds[a["type"]] = kinds.get(a["type"], 0) + 1
    for kind, n in kinds.items():
        if n > w.max_kind:
            out.append(f"{n} {kind.lower()}es (most is {w.max_kind})")
    total = w.max_total if w.max_total is not None else 2 * w.max_kind
    if len(w.meta) > total:
        out.append(f"{len(w.meta)} affixes (most is {total})")
    groups = [grp for grp, _, _ in w.meta]
    for grp in {x for x in groups if groups.count(x) > 1}:
        out.append(f"two mods from group {grp}")
    stats = [tuple(a.get("stats") or ()) for _, a, _ in w.meta]
    for st in {x for x in stats if x and stats.count(x) > 1}:
        out.append(f"two mods with the same stat {st}")
    for i, (grp, a, _) in enumerate(w.meta):
        if (a.get("level") or 0) > item_level:
            out.append(f"{grp} needs item level {a['level']}")
        if w.base_tags is not None:
            # Tags the base has plus every OTHER mod adds: a mod that adds "no_cold_spell_mods" rules out cold
            # spell levels whichever was added first.
            tags = set(w.base_tags)
            for j, (_, b, _) in enumerate(w.meta):
                if j != i:
                    tags |= set(b.get("adds") or ())
            if not _allowed_with(a, tags):
                out.append(f"{grp} can't roll on this item with its other mods")
    return out


def _enforce_rules(w: "_Work", stage: "Stage", log=lambda *a: None) -> bool:
    """Make sure the finished item could exist: in tests a broken rule is an error; live, offending affixes are
    taken off (lowest priority first) so nobody is ever shown an impossible item."""
    probs = item_problems(w, stage.item_level)
    if not probs:
        return False
    if STRICT_ITEMS:
        raise AssertionError(f"{w.slot} {w.base}: {probs} :: {w.picked}")
    log(f"  {w.slot}: removed affixes that break the game's rules: {probs}")
    while item_problems(w, stage.item_level) and w.meta:
        _remove(w, len(w.meta) - 1)
    return True


def _is_res_group(group: str) -> bool:
    return "Resist" in group and "Penetration" not in group and "Minion" not in group and "Allies" not in group


def _affix_info(work: "_Work") -> list[dict]:
    return [{"tier": a.get("_tier"), "of": a.get("_tiers"), "type": a.get("type")} for _, a, _ in work.meta]


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
    work.options[group] = affix.get("_low") or affix


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


def _req_fields(slot: str) -> list[str]:
    return [f"{a}RequirementsOn{slot}" for a in ("Str", "Dex", "Int")]


def own_deficit(out: dict, slot: str) -> float:
    """Attribute points this slot's own item needs that the character doesn't have. The build's requirement is the
    highest of all items and gems, so once one item is short every other item looks free; this looks at the item."""
    return sum(max(0.0, (out.get(f"{a}RequirementsOn{slot}") or 0) - (out.get(a) or 0)) for a in ("Str", "Dex", "Int"))


def _try(pob: PoB, slot: str, raws: list[str]) -> list[dict | None]:
    """Score candidate items for a slot without equipping them (PoB's fast what-if calc)."""
    if not raws:
        return []
    res = pob.send("try_items", slot=slot, items=raws, fields=SCORE_FIELDS + _req_fields(slot))["results"]
    return [None if (not isinstance(r, dict) or "error" in r) else r for r in res]


def _fill(pob: PoB, work: _Work, stage: Stage, score: Scorer, limit: int, allow, ) -> None:
    """Greedy: keep adding the affix with the best score until `limit` affixes or no gain."""
    current = pob.send("equip", slot=work.slot, raw=work.raw(), fields=SCORE_FIELDS)["output"]
    while len(work.picked) < limit:
        cands = []
        top_left = work.top_used() < stage.top_mods
        for group, a in work.options.items():
            if allow(group) and work.has_room(stage, a["type"]) and work.allows(a):
                cands.append((group, a, [_value_at(line, stage.roll) for line in a["lines"]]))
                best = a.get("_best")
                if top_left and best and work.allows(best):
                    cands.append((group, {**best, "_low": a}, [_value_at(line, stage.roll) for line in best["lines"]]))
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
    targets = {"fire": stage.res_target, "cold": stage.res_target, "lightning": stage.res_target,
               "chaos": stage.chaos_target}
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
                if len(short) >= 2 and "AllResistances" in w.options and w.has_room(stage, w.options["AllResistances"]["type"]) \
                        and w.allows(w.options["AllResistances"]):
                    choices.append((0, w, "AllResistances"))
                g = groups[elem]
                if g in w.options and w.has_room(stage, w.options[g]["type"]) and w.allows(w.options[g]):
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
            for w in sorted((w for w in works if not w.slot.startswith("Weapon") and not w.unique and g in w.options
                             and w.allows(w.options[g])),
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


# Which uniques a player realistically has at each stage. How common a unique is comes from poe.ninja (a unique
# everyone finds is listed cheaply by everyone). It is only a measure of how easy a unique is to get: nothing about
# money is shown and the player never sets a spending limit.
#   none: self-found rares only (the acts)   common: uniques that drop all the time   most: all but the rarest
#   all: every unique, best in slot (pinnacle bosses)
UNIQUE_ACCESS = {"none": 0.0, "common": 1.0, "most": 15.0, "all": float("inf")}
SLOT_TYPES = {"Helmet": "Helmet", "Body Armour": "Body Armour", "Gloves": "Gloves", "Boots": "Boots",
              "Amulet": "Amulet", "Ring 1": "Ring", "Ring 2": "Ring", "Belt": "Belt"}
_PRICES: dict | None = None


def price_league() -> str:
    """The league the poe.ninja unique data came from (engine/data/unique_prices.meta.json), for trade links."""
    import json
    from pathlib import Path
    try:
        return json.loads((Path(__file__).parent / "data" / "unique_prices.meta.json").read_text(encoding="utf-8"))["league"]
    except (OSError, ValueError, KeyError):
        return "Standard"


def trade_link(query: dict, league: str) -> str:
    """The official PoE 2 trade search with `query` pre-filled. The query rides in the link (gzip + base64url,
    as Path of Building does), so opening it is the player's own search: nothing is sent to GGG from here."""
    import base64
    import gzip
    import json
    from urllib.parse import quote
    blob = gzip.compress(json.dumps(query, separators=(",", ":")).encode("utf-8"))
    return f"https://www.pathofexile.com/trade2/search/poe2/{quote(league)}/{base64.urlsafe_b64encode(blob).decode()}"


def add_trade_info(pob: "PoB", plans: list["SlotPlan"]) -> None:
    """Give every item a trade search link."""
    league = price_league()
    for p in plans:
        if p.raw:
            try:
                p.trade_url = trade_link(pob.send("trade_query", raw=p.raw)["query"], league)
            except Exception:  # noqa: BLE001 - a link is a nice-to-have; never fail a build over it
                p.trade_url = None


def unique_prices() -> dict:
    """How rare each unique is: its poe.ninja value (engine/data/unique_prices.json). Used only to tell which
    uniques a player has at each stage (UNIQUE_ACCESS); never shown."""
    global _PRICES
    if _PRICES is None:
        import json
        from pathlib import Path
        try:
            _PRICES = json.loads((Path(__file__).parent / "data" / "unique_prices.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _PRICES = {}
    return _PRICES


def _unique_allowed(name: str, stage: Stage) -> bool:
    """A player at this stage realistically has this unique (anchors skip this: the player asked for them)."""
    cap = UNIQUE_ACCESS.get(stage.uniques, 0.0)
    if cap == float("inf"):
        return True
    rarity = unique_prices().get(name.split(",")[0])
    # No poe.ninja data: a new or very rare unique, so only the pinnacle stage counts on it.
    return rarity is not None and rarity <= cap


VARIANT_KEYS = ["Selected Variant", "Selected Alt Variant", "Selected Alt Variant Two", "Selected Alt Variant Three",
                "Selected Alt Variant Four", "Selected Alt Variant Five"]
HAS_ALT = {"Selected Alt Variant": "Has Alt Variant: true", "Selected Alt Variant Two": "Has Alt Variant Two: true",
           "Selected Alt Variant Three": "Has Alt Variant Three: true", "Selected Alt Variant Four": "Has Alt Variant Four: true",
           "Selected Alt Variant Five": "Has Alt Variant Five: true"}


def _set_variant(raw: str, key: str, value: int) -> str:
    lines = [ln for ln in raw.split("\n") if not ln.startswith(key + ":")]
    # The "Selected ..." lines go in the item's header, before its list of variants.
    at = next((i for i, ln in enumerate(lines) if ln.startswith("Variant: ")), min(3, len(lines)))
    lines.insert(at, f"{key}: {value}")
    return "\n".join(lines)


def best_variants(pob: PoB, raw: str, slot: str, score: "Scorer") -> str:
    """For a unique whose mods you choose (Mageblood: four "Legacy of ..." effects), pick each choice in turn as the
    one that helps this build most. Uniques with version variants ("Pre 0.2.0") keep their current version."""
    import re
    names = [ln[len("Variant: "):] for ln in raw.split("\n") if ln.startswith("Variant: ")]
    if len(names) < 2 or any(re.match(r"\(?Pre \d|Current", n) for n in names):
        return raw
    keys = ["Selected Variant"] + [k for k in VARIANT_KEYS[1:] if HAS_ALT[k] in raw]
    current = pob.calc(SCORE_FIELDS)
    for key in keys:
        cands = [_set_variant(raw, key, i) for i in range(1, len(names) + 1)]
        outs = _try(pob, slot, cands)
        scored = [(score(o, current), i) for i, o in enumerate(outs) if o is not None]
        if scored:
            raw = cands[max(scored)[1]]
    return raw


def unique_lines(pob: PoB, raw: str) -> tuple[list[str], list[str]]:
    """A unique's mods and chosen variants, as the game shows them."""
    try:
        res = pob.send("item_lines", raw=raw)
        mods, variants = list(res.get("implicits") or []) + list(res.get("explicits") or []), list(res.get("variants") or [])
    except PoBError:
        mods, variants = [], []
    if not mods:
        # Some uniques' mods are generated (Megalomaniac grants random notables), so PoB lists none: show the
        # item text's own mod lines instead of an empty card.
        import re
        lines = raw.split("\n")
        body = [ln for ln in lines[2:] if ln.strip() and not re.match(r"^[A-Za-z ]+:\s", ln) and not ln.startswith("Rarity")]
        mods = [re.sub(r"\{[^}]*\}", "", ln).strip() for ln in body][:12]
    return mods, variants


def unique_limit_ok(u: dict, counts: dict[str, int]) -> bool:
    """Within the unique's "Limited to: N" (by name, across bases: Grand Spectrum on a Ruby and an Emerald counts
    twice). A unique with no limit text is still taken once per name and base (the `used` sets)."""
    m = re.search(r"Limited to: (\d+)", u.get("raw") or "")
    return not m or counts.get(u["name"].split(",")[0], 0) < int(m.group(1))


def count_unique(u: dict, counts: dict[str, int]) -> None:
    key = u["name"].split(",")[0]
    counts[key] = counts.get(key, 0) + 1


def _consider_uniques(pob: PoB, works: list["_Work"], stage: Stage, score: "Scorer",
                      weapon_types: dict[str, tuple[str, str | None]], min_gain: float = 0.02) -> None:
    """Swap a crafted rare for a unique wherever a unique scores clearly better."""
    uniques = pob.list_uniques()
    used: set[str] = set()
    counts: dict[str, int] = {}
    for w in works:
        if w.unique:
            used.add(w.unique)   # the anchor unique: already chosen
            count_unique({"name": w.unique}, counts)
    for w in works:
        if w.unique:
            continue
        if w.slot in weapon_types:
            wtype, wsub = weapon_types[w.slot]
            pool = [u for u in uniques if u["type"] == wtype and _sub_ok(u.get("subType"), wsub)]
        else:
            pool = [u for u in uniques if u["type"] == SLOT_TYPES.get(w.slot)]
        pool = [u for u in pool if (u.get("level") or 0) <= stage.level and u["name"] not in used
                and unique_limit_ok(u, counts)]
        allowed = [u for u in pool if _unique_allowed(u["name"], stage)]
        if not allowed:
            continue
        current = pob.calc(SCORE_FIELDS)
        # Uniques with choices (Mageblood) are tried with their best choices for this build.
        allowed = [{**u, "raw": best_variants(pob, u["raw"], w.slot, score)} for u in allowed]
        outs = _try(pob, w.slot, [u["raw"] for u in allowed])
        best, best_score = None, min_gain
        for u, out in zip(allowed, outs):
            if out is None:
                continue
            sc = score(out, current) - score.attr_weight * own_deficit(out, w.slot)
            if getattr(pob, "off_meta", False):
                sc *= meta_factor(unique=u["name"])   # off-meta: a unique half the ladder wears counts for less
            if sc > best_score:
                best, best_score = u, sc
        if best:
            u = best
            w.unique, w.unique_raw = u["name"], u["raw"]
            used.add(u["name"])
            count_unique(u, counts)
            pob.send("equip", slot=w.slot, raw=u["raw"], fields=SCORE_FIELDS)


def _best_base(pob: PoB, slot: str, candidates: list[dict], stage: Stage, score: Scorer) -> str:
    """Try each candidate base bare (implicit + base defences only) and keep the best."""
    title = f"{stage.name} {slot}"
    ref = pob.calc(SCORE_FIELDS)
    outs = _try(pob, slot, [_item_raw(title, c["name"], [], base_implicits(c, stage.roll) or ()) for c in candidates])
    best, best_score = candidates[0]["name"], float("-inf")
    for c, out in zip(candidates, outs):
        if out is None:
            continue
        sc = score(out, ref) - score.attr_weight * own_deficit(out, slot)
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


def _meets(base: dict, attrs: dict | None) -> bool:
    """The character has the attributes this base asks for (attrs: current Str / Dex / Int)."""
    req = base.get("req") or {}
    req = req if isinstance(req, dict) else {}
    return attrs is None or all((req.get(k) or 0) <= (attrs.get(a) or 0)
                                for k, a in (("str", "Str"), ("dex", "Dex"), ("int", "Int")))


def _top_bases(bases: list[dict], item_type: str, sub_type: str | None = None, per_subtype: int = 1,
               attrs: dict | None = None) -> list[dict]:
    """Highest-level base of each defence subtype (or of the given subtype). With `attrs`, also the best one the
    character can wear: at level 55 the top bases ask 86 of one attribute, which many characters don't have yet."""
    pool = [b for b in bases if b["type"] == item_type and (sub_type is None or b.get("subType") == sub_type)
            and not b["name"].startswith("Runeforged") and base_usable(b)]
    groups: dict[str, list[dict]] = {}
    for b in pool:
        groups.setdefault(b.get("subType") or "", []).append(b)
    out = []
    for items in groups.values():
        items.sort(key=lambda b: -b["level"])
        out += items[:per_subtype]
        if attrs is not None:
            wearable = next((b for b in items if _meets(b, attrs)), None)
            if wearable and wearable not in out:
                out.append(wearable)
    return out


def _anchor_work(pob: PoB, stage: Stage, score: "Scorer") -> "_Work | None":
    """The anchor unique as an equipped, finished item (None: no anchor, or the stage is below its level)."""
    u = (getattr(pob, "anchors", None) or {}).get("unique")
    if not u:
        return None
    if (u.get("level") or 0) > stage.level:
        notes = getattr(pob, "anchor_notes", None)
        if notes is not None and f"unique_level:{u['name']}" not in notes:
            notes.append(f"unique_level:{u['name']}")
        return None
    raw = best_variants(pob, u["raw"], u["slot"], score)
    w = _Work(u["slot"], u.get("base") or u["name"], u["name"], {}, unique=u["name"], unique_raw=raw)
    pob.send("equip", slot=w.slot, raw=raw, fields=SCORE_FIELDS)
    return w


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
    attr_weight: float | None = None,
) -> list[SlotPlan]:
    """Craft every slot for a build already loaded in `pob` (class, level, skills set).

    1. Damage and defence affixes first, leaving room on armour and jewellery.
    2. Resistances only where still needed, on items with room.
    3. Fill any room left with the best remaining affixes.
    """
    score = Scorer(def_weight=def_weight, mode=mode, metric=metric, goals=goals, attr_weight=attr_weight)
    keep = {"ItemFoundRarityIncrease"} if goals and "rarity" in goals else set()
    bases = pob.send("bases", max_level=stage.item_level)["bases"]
    # The final pass (attr_weight set) also offers bases the character can wear right now.
    attrs = pob.calc(["Str", "Dex", "Int"]) if attr_weight else None

    slot_bases: list[tuple[str, list[dict]]] = []
    weapon_slots = [("Weapon 1", weapon_type, weapon_subtype)]
    if dual_wield:
        weapon_slots.append(("Weapon 2", weapon_type, weapon_subtype))
    elif offhand_type:
        weapon_slots.append(("Weapon 2", offhand_type, None))
    # The anchor unique (the build is made around it) is equipped first, so every other slot is crafted around it.
    anchor = _anchor_work(pob, stage, score)
    for slot, wtype, wsub in weapon_slots:
        if anchor and anchor.slot == slot:
            continue
        pool = sorted((b for b in bases if b["type"] == wtype and _sub_ok(b.get("subType"), wsub)
                       and not b["name"].startswith("Runeforged") and base_usable(b)),
                      key=lambda b: -b["level"])
        cands = pool[:6]
        if attrs is not None:
            cands += [b for b in pool if _meets(b, attrs) and b not in cands][:2]
        if not cands:
            raise ValueError(f"No {wtype} bases up to item level {stage.item_level}")
        slot_bases.append((slot, cands))
    for slot, item_type in {**ARMOUR_SLOTS, **JEWELLERY_SLOTS}.items():
        if anchor and anchor.slot == slot:
            continue
        per = 1 if item_type in ARMOUR_SLOTS.values() else 40   # every ring, amulet and belt base competes
        cands = _top_bases(bases, item_type, per_subtype=per, attrs=attrs)
        if cands:
            slot_bases.append((slot, cands))

    works: list[_Work] = [anchor] if anchor else []
    for slot, cands in slot_bases:
        base = _best_base(pob, slot, cands, stage, score)
        res = pob.send("affixes", base=base, max_level=stage.item_level)
        imp = base_implicits(next(c for c in cands if c["name"] == base), stage.roll) or []
        works.append(_Work(slot, base, f"{stage.name} {slot}", _tier_choices(res["affixes"], stage, keep), implicits=tuple(imp),
                           base_tags=frozenset(res.get("item_tags") or ())))

    no_res = Scorer(def_weight=def_weight, res_weight=0.0, mode=mode, metric=metric, goals=goals, attr_weight=attr_weight)
    for w in works:
        reserve = 0 if w.slot.startswith("Weapon") else 2
        _fill(pob, w, stage, no_res, stage.max_affixes - reserve, allow=lambda g: not _is_res_group(g))
    _cap_resistances(pob, works, stage)
    for w in works:
        _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)

    if uniques and UNIQUE_ACCESS.get(stage.uniques, 0) > 0:
        wt = {slot: (t, sub) for slot, t, sub in weapon_slots if not (anchor and anchor.slot == slot)}
        _consider_uniques(pob, works, stage, score, wt)
        if any(w.unique for w in works):
            # A unique replaced a rare: its resistances and stats may be gone, so re-balance the rares.
            _cap_resistances(pob, works, stage)
            for w in works:
                _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)

    plans = []
    for w in works:
        if _enforce_rules(w, stage, log):
            pob.send("equip", slot=w.slot, raw=w.raw(), fields=SCORE_FIELDS)
        if w.unique:
            log(f"  {w.slot:<12} UNIQUE {w.unique}")
            mods, variants = unique_lines(pob, w.unique_raw)
            plans.append(SlotPlan(w.slot, w.unique.split(",")[-1].strip(), [], w.unique_raw, w.unique,
                                  mods=mods, variants=variants))
        else:
            log(f"  {w.slot:<12} {w.base:<28} " + "; ".join(w.picked))
            plans.append(SlotPlan(w.slot, w.base, w.picked, w.raw(), affix_info=_affix_info(w),
                                  implicits=list(w.implicits)))
    return plans


def craft_weapon(pob: PoB, stage: Stage, slot: str, weapon_type: str, weapon_subtype: str | None = None,
                 mode: str = "bossing", def_weight: float = 0.4, metric: str | None = None, log=print) -> SlotPlan:
    """Craft one weapon slot on its own, e.g. "Weapon 1 Swap" for a boss skill on weapon set 2.
    The skill that uses it must be the main skill while this runs."""
    score = Scorer(def_weight=def_weight, mode=mode, metric=metric)
    bases = pob.send("bases", max_level=stage.item_level)["bases"]
    cands = sorted((b for b in bases if b["type"] == weapon_type and _sub_ok(b.get("subType"), weapon_subtype)
                    and not b["name"].startswith("Runeforged") and base_usable(b)),
                   key=lambda b: -b["level"])[:6]
    if not cands:
        raise ValueError(f"No {weapon_type} bases up to item level {stage.item_level}")
    base = _best_base(pob, slot, cands, stage, score)
    res = pob.send("affixes", base=base, max_level=stage.item_level)
    imp = base_implicits(next(c for c in cands if c["name"] == base), stage.roll) or []
    w = _Work(slot, base, f"{stage.name} {slot}", _tier_choices(res["affixes"], stage), implicits=tuple(imp),
              base_tags=frozenset(res.get("item_tags") or ()))
    _fill(pob, w, stage, score, stage.max_affixes, allow=lambda g: True)
    if _enforce_rules(w, stage, log):
        pob.send("equip", slot=w.slot, raw=w.raw(), fields=SCORE_FIELDS)
    log(f"  {slot:<12} {base:<28} " + "; ".join(w.picked))
    return SlotPlan(slot, base, w.picked, w.raw(), affix_info=_affix_info(w), implicits=list(w.implicits))
