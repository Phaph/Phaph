"""Build generator: from a theme ("lightning minion", optional class) to the strongest
skill + weapon + ascendancy, with every alternative ranked.

Round 1 (skills): every main skill that fits the theme, on each weapon it can use, gets a
crafted weapon and its best supports, and is scored by PoB. The top few go on.
Round 2 (ascendancies): those skills are tried on every allowed ascendancy with passive and
ascendancy points spent, and scored again.

The result is a ranked list. The winner becomes a guide spec; the rest power the feedback
option ("I want the other ascendancy"): we already know how much damage it costs.

Request:
    {"damage": ["lightning"], "kinds": ["minion"], "ailment": null, "weapons": [],
     "class": "Monk", "ascendancy": null, "skill": null, "budget": "high", "mode": "balanced"}
mode: balanced (default: geometric mean of clear and single-target damage) | mapping | bossing
Everything is optional; locked fields (class, ascendancy, skill, weapons) narrow the search.

Deep search ("deep": true) is for "find the strongest build there is". It casts a wider net and
gives skills that only shine with passives a fair chance:
  Round 1:  as above (no passives).
  Round 1b: the best DEEP_POOL skills again, now with a passive tree. Keeps DEEP_SKILLS.
  Round 2a: every one of those skills is scouted on every allowed ascendancy (ascendancy points
            only, which is quick), and keeps its own best DEEP_ASCS.
  Round 2:  each skill on its own best ascendancies, full passive trees.
Normal searches are unchanged.

CLI:  python3 generate.py '{"damage":["lightning"],"kinds":["minion"]}'
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from gear import Scorer, Stage, craft_gear, make_stage
from jewels import proxy_jewel
from optimize import (MODE_CONFIG, ailment_dps, broken_numbers, ailment_score, clear_score, damage_types, hit_dps, metric_for, seed_ailment, optimise_supports,
                      score_of, total_dps)
from pob import PoB, PoBError

# Types that make a skill a support act rather than a main damage skill.
NOT_MAIN = {"Buff", "Aura", "Herald", "Meta", "Triggered", "InbuiltTrigger", "OngoingSkill", "Shapeshift",
            "AppliesCurse", "ActiveBlock"}
from goals import FOCUS_FIELDS, focus_factor  # noqa: E402

KIND_TYPES = {
    "minion": "Minion", "spell": "Spell", "attack": "Attack", "melee": "Melee", "projectile": "Projectile",
    "totem": "SummonsTotem", "slam": "Slam", "strike": "MeleeSingleTarget", "area": "Area",
    "channel": "Channel", "chaining": "Chains", "grenade": "Grenade", "ammo": "CrossbowAmmoSkill",
    "dot": "DamageOverTime", "nova": "Nova", "storm": "Storm", "wall": "Wall", "orb": "Orb", "remnant": "GeneratesRemnants",
    "ballista": "TotemsAreBallistae", "companion": "Companion", "ranged": "RangedAttack", "bear": "Bear",
    "wolf": "Wolf", "wyvern": "Wyvern", "plant": "Plant", "barrage": "Barrageable", "rain": "Rain",
    "jump": "Jumping", "cooldown": "Cooldown", "duration": "Duration", "invocation": "Invocation",
    "detonate": "Detonator", "ice crystal": "IceCrystal", "ground": "CreatesGroundEffect", "skeleton": "CreatesSkeletonMinion",
    "undead": "CreatesUndeadMinion", "demon": "CreatesDemonMinion",
}
# Helper kinds: "warcries", "auras"... The best skill of that type is put beside the main skill (best_helper).
HELPER_TYPES = {"warcry": "Warcry", "aura": "Aura", "herald": "Herald", "curse": "AppliesCurse", "banner": "Banner",
                "mark": "Mark", "offering": "Offering"}
AILMENT_DAMAGE = {"bleed": {"Physical"}, "poison": {"Physical", "Chaos"}, "ignite": {"Fire"},
                  "shock": {"Lightning"}, "chill": {"Cold"}, "freeze": {"Cold"}}
AILMENT_FIELD = {"bleed": "BleedDPS", "poison": "PoisonDPS", "ignite": "IgniteDPS"}
SPELL_WEAPONS = [("Wand", None, None), ("Staff", "none", None)]
MINION_WEAPONS = [("Sceptre", None, None), ("Wand", None, None)]
SHIELD_WEAPONS = [("One Hand Mace", None, "Shield"), ("Spear", None, "Shield")]
ONE_HANDED = {"One Hand Mace", "One Hand Sword", "One Hand Axe", "Claw", "Dagger", "Wand", "Sceptre", "Spear", "Flail"}
THEME_MIN_SHARE = 0.3   # candidates below this share of their theme's ailment are dropped
DEFAULT_CLASS = {"Minion": "Witch", "Spell": "Sorceress"}
DEEP_POOL, DEEP_SKILLS, DEEP_ASCS = 24, 10, 3


@dataclass
class Candidate:
    skill: str
    weapon_type: str
    weapon_subtype: str | None
    offhand_type: str | None
    cls: str
    ascendancy: str | None = None
    score: float = 0.0
    dps: float = 0.0
    clear: float = 0.0
    boss: float = 0.0     # single-target score in the theme's terms (e.g. bleed vs a boss)
    ehp: float = 0.0
    supports: list[str] = field(default_factory=list)
    is_minion: bool = False
    error: str | None = None
    totem: str | None = None   # the totem gem that places the skill (Spell Totem), if any

    def spec(self) -> dict:
        return {"class": self.cls, "ascendancy": self.ascendancy, "skill": self.skill,
                "weapon_type": self.weapon_type, "weapon_subtype": self.weapon_subtype,
                "offhand_type": self.offhand_type, **({"totem": self.totem} if self.totem else {})}


_local = threading.local()
# Each search's worker threads are bound to that search's own list of PoBs, so the search can close all of them
# when it ends (each holds ~800 MB) without touching another search running at the same time. Without this,
# worker threads left their PoB processes running: 21 processes / 17 GB were seen after one search.


def _bind(registry: list) -> None:
    _local.registry = registry


def _pob() -> PoB:
    if getattr(_local, "pob", None) is None:
        _local.pob = PoB()
        reg = getattr(_local, "registry", None)
        if reg is not None:
            reg.append(_local.pob)
    return _local.pob


def _close_all(pobs: list[PoB]) -> None:
    for p in pobs:
        try:
            p.close()
        except Exception:  # noqa: BLE001 - already gone is fine
            pass


MACES = {"One Hand Mace", "Two Hand Mace"}
TOTEM_GEMS = ("Spell Totem", "Ancestral Warrior Totem")


def totem_gem(skill: dict) -> str | None:
    """The totem gem that can place this skill: Spell Totem for spells, Ancestral Warrior Totem for mace attacks."""
    types = set(skill["types"])
    if "Totemable" not in types or "Minion" in types or "SummonsTotem" in types:
        return None
    if "Spell" in types:
        return "Spell Totem"
    if "Attack" in types and MACES & set(skill.get("weapons") or []):
        return "Ancestral Warrior Totem"
    return None


def as_totem(skill: dict, gem: str) -> dict:
    """The skill placed by a totem gem: counts as a totem skill; Ancestral Warrior Totem needs a mace."""
    weapons = [w for w in skill.get("weapons") or [] if w in MACES] if gem == "Ancestral Warrior Totem" else skill.get("weapons")
    return {**skill, "types": [*skill["types"], "SummonsTotem"], "weapons": weapons, "totem": gem}


def main_skills(catalog: list[dict], req: dict) -> list[dict]:
    """Skills that can carry a build and fit the theme."""
    want_damage = {d.capitalize() for d in req.get("damage") or []}
    want_kinds = [KIND_TYPES.get(k.lower(), k) for k in req.get("kinds") or []]
    avoid = {KIND_TYPES.get(a.lower()) or a.capitalize() for a in req.get("avoid") or []}
    ailment = (req.get("ailment") or "").lower() or None
    seen, out = set(), []
    totem_gems = {s["name"] for s in catalog if s["name"] in TOTEM_GEMS}
    if req.get("_totem_gem"):
        totem_gems &= {req["_totem_gem"]}
    if "SummonsTotem" in want_kinds:
        # A totem build can also be any skill a totem gem places (Spell Totem + Fireball, Ancestral Warrior Totem +
        # Boneshatter): those are offered as totem skills too.
        catalog = list(catalog) + [as_totem(s, g) for s in catalog if (g := totem_gem(s)) in totem_gems]
    for s in catalog:
        types = damage_types(s["types"])
        if s["name"] in seen or types & NOT_MAIN:
            continue
        is_minion = "Minion" in types
        if "Persistent" in types and not is_minion:
            continue
        if s.get("from_item"):
            continue   # granted by a unique item or a passive, not a gem (needs that item or node; not handled yet)
        if "Movement" in types and "Spell" in types:
            continue   # teleports like Lightning Warp: PoB scores them as if spammed
        if not (types & {"Attack", "Damage", "Spell"} or is_minion):
            continue
        if not want_damage <= types:
            continue
        if any(k not in types for k in want_kinds):
            continue
        if req.get("_totem_gem") and "SummonsTotem" in want_kinds and s.get("totem") != req["_totem_gem"]:
            continue   # "Spell Totem build": only skills that totem gem places
        if types & avoid:
            continue   # "no minions", "without chaos": never relaxed
        if ailment in AILMENT_DAMAGE and not types & AILMENT_DAMAGE[ailment]:
            continue
        if req.get("skill") and s["name"] != req["skill"]:
            continue
        if req.get("_attack_only") and "Attack" not in types:
            continue   # a weapon buff (e.g. Charged Staff) only helps attacks made with that weapon
        if req.get("_spell_only") and "Spell" not in types:
            continue   # a Cast on X gem triggers spells
        if not weapon_options(s, req):
            continue
        seen.add(s["name"])
        out.append(s)
    return out


def weapon_options(skill: dict, req: dict) -> list[tuple[str, str | None, str | None]]:
    """(main hand type, subtype, off hand type) the skill can be used with."""
    types = set(skill["types"])
    allowed = [w for w in skill["weapons"] if w != "None"]
    if "RequiresShield" in types:
        opts = SHIELD_WEAPONS
    elif allowed:
        opts = [(w, "Warstaff" if w == "Staff" and "Attack" in types else None, None) for w in allowed]
    elif "Minion" in types:
        opts = MINION_WEAPONS
    else:
        opts = SPELL_WEAPONS
    if "block" in (req.get("goals") or []):
        # Block comes from a shield: a block build holds a one-handed weapon and a shield. A skill that needs a
        # bow or a two-handed weapon can't, so it isn't a block build.
        opts = [(w, sub, "Shield") for w, sub, off in opts if w in ONE_HANDED]
    if req.get("weapons"):
        wanted = {w.lower() for w in req["weapons"]}
        opts = [o for o in opts if o[0].lower() in wanted]
    return opts[:3]


def _score(out: dict, req: dict) -> float:
    return _score_plain(out, req) * focus_factor(out, req.get("goals") or ())


def _score_plain(out: dict, req: dict) -> float:
    if req.get("ailment") in AILMENT_FIELD:
        return ailment_score(out, req["ailment"])   # the ailment counts fully, hits a quarter, share enforced
    mode = req.get("mode", "balanced")
    if mode == "mapping":
        return clear_score(out)
    if mode == "bossing":
        return total_dps(out)
    # Balanced (default): a build has to clear maps and kill bosses. The geometric mean
    # punishes a build that is great at one and poor at the other.
    return (max(clear_score(out), 0) * max(total_dps(out), 0)) ** 0.5


FIELDS = ["TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "BleedDPS",
          "PoisonDPS", "IgniteDPS", "MinionBleedDPS", "MinionPoisonDPS", "MinionIgniteDPS",
          "AreaOfEffectMod", "ProjectileCount", "TotalEHP", *FOCUS_FIELDS]


def evaluate(c: Candidate, stage: Stage, req: dict, tree: bool) -> Candidate:
    """Build one candidate quickly and score it."""
    p = _pob()
    quiet = lambda *a: None
    try:
        p.totem_for = {c.skill: c.totem} if c.totem else None
        p.new()
        p.set_class(c.cls, c.ascendancy)
        p.set_level(stage.level)
        group = p.add_skill([c.skill], full_dps=c.is_minion)["group"]
        seed_ailment(p, group, c.skill, req.get("ailment"))
        add_helpers(p, req, c.skill)
        mode = "mapping" if req.get("mode", "balanced") == "mapping" else "bossing"
        p.set_config(**MODE_CONFIG[mode])
        metric = metric_for(mode, req.get("ailment"), req.get("goals"))
        craft_gear(p, stage, c.weapon_type, c.weapon_subtype, offhand_type=c.offhand_type, uniques=False,
                   metric=metric, log=quiet)
        if tree:
            # Ranking only: the long reach stays (it changes which skills win), the slower swap phase runs
            # on the final build in guide.py.
            # Jewels count in the ranking too: sockets are worth their path plus the best jewel for this build.
            stand_in = proxy_jewel(p, stage, Scorer(def_weight=0.25, mode=mode, metric=metric))
            p.optimise_tree(def_weight=0.25, metric=metric, refine=False, jewel=stand_in)
        p.auto_config(mode)
        best = optimise_supports(p, group, c.skill, slots=5, top_k=10, metric=metric, log=quiet)[0]
        out = p.calc(FIELDS)
        if (bad := broken_numbers(out)):
            raise ValueError(f"impossible damage from Path of Building ({', '.join(bad)}), a calculation bug: skipped")
        c.supports, c.score, c.dps = best.supports, _score(out, req), total_dps(out)
        c.clear, c.ehp = clear_score(out), out.get("TotalEHP") or 0
        c.boss = score_of(out, metric_for("bossing", req.get("ailment")))
        # Theme check: an ailment build that gets most of its damage elsewhere is off brief.
        if req.get("ailment") in AILMENT_FIELD:
            share = ailment_dps(out, req["ailment"]) / max(total_dps(out), 1)
            if share < req.get("_min_share", THEME_MIN_SHARE):
                c.error = f"off theme: only {share:.0%} of damage is {req['ailment']}"
    except (PoBError, ValueError) as e:
        c.error = str(e)
    except Exception as e:  # noqa: BLE001 - one broken candidate must not end the whole search
        c.error = f"{type(e).__name__}: {e}"
    return c


def best_helper(p, catalog: list[dict], kind: str, metric: str, weapon_type: str | None, offhand_type: str | None = None,
                skip=()) -> str | None:
    """The skill of a helper kind ("warcry", "curse"...) that raises the build's metric most, tried one by one."""
    want = HELPER_TYPES.get(kind, kind)
    names = []
    for s in catalog:
        types = set(s["types"])
        if want not in types or s.get("from_item") or s["name"] in skip or s["name"] in names:
            continue
        if types & {"RequiresShield", "RequiresBuckler"} and offhand_type != "Shield":
            continue
        weapons = [w for w in s.get("weapons", []) if w != "None"]
        if weapons and weapon_type not in weapons:
            continue
        names.append(s["name"])
    if not names:
        return None
    p.use_full_dps()
    base = score_of(p.calc(FIELDS), metric)
    best, best_score = names[0], None
    for n in names:
        try:
            g = p.add_skill([n], main=False, full_dps=True)["group"]
            sc = score_of(p.calc(FIELDS), metric)
            p.remove_skill(g)
        except Exception:  # noqa: BLE001 - one skill that fails to load must not stop the pick
            continue
        if best_score is None or sc > best_score:
            best, best_score = n, sc
    return best if best_score is not None and best_score >= base * 0.98 else names[0]


def add_helpers(p, req: dict, main_skill: str, metas=None) -> None:
    """Put the player's helper skills in the build: a Cast on X gem with the main spell socketed in it, others alone."""
    metas = set(req.get("_metas") or []) if metas is None else set(metas)
    for h in req.get("with_skills") or []:
        p.add_skill([main_skill, h] if h in metas else [h], main=False)


def scout_ascendancies(f: Candidate, ascs: list[tuple[str, str]], stage: Stage, req: dict,
                       keep: int = DEEP_ASCS) -> list[tuple[str, str]]:
    """The `keep` ascendancies that suit one skill best. Gear is crafted once; each ascendancy then only
    spends its ascendancy points, so 23 of them take about as long as one full candidate."""
    p = _pob()
    quiet = lambda *a: None
    mode = "mapping" if req.get("mode", "balanced") == "mapping" else "bossing"
    metric = metric_for(mode, req.get("ailment"), req.get("goals"))
    try:
        p.totem_for = {f.skill: f.totem} if f.totem else None
        p.new()
        p.set_class(f.cls)
        p.set_level(stage.level)
        p.add_skill([f.skill, *f.supports], full_dps=f.is_minion)
        add_helpers(p, req, f.skill)
        p.set_config(**MODE_CONFIG[mode])
        craft_gear(p, stage, f.weapon_type, f.weapon_subtype, offhand_type=f.offhand_type, uniques=False,
                   metric=metric, log=quiet)
        xml = p.save_xml()
    except Exception:  # noqa: BLE001
        return ascs[:keep]
    scores = []
    for cls, asc in ascs:
        try:
            p.load_xml(xml)
            p.set_class(cls, asc)
            p.optimise_tree(points=0, def_weight=0.25, metric=metric, refine=False)
            p.auto_config(mode)
            scores.append((_score(p.calc(FIELDS), req), cls, asc))
        except Exception:  # noqa: BLE001 - skip an ascendancy that fails to build
            continue
    scores.sort(key=lambda t: -t[0])
    return [(c, a) for _, c, a in scores[:keep]] or ascs[:keep]


def _relax_steps(req: dict) -> list[tuple[str, dict]]:
    """Ways to loosen a request that found nothing, mildest first, each with a note for the player.
    They apply cumulatively: step 3 keeps the changes of steps 1 and 2."""
    steps = []
    ail = req.get("ailment")
    if ail in AILMENT_FIELD:
        steps.append((f"No build got most of its damage from {ail}, so builds where {ail} is a smaller part were allowed.",
                      {"_min_share": 0.0}))
    if ail:
        steps.append((f"No {ail} build worked with these choices, so {ail} isn't required.", {"ailment": None}))
    if req.get("weapons"):
        steps.append((f"Nothing worked with {' or '.join(req['weapons'])}, so any weapon was allowed.", {"weapons": []}))
    if req.get("damage"):
        steps.append((f"No {'/'.join(req['damage'])} skill worked with these choices, so any damage type was allowed.",
                      {"damage": []}))
    if req.get("kinds"):
        steps.append((f"No {'/'.join(req['kinds'])} skill worked with these choices, so any kind of skill was allowed.",
                      {"kinds": []}))
    if req.get("skill"):
        steps.append((f"{req['skill']} couldn't be built here, so the best skill was picked instead.", {"skill": None}))
    if req.get("ascendancy") or req.get("class"):
        who = req.get("ascendancy") or req.get("class")
        steps.append((f"Nothing worked on {who}, so every class was tried.", {"class": None, "ascendancy": None}))
    return steps


def generate(req: dict, workers: int = 4, top_skills: int = 4, log=print, progress=None) -> dict:
    """Best builds for a theme. Never comes back empty: when nothing fits, the request is loosened one step at
    a time (see _relax_steps) and result["relaxed"] lists what was changed, in the player's words.

    progress, if given, gets {"step": "round", ...} when a round starts, {"step": "candidate", ...} as each
    skill/weapon/ascendancy option is scored, and {"step": "relaxed", "label": note} when the request is loosened."""
    notes: list[str] = []
    # Every skill the player named is a requirement. A damage skill is the main skill; one that boosts others instead
    # (Cast on X, a buff like Charged Staff, a herald, an aura) is kept in every candidate beside it:
    #   - a Cast on X gem gets the main spell socketed into it, so the main skill must be a spell;
    #   - a weapon buff locks its weapon and pairs only with attacks made with it.
    helpers = list(req.get("with_skills") or [])
    if req.get("skill") or helpers:
        with PoB() as p:
            cat = {s["name"]: s for s in p.send("skill_catalog")["skills"]}
        if req.get("skill") and set(cat.get(req["skill"], {}).get("types", [])) & NOT_MAIN:
            helpers.insert(0, req["skill"])
            req = {**req, "skill": None}
        req = dict(req)
        # "Spell Totem build", "Ancestral Warrior Totem slam": a totem build where that gem places the main skill.
        for g in [h for h in helpers if h in TOTEM_GEMS]:
            helpers.remove(g)
            req["kinds"] = list(dict.fromkeys([*(req.get("kinds") or []), "totem"]))
            req["_totem_gem"] = g
        req["with_skills"] = helpers
        metas = [h for h in helpers if "Meta" in cat.get(h, {}).get("types", [])]
        for h in helpers:
            info = cat.get(h, {})
            if h in metas:
                continue
            if info.get("weapons"):
                if not req.get("weapons"):
                    req["weapons"] = list(info["weapons"])
                req["_attack_only"] = True
        if metas:
            req["_spell_only"] = True
        if helpers:
            req["with_skills"], req["_metas"] = helpers, metas
            for h in helpers:
                if h in metas:
                    notes.append(f"{h} is kept with the main spell socketed in it. How often it triggers isn't modelled "
                                 f"yet, so the damage shown is the spell cast normally.")
                else:
                    notes.append(f"{h} boosts other skills rather than dealing damage itself, so it's kept in the build "
                                 f"and the best skill to use with it was picked.")
    tried = dict(req)
    steps = _relax_steps(req)
    while True:
        try:
            result = _generate_once({k: v for k, v in tried.items() if v not in (None, [], "")} | {"budget": req.get("budget", "high")},
                                    workers, top_skills, log, progress)
        except ValueError as e:
            if not steps:
                raise ValueError(f"{e} Even a fully open search found nothing; please report this.") from e
            note, change = steps.pop(0)
            log(f"Relaxing: {note}")
            if progress:
                progress({"step": "relaxed", "label": note})
            tried.update(change)
            notes.append(note)
            continue
        result["request"] = req
        result["searched"] = {k: v for k, v in tried.items() if not k.startswith("_")}
        result["relaxed"] = notes
        return result


def _generate_once(req: dict, workers: int, top_skills: int, log, progress) -> dict:
    """One search, on one pool of `workers` threads (one PoB each) for all rounds; every PoB is closed after."""
    mine: list[PoB] = []
    try:
        with ThreadPoolExecutor(workers, initializer=_bind, initargs=(mine,)) as pool:
            return _search(req, pool, top_skills, log, progress)
    finally:
        _close_all(mine)


def _search(req: dict, pool: ThreadPoolExecutor, top_skills: int, log, progress) -> dict:
    t0 = time.time()

    def scored(c: Candidate, rnd: int) -> Candidate:
        if progress and not c.error and c.score > 0:
            progress({"step": "candidate", "round": rnd, "skill": c.skill, "weapon": c.weapon_type,
                      "ascendancy": c.ascendancy, "score": round(c.score, 1)})
        return c

    def round_start(rnd: float, label: str, count: int, text: str | None = None):
        log(label)
        if progress:
            ev = {"step": "round", "round": rnd, "label": label, "count": count}
            if text:
                ev["text"] = text   # what the page shows for this round
            progress(ev)
    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        classes = p.list_classes()
    skills = main_skills(catalog, req)
    if not skills:
        raise ValueError("No skills match that theme. Try fewer filters.")
    stage = make_stage("mid", req.get("budget", "high"))

    # Which ascendancies are allowed.
    if req.get("ascendancy"):
        ascs = [(c["name"], req["ascendancy"]) for c in classes if req["ascendancy"] in c["ascendancies"]]
    elif req.get("class"):
        ascs = [(c["name"], a) for c in classes if c["name"].lower() == req["class"].lower() for a in c["ascendancies"]]
    else:
        ascs = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    if not ascs:
        raise ValueError("Unknown class or ascendancy.")
    base_class = ascs[0][0] if len({c for c, _ in ascs}) == 1 else None

    # Round 1: skills x weapons, no passives, on the requested class (or a neutral default).
    round1 = []
    for s in skills:
        cls = base_class or DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else "Spell" if "Spell" in s["types"] else "", "Mercenary")
        for wtype, wsub, off in weapon_options(s, req):
            round1.append(Candidate(s["name"], wtype, wsub, off, cls, is_minion="Minion" in s["types"],
                                    totem=s.get("totem")))
    round_start(1, f"Round 1: {len(round1)} skill and weapon options", len(round1))
    round1 = list(pool.map(lambda c: scored(evaluate(c, stage, req, tree=False), 1), round1))
    ok1 = sorted((c for c in round1 if not c.error and c.score > 0), key=lambda c: -c.score)
    for c in ok1[:8]:
        log(f"  {c.skill:<26} {c.weapon_type:<14} {c.score:>12,.0f}")
    # One finalist per skill (its best weapon), so one skill can't crowd out the others.
    def one_per_skill(cands, n):
        out, seen = [], set()
        for c in cands:
            if c.skill not in seen:
                seen.add(c.skill)
                out.append(c)
            if len(out) >= n:
                break
        return out

    deep = bool(req.get("deep"))
    finalists = one_per_skill(ok1, DEEP_POOL if deep else top_skills)
    if not finalists:
        raise ValueError("None of the matching skills dealt damage. Try a different theme.")
    if deep and len(finalists) > DEEP_SKILLS:
        # Round 1b: some skills are ordinary on their own and strong with the right passives. Re-score the
        # wider pool with a passive tree before cutting it down.
        round_start(1.5, f"Round 1b: best {len(finalists)} skills again, with passives", len(finalists),
                    f"Deep search: the best {len(finalists)} skills again, now with passive trees, so skills that "
                    f"need passives to shine aren't cut early.")
        again = [Candidate(f.skill, f.weapon_type, f.weapon_subtype, f.offhand_type, f.cls, is_minion=f.is_minion,
                           totem=f.totem)
                 for f in finalists]
        again = list(pool.map(lambda c: scored(evaluate(c, stage, req, tree=True), 1.5), again))
        ok1b = sorted((c for c in again if not c.error and c.score > 0), key=lambda c: -c.score)
        finalists = one_per_skill(ok1b, DEEP_SKILLS) or finalists[:DEEP_SKILLS]

    def build_round(pairs):
        cands = [Candidate(f.skill, f.weapon_type, f.weapon_subtype, f.offhand_type, cls, asc, is_minion=f.is_minion,
                           totem=f.totem)
                 for f, (cls, asc) in pairs]
        return list(pool.map(lambda c: scored(evaluate(c, stage, req, tree=True), 2), cands))

    round2 = []
    if deep and len(ascs) > DEEP_ASCS:
        # Each skill gets its own best ascendancies, not the ones that suit the top skill.
        round_start(1.75, f"Round 2a: {len(finalists)} skills scouted on {len(ascs)} ascendancies",
                    len(finalists) * len(ascs),
                    f"Deep search: each of {len(finalists)} skills tried on all {len(ascs)} ascendancies to find "
                    f"the {DEEP_ASCS} that suit it best.")
        picks = list(pool.map(lambda f: scout_ascendancies(f, ascs, stage, req), finalists))
        pairs = [(f, a) for f, best in zip(finalists, picks) for a in best]
        round_start(2, f"Round 2: {len(pairs)} skill and ascendancy options", len(pairs),
                    f"Deep search: each skill on its own best ascendancies, with full passive trees. {len(pairs)} builds.")
        round2 += build_round(pairs)
        finalists_rest, pairs = [], []
    elif len(ascs) > 6:
        # Many ascendancies (no class chosen): find the best few with the top skill first.
        round_start(2, f"Round 2a: {finalists[0].skill} on {len(ascs)} ascendancies", len(ascs))
        scout = build_round([(finalists[0], a) for a in ascs])
        round2 += scout
        best_ascs = [(c.cls, c.ascendancy) for c in sorted((c for c in scout if not c.error), key=lambda c: -c.score)[:3]]
        ascs = best_ascs
        finalists_rest = finalists[1:]
    else:
        finalists_rest = finalists
    if not deep or len(ascs) <= DEEP_ASCS:
        pairs = [(f, a) for f in finalists_rest for a in ascs]
        round_start(2, f"Round 2: {len(pairs)} skill and ascendancy options", len(pairs))
        round2 += build_round(pairs)
    ranked = sorted((c for c in round2 if not c.error and c.score > 0), key=lambda c: -c.score)
    if not ranked:
        raise ValueError("Every candidate failed to build.")
    best = ranked[0]
    for c in ranked[:10]:
        log(f"  {c.ascendancy:<22} {c.skill:<24} {c.weapon_type:<10} {c.score:>12,.0f}  {c.score / best.score:6.0%}")
    log(f"Done in {time.time() - t0:.0f}s")
    return {
        "request": req,
        "best": asdict(best),
        "ranked": [asdict(c) | {"relative": c.score / best.score} for c in ranked],
        "skills_considered": [c.skill for c in ok1],
        "failed": [asdict(c) for c in round1 + round2 if c.error],
    }


BOSS_SKILL_MIN_GAIN = 1.25   # a separate boss skill must hit this much harder than the mapping skill
CLEAR_SKILL_MIN_GAIN = 1.25  # a separate clear skill must clear this much better than the main skill


def plan_build(result: dict, ascendancy: str | None = None, skill: str | None = None) -> dict:
    """Turn a generator result into a guide spec.

    With no locks this is the top-ranked build. Locking `ascendancy` and/or `skill` (the
    feedback option: "I love it, but I want the other ascendancy") picks the best build that
    matches, and reports how much damage that choice gives up versus the recommendation.

    If a different skill on the same ascendancy hits single targets clearly harder, it is added
    as a boss skill, on weapon set 2 when it needs a different weapon.
    """
    ranked = result["ranked"]
    rows = [r for r in ranked
            if (ascendancy is None or r["ascendancy"] == ascendancy) and (skill is None or r["skill"] == skill)]
    if not rows:
        raise ValueError("That combination was not part of the search. Run the generator with it locked.")
    main = rows[0]
    # The request as actually searched: if it had to be loosened (result["relaxed"]), the guide follows suit
    # rather than chasing, say, an ailment no candidate could deliver.
    req = result.get("searched") or result.get("request", {})
    spec = {
        "name": f"{main['skill']} {main['ascendancy']}",
        "class": main["cls"], "ascendancy": main["ascendancy"], "skill": main["skill"],
        "weapon_type": main["weapon_type"], "weapon_subtype": main["weapon_subtype"],
        "offhand_type": main["offhand_type"], "budget": req.get("budget", "high"),
    }
    for key in ("ailment", "damage", "kinds", "goals"):
        if req.get(key):
            spec[key] = req[key]   # carried into the guide: theme metric, theme checks, goals
    if req.get("with_skills"):
        spec["with_skills"] = list(req["with_skills"])   # skills the player asked for, kept beside the main skill
    if req.get("with_types"):
        spec["with_types"] = list(req["with_types"])     # "warcries": the guide picks the best one
    same_asc = [r for r in ranked if r["ascendancy"] == main["ascendancy"] and r["skill"] != main["skill"]]
    # Compare single-target strength in the theme's own terms (a bleed build wants a better
    # bleed boss skill, not just bigger hits). Older results without "boss" fall back to dps.
    key = lambda r: r.get("boss") or r["dps"]
    boss = max(same_asc, key=key, default=None)
    if boss and key(boss) >= BOSS_SKILL_MIN_GAIN * key(main):
        spec["boss_skill"] = boss["skill"]
        spec["boss_weapon_type"] = boss["weapon_type"]
        spec["boss_weapon_subtype"] = boss["weapon_subtype"]
    # A separate clear skill (Glacial Lance beside Whirlwind Lance): a skill on the same weapon that clears clearly
    # better than the main skill, which stays for bosses. Same weapon set, so it's a button away.
    clearers = [r for r in same_asc if r["weapon_type"] == main["weapon_type"]
                and r.get("offhand_type") == main.get("offhand_type") and r["skill"] != spec.get("boss_skill")]
    clear = max(clearers, key=lambda r: r.get("clear") or 0, default=None)
    if clear and (clear.get("clear") or 0) >= CLEAR_SKILL_MIN_GAIN * max(main.get("clear") or 0, 1):
        spec["clear_skill"] = clear["skill"]
    # Skills placed by a totem gem (Spell Totem + Fireball): the guide puts the gem in front of each.
    picked = {main["skill"]: main} | {r["skill"]: r for r in same_asc
                                      if r["skill"] in (spec.get("boss_skill"), spec.get("clear_skill"))}
    totems = {name: r["totem"] for name, r in picked.items() if r.get("totem")}
    if totems:
        spec["totems"] = totems
    best = ranked[0]
    cost = 1 - main["score"] / best["score"] if best["score"] else 0
    return {
        "spec": spec,
        "vs_recommended": cost,   # 0.12 = this choice deals 12% less than the recommended build
        "recommended": {"skill": best["skill"], "ascendancy": best["ascendancy"]},
        "note": None if cost <= 0 else (
            f"{main['ascendancy']} {main['skill']} does about {cost:.0%} less damage than the recommended "
            f"{best['ascendancy']} {best['skill']}."),
    }


def options(result: dict) -> dict:
    """Alternatives to offer after a build: each other ascendancy and skill, with its damage
    relative to the recommendation."""
    best = result["ranked"][0]["score"]
    asc, skills = {}, {}
    for r in result["ranked"]:
        asc.setdefault(r["ascendancy"], r)
        skills.setdefault(r["skill"], r)
    fmt = lambda r: {"skill": r["skill"], "ascendancy": r["ascendancy"], "weapon": r["weapon_type"],
                     "relative": r["score"] / best if best else 0}
    return {"ascendancies": [fmt(r) for r in asc.values()], "skills": [fmt(r) for r in skills.values()]}


if __name__ == "__main__":
    request = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"damage": ["lightning"], "kinds": ["minion"]}
    res = generate(request)
    print(json.dumps({"plan": plan_build(res), "options": options(res)}, indent=2))
