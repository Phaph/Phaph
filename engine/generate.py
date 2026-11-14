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
     "class": "Monk", "ascendancy": null, "skill": null, "budget": "high", "mode": "bossing"}
Everything is optional; locked fields (class, ascendancy, skill, weapons) narrow the search.

CLI:  python3 generate.py '{"damage":["lightning"],"kinds":["minion"]}'
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from gear import Stage, craft_gear, make_stage
from optimize import MODE_CONFIG, clear_score, optimise_supports, total_dps
from pob import PoB, PoBError

# Types that make a skill a support act rather than a main damage skill.
NOT_MAIN = {"Buff", "Aura", "Herald", "Meta", "Triggered", "InbuiltTrigger", "OngoingSkill", "Shapeshift",
            "AppliesCurse", "ActiveBlock"}
KIND_TYPES = {
    "minion": "Minion", "spell": "Spell", "attack": "Attack", "melee": "Melee", "projectile": "Projectile",
    "totem": "Totemable", "trap": "Trappable", "slam": "Slam", "strike": "MeleeSingleTarget", "area": "Area",
    "channel": "Channel", "chaining": "Chains", "grenade": "Grenade", "ammo": "CrossbowAmmoSkill",
}
AILMENT_DAMAGE = {"bleed": {"Physical"}, "poison": {"Physical", "Chaos"}, "ignite": {"Fire"},
                  "shock": {"Lightning"}, "chill": {"Cold"}, "freeze": {"Cold"}}
AILMENT_FIELD = {"bleed": "BleedDPS", "poison": "PoisonDPS", "ignite": "IgniteDPS"}
SPELL_WEAPONS = [("Wand", None, None), ("Staff", "none", None)]
MINION_WEAPONS = [("Sceptre", None, None), ("Wand", None, None)]
SHIELD_WEAPONS = [("One Hand Mace", None, "Shield"), ("Spear", None, "Shield")]
DEFAULT_CLASS = {"Minion": "Witch", "Spell": "Sorceress"}


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
    ehp: float = 0.0
    supports: list[str] = field(default_factory=list)
    is_minion: bool = False
    error: str | None = None

    def spec(self) -> dict:
        return {"class": self.cls, "ascendancy": self.ascendancy, "skill": self.skill,
                "weapon_type": self.weapon_type, "weapon_subtype": self.weapon_subtype,
                "offhand_type": self.offhand_type}


_local = threading.local()


def _pob() -> PoB:
    if getattr(_local, "pob", None) is None:
        _local.pob = PoB()
    return _local.pob


def main_skills(catalog: list[dict], req: dict) -> list[dict]:
    """Skills that can carry a build and fit the theme."""
    want_damage = {d.capitalize() for d in req.get("damage") or []}
    want_kinds = [KIND_TYPES.get(k.lower(), k) for k in req.get("kinds") or []]
    ailment = (req.get("ailment") or "").lower() or None
    seen, out = set(), []
    for s in catalog:
        types = set(s["types"])
        if s["name"] in seen or types & NOT_MAIN:
            continue
        is_minion = "Minion" in types
        if "Persistent" in types and not is_minion:
            continue
        if s.get("from_item"):
            continue   # granted by a unique item, not a gem (needs that item; not handled yet)
        if "Movement" in types and "Spell" in types:
            continue   # teleports like Lightning Warp: PoB scores them as if spammed
        if not (types & {"Attack", "Damage", "Spell"} or is_minion):
            continue
        if not want_damage <= types:
            continue
        if any(k not in types for k in want_kinds):
            continue
        if ailment in AILMENT_DAMAGE and not types & AILMENT_DAMAGE[ailment]:
            continue
        if req.get("skill") and s["name"] != req["skill"]:
            continue
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
    if req.get("weapons"):
        wanted = {w.lower() for w in req["weapons"]}
        opts = [o for o in opts if o[0].lower() in wanted]
    return opts[:3]


def _score(out: dict, req: dict) -> float:
    if req.get("ailment") in AILMENT_FIELD:
        # An ailment build lives on its ailment: count it fully, hits a quarter.
        return out.get(AILMENT_FIELD[req["ailment"]], 0) + 0.25 * out.get("TotalDPS", 0)
    if req.get("mode") == "mapping":
        return clear_score(out)
    return total_dps(out)


FIELDS = ["TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "BleedDPS",
          "PoisonDPS", "IgniteDPS", "AreaOfEffectMod", "ProjectileCount", "TotalEHP"]


def evaluate(c: Candidate, stage: Stage, req: dict, tree: bool) -> Candidate:
    """Build one candidate quickly and score it."""
    p = _pob()
    quiet = lambda *a: None
    try:
        p.new()
        p.set_class(c.cls, c.ascendancy)
        p.set_level(stage.level)
        group = p.add_skill([c.skill], full_dps=c.is_minion)["group"]
        p.set_config(**MODE_CONFIG[req.get("mode", "bossing")])
        craft_gear(p, stage, c.weapon_type, c.weapon_subtype, offhand_type=c.offhand_type, uniques=False, log=quiet)
        if tree:
            p.optimise_tree(def_weight=0.25, metric="mapping" if req.get("mode") == "mapping" else "total")
        p.auto_config(req.get("mode", "bossing"))
        best = optimise_supports(p, group, c.skill, slots=5, top_k=10, log=quiet)[0]
        out = p.calc(FIELDS)
        c.supports, c.score, c.dps = best.supports, _score(out, req), total_dps(out)
        c.clear, c.ehp = clear_score(out), out.get("TotalEHP", 0)
    except (PoBError, ValueError) as e:
        c.error = str(e)
    return c


def generate(req: dict, workers: int = 4, top_skills: int = 4, log=print) -> dict:
    t0 = time.time()
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
            round1.append(Candidate(s["name"], wtype, wsub, off, cls, is_minion="Minion" in s["types"]))
    log(f"Round 1: {len(round1)} skill and weapon options")
    with ThreadPoolExecutor(workers) as ex:
        round1 = list(ex.map(lambda c: evaluate(c, stage, req, tree=False), round1))
    ok1 = sorted((c for c in round1 if not c.error and c.score > 0), key=lambda c: -c.score)
    for c in ok1[:8]:
        log(f"  {c.skill:<26} {c.weapon_type:<14} {c.score:>12,.0f}")
    finalists = ok1[:top_skills]
    if not finalists:
        raise ValueError("None of the matching skills dealt damage. Try a different theme.")

    # Round 2: finalists x ascendancies, with passives.
    round2 = [Candidate(f.skill, f.weapon_type, f.weapon_subtype, f.offhand_type, cls, asc, is_minion=f.is_minion)
              for f in finalists for cls, asc in ascs]
    log(f"Round 2: {len(round2)} skill and ascendancy options")
    with ThreadPoolExecutor(workers) as ex:
        round2 = list(ex.map(lambda c: evaluate(c, stage, req, tree=True), round2))
    ranked = sorted((c for c in round2 if not c.error and c.score > 0), key=lambda c: -c.score)
    if not ranked:
        raise ValueError("Every candidate failed to build.")
    best = ranked[0]
    for c in ranked[:10]:
        log(f"  {c.ascendancy:<22} {c.skill:<24} {c.score:>12,.0f}  {c.score / best.score:6.0%}")
    log(f"Done in {time.time() - t0:.0f}s")
    return {
        "best": asdict(best),
        "ranked": [asdict(c) | {"relative": c.score / best.score} for c in ranked],
        "skills_considered": [c.skill for c in ok1],
        "failed": [asdict(c) for c in round1 + round2 if c.error],
    }


def alternatives(result: dict, ascendancy: str | None = None, skill: str | None = None) -> list[dict]:
    """What a player gives up by locking a choice: the best ranked build that matches it."""
    rows = [r for r in result["ranked"]
            if (ascendancy is None or r["ascendancy"] == ascendancy) and (skill is None or r["skill"] == skill)]
    return rows


if __name__ == "__main__":
    request = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"damage": ["lightning"], "kinds": ["minion"]}
    res = generate(request)
    print(json.dumps(res["best"], indent=2))
