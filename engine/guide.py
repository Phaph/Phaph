"""Full build guide: one build spec -> Leveling, Early maps, Mid maps and Endgame versions.

Each stage gets its own level, passive points, gear budget, support gems and passives:
    supports (bare) -> gear -> passive tree -> supports again
Stages run side by side, one PoB process each.

Spec:
    {"name": "Tempest Flurry Invoker", "class": "Monk", "ascendancy": "Invoker",
     "skill": "Tempest Flurry", "weapon_type": "Staff", "weapon_subtype": "Warstaff",
     "dual_wield": false, "stages": ["leveling", "early", "mid", "end"]}

CLI:  python3 guide.py spec.json [--stages early,end] [--json]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from gear import STAGES, SlotPlan, craft_gear
from optimize import optimise_supports, total_dps
from pob import PoB

STAT_FIELDS = ["TotalDPS", "TotalDotDPS", "Speed", "CritChance", "HitChance", "Life", "EnergyShield", "Mana",
               "Armour", "Evasion", "TotalEHP", "FireResist", "ColdResist", "LightningResist", "ChaosResist"]


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
    notes: list[str] = field(default_factory=list)


def build_stage(spec: dict, stage_key: str, log=lambda *a: None) -> StageGuide:
    stage = STAGES[stage_key]
    with PoB() as pob:
        pob.new()
        pob.set_class(spec["class"], spec.get("ascendancy"))
        pob.set_level(stage.level)
        skill = spec["skill"]
        group = pob.add_skill([skill])["group"]
        slots = spec.get("support_slots", 5)
        quiet = lambda *a: None

        optimise_supports(pob, group, skill, slots=slots, log=quiet)
        craft_gear(pob, stage, spec["weapon_type"], spec.get("weapon_subtype"),
                   dual_wield=spec.get("dual_wield", False), offhand_type=spec.get("offhand_type"),
                   def_weight=spec.get("defence_weight", 0.4), log=quiet)
        tree = pob.optimise_tree(def_weight=spec.get("defence_weight", 0.25))
        best = optimise_supports(pob, group, skill, slots=slots, log=quiet)[0]
        # Passives and gear moved resistances around; re-craft gear once so it fits the final tree.
        gear = craft_gear(pob, stage, spec["weapon_type"], spec.get("weapon_subtype"),
                          dual_wield=spec.get("dual_wield", False), offhand_type=spec.get("offhand_type"),
                          def_weight=spec.get("defence_weight", 0.4), log=quiet)
        stats = pob.calc(STAT_FIELDS)
        guide = StageGuide(
            stage=stage.key, name=stage.name, level=stage.level, budget=stage.budget,
            supports=best.supports,
            notables=[s["node"] for s in tree["steps"] if s["type"] != "Normal"],
            gear=gear, stats=stats, dps=total_dps(stats), code=pob.save_code(),
        )
        for k, label in (("FireResist", "fire"), ("ColdResist", "cold"), ("LightningResist", "lightning")):
            if stats.get(k, 0) < 75:
                guide.notes.append(f"{label} resistance {stats.get(k, 0):.0f}%: cap it with jewels or by swapping a gear affix")
        log(f"{stage.name}: {guide.dps:,.0f} DPS")
        return guide


def build_guide(spec: dict, stages: list[str] | None = None, log=print) -> list[StageGuide]:
    keys = stages or spec.get("stages") or list(STAGES)
    with ThreadPoolExecutor(max_workers=len(keys)) as ex:
        return list(ex.map(lambda k: build_stage(spec, k, log), keys))


def to_markdown(spec: dict, guides: list[StageGuide]) -> str:
    out = [f"# {spec.get('name') or spec['skill']}", ""]
    out.append("| Stage | Level | Budget | DPS | Life / ES | Effective HP | Res (F/C/L/Chaos) |")
    out.append("|---|---|---|---|---|---|---|")
    for g in guides:
        s = g.stats
        res = "/".join(f"{s.get(k, 0):.0f}" for k in ("FireResist", "ColdResist", "LightningResist", "ChaosResist"))
        out.append(f"| {g.name} | {g.level} | {g.budget} | {g.dps:,.0f} | {s.get('Life', 0):,.0f} / "
                   f"{s.get('EnergyShield', 0):,.0f} | {s.get('TotalEHP', 0):,.0f} | {res} |")
    for g in guides:
        out += ["", f"## {g.name}", f"**Skill:** {spec['skill']} + " + ", ".join(g.supports)]
        if g.notables:
            out.append("**Key passives:** " + ", ".join(g.notables))
        out.append("\n**Gear** (affixes in priority order):")
        for p in g.gear:
            out.append(f"- **{p.slot}**: {p.base}. " + ("; ".join(p.affixes) or "base only"))
        for n in g.notes:
            out.append(f"- Note: {n}")
        out.append(f"\nPoB code: `{g.code}`")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="JSON build spec")
    ap.add_argument("--stages", help="comma list, e.g. early,end")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    spec = json.load(open(args.spec))
    stages = args.stages.split(",") if args.stages else None
    guides = build_guide(spec, stages, log=lambda *a: None)
    if args.json:
        print(json.dumps([asdict(g) for g in guides], indent=2))
    else:
        print(to_markdown(spec, guides))


if __name__ == "__main__":
    main()
