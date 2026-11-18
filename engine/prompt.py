"""Prompt mode: turn "lightning minion build for a monk, 5 div" into a /generate request.

Keyword based, no AI: every phrase we recognise maps to one picker option, and the website fills the picker in
so the player sees exactly what was understood and can fix it. Skill, class and ascendancy names come from
PoB's catalog, so they follow PoB updates on their own. A Claude fallback for vaguer prompts can sit on top
later; this covers the common shapes for free.
"""
from __future__ import annotations

import re

from goals import FOCUS

# phrase pattern (regex, matched on whole words) -> value
DAMAGE = {
    r"phys(ical)?": "physical", r"fire|flames?|burning": "fire", r"cold|ice|icy|frost": "cold",
    r"lightning|lighting|electric|thunder|electrocut(e|es|ion|ing)": "lightning", r"chaos": "chaos",
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
    r"dot|damage over time|degen": "dot", r"novas?": "nova", r"walls?": "wall", r"orbs?": "orb",
    r"remnants?": "remnant", r"ballista(e|s)?": "ballista", r"companions?|beasts?|tamed": "companion",
    r"ranged": "ranged", r"bears?": "bear", r"wolf|wolves|werewolf": "wolf", r"wyverns?|dragons?": "wyvern",
    r"plants?|vines?|nature": "plant", r"barrage": "barrage", r"rains?": "rain", r"invocations?": "invocation",
    r"detonat(e|or|ion)s?": "detonate", r"ice crystals?": "ice crystal", r"skeletons?|skellies": "skeleton",
    r"undead": "undead", r"demons?": "demon", r"storms?": "storm",
}
# weapon word -> PoB weapon types it means (kept only if PoB's catalog has them)
WEAPONS = {
    # One- and two-handed first: the matched words are blanked, so "two hand mace" isn't also any "mace".
    r"(two|2)[- ]?hand(ed)? (maces?|hammers?)|2h (maces?|hammers?)": ["Two Hand Mace"],
    r"(one|1)[- ]?hand(ed)? (maces?|hammers?)|1h (maces?|hammers?)": ["One Hand Mace"],
    r"(two|2)[- ]?hand(ed)? swords?|2h swords?|greatswords?": ["Two Hand Sword"],
    r"(one|1)[- ]?hand(ed)? swords?|1h swords?": ["One Hand Sword"],
    r"(two|2)[- ]?hand(ed)? axes?|2h axes?|greataxes?": ["Two Hand Axe"],
    r"(one|1)[- ]?hand(ed)? axes?|1h axes?": ["One Hand Axe"],
    r"(two|2)[- ]?hand(ed)?( weapons?)?|2h( weapons?)?": ["Two Hand Mace", "Two Hand Sword", "Two Hand Axe", "Staff"],
    r"bows?": ["Bow"], r"crossbows?|xbows?": ["Crossbow"], r"daggers?": ["Dagger"], r"claws?": ["Claw"],
    r"spears?": ["Spear"], r"(quarter)?sta(ff|ves)": ["Staff"], r"wands?": ["Wand"], r"scept(re|er)s?": ["Sceptre"],
    r"maces?|hammers?": ["One Hand Mace", "Two Hand Mace"], r"swords?": ["One Hand Sword", "Two Hand Sword"],
    r"axes?": ["One Hand Axe", "Two Hand Axe"], r"flails?": ["Flail"], r"talismans?": ["Talisman"],
}
GOALS = {
    r"move(ment)? ?speed|movespeed|fast|faster|speedy|zoom(y|ing)?|movement": "movement",
    r"loot|rarity|magic find|mf|iir": "rarity",
    r"tank(y|ier)?|tough(er)?|surviv(e|able|al)|durable|safe|hardcore|hc|defen[cs]ive": "tanky",
}
# Stat focuses (goals.FOCUS), read before the tables above and blanked out, so "cast speed" is not also "Kind: spell"
# and "fast attacks" not also "Faster mapping". Longest phrases first within each entry.
FOCUS_WORDS = {
    r"crit(ical)? (strike|hit)s?( chance)?|crit (chance|multi(plier)?|damage)|crit(ical)? stack(ing|er)?|crits?|critical(ly)?": "crit",
    r"((fast|faster|high|more) )?(attack|cast(ing)?|skill|swing) speed|fast (attacks?|cast(s|ing)?|hits?)|speed stack(ing|er)?|ias|ics": "speed",
    r"energy shield( stack(ing|er)?)?|es stack(ing|er)?|ci|chaos inoculation|es": "es",
    r"(max(imum)? |spell |shield )?block(ing| chance)?|blocker|shields?": "block",
    r"(life )?leech(ing|er)?|lifesteal|life steal": "leech",
    r"(life )?regen(eration)?|recovery": "regen",
    r"(?<!low )(?:life( stack(ing|er)?)?|hp|health|high life)": "life",   # not "low life", the opposite
    r"armou?r( stack(ing|er)?)?|armou?red": "armour",
    r"evasion( stack(ing|er)?)?|evade|evasive|eva|dodge": "evasion",
    r"mana( stack(ing|er)?)?|mom|mind over matter": "mana",
    r"str(ength)?( stack(ing|er)?)?": "str",
    r"dex(terity)?( stack(ing|er)?)?": "dex",
    r"int(elligence)?( stack(ing|er)?)?": "int",
    r"spirit( stack(ing|er)?)?": "spirit",
}
# Kinds of helper skill: "with warcries" adds the best warcry for the build (generate.HELPER_TYPES).
HELPER_WORDS = {
    r"warcr(y|ies)|war cr(y|ies)|shouts?|cr(y|ies)": "warcry", r"auras?": "aura", r"heralds?": "herald",
    r"curses?|hex(es)?": "curse", r"banners?": "banner", r"marks?": "mark", r"offerings?": "offering",
}
MODE = {
    r"boss(es|ing|er)?|pinnacle|single target|ubers?": "bossing",
    r"mapp(ing|er)|maps|clear(ing)?|clear speed|farm(ing)?": "mapping",
}
# "Find me the strongest build there is": a deep search (see generate.py).
DEEP = (r"(highest|max(imum)?|most|biggest|top|insane|crazy)\s+(possible\s+)?(dps|damage)"
        r"|(strongest|most broken|broken|overpowered)\s+(possible\s+)?builds?"
        r"|(highest|max(imum)?|strongest|best)\s+possible|deep search|search everything|try everything")
NEGATION = r"(?:no|not|non|without|avoid|avoiding|hate)\s+(?:\w+\s+)?"
CURRENCY = r"(\d+(?:\.\d+)?)\s*(k\b)?\s*(div(?:ine)?s?|d\b|ex(?:alt(?:ed)?s?)?\b|chaos(?: orbs?)?)"


# Short names players type for skills; matched as whole words.
SKILL_ALIASES = {
    "coc": "Cast on Critical", "cast on crit": "Cast on Critical",
    "coea": "Cast on Elemental Ailment", "cast on ailment": "Cast on Elemental Ailment",
    "com": "Cast on Minion Death", "cod": "Cast on Dodge",
    "cast on freeze": "Cast on Elemental Ailment", "cast on ignite": "Cast on Elemental Ailment",
    "cast on shock": "Cast on Elemental Ailment", "cast on chill": "Cast on Elemental Ailment",
    "spectre": "Summon Spectre", "spectres": "Summon Spectre", "corpse explosion": "Detonate Dead",
}
# Off-meta and random builds (generate.py): words for each.
OFF_META = (r"off[- ]?meta|non[- ]?meta|anti[- ]?meta|unpopular|niche|under(played|used|rated)|hipster|unusual|unique "
            r"builds?|nobody (plays|uses)|no ?one (plays|uses)|not (the )?meta|weird|jank(y)?|meme builds?|crazy builds?"
            r"|creative|outside the box|something different")
RANDOM = r"random(i[sz]e[ds]?|ly)?|surprise me|roll (me )?a build|anything goes|dealer'?s choice|spin the wheel"
# Short names for keystones (only used when that keystone exists in PoB's tree).
KEYSTONE_ALIASES = {"ci": "Chaos Inoculation", "mom": "Mind Over Matter", "eb": "Eldritch Battery",
                    "rt": "Resolute Technique", "hollow palm": "Hollow Palm Technique",
                    "unarmed": "Hollow Palm Technique"}
# A keystone also says what the build stands on: CI means energy shield.
KEYSTONE_GOALS = {"Chaos Inoculation": "es", "Mind Over Matter": "mana", "Eldritch Battery": "es"}
# A support is only read as the anchor after "around" ("built around brutality"), or typed with its tier
# ("Martial Tempo II"): support names are everyday words ("bleed", "life leech") the other tables need.
AROUND = r"(?:(?:built?|made|centered|centred|based)\s+)?around\s+(?:the\s+)?"
ROMAN = re.compile(r"\s+(I|II|III|IV|V)$")


def name_pattern(name: str) -> str:
    """A unique or keystone name as typed: any case, apostrophe optional ("atziris allure")."""
    return r"\s+".join(re.escape(w).replace("'", "'?") for w in name.lower().split())


# One-word skill names that are also a kind of skill: "grenade build" means grenade skills, not the gem "Grenade".
KIND_NOT_SKILL = {"Grenade"}


def skill_pattern(name: str) -> str:
    """How a skill name may be typed: any word may be plural ("sparks", "comets"), and in a name of two or more
    words the last word may be shortened to its first four letters or more ("cast on crit" = Cast on Critical)."""
    words = name.lower().split()

    def plural(w: str) -> str:
        return re.escape(w) + "(?:s|es)?"
    parts = [plural(w) for w in words]
    last = words[-1]
    if len(words) >= 2 and len(last) > 4:
        # "crit", "criti", "critical" (and plural): a prefix of the last word, at least four letters long.
        prefixes = "|".join(re.escape(last[:k]) for k in range(len(last), 3, -1))
        parts[-1] = f"(?:{prefixes})(?:s|es)?"
    return r"\s+".join(parts)


# Filler words: never reported as "not used".
FILLER = set("""a an the and or with without for of to in on at by from as is are be it its that this these my me i
im i'm want wants need give make makes made build builds character char setup please some any can you could would
should like using use uses used good great nice strong strongest best top high highest max maximum most possible
dps damage league new also but very really just one two which what who how do does get got so all every whole game
ever time around based killer killing slayer player players new newbie beginner first focus focused focusing type style playstyle version no not non avoid avoiding hate""".split())


def unused_words(text: str, found: list[tuple[str, str]]) -> list[str]:
    """Words of the prompt that nothing matched, so the player sees what was not taken into account."""
    t = _norm(text)
    for phrase, _ in sorted(found, key=lambda f: -len(f[0])):
        t = re.sub(rf"(?<![\w']){re.escape(phrase)}(?![\w'])", " ", t, count=1)
    out = []
    for w in t.split():
        w = w.strip(".-'")
        if w and w not in FILLER and not w.isdigit() and w not in out:
            out.append(w)
    return out


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


def parse_prompt(text: str, catalog: dict) -> dict:
    """Returns {"request": <GenerateRequest fields>, "found": [(phrase, meaning)], "unused": [words]}.

    catalog is the API's /catalog: classes (with ascendancies), skills and weapon_types.
    """
    prompt_text = text
    t = _norm(text)
    req: dict = {"damage": [], "kinds": [], "weapons": [], "goals": []}
    found: list[tuple[str, str]] = []

    # Currency amounts ("5 div", "20 chaos") mean nothing (the site has no budget), but are blanked out so "20 chaos"
    # isn't read as chaos damage.
    amounts = []
    while (m := re.search(CURRENCY, t)):
        amounts.append(m.group(0))
        t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]

    # Random and off-meta first ("random build", "off meta"), then what the build is made around (anchors.py): a unique,
    # a keystone, a support gem. Each is blanked out, so "Chaos Inoculation" isn't also read as chaos damage.
    def cut(m):
        nonlocal t
        t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
    if (m := re.search(rf"(?<![\w'])(?:{OFF_META})(?![\w'])", t)):
        req["off_meta"] = True
        found.append((m.group(0), "Off-meta: popular skills, ascendancies and uniques score lower"))
        cut(m)
    if (m := _find(RANDOM, t)):
        req["random"] = True
        found.append((m.group(0), "Random build: picked at random, not by damage"))
        cut(m)
    for name in sorted(catalog.get("uniques", []), key=len, reverse=True):
        if len(name) >= 5 and (m := _find(name_pattern(name), t)):
            req["anchor_unique"] = name
            found.append((m.group(0), f"Built around: {name}"))
            cut(m)
            break
    keystones = set(catalog.get("keystones", []))
    ks_pats = [(name_pattern(k), k) for k in sorted(keystones, key=len, reverse=True)]
    ks_pats += [(a, k) for a, k in KEYSTONE_ALIASES.items() if k in keystones]
    for pat, name in ks_pats:
        if (m := _find(pat, t)):
            req["anchor_keystone"] = name
            found.append((m.group(0), f"Built around: {name}"))
            cut(m)
            if KEYSTONE_GOALS.get(name) and KEYSTONE_GOALS[name] not in req["goals"]:
                req["goals"].append(KEYSTONE_GOALS[name])
            break
    # Supports: the full name ("Martial Tempo"), or the name without its tier ("brutality" = the top Brutality).
    # Only after "around", unless typed with its tier (see AROUND).
    tiers: dict[str, str] = {}
    for sup in catalog.get("supports", []):
        tiers[sup] = sup
        base = ROMAN.sub("", sup)
        if base != sup and (base not in tiers or sup > tiers[base]):
            tiers[base] = sup
    for typed, sup in sorted(tiers.items(), key=lambda kv: -len(kv[0])):
        pat = name_pattern(typed)
        if not ROMAN.search(typed):
            pat = AROUND + pat
        if (m := _find(pat, t)):
            req["anchor_support"] = sup
            found.append((m.group(0), f"Built around: {sup}"))
            cut(m)
            break

    # Names from PoB: skill (longest first so "Lightning Arrow" beats "Lightning"), ascendancy, class.
    # Every skill named, longest first ("Lightning Arrow" before "Lightning"). Each match is blanked out of the
    # text so its words aren't read again ("cast" in "Cast on Elemental Ailment" is not "Kind: spell"). The first
    # damage skill becomes the locked main skill; Cast on X gems, buffs, auras and heralds are kept beside it.
    helper_names = set(catalog.get("helper_skills", []))
    known = set(catalog.get("skills", []))
    named = []

    def take(skill: str, pattern: str):
        nonlocal t
        if (m := _find(pattern, t)):
            if skill not in {n for _, n, _ in named}:
                named.append((m.start(), skill, m.group(0)))
            t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
    # Abbreviations first ("coc"), then full names longest first (plurals and shortened last words allowed).
    for alias, skill in sorted(SKILL_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if skill in known:
            take(skill, re.escape(alias))
    for skill in sorted(known - KIND_NOT_SKILL, key=len, reverse=True):
        take(skill, skill_pattern(skill))
    named.sort()
    helpers = []
    for _, skill, text in named:
        if skill not in helper_names and not req.get("skill"):
            req["skill"] = skill
            found.append((text, f"Skill: {skill}"))
        else:
            helpers.append(skill)
            found.append((text, f"With: {skill}"))
    if helpers:
        req["with_skills"] = helpers[:3]
    # Longest names first, so "Abyssal Lich" is read before "Lich".
    asc_pairs = sorted(((asc, c) for c in catalog.get("classes", []) for asc in c.get("ascendancies", [])),
                       key=lambda ac: -len(ac[0]))
    for asc, c in asc_pairs:
        if not req.get("ascendancy") and (m := _find(re.escape(asc.lower()) + "s?", t)):
            req["ascendancy"], req["class"] = asc, c["name"]
            found.append((m.group(0), f"Ascendancy: {asc} ({c['name']})"))
            t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
            if (cm := _find(re.escape(c["name"].lower()) + "e?s?", t)):   # "shaman druid": the class said too
                found.append((cm.group(0), f"Class: {c['name']}"))
                t = t[:cm.start()] + " " * (cm.end() - cm.start()) + t[cm.end():]
    if not req.get("class"):
        for c in catalog.get("classes", []):
            if (m := _find(re.escape(c["name"].lower()) + "e?s?", t)):
                req["class"] = c["name"]
                found.append((m.group(0), f"Class: {c['name']}"))
                t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
                break

    consumed: list[str] = []

    def blank(m):
        nonlocal t
        t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]

    for pat, val in FOCUS_WORDS.items():
        while (m := _find(pat, t)):
            if val not in req["goals"]:
                req["goals"].append(val)
                found.append((m.group(0), f"Focus: {FOCUS[val][2]}"))
            blank(m)
    for pat, val in HELPER_WORDS.items():
        if (m := _find(pat, t)):
            req.setdefault("with_types", [])
            if val not in req["with_types"]:
                req["with_types"].append(val)
                found.append((m.group(0), f"With: best {val}"))
            blank(m)

    # "no minions", "without chaos": the build never uses that as its main skill (generate.main_skills).
    for table in (DAMAGE, KINDS):
        for pat, val in table.items():
            while (m := re.search(rf"(?<![\w']){NEGATION}(?:{pat})(?![\w'])", t)):
                if val not in req.setdefault("avoid", []):
                    req["avoid"].append(val)
                    found.append((m.group(0), f"Not: {val}"))
                blank(m)

    for table, field, label in ((DAMAGE, "damage", "Damage"), (KINDS, "kinds", "Kind"), (GOALS, "goals", "Goal")):
        for pat, val in table.items():
            while (m := _find(pat, t)):
                if val not in req[field]:
                    req[field].append(val)
                    found.append((m.group(0), f"{label}: {val}"))
                else:
                    consumed.append(m.group(0))   # said twice ("fast ... movement speed"): understood, shown once
                blank(m)

    for pat, val in AILMENT.items():
        if (m := _find(pat, t)):
            req["ailment"] = val
            found.append((m.group(0), f"Ailment: {val}"))
            break

    # Weapons in the order they're named: the first is the main weapon; a second one goes on weapon set 2
    # ("crossbow mace build" = a crossbow build with a mace swap). More than two: the rest are ignored.
    known_weapons = set(catalog.get("weapon_types", {}))
    named = []
    for pat, types in WEAPONS.items():
        if (m := _find(pat, t)):
            named.append((m.start(), m.group(0), [w for w in types if not known_weapons or w in known_weapons]))
            t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
    for i, (_, text, types) in enumerate(sorted(named)[:2]):
        key = "weapons" if i == 0 else "second_weapons"
        req.setdefault(key, [])
        req[key] += [w for w in types if w not in req[key]]
        found.append((text, f"Weapon: {' or '.join(types)}" if i == 0 else f"Weapon set 2: {' or '.join(types)}"))

    modes = [(m, val) for pat, val in MODE.items() if (m := _find(pat, t))]
    if len(modes) == 1:
        req["mode"] = modes[0][1]
        found.append((modes[0][0].group(0), f"Focus: {modes[0][1]}"))

    if (m := _find(DEEP, t)):
        req["deep"] = True
        found.append((m.group(0), "Deep search: every skill gets a fair chance"))
        if "mode" not in req and re.search(r"dps|damage", m.group(0)):
            req["mode"] = "bossing"
            found.append((m.group(0), "Focus: bossing (raw damage)"))

    # The request schema caps lists at 5.
    for k in ("damage", "kinds", "weapons"):
        req[k] = req[k][:5]
    req["goals"] = req["goals"][:8]
    if "with_types" in req:
        req["with_types"] = req["with_types"][:3]
    return {"request": req, "found": [{"text": a, "means": b} for a, b in found],
            "unused": unused_words(prompt_text, found + [(c, "") for c in consumed + amounts])}
