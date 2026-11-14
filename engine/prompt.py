"""Prompt mode: turn "lightning minion build for a monk, 5 div" into a /generate request.

Keyword based, no AI: every phrase we recognise maps to one picker option, and the website fills the picker in
so the player sees exactly what was understood and can fix it. Skill, class and ascendancy names come from
PoB's catalog, so they follow PoB updates on their own. A Claude fallback for vaguer prompts can sit on top
later; this covers the common shapes for free.
"""
from __future__ import annotations

import re

# phrase pattern (regex, matched on whole words) -> value
DAMAGE = {
    r"phys(ical)?": "physical", r"fire|flames?|burning": "fire", r"cold|ice|icy|frost": "cold",
    r"lightning|lighting|electric|thunder|storms?": "lightning", r"chaos": "chaos",
}
AILMENT = {
    r"bleed(s|ing)?": "bleed", r"poison(s|ous)?": "poison", r"ignites?": "ignite",
    r"shocks?": "shock", r"chill(s|ed)?": "chill", r"freez(e|es|ing)|frozen": "freeze",
}
KINDS = {
    r"minions?|summon(er|s|ing)?|necro(mancer)?|skeletons?|zombies?|pets?": "minion",
    r"spells?|cast(er|ing)?": "spell", r"attacks?": "attack", r"melee": "melee",
    r"projectiles?": "projectile", r"totems?": "totem", r"traps?": "trap", r"slams?": "slam",
    r"strikes?": "strike", r"aoe|area": "area", r"channel(l?ing|led)?": "channel",
    r"chain(s|ing)?": "chaining", r"grenades?": "grenade", r"ammo": "ammo",
}
# weapon word -> PoB weapon types it means (kept only if PoB's catalog has them)
WEAPONS = {
    r"bows?": ["Bow"], r"crossbows?|xbows?": ["Crossbow"], r"daggers?": ["Dagger"], r"claws?": ["Claw"],
    r"spears?": ["Spear"], r"(quarter)?sta(ff|ves)": ["Staff"], r"wands?": ["Wand"], r"scept(re|er)s?": ["Sceptre"],
    r"maces?|hammers?": ["One Hand Mace", "Two Hand Mace"], r"swords?": ["One Hand Sword", "Two Hand Sword"],
    r"axes?": ["One Hand Axe", "Two Hand Axe"], r"flails?": ["Flail"], r"talismans?": ["Talisman"],
}
GOALS = {
    r"fast|faster|speedy|zoom(y|ing)?|movement|move speed": "movement",
    r"loot|rarity|magic find|mf|iir": "rarity",
    r"tank(y|ier)?|tough(er)?|surviv(e|able|al)|durable|safe|hardcore|hc|defen[cs]ive": "tanky",
}
MODE = {
    r"boss(es|ing|er)?|pinnacle|single target|ubers?": "bossing",
    r"mapp(ing|er)|maps|clear(ing)?|clear speed|farm(ing)?": "mapping",
}
# Checked in this order, so "high budget" is high, not the plain "budget" rule.
BUDGET_WORDS = {
    r"no limit|unlimited|mirror(ed)?|money is no object|max budget": "unlimited",
    r"expensive|high budget|rich": "high",
    r"medium|mid budget|moderate": "medium",
    r"ssf|self found|no money|broke|zero budget|free": "free",
    r"cheap|budget|league start(er|ing)?|starter": "budget",
}
NEGATION = r"(?:no|not|non|without|avoid|avoiding|hate)\s+(?:\w+\s+)?"
CURRENCY = r"(\d+(?:\.\d+)?)\s*(k\b)?\s*(div(?:ine)?s?|d\b|ex(?:alt(?:ed)?s?)?\b|chaos(?: orbs?)?)"


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"[^a-z0-9'.\s-]", " ", text)


def _find(pattern: str, text: str) -> re.Match | None:
    """Whole-word match that isn't negated ("no minions")."""
    for m in re.finditer(rf"(?<![\w'])(?:{pattern})(?![\w'])", text):
        before = text[max(0, m.start() - 30):m.start()]
        if not re.search(rf"(?<![\w']){NEGATION}$", before):
            return m
    return None


def divines_to_budget(div: float) -> str:
    if div <= 0:
        return "free"
    if div <= 5:
        return "budget"
    if div <= 30:
        return "medium"
    if div <= 100:
        return "high"
    return "unlimited"


def parse_prompt(text: str, catalog: dict, divine_in_exalts: float = 640, divine_in_chaos: float = 10) -> dict:
    """Returns {"request": <GenerateRequest fields>, "found": [(phrase, meaning)], "budget_set": bool}.

    catalog is the API's /catalog: classes (with ascendancies), skills and weapon_types.
    """
    t = _norm(text)
    req: dict = {"damage": [], "kinds": [], "weapons": [], "goals": []}
    found: list[tuple[str, str]] = []

    # Budget from an amount first ("5 div", "300 ex", "2k chaos"), then from words.
    m = re.search(CURRENCY, t)
    if m:
        n = float(m.group(1)) * (1000 if m.group(2) else 1)
        unit = m.group(3)
        div = n if unit.startswith("d") else n / divine_in_exalts if unit.startswith("ex") else n / divine_in_chaos
        req["budget"] = divines_to_budget(div)
        found.append((m.group(0).strip(), f"Budget: {req['budget']}"))
        t = t[:m.start()] + " " + t[m.end():]   # so "20 chaos" isn't also chaos damage
    else:
        for pat, key in BUDGET_WORDS.items():
            if (m := _find(pat, t)):
                req["budget"] = key
                found.append((m.group(0), f"Budget: {key}"))
                break

    # Names from PoB: skill (longest first so "Lightning Arrow" beats "Lightning"), ascendancy, class.
    for skill in sorted(catalog.get("skills", []), key=len, reverse=True):
        if (m := _find(re.escape(skill.lower()), t)):
            req["skill"] = skill
            found.append((m.group(0), f"Skill: {skill}"))
            break
    for c in catalog.get("classes", []):
        for asc in c.get("ascendancies", []):
            if not req.get("ascendancy") and (m := _find(re.escape(asc.lower()) + "s?", t)):
                req["ascendancy"], req["class"] = asc, c["name"]
                found.append((m.group(0), f"Ascendancy: {asc} ({c['name']})"))
    if not req.get("class"):
        for c in catalog.get("classes", []):
            if (m := _find(re.escape(c["name"].lower()) + "e?s?", t)):
                req["class"] = c["name"]
                found.append((m.group(0), f"Class: {c['name']}"))
                break

    for table, field, label in ((DAMAGE, "damage", "Damage"), (KINDS, "kinds", "Kind"), (GOALS, "goals", "Goal")):
        for pat, val in table.items():
            if val not in req[field] and (m := _find(pat, t)):
                req[field].append(val)
                found.append((m.group(0), f"{label}: {val}"))

    for pat, val in AILMENT.items():
        if (m := _find(pat, t)):
            req["ailment"] = val
            found.append((m.group(0), f"Ailment: {val}"))
            break

    known_weapons = set(catalog.get("weapon_types", {}))
    for pat, types in WEAPONS.items():
        if (m := _find(pat, t)):
            for w in types:
                if (not known_weapons or w in known_weapons) and w not in req["weapons"]:
                    req["weapons"].append(w)
            found.append((m.group(0), f"Weapon: {' or '.join(types)}"))

    modes = [(m, val) for pat, val in MODE.items() if (m := _find(pat, t))]
    if len(modes) == 1:
        req["mode"] = modes[0][1]
        found.append((modes[0][0].group(0), f"Focus: {modes[0][1]}"))

    # The request schema caps lists at 5.
    for k in ("damage", "kinds", "weapons", "goals"):
        req[k] = req[k][:5]
    return {"request": req, "found": [{"text": a, "means": b} for a, b in found], "budget_set": "budget" in req}
