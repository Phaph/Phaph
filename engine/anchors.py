"""Anchors: the one thing a player wants a build made around.

"Build around Atziri's Allure", "Chaos Inoculation build", "built around Brutality". The anchor is locked first;
skill, weapon, ascendancy, supports, passives and the rest of the gear are then chosen to suit it, exactly as
they would be for any build. This is how off-meta builds are usually made: start from an odd piece, then find
what makes it work.

  unique:   always equipped (from the first stage whose level allows it). A weapon unique locks the weapon type;
            an off-hand one (shield, focus, quiver) locks the off hand and a weapon that can hold it.
  keystone: allocated with its path before the passive search, which then never takes it back (runner.lua
            optimise_tree `locked`). Stages too low to reach it go without, with a note.
  support:  always in the main skill's supports; only skills it can support are candidates.

The anchor ignores the budget (the player asked for it by name); the page says what it costs.
"""
from __future__ import annotations

from gear import unique_prices

ARMOUR = {"Helmet": "Helmet", "Body Armour": "Body Armour", "Gloves": "Gloves", "Boots": "Boots",
          "Amulet": "Amulet", "Ring": "Ring 1", "Belt": "Belt"}
OFFHAND = {"Shield", "Buckler", "Focus", "Quiver"}
NEEDS_NO_WEAPON = {"Hollow Palm Technique"}   # the engine always gives a build a weapon
NOT_ANCHOR = {"Jewel", "Flask", "Charm", "Life Flask", "Mana Flask"}


def unique_slot(u: dict) -> str | None:
    """The slot a unique is worn in, or None for jewels, flasks and charms (not anchors yet)."""
    t = u.get("type") or ""
    if t in NOT_ANCHOR:
        return None
    if t in ARMOUR:
        return ARMOUR[t]
    if t in OFFHAND:
        return "Weapon 2"
    return "Weapon 1"


def find_unique(uniques: list[dict], name: str) -> dict | None:
    """PoB lists uniques as "Name, Base" (some have several bases): the first equippable one by name."""
    key = name.split(",")[0].strip().lower()
    for u in uniques:
        if u["name"].split(",")[0].strip().lower() == key and unique_slot(u):
            return {**u, "slot": unique_slot(u)}
    return None


def resolve(pob, req: dict) -> tuple[dict, dict, list[str]]:
    """(anchors for the PoB client, request changes, notes) from req's anchor_unique / anchor_keystone /
    anchor_support. Raises ValueError for a name that doesn't exist."""
    anchors: dict = {}
    change: dict = {}
    notes: list[str] = []
    if req.get("anchor_unique"):
        u = find_unique(pob.list_uniques(), req["anchor_unique"])
        if not u:
            raise ValueError(f"No wearable unique called {req['anchor_unique']} (jewels, flasks and charms can't be "
                             f"built around yet).")
        anchors["unique"] = {k: u.get(k) for k in ("name", "raw", "type", "subType", "level", "slot", "base")}
        if u["slot"] == "Weapon 1":
            change["weapons"] = [u["type"]]
            if u.get("subType"):
                change["_weapon_subtype"] = u["subType"]
        elif u["slot"] == "Weapon 2":
            change["_offhand"] = u["type"]
        price = unique_prices().get(u["name"].split(",")[0])
        name = u["name"].split(",")[0]
        notes.append(f"Built around {name}" + (f" (about {price:g} divines)" if price is not None else "")
                     + ": it's worn at every stage that meets its level, and everything else was picked to suit it.")
    if req.get("anchor_keystone"):
        names = {k["name"].lower(): k["name"] for k in pob.list_keystones()}
        ks = names.get(req["anchor_keystone"].lower())
        if not ks:
            raise ValueError(f"No keystone called {req['anchor_keystone']}.")
        if ks in NEEDS_NO_WEAPON:
            notes.append(f"{ks} needs empty hands, and builds without a weapon aren't made yet, so it was left out.")
            ks = None
    if req.get("anchor_keystone") and ks:
        anchors["keystone"] = ks
        notes.append(f"Built around {ks}: the passive tree always takes it, and the skill and gear were picked to suit it.")
    if req.get("anchor_support"):
        sup = {g["name"].lower(): g["name"] for g in pob.list_gems("support")}.get(req["anchor_support"].lower())
        if not sup:
            raise ValueError(f"No support gem called {req['anchor_support']}.")
        anchors["support"] = sup
        notes.append(f"Built around {sup}: it's always one of the main skill's supports, and only skills it "
                     f"supports were tried.")
    return anchors, change, notes


def stage_notes(anchor_notes: list[str] | None) -> list[str]:
    """The guide's words for what an anchor couldn't do at one stage."""
    out = []
    for n in anchor_notes or []:
        kind, _, name = n.partition(":")
        if kind == "keystone":
            out.append(f"{name} is too far away for the points this stage has, so it's taken at the next stage.")
        elif kind == "unique_level":
            out.append(f"{name.split(',')[0]} needs a higher level than this stage, so a crafted item stands in for now.")
    return out
