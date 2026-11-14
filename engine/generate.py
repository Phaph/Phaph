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
from optimize import MODE_CONFIG, clear_score, metric_for, optimise_supports, total_dps
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
    mode = req.get("mode", "balanced")
    if mode == "mapping":
        return clear_score(out)
    if mode == "bossing":
        return total_dps(out)
    # Balanced (default): a build has to clear maps and kill bosses. The geometric mean
    # punishes a build that is great at one and poor at the other.
    return (max(clear_score(out), 0) * max(total_dps(out), 0)) ** 0.5


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
        mode = "mapping" if req.get("mode", "balanced") == "mapping" else "bossing"
        p.set_config(**MODE_CONFIG[mode])
        metric = metric_for(mode, req.get("ailment"))
        craft_gear(p, stage, c.weapon_type, c.weapon_subtype, offhand_type=c.offhand_type, uniques=False,
                   metric=metric, log=quiet)
        if tree:
            p.optimise_tree(def_weight=0.25, metric=metric)
        p.auto_config(mode)
        best = optimise_supports(p, group, c.skill, slots=5, top_k=10, metric=metric, log=quiet)[0]
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
    # One finalist per skill (its best weapon), so one skill can't crowd out the others.
    finalists, seen_skills = [], set()
    for c in ok1:
        if c.skill not in seen_skills:
            seen_skills.add(c.skill)
            finalists.append(c)
        if len(finalists) >= top_skills:
            break
    if not finalists:
        raise ValueError("None of the matching skills dealt damage. Try a different theme.")

    def build_round(pairs):
        cands = [Candidate(f.skill, f.weapon_type, f.weapon_subtype, f.offhand_type, cls, asc, is_minion=f.is_minion)
                 for f, (cls, asc) in pairs]
        with ThreadPoolExecutor(workers) as ex:
            return list(ex.map(lambda c: evaluate(c, stage, req, tree=True), cands))

    round2 = []
    if len(ascs) > 6:
        # Many ascendancies (no class chosen): find the best few with the top skill first.
        log(f"Round 2a: {finalists[0].skill} on {len(ascs)} ascendancies")
        scout = build_round([(finalists[0], a) for a in ascs])
        round2 += scout
        best_ascs = [(c.cls, c.ascendancy) for c in sorted((c for c in scout if not c.error), key=lambda c: -c.score)[:3]]
        ascs = best_ascs
        finalists_rest = finalists[1:]
    else:
        finalists_rest = finalists
    pairs = [(f, a) for f in finalists_rest for a in ascs]
    log(f"Round 2: {len(pairs)} skill and ascendancy options")
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
    req = result.get("request", {})
    spec = {
        "name": f"{main['skill']} {main['ascendancy']}",
        "class": main["cls"], "ascendancy": main["ascendancy"], "skill": main["skill"],
        "weapon_type": main["weapon_type"], "weapon_subtype": main["weapon_subtype"],
        "offhand_type": main["offhand_type"], "budget": req.get("budget", "high"),
    }
    if req.get("ailment"):
        spec["ailment"] = req["ailment"]
    same_asc = [r for r in ranked if r["ascendancy"] == main["ascendancy"] and r["skill"] != main["skill"]]
    boss = max(same_asc, key=lambda r: r["dps"], default=None)
    if boss and boss["dps"] >= BOSS_SKILL_MIN_GAIN * main["dps"]:
        spec["boss_skill"] = boss["skill"]
        spec["boss_weapon_type"] = boss["weapon_type"]
        spec["boss_weapon_subtype"] = boss["weapon_subtype"]
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
