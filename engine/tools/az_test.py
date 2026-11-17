"""A-to-Z test: build many prompts end to end, all four stages, and check the result is what was asked for and that
every item and gem is real.

    python tools/az_test.py run [--only 1,5] [--out data/baseline/az_<PoB version>.json]
    python tools/az_test.py report <file.json>

Per prompt:
  asked for   the weapon, class, ascendancy, named skill, "with" skills, helper kinds (warcries...), damage type,
              skill kind (minion, spell...), ailment share, stat focuses, and anything the prompt said no to
  real        every gem, unique and base exists in Path of Building; every base is one players can find on trade;
              every rare passes the crafting rules (strict mode); PoB reads every item back with all its affixes
  usable      attributes met, gem levels fit the character level, no unique over its "Limited to"
  budget      every unique fits the budget picked (prices from poe.ninja)
Results are saved as they come in (resumable). Also writes the end-stage numbers in the same shape as
tools/baseline.py, so the run doubles as the pre-1.0 baseline. About 15 minutes a prompt.
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS.parent))
sys.path.insert(0, str(TOOLS))
os.environ.setdefault("STRICT_ITEMS", "1")

from check_prompt import catalog  # noqa: E402
from gear import _unique_allowed, base_available, make_stage  # noqa: E402
from generate import HELPER_TYPES, KIND_TYPES, generate, plan_build  # noqa: E402
from goals import FOCUS, focus_value  # noqa: E402
from guide import build_guide  # noqa: E402
from item_audit import audit_stage  # noqa: E402
from optimize import AILMENT_FIELD, AILMENT_TARGET, ailment_dps, damage_types, total_dps  # noqa: E402
from pob import PoB  # noqa: E402
from prompt import parse_prompt  # noqa: E402

STAGES = ["leveling", "early", "mid", "end"]

# (prompt, budget the player picked, extra expectations). The prompt's own budget words win over the picked one.
PROMPTS = [
    # The baseline set (tools/baseline.py)
    ("crossbow crit bleed build", "high", {}),
    ("lightning minion build", "medium", {}),
    ("dagger bleed build", "high", {}),
    ("cast on crit fire spells", "unlimited", {}),
    ("poison bow build", "budget", {}),
    ("tanky ignite build", "high", {}),
    ("cheap cold spell build", "budget", {}),
    ("two hand mace slam warrior", "free", {}),
    ("spear attack speed build", "high", {}),
    ("chaos damage over time witch", "medium", {}),
    ("warcry build", "high", {}),
    ("block energy shield build", "high", {}),
    ("lightning arrow with heralds", "medium", {}),
    ("starter minion build for a new player", "free", {}),
    ("highest dps build possible", "unlimited", {}),
    # Every class, more weapons, ascendancies, named skills, negations, goals
    ("fire spell build, no minions", "medium", {"not_kind": "minion"}),
    ("sorceress cold build", "high", {}),
    ("mercenary grenade build", "medium", {}),
    ("huntress spear build", "budget", {}),
    ("monk quarterstaff lightning build", "high", {}),
    ("ranger poison build", "medium", {}),
    ("invoker build", "high", {}),
    ("infernalist minions", "medium", {}),
    ("fast mapping build with movement speed", "medium", {}),
    ("magic find build", "medium", {}),
    ("life leech melee build", "high", {}),
    ("armour tank build two handed", "medium", {}),
    ("evasion crit bow build", "high", {}),
    ("curse build for a witch", "medium", {}),
    ("totem build", "medium", {}),
    ("ssf boss killer", "free", {}),
    ("10 div physical crossbow", "high", {}),
]


def load_game() -> dict:
    with PoB() as p:
        return {
            "gems": {g["name"] for g in p.list_gems()},
            "uniques": {u["name"] for u in p.list_uniques()},
            "bases": {b["name"] for b in p.send("bases")["bases"]},
            "skills": {s["name"]: s for s in p.send("skill_catalog")["skills"]},
            "version": p.version,
        }


def asked_for(req: dict, spec: dict, guides: list, game: dict, expect: dict, groups_end: list) -> list[str]:
    """What the prompt asked for that the build doesn't have."""
    fails = []
    end = guides[-1]
    s = end.stats
    if req.get("weapons") and spec["weapon_type"] not in req["weapons"] and spec.get("offhand_type") not in req["weapons"]:
        fails.append(f"weapon: asked {req['weapons']}, got {spec['weapon_type']}")
    if req.get("class") and spec["class"] != req["class"]:
        fails.append(f"class: asked {req['class']}, got {spec['class']}")
    if req.get("ascendancy") and spec["ascendancy"] != req["ascendancy"]:
        fails.append(f"ascendancy: asked {req['ascendancy']}, got {spec['ascendancy']}")
    if req.get("skill") and spec["skill"] != req["skill"]:
        fails.append(f"skill: asked {req['skill']}, got {spec['skill']}")
    gems_end = {g for grp in groups_end for g in grp["gems"]}
    for w in req.get("with_skills") or []:
        if w not in gems_end:
            fails.append(f"with: {w} isn't in the endgame skills")
    for kind in req.get("with_types") or []:
        t = HELPER_TYPES.get(kind)
        if t and not any(t in (game["skills"].get(g, {}).get("types") or []) for g in gems_end):
            fails.append(f"with: no {kind} in the endgame skills")
    main = game["skills"].get(spec["skill"], {})
    main_types = damage_types(main.get("types") or [])
    if spec["skill"] in (spec.get("totems") or {}):
        main_types.add("SummonsTotem")   # placed by Spell Totem / Ancestral Warrior Totem
    split = end.damage_split or {}
    total = sum(split.values()) or 1
    for d in req.get("damage") or []:
        share = split.get(d, 0) / total
        if d.capitalize() not in main_types and share < 0.3:
            fails.append(f"damage: asked {d}, {spec['skill']} isn't {d} and {d} is {share:.0%} of the damage")
    for k in req.get("kinds") or []:
        t = KIND_TYPES.get(k)
        if t and t not in main_types:
            fails.append(f"kind: asked {k}, {spec['skill']} isn't tagged {t}")
    if req.get("ailment") in AILMENT_FIELD:
        share = ailment_dps(s, req["ailment"]) / max(total_dps(s), 1)
        if share < AILMENT_TARGET:
            fails.append(f"ailment: {req['ailment']} is {share:.0%} of endgame damage (target {AILMENT_TARGET:.0%})")
    for k in req.get("goals") or []:
        if k in FOCUS and FOCUS[k][3] and focus_value(s, k) < FOCUS[k][3]:
            fails.append(f"focus: {FOCUS[k][2]} {focus_value(s, k):.1f}, minimum {FOCUS[k][3]}")
    nk = expect.get("not_kind")
    if nk and KIND_TYPES[nk] in main_types:
        fails.append(f"said no {nk}, got {spec['skill']}")
    if not total_dps(s):
        fails.append("no damage at endgame")
    return fails


def real_and_usable(pob: PoB, guides: list, game: dict, budget: str) -> list[str]:
    fails = []
    for g in guides:
        tag = g.stage
        for k, v in audit_stage(pob, g).items():   # real (strict), stats, readable, attributes, gems, uniques
            for x in v:
                fails.append(f"{tag} {k}: {x}")
        for p in list(g.gear) + list(g.jewels or []):
            if p.unique:
                if p.unique not in game["uniques"]:
                    fails.append(f"{tag} made-up unique: {p.unique}")
                ok, note = _unique_allowed(p.unique, make_stage(g.stage, budget))
                if not ok:
                    fails.append(f"{tag} over budget: {p.unique} ({note})")
            else:
                if p.base not in game["bases"]:
                    fails.append(f"{tag} made-up base: {p.base}")
                elif not base_available(p.base):
                    fails.append(f"{tag} base nobody can buy: {p.base}")
        pob.load_code(g.code)
        for grp in pob.send("groups")["groups"]:
            for gem in grp["gems"]:
                if gem and gem not in game["gems"]:   # "" is a skill the character gets for free (Thorns)
                    fails.append(f"{tag} made-up gem: {gem}")
    return fails


def run_one(text: str, budget: str, expect: dict, game: dict) -> dict:
    parsed = parse_prompt(text, catalog())
    req = {"budget": budget, **parsed["request"]}
    r = {"prompt": text, "budget": req["budget"], "read_as": [f["means"] for f in parsed["found"]],
         "unused": parsed["unused"]}
    t0 = time.time()
    try:
        result = generate(req, workers=int(os.environ.get("WORKERS", "3")), log=lambda *a: None)
        spec = {**plan_build(result)["spec"], "budget": req["budget"]}
        r.update(relaxed=result.get("relaxed") or [], skill=spec["skill"], ascendancy=spec["ascendancy"],
                 weapon=spec["weapon_type"])
        guides = build_guide(spec, STAGES, log=lambda *a: None)
    except AssertionError as e:
        return {**r, "fails": [f"ILLEGAL ITEM: {e}"], "seconds": round(time.time() - t0)}
    except Exception as e:  # noqa: BLE001
        return {**r, "fails": [f"build failed: {type(e).__name__}: {e}"], "trace": traceback.format_exc()[-1500:],
                "seconds": round(time.time() - t0)}
    with PoB() as pob:
        pob.load_code(guides[-1].code)
        groups_end = pob.send("groups")["groups"]
        fails = asked_for(req, spec, guides, game, expect, groups_end)
        if r["relaxed"]:
            fails.append(f"relaxed (the site says what changed): {r['relaxed']}")
        if r["unused"]:
            fails.append(f"words not understood: {r['unused']}")
        fails += real_and_usable(pob, guides, game, req["budget"])
    fails += build_checks(guides, time.time() - t0)
    end = guides[-1]
    s = end.stats
    r.update(
        fails=fails, seconds=round(time.time() - t0),
        stages={g.stage: {"dps": round(total_dps(g.stats)), "items": len(g.gear) + len(g.jewels or []),
                          "uniques": [p.unique for p in list(g.gear) + list(g.jewels or []) if p.unique]}
                for g in guides},
        setups=[f'{x.get("skill")} + {", ".join(x.get("supports") or [])}' for x in end.setups[:4]],
        main_supports=end.supports, total_dps=round(total_dps(s)), boss_dps=round(end.boss_dps or 0),
        skills=1 + len(end.setups) + len(end.triggers or []) + (1 if end.boss_skill else 0) + (1 if end.clear_skill else 0),
        boss_skill=end.boss_skill, weapon_sets=bool(end.weapon_sets),
        triggers=[f'{t.get("gem")}: {", ".join(t.get("spells") or [])}' for t in end.triggers or []],
        focus={k: {"value": round(focus_value(s, k), 1), "target": FOCUS[k][3]}
               for k in req.get("goals") or [] if k in FOCUS},
        off_theme=[n for n in end.notes if n.startswith("Off theme")],
    )
    if req.get("ailment") in AILMENT_FIELD:
        r["ailment"] = req["ailment"]
        r["ailment_share"] = round(ailment_dps(s, req["ailment"]) / max(total_dps(s), 1), 3)
    return r


SLOW_SECONDS = 1200   # a whole build (search + 4 stages) over 20 minutes is too slow for players


def build_checks(guides: list, seconds: float) -> list[str]:
    """The checks added with fuller builds (2026-11-17): every stage fits its spirit, the main skill fills the sockets
    its stage allows, the endgame build runs a full kit of skills, and the build doesn't take too long."""
    from guide import STAGE_SOCKETS
    out = []
    for g in guides:
        left = (g.stats or {}).get("SpiritUnreserved")
        if left is not None and left < 0:
            out.append(f"SPIRIT OVERDRAWN at {g.stage}: {left:.0f}")
        want = STAGE_SOCKETS.get(g.stage, 5)
        if len(g.supports) < want:
            out.append(f"main skill has {len(g.supports)} of {want} supports at {g.stage}")
    end = guides[-1]
    n = 1 + len(end.setups) + len(end.triggers or []) + (1 if end.boss_skill else 0) + (1 if end.clear_skill else 0)
    if n < 6:
        out.append(f"only {n} skills at endgame")
    if seconds > SLOW_SECONDS:
        out.append(f"slow: {seconds / 60:.0f} minutes")
    return out


def sweep_prompts() -> list:
    """One build per ascendancy ("Invoker build"), high budget: the same checks for every ascendancy."""
    return [(f"{asc} build", "high", {}) for c in catalog()["classes"] for asc in c["ascendancies"]]


def run(only: set[int] | None, out: Path | None) -> None:
    game = load_game()
    out = out or TOOLS.parent / "data" / "baseline" / f"az_{game['version']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    if done.get("pob_version") != game["version"]:
        done = {"pob_version": game["version"], "results": {}}
    prompts = sweep_prompts() if os.environ.get("SWEEP") else PROMPTS
    for i, (text, budget, expect) in enumerate(prompts, 1):
        key = f"{text} [{budget}]"
        if (only and i not in only) or key in done["results"]:
            continue
        print(f"#{i} {key} ...", flush=True)
        r = run_one(text, budget, expect, game)
        done["results"][key] = r
        done["updated"] = time.strftime("%Y-%m-%d %H:%M")
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"   {r.get('skill')} {r.get('ascendancy')} {r.get('weapon')}  {r.get('total_dps', 0):,} dps  "
              f"{r['seconds']}s  {'PASS' if not r['fails'] else f'{len(r['fails'])} issues'}", flush=True)
        for f in r["fails"]:
            print("     -", f, flush=True)
    write_baseline(done)
    report(done)


def write_baseline(done: dict) -> None:
    """The baseline-prompt subset in tools/baseline.py's format, for `baseline.py compare` after 1.0."""
    from baseline import PROMPTS as BASE
    keys = {f"{t} [{b}]" for t, b in BASE}
    res = {k: v for k, v in done["results"].items() if k in keys and "skill" in v}
    if res:
        path = TOOLS.parent / "data" / "baseline" / f"prompts_{done['pob_version']}.json"
        path.write_text(json.dumps({"pob_version": done["pob_version"], "results": res}, indent=1,
                                   ensure_ascii=False), encoding="utf-8")


def report(done: dict) -> None:
    res = done["results"]
    passed = [k for k, r in res.items() if not r["fails"]]
    print(f"\n{len(passed)} of {len(res)} prompts pass every check (PoB {done['pob_version']})")
    kinds: dict[str, int] = {}
    for r in res.values():
        for f in r["fails"]:
            k = re.sub(r"^(leveling|early|mid|end) ", "", f).split(":")[0]
            kinds[k] = kinds.get(k, 0) + 1
    for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {k}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        only = set(int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
        run(only, out)
    elif len(sys.argv) == 3 and sys.argv[1] == "report":
        report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    else:
        print(__doc__)
