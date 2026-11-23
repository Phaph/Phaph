"""Leveling skills for the campaign stages (NIGHT_TASKS 36b, Kyle 2026-11-22).

Builds are chosen for endgame; the campaign stages (Act 1, Act 2, Acts 3-4, Interludes) may level with another
skill, under Kyle's rules: "keep the builds close to the end result they asked for and not have them swapping
spells every act", and "as you level up and unlock better skills of course you should swap to the better new one if
it makes sense", "maybe 3 max? or 4?".

  - Candidates: same kind as the endgame skill (spell / attack / minion), usable with the build's weapon, sharing a
    damage type with it (a lightning monk levels with lightning), unlocked by the stage's character level.
  - Each campaign stage scores its candidates with a quick clear build (generate.evaluate, mapping, no tree).
  - The endgame skill is used from the first stage where it's unlocked and within ENDGAME_WITHIN of the best.
  - Otherwise keep the current skill unless a newly unlocked one is SWAP_GAIN better; never go back to an earlier
    one; at most MAX_SKILLS skills across the campaign, the endgame skill included.

plan_leveling(spec) -> {"act1": "Spark", "act2": "Spark", "act34": "Arc", "interludes": "Arc"} (stages that use the
endgame skill are left out), with the reasons in "_why".
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

CAMPAIGN = ["act1", "act2", "act34", "interludes"]
MAX_SKILLS = 3          # across the campaign, the endgame skill included (4 if guides for the archetype do: check)
SWAP_GAIN = 1.30        # a newly unlocked skill must clear ~30% faster to be worth a swap
ENDGAME_WITHIN = 0.80   # the endgame skill takes over once it's within 20% of the best option
KINDS = ("Minion", "Spell", "Attack")
SHORTLIST = 5           # candidates kept after the mid-campaign screen (plus the endgame skill)


def kind_of(types) -> str | None:
    t = set(types)
    return next((k for k in KINDS if k in t), None)


def candidates(catalog: list[dict], spec: dict) -> list[dict]:
    """Skills a player could level with, close to the endgame skill."""
    from generate import main_skills, weapon_options
    from optimize import damage_types
    skills = {s["name"]: s for s in main_skills(catalog, {})}
    main = skills.get(spec["skill"])
    if not main:
        return []
    # damage_types() returns all of a skill's tags; keep the damage types only (2026-11-23: "Spell" in common let a
    # physical Bonestorm level a fire Firestorm build)
    elements = {"Physical", "Fire", "Cold", "Lightning", "Chaos"}
    kind, dmg = kind_of(main["types"]), damage_types(main["types"]) & elements
    want_weapon = (spec.get("weapon_type"), spec.get("weapon_subtype"))
    out = []
    for s in skills.values():
        if kind_of(s["types"]) != kind or s.get("from_item"):
            continue
        if s["name"] != main["name"] and not (damage_types(s["types"]) & elements & dmg):
            continue
        opts = weapon_options(s, {})
        if opts and not any((w, ws) == want_weapon or (w, None) == (want_weapon[0], None) for w, ws, _ in opts):
            continue
        out.append(s)
    return out


def choose(scores: dict[str, dict[str, float]], endgame: str, stages: list[str] = CAMPAIGN) -> tuple[dict, list[str]]:
    """The leveling plan from per-stage scores ({stage: {skill: score}}, only unlocked skills present)."""
    plan, why, used, cur = {}, [], [], None
    for st in stages:
        sc = scores.get(st) or {}
        if not sc:
            continue
        best = max(sc, key=sc.get)
        if endgame in sc and sc[endgame] >= ENDGAME_WITHIN * sc[best]:
            pick = endgame
            if cur != endgame:
                why.append(f"{st}: {endgame} from here on (within {1 - sc[endgame] / sc[best]:.0%} of the best option)"
                           if best != endgame else f"{st}: {endgame} from here on")
        elif cur and cur in sc and sc[best] < SWAP_GAIN * sc[cur]:
            pick = cur
        elif cur and best not in used and len(set(used) | {best, endgame}) > MAX_SKILLS:
            pick = cur   # no more swaps: the cap is reached
        elif best in used and best != cur:
            pick = cur or best   # never go back to an earlier skill
        else:
            pick = best
            if pick != cur:
                why.append(f"{st}: level with {pick}" + (f" ({sc[pick] / sc[cur] - 1:.0%} faster than {cur})" if cur else ""))
        if pick not in used:
            used.append(pick)
        cur = pick
        if pick != endgame:
            plan[st] = pick
        if pick == endgame:
            break   # once on the endgame skill, stay on it
    return plan, why


def plan_leveling(spec: dict, catalog: list[dict] | None = None, workers: int = 4, log=lambda *a: None) -> dict:
    from gear import make_stage
    from generate import Candidate, evaluate
    from pob import PoB
    if catalog is None:
        with PoB() as p:
            catalog = p.send("skill_catalog")["skills"]
    cands = candidates(catalog, spec)
    if not cands:
        return {}
    req = {"mode": "mapping"}

    # Screen once at mid-campaign, keep the best SHORTLIST (+ the endgame skill) for the per-stage scoring: scoring
    # every candidate at every stage took 30-55 min on one core (2026-11-22).
    mid = make_stage("act34")
    screen = [(None, mid, s) for s in cands]

    def one(job):
        st, stage, s = job
        c = Candidate(s["name"], spec["weapon_type"], spec.get("weapon_subtype"), spec.get("offhand_type"),
                      spec["class"], spec.get("ascendancy"), is_minion="Minion" in s["types"])
        c = evaluate(c, stage, req, tree=False)
        return st, s["name"], (0.0 if c.error else c.score)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        first = list(ex.map(one, screen))
    keep = {n for _, n, sc in sorted(first, key=lambda x: -x[2])[:SHORTLIST] if sc > 0} | {spec["skill"]}
    short = [s for s in cands if s["name"] in keep]
    jobs = []
    for st in CAMPAIGN:
        stage = make_stage(st)
        for s in short:
            if (s.get("unlock") or 0) <= stage.level and st != "act34":
                jobs.append((st, stage, s))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(one, jobs))
    res += [("act34", n, sc) for _, n, sc in first if n in keep
            and next((s.get("unlock") or 0) for s in short if s["name"] == n) <= mid.level]
    scores: dict[str, dict[str, float]] = {}
    for st, name, sc in res:
        if sc > 0:
            scores.setdefault(st, {})[name] = sc
    plan, why = choose(scores, spec["skill"])
    log("; ".join(why))
    return {**plan, "_why": why}
