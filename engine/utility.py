"""Utility skills: curses, marks, banners and warcries that make the main skill hit harder.

Each candidate is added as its own skill and the main skill's score is re-measured (PoB applies
their effects to the calculation). A utility skill whose weapon the main hand can't use goes
on weapon set 2 with a plain weapon of the type it needs: the "crossbow build with a bow on
swap" case. The best ones are kept, up to `limit`, and PoB's own limits (one curse unless the
build allows more) still apply.
"""
from __future__ import annotations

from optimize import CLEAR_FIELDS, DPS_FIELDS, score_of
from pob import PoB, PoBError

UTILITY_TYPES = {"AppliesCurse", "Mark", "Banner", "Warcry"}
FIELDS = [*DPS_FIELDS, *CLEAR_FIELDS, "TotalEHP"]


def utility_candidates(catalog: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in catalog:
        types = set(s["types"])
        if types & UTILITY_TYPES and "Persistent" not in types and not s.get("from_item") and s["name"] not in seen:
            seen.add(s["name"])
            out.append(s)
    return out


def _plain_weapon(pob: PoB, weapon_type: str, max_level: int) -> str | None:
    bases = [b for b in pob.send("bases", types=[weapon_type], max_level=max_level)["bases"]
             if not b["name"].startswith("Runeforged")]
    if not bases:
        return None
    best = max(bases, key=lambda b: b["level"])
    return f"Rarity: Normal\n{best['name']}"


def optimise_utility(pob: PoB, catalog: list[dict], main_weapon: str, metric: str, item_level: int = 82,
                     swap_weapon: str | None = None, limit: int = 2, min_gain: float = 0.03,
                     log=print) -> list[dict]:
    """Returns the utility skills kept: {"skill", "weapon_set", "weapon", "gain"}.
    `swap_weapon`: weapon type already on weapon set 2 (e.g. for a boss skill), if any."""
    chosen: list[dict] = []
    tried_swap_weapon = swap_weapon
    for _ in range(limit):
        base = score_of(pob.calc(FIELDS), metric)
        if base <= 0:
            break
        best = None
        for cand in utility_candidates(catalog):
            if any(c["skill"] == cand["name"] for c in chosen):
                continue
            weapons = [w for w in cand["weapons"] if w != "None"]
            needs_swap = bool(weapons) and main_weapon not in weapons
            weapon = None
            if needs_swap:
                if tried_swap_weapon and tried_swap_weapon in weapons:
                    weapon = tried_swap_weapon
                elif tried_swap_weapon:
                    continue   # weapon set 2 already holds a different weapon type
                else:
                    weapon = weapons[0]
            try:
                group = pob.add_skill([cand["name"]], main=False)["group"]
                equipped = False
                if needs_swap:
                    pob.send("set_weapon_set", group=group, set=2)
                    if weapon != swap_weapon:
                        raw = _plain_weapon(pob, weapon, item_level)
                        if raw:
                            pob.send("equip", slot="Weapon 1 Swap", raw=raw, fields=["TotalDPS"])
                            equipped = True
                gain = score_of(pob.calc(FIELDS), metric) / base - 1
                pob.remove_skill(group)
                if equipped:
                    pob.send("unequip", slot="Weapon 1 Swap")
            except PoBError:
                continue
            if gain > min_gain and (best is None or gain > best["gain"]):
                best = {"skill": cand["name"], "weapon_set": 2 if needs_swap else 1, "weapon": weapon, "gain": gain}
        if not best:
            break
        group = pob.add_skill([best["skill"]], main=False)["group"]
        if best["weapon_set"] == 2:
            pob.send("set_weapon_set", group=group, set=2)
            if best["weapon"] != swap_weapon:
                raw = _plain_weapon(pob, best["weapon"], item_level)
                if raw:
                    pob.send("equip", slot="Weapon 1 Swap", raw=raw, fields=["TotalDPS"])
            tried_swap_weapon = best["weapon"]
        chosen.append(best)
        where = f" (weapon set 2, {best['weapon']})" if best["weapon_set"] == 2 else ""
        log(f"  utility: + {best['skill']}{where} ({best['gain']:+.0%})")
    return chosen
