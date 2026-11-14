"""Jewels: a rare (or unique) jewel for every jewel socket the passive tree takes.

Everything comes from Path of Building's own data: the jewel bases (Ruby, Emerald, Sapphire), their
affix pools and roll ranges (PoB's ModJewel), and the unique jewels. Nothing about which jewel mods
are strong is written here, so when PoB updates (e.g. for PoE 2 1.0) the jewels follow on their own.

How it fits in a build stage:
1. proxy_jewel(): before the passive tree, craft the best jewel this build could put in a socket.
   The tree optimiser then treats every socket as "its path plus this jewel" (runner.lua
   optimise_tree, cmd.jewel), so it travels to sockets exactly when jewels are worth it, and fills each
   socket it takes with a copy so later picks see the jewel.
2. craft_jewels(): after the tree, gear and gems are settled, craft each socket's jewel for real, one
   after another (so the second jewel is crafted with the first one in place), and swap in a unique
   jewel where one clearly beats the rare and fits the budget.
"""
from __future__ import annotations

from gear import (SCORE_FIELDS, Scorer, SlotPlan, Stage, _affix_info, _fill, _tier_choices, _try, _unique_allowed,
                  _Work)
from pob import PoB

JEWEL_BASES = ("Ruby", "Emerald", "Sapphire")
# How many good affixes a rare jewel has at each budget (a jewel holds up to 2 prefixes and 2 suffixes).
JEWEL_AFFIXES = {"free": 2, "budget": 3, "medium": 4, "high": 4, "unlimited": 4}


def jewel_sockets(pob: PoB) -> list[dict]:
    """Plain jewel sockets on the main tree that can be reached (no charm, cluster or ascendancy sockets)."""
    return [s for s in pob.send("jewel_sockets")["sockets"] if s.get("plain") and s.get("linked", 0) > 0]


def _affix_count(stage: Stage) -> int:
    return JEWEL_AFFIXES.get(stage.budget_key, 4)


def _craft_in(pob: PoB, slot: str, stage: Stage, score: Scorer, bases, cache: dict) -> tuple[_Work, float]:
    """Craft the best rare jewel for one (allocated) socket. Returns the jewel and its gain over an empty socket."""
    pob.send("unequip", slot=slot)
    empty = pob.calc(SCORE_FIELDS)
    n = _affix_count(stage)
    best, best_score = None, float("-inf")
    for base in bases:
        if base not in cache:
            cache[base] = pob.send("affixes", base=base, max_level=stage.item_level)["affixes"]
        w = _Work(slot, base, f"{stage.name} Jewel", _tier_choices(cache[base], stage), max_total=n, max_kind=2)
        _fill(pob, w, stage, score, n, allow=lambda g: True)
        sc = score(pob.calc(SCORE_FIELDS), empty)
        if sc > best_score:
            best, best_score = w, sc
    pob.send("equip", slot=slot, raw=best.raw(), fields=SCORE_FIELDS)
    return best, best_score


def proxy_jewel(pob: PoB, stage: Stage, score: Scorer) -> str | None:
    """The best jewel this build could socket, as raw item text, or None if no jewel helps.

    Crafted in the nearest socket (taken just for this, then the build is put back exactly as it was)."""
    socks = jewel_sockets(pob)
    target = next((s for s in socks if s["alloc"]), None) or min(
        (s for s in socks if s.get("dist")), key=lambda s: s["dist"], default=None)
    if not target:
        return None
    xml = pob.save_xml()
    try:
        pob.send("alloc_ids", ids=[target["id"]])
        w, gain = _craft_in(pob, target["slot"], stage, score, JEWEL_BASES, {})
        return w.raw() if gain > 0 and w.picked else None
    finally:
        pob.load_xml(xml)


def craft_jewels(pob: PoB, stage: Stage, score: Scorer, uniques: bool = True, min_unique_gain: float = 0.02,
                 log=print) -> list[SlotPlan]:
    """A jewel for every socket the tree took, crafted one after another, uniques where they clearly win."""
    socks = [s for s in jewel_sockets(pob) if s["alloc"]]
    plans: list[SlotPlan] = []
    if not socks:
        return plans
    cache: dict = {}
    works: list[_Work] = []
    base_order = JEWEL_BASES
    for s in socks:
        w, _ = _craft_in(pob, s["slot"], stage, score, base_order, cache)
        works.append(w)
        # Later sockets start with the base that won the first one (the pools differ by attribute), plus the others
        # only on the first socket: crafting three bases per socket is slow and rarely changes the answer.
        base_order = (w.base,)

    if uniques:
        from gear import BUDGET_DIVINES
        if BUDGET_DIVINES.get(stage.budget_key, 0) > 0:
            pool = [u for u in pob.list_uniques() if u["type"] == "Jewel" and (u.get("level") or 0) <= stage.level]
            allowed = [(u, note) for u in pool for ok, note in [_unique_allowed(u["name"], stage)] if ok]
            used: set[str] = set()
            for w in works:
                cands = [(u, note) for u, note in allowed if u["name"] not in used]
                if not cands:
                    break
                current = pob.calc(SCORE_FIELDS)
                outs = _try(pob, w.slot, [u["raw"] for u, _ in cands])
                best, best_score = None, min_unique_gain
                for (u, note), out in zip(cands, outs):
                    if out is not None and (sc := score(out, current)) > best_score:
                        best, best_score = (u, note), sc
                if best:
                    u, note = best
                    w.unique, w.unique_raw, w.price_note = u["name"], u["raw"], note
                    used.add(u["name"])
                    pob.send("equip", slot=w.slot, raw=u["raw"], fields=SCORE_FIELDS)

    for w in works:
        if w.unique:
            log(f"  {w.slot:<12} UNIQUE {w.unique} ({w.price_note})")
            plans.append(SlotPlan(w.slot, w.unique.split(",")[-1].strip(), [], w.unique_raw, w.unique, w.price_note))
        else:
            log(f"  {w.slot:<12} {w.base:<10} " + "; ".join(w.picked))
            plans.append(SlotPlan(w.slot, w.base, w.picked, w.raw(), affix_info=_affix_info(w)))
    return plans
