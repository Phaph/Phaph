"""Full build guide: one build spec -> Leveling, Early maps, Mid maps and Endgame versions.

Each stage gets its own level, passive points, gear budget, support gems and passives:
    supports (bare) -> gear -> passive tree -> supports again
Stages run side by side, one PoB process each.

Spec:
    {"name": "Tempest Flurry Invoker", "class": "Monk", "ascendancy": "Invoker",
     "skill": "Tempest Flurry", "weapon_type": "Staff", "weapon_subtype": "Warstaff",
     "dual_wield": false, "budget": "budget", "stages": ["leveling", "early", "mid", "end"]}

budget: free | budget (<=5 div) | medium (5-30) | high (30-100) | unlimited. Default: high.
Every stage's gear is capped at the budget, so a 5 divine player still gets mid maps
and endgame versions, built with gear they can afford.

CLI:  python3 guide.py spec.json [--budget budget] [--stages early,end] [--json]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from gear import BUDGET_ORDER, STAGE_DEFS, SlotPlan, add_trade_info, craft_gear, craft_weapon, make_stage
from optimize import CLEAR_FIELDS, MINION_AILMENT_FIELDS, MODE_CONFIG, clear_score, metric_for, optimise_supports, total_dps
from goals import GOAL_FIELDS, GOAL_LABELS, mobility_skills
from pob import PoB
from rating import rate
from spirit import optimise_spirit
from themes import check as theme_check
from utility import optimise_utility

STAT_FIELDS = ["TotalDPS", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "Spirit",
               "SpiritUnreserved", "Speed", "CritChance", "HitChance", "Life", "EnergyShield", "Mana",
               "Armour", "Evasion", "TotalEHP", "FireResist", "ColdResist", "LightningResist", "ChaosResist"]
DAMAGE_TYPES = ["Physical", "Fire", "Cold", "Lightning", "Chaos"]
# Per-type hit size and skill DoT, so the website can colour damage by what it is.
SPLIT_FIELDS = [f"{t}HitAverage" for t in DAMAGE_TYPES] + [f"{t}Dot" for t in DAMAGE_TYPES]
AILMENT_TYPE = {"BleedDPS": "physical", "IgniteDPS": "fire", "PoisonDPS": "chaos"}


def damage_split(stats: dict) -> dict[str, float]:
    """Damage per second by type: hits split by each type's share of the average hit, skill DoT by
    type, ailments by their element, and minions as one block (PoB doesn't split their damage)."""
    out = {t.lower(): 0.0 for t in DAMAGE_TYPES}
    hit = stats.get("TotalDPS", 0) or 0
    avgs = {t: max(stats.get(f"{t}HitAverage", 0) or 0, 0) for t in DAMAGE_TYPES}
    total_avg = sum(avgs.values())
    if hit > 0 and total_avg > 0:
        for t, a in avgs.items():
            out[t.lower()] += hit * a / total_avg
    for t in DAMAGE_TYPES:
        out[t.lower()] += max(stats.get(f"{t}Dot", 0) or 0, 0)
    for field_name, t in AILMENT_TYPE.items():
        out[t] += max(stats.get(field_name, 0) or 0, 0)
    minion = (stats.get("MinionDPS", 0) or 0) + (stats.get("MinionDotDPS", 0) or 0)
    if minion > 0:
        out["minion"] = minion
    return {k: round(v, 1) for k, v in out.items() if v > 0}


@dataclass
class StageGuide:
    stage: str
    name: str
    level: int
    budget: str
    supports: list[str]
    notables: list[str]
    gear: list[SlotPlan]
    stats: dict
    dps: float
    code: str
    boss_supports: list[str] = field(default_factory=list)
    boss_dps: float = 0.0   # single target vs a pinnacle boss, with the boss setup
    boss_skill: str | None = None      # a second skill used for bosses, if the build has one
    boss_weapon_set: int = 1           # 2 when the boss skill is on the weapon swap
    spirit: list[str] = field(default_factory=list)       # auras, heralds, buffs, extra minions
    conditions: list[dict] = field(default_factory=list)  # bonuses assumed up, and why
    notes: list[str] = field(default_factory=list)
    ailment: str | None = None   # the build's theme ailment, e.g. "bleed"
    goals: list[str] = field(default_factory=list)          # movement / rarity / tanky
    mobility: list[str] = field(default_factory=list)       # recommended movement skills
    theme_issues: list[str] = field(default_factory=list)   # empty when the build matches the request
    clear: float = 0.0                                      # mapping clear score
    rating: dict | None = None                              # 1-10, endgame stage only
    utility: list[dict] = field(default_factory=list)       # curses, marks, banners, warcries kept
    # Supports for every other skill in the build: [{"skill", "role": spirit/utility/movement, "supports"}]
    setups: list[dict] = field(default_factory=list)
    damage_split: dict = field(default_factory=dict)        # dps by type: physical, fire, ..., minion
    budget_key: str = "high"                                 # free / budget / medium / high / unlimited
    tree_nodes: list[int] = field(default_factory=list)      # allocated passive ids, for the tree viewer
    # The order to take passives: each pick (most value per point first) with the path that reaches it.
    tree_order: list[dict] = field(default_factory=list)
    tree_version: str | None = None


DEFAULT_BUDGET = "high"


def condition_label(var: str) -> str:
    """conditionEnemyBleeding -> 'enemy bleeding', usePowerCharges -> 'power charges'."""
    import re
    name = re.sub(r"^(condition|use)", "", var)
    return re.sub(r"(?<!^)([A-Z])", r" \1", name).lower()


def build_stage(spec: dict, stage_key: str, log=lambda *a: None, progress=None) -> StageGuide:
    """One stage of a guide. Gear and passives are built for mapping (where players spend most
    of their time); then a bossing setup is picked: a support swap, or a separate boss skill
    (on weapon set 2 when it needs a different weapon).

    Order: conditions -> gear -> passives -> supports -> spirit -> gear again -> final supports.
    Conditions (auto_config) are re-checked whenever the build changes enough to affect them.

    progress, if given, receives one dict per real step ({"stage", "step", "label", "dps"}) so the
    website can show the work as it happens.
    """
    stage = make_stage(stage_key, spec.get("budget", DEFAULT_BUDGET))
    weapon = dict(weapon_type=spec["weapon_type"], weapon_subtype=spec.get("weapon_subtype"),
                  dual_wield=spec.get("dual_wield", False), offhand_type=spec.get("offhand_type"))
    dw_gear, dw_tree = spec.get("defence_weight", 0.4), spec.get("defence_weight", 0.25)
    boss_skill = spec.get("boss_skill") if stage_key != "leveling" else None
    boss_swap = bool(boss_skill and spec.get("boss_weapon_type")
                     and (spec.get("boss_weapon_type"), spec.get("boss_weapon_subtype"))
                     != (spec["weapon_type"], spec.get("weapon_subtype")))
    quiet = lambda *a: None
    slots = spec.get("support_slots", 5)
    # The build's goal: e.g. a bleed build optimises bleed damage everywhere, not raw hits.
    map_metric = metric_for("mapping", spec.get("ailment"))
    boss_metric = metric_for("bossing", spec.get("ailment"))
    goals = list(spec.get("goals") or [])
    with PoB() as pob:
        catalog = pob.send("skill_catalog")["skills"]
        minion_build = any(s["name"] == spec["skill"] and "Minion" in s["types"] for s in catalog)
        pob.new()
        pob.set_class(spec["class"], spec.get("ascendancy"))
        pob.set_level(stage.level)
        skill = spec["skill"]
        group = pob.add_skill([skill], full_dps=minion_build)["group"]
        boss_group = None
        if boss_skill:
            boss_group = pob.add_skill([boss_skill], main=False, full_dps=True)["group"]
            pob.use_full_dps()
            if boss_swap:
                pob.send("set_weapon_set", group=boss_group, set=2)
        shortlist: dict = {}

        def report(step: str, label: str = "", **extra):
            if progress:
                progress({"stage": stage_key, "step": step, "label": label,
                          "dps": round(total_dps(pob.calc(STAT_FIELDS)), 1), **extra})

        report("start", f"{stage.name}: level {stage.level}, {stage.budget}")

        def boss_weapon():
            # The swap weapon is scored with the boss skill as the main skill.
            pob.send("set_main", group=boss_group)
            plan = craft_weapon(pob, stage, "Weapon 1 Swap", spec["boss_weapon_type"],
                                spec.get("boss_weapon_subtype"), mode="bossing", metric=boss_metric, log=quiet)
            pob.send("set_main", group=group)
            return plan

        pob.set_config(**MODE_CONFIG["mapping"])
        pob.auto_config("mapping")
        craft_gear(pob, stage, **weapon, def_weight=dw_gear, mode="mapping", metric=map_metric, goals=goals, log=quiet)
        if boss_swap:
            boss_weapon()
        report("gear", "First gear pass")
        def tree_live(ev):
            if progress:
                progress({"stage": stage_key, "step": "tree_live", "chosen": ev.get("chosen"), "name": ev.get("name"),
                          "type": ev.get("type"), "path": ev.get("path") or [], "considered": ev.get("considered") or [],
                          "scanned": ev.get("scanned", 0), "evals": ev.get("evals", 0),
                          "ascendancy": bool(ev.get("ascendancy")), "score": round(ev.get("score") or 0, 1)})

        tree = pob.optimise_tree(def_weight=dw_tree, metric=map_metric, goals=goals,
                                 on_step=tree_live if progress else None)
        if progress:
            for s in tree["steps"]:
                if s["type"] != "Normal":
                    progress({"stage": stage_key, "step": "passive", "label": s["node"],
                              "ascendancy": bool(s.get("ascendancy")), "gain": round(s.get("gain_per_point", 0), 4)})
        report("tree", f"{sum(s['cost'] for s in tree['steps'])} passive points spent")
        pob.auto_config("mapping")
        first = optimise_supports(pob, group, skill, slots=slots, metric=map_metric, log=quiet, shortlist=shortlist)
        report("supports", ", ".join(first[0].supports) if first else "")
        spirit = optimise_spirit(pob, catalog, mode="mapping", minion_build=minion_build, metric=map_metric, log=quiet)
        if spirit:
            report("spirit", ", ".join(spirit))
        # Curses, marks, banners, warcries: kept when they raise the main skill's damage. One
        # that needs a weapon the main hand can't use goes on weapon set 2.
        utility = []
        if stage_key != "leveling":
            pob.set_config(**MODE_CONFIG["bossing"])
            utility = optimise_utility(pob, catalog, spec["weapon_type"], boss_metric, item_level=stage.item_level,
                                       swap_weapon=spec.get("boss_weapon_type") if boss_swap else None, log=quiet)
            pob.set_config(**MODE_CONFIG["mapping"])
        # Passives, supports and spirit moved damage and resistances around: re-craft gear to fit.
        gear = craft_gear(pob, stage, **weapon, def_weight=dw_gear, mode="mapping", metric=map_metric, goals=goals, log=quiet)
        if boss_swap:
            gear.append(boss_weapon())
        add_trade_info(pob, gear)
        report("gear", "Gear re-crafted to fit", slots=[g.unique.split(",")[0] if g.unique else g.base for g in gear])

        # Bossing setup: a separate boss skill if the build has one, else a support swap.
        pob.set_config(**MODE_CONFIG["bossing"])
        boss, boss_dps = None, 0.0
        if stage_key != "leveling":
            # boss_dps is real single-target damage (not the theme score used to pick supports).
            if boss_group:
                pob.send("set_main", group=boss_group)
                pob.auto_config("bossing")
                boss = optimise_supports(pob, boss_group, boss_skill, slots=slots, metric=boss_metric, log=quiet)[0]
                boss_dps = total_dps(pob.calc(STAT_FIELDS))
                pob.send("set_main", group=group)
            else:
                pob.auto_config("bossing")
                boss = optimise_supports(pob, group, skill, slots=slots, metric=boss_metric, log=quiet)[0]
                boss_dps = total_dps(pob.calc(STAT_FIELDS))

        # Mapping setup last, so the PoB code and stats are the mapping version.
        pob.set_config(**MODE_CONFIG["mapping"])
        conditions = pob.auto_config("mapping")
        mobility = mobility_skills(catalog, spec["weapon_type"], offhand_type=spec.get("offhand_type"))
        best = optimise_supports(pob, group, skill, slots=slots, metric=map_metric, log=quiet,
                                 shortlist=shortlist)[0]
        alloc = pob.send("allocated")
        used = set(best.supports) | set(boss.supports if boss else [])
        setups = kit_out(pob, group, spirit, utility, mobility[:1], map_metric, slots, used, log=quiet)
        report("kit", f"Supports for {len(setups)} more skills")
        stats = pob.calc(STAT_FIELDS + CLEAR_FIELDS + GOAL_FIELDS + SPLIT_FIELDS + ["BleedDPS", "PoisonDPS", "IgniteDPS"]
                         + MINION_AILMENT_FIELDS)
        guide = StageGuide(
            stage=stage.key, name=stage.name, level=stage.level, budget=stage.budget, budget_key=stage.budget_key,
            supports=best.supports,
            notables=[s["node"] for s in tree["steps"] if s["type"] != "Normal"],
            gear=gear, stats=stats, dps=total_dps(stats), code=pob.save_code(),
            ailment=spec.get("ailment"),
            boss_supports=boss.supports if boss else [], boss_dps=boss_dps,
            boss_skill=boss_skill, boss_weapon_set=2 if boss_swap else 1,
            spirit=spirit, conditions=conditions, goals=goals, utility=utility,
            mobility=mobility, setups=setups,
            tree_nodes=[int(n) for n in alloc.get("nodes") or []], tree_version=alloc.get("version"),
            tree_order=[{"id": s.get("id"), "name": s["node"], "type": s["type"], "path": s.get("path") or [],
                         "ascendancy": bool(s.get("ascendancy")), "gain": round(s.get("gain_per_point") or 0, 4)}
                        for s in tree["steps"]],
            theme_issues=theme_check(spec, stats, catalog),
            clear=clear_score(stats),
            damage_split=damage_split(stats),
        )
        if stage_key == "end":
            guide.rating = rate(boss_dps or total_dps(stats), guide.clear, stats.get("TotalEHP", 0))
        for issue in guide.theme_issues:
            guide.notes.append("Off theme: " + issue)
        for k, label in (("FireResist", "fire"), ("ColdResist", "cold"), ("LightningResist", "lightning")):
            if stats.get(k, 0) < 75:
                guide.notes.append(f"{label} resistance {stats.get(k, 0):.0f}%: cap it with jewels or by swapping a gear affix")
        for p in gear:
            if p.unique and p.price_note == "price unknown":
                guide.notes.append(f"{p.unique.split(',')[0]}: price not checked yet")
        log(f"{stage.name}: {guide.dps:,.0f} mapping DPS, {guide.boss_dps:,.0f} boss DPS")
        if progress:
            progress({"stage": stage_key, "step": "done", "label": f"{guide.dps:,.0f} mapping DPS",
                      "dps": round(guide.dps, 1), "boss_dps": round(boss_dps, 1)})
        return guide


def kit_out(pob: PoB, main_group: int, spirit: list[str], utility: list[dict], movement: list[str], metric: str,
            slots: int, used: set[str], log=lambda *a: None) -> list[dict]:
    """Supports for every skill besides the main one, so the build is complete, not just its main attack.

    Spirit and utility skills (auras, heralds, curses, banners) are scored by what they do for the main skill:
    the main skill stays main while their supports are tried (keep_main). The movement skill gets its own group
    and is scored on uses per second per mana spent. Each support gem is used once in the whole build, as in game.
    """
    groups = pob.send("groups")["groups"]
    by_skill = {g["gems"][0]: g["group"] for g in groups if g["gems"] and g["group"] != main_group}
    setups = []
    todo = [(n, "spirit") for n in spirit] + [(u["skill"], "utility") for u in utility]
    for name, role in todo:
        gid = by_skill.get(name)
        if not gid:
            continue
        res = optimise_supports(pob, gid, name, slots=slots, metric=metric, exclude=used, keep_main=True, log=log)
        chosen = res[0].supports if res else []
        used |= set(chosen)
        setups.append({"skill": name, "role": role, "supports": chosen})
    for name in movement:
        gid = pob.add_skill([name], main=False)["group"]
        res = optimise_supports(pob, gid, name, slots=slots, metric="movement", exclude=used, log=log)
        chosen = res[0].supports if res else []
        used |= set(chosen)
        setups.append({"skill": name, "role": "movement", "supports": chosen})
        pob.send("set_main", group=main_group)
    return setups


def build_guide(spec: dict, stages: list[str] | None = None, log=print, progress=None) -> list[StageGuide]:
    keys = stages or spec.get("stages") or list(STAGE_DEFS)
    with ThreadPoolExecutor(max_workers=len(keys)) as ex:
        return list(ex.map(lambda k: build_stage(spec, k, log, progress), keys))


def to_markdown(spec: dict, guides: list[StageGuide]) -> str:
    out = [f"# {spec.get('name') or spec['skill']}", "",
           f"Budget: **{make_stage('end', spec.get('budget', DEFAULT_BUDGET)).budget}**", ""]
    out.append("| Stage | Level | Budget | Mapping DPS | Boss DPS | Life / ES | Effective HP | Res (F/C/L/Chaos) |")
    out.append("|---|---|---|---|---|---|---|---|")
    for g in guides:
        s = g.stats
        res = "/".join(f"{s.get(k, 0):.0f}" for k in ("FireResist", "ColdResist", "LightningResist", "ChaosResist"))
        boss = f"{g.boss_dps:,.0f}" if g.boss_dps else "-"
        out.append(f"| {g.name} | {g.level} | {g.budget} | {g.dps:,.0f} | {boss} | {s.get('Life', 0):,.0f} / "
                   f"{s.get('EnergyShield', 0):,.0f} | {s.get('TotalEHP', 0):,.0f} | {res} |")
    for g in guides:
        out += ["", f"## {g.name}", f"**Mapping:** {spec['skill']} + " + ", ".join(g.supports)]
        if g.boss_skill:
            where = " (weapon set 2)" if g.boss_weapon_set == 2 else ""
            out.append(f"**Bossing:** {g.boss_skill}{where} + " + ", ".join(g.boss_supports))
        elif g.boss_supports:
            out.append(f"**Bossing swap:** {spec['skill']} + " + ", ".join(g.boss_supports))
        if g.rating:
            r = g.rating
            out.append(f"**Rating: {r['overall']}/10 ({r['label']})**: damage {r['damage']}, clear {r['clear']}, "
                       f"toughness {r['toughness']}")
        if g.spirit:
            out.append("**Spirit:** " + ", ".join(g.spirit))
        if g.utility:
            out.append("**Utility:** " + ", ".join(
                f"{u['skill']}" + (f" (weapon set 2, {u['weapon']})" if u["weapon_set"] == 2 else "") + f" {u['gain']:+.0%}"
                for u in g.utility))
        if g.mobility:
            out.append("**Movement skill:** " + " or ".join(g.mobility))
        if g.goals:
            out.append("**Also optimised for:** " + ", ".join(GOAL_LABELS[x] for x in g.goals))
        if g.conditions:
            out.append("**Assumed in combat:** " + "; ".join(f"{condition_label(c['var'])} ({c['why']})" for c in g.conditions))
        if g.notables:
            out.append("**Key passives:** " + ", ".join(g.notables))
        out.append("\n**Gear** (affixes in priority order):")
        for p in g.gear:
            if p.unique:
                out.append(f"- **{p.slot}**: {p.unique} (unique, {p.price_note})")
            else:
                out.append(f"- **{p.slot}**: {p.base}. " + ("; ".join(p.affixes) or "base only"))
        for n in g.notes:
            out.append(f"- Note: {n}")
        out.append(f"\nPoB code: `{g.code}`")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="JSON build spec")
    ap.add_argument("--stages", help="comma list, e.g. early,end")
    ap.add_argument("--budget", choices=BUDGET_ORDER, help="cap all gear at this budget")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    spec = json.load(open(args.spec))
    if args.budget:
        spec["budget"] = args.budget
    stages = args.stages.split(",") if args.stages else None
    guides = build_guide(spec, stages, log=lambda *a: None)
    if args.json:
        print(json.dumps([asdict(g) for g in guides], indent=2))
    else:
        print(to_markdown(spec, guides))


if __name__ == "__main__":
    main()
