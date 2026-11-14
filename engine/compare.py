"""Evaluate one build or compare up to three: damage numbers plus basic pros and cons.

A build is either a PoB share code or a recipe:
    {"name": "...", "code": "<PoB code>"}
    {"name": "...", "class": "Monk", "ascendancy": "Invoker", "level": 90,
     "items": ["<PoB item text>", ...],
     "skills": [["Tempest Flurry", "Rakiata's Flow", ...], ...],   # first is the main skill
     "config": {"enemyIsBoss": "Pinnacle"},
     "optimise_supports": 5}   # optional: let the optimiser pick the main skill's supports

CLI:  python3 compare.py builds.json [--json]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from optimize import optimise_supports, total_dps
from pob import PoB

FIELDS = [
    "FullDPS", "TotalDPS", "CombinedDPS", "AverageHit", "Speed", "HitChance", "CritChance",
    "CritMultiplier", "BleedDPS", "PoisonDPS", "IgniteDPS", "TotalDotDPS",
    "Life", "EnergyShield", "Mana", "Armour", "Evasion", "TotalEHP", "PhysicalMaximumHitTaken",
    "FireResist", "ColdResist", "LightningResist", "ChaosResist",
]

MAX_BUILDS = 3
RES_CAP = 75


@dataclass
class Report:
    name: str
    main_skill: str | None
    dps: float
    hit_dps: float
    ailment_dps: float
    ehp: float
    stats: dict
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    code: str = ""
    supports: list[str] = field(default_factory=list)


def load_build(pob: PoB, build: dict) -> str | None:
    """Load a build into PoB. Returns the main skill name."""
    if build.get("code"):
        pob.load_code(build["code"])
    else:
        pob.new()
        pob.set_class(build["class"], build.get("ascendancy"))
        pob.set_level(build.get("level", 90))
        for raw in build.get("items", []):
            pob.add_item(raw)
        main_group = None
        for i, gems in enumerate(build.get("skills", [])):
            res = pob.add_skill(gems, main=(i == 0))
            if res["unknown_gems"]:
                raise ValueError(f"{build.get('name')}: unknown gems {res['unknown_gems']}")
            if i == 0:
                main_group = res["group"]
        if build.get("nodes"):
            pob.alloc_nodes(build["nodes"])
        if main_group:
            pob.send("set_main", group=main_group)
        if main_group and build.get("optimise_supports"):
            skills = build["skills"][0]
            best = optimise_supports(pob, main_group, skills[0], slots=int(build["optimise_supports"]),
                                     log=lambda *a: None)[0]
            build["chosen_supports"] = best.supports
    if build.get("config"):
        pob.set_config(**build["config"])
    return pob.send("calc", fields=["TotalDPS"]).get("main_skill")


def evaluate(pob: PoB, build: dict) -> Report:
    skill = load_build(pob, build)
    s = pob.calc(FIELDS)
    hit = s.get("TotalDPS", 0)
    ailment = s.get("TotalDotDPS", 0)
    dps = total_dps(s)
    return Report(
        name=build.get("name") or skill or "Build",
        main_skill=skill,
        dps=dps,
        hit_dps=hit,
        ailment_dps=ailment,
        ehp=s.get("TotalEHP", 0),
        stats=s,
        code=pob.save_code(),
        supports=build.get("chosen_supports") or list(build.get("skills", [[None]])[0][1:]),
    )


def absolute_notes(r: Report) -> None:
    """Pros and cons that hold on their own, without other builds to compare to."""
    s = r.stats
    share = r.ailment_dps / r.dps if r.dps else 0
    if share >= 0.6:
        kinds = [k for k in ("Bleed", "Ignite", "Poison") if s.get(f"{k}DPS", 0) > 0] or ["damage over time"]
        r.pros.append(f"{share:.0%} of damage is {'/'.join(kinds).lower()}: keeps ticking while you dodge, good for bosses")
        r.cons.append("Ailment damage ramps up, so packs die slower than with a pure hit build")
    elif share <= 0.1:
        r.pros.append("Almost all hit damage: instant kills on packs, good map clear")
    else:
        r.pros.append(f"Mixed damage ({share:.0%} over time): hits clear packs, ailments keep bosses ticking")

    hit_chance = s.get("HitChance")
    if hit_chance is not None and hit_chance < 90 and r.hit_dps > 0:
        r.cons.append(f"Only {hit_chance:.0f}% chance to hit: needs more accuracy")

    crit = s.get("CritChance", 0)
    if crit >= 50:
        r.pros.append(f"{crit:.0f}% crit chance: reliable crits")
    elif 0 < crit < 15 and s.get("CritMultiplier", 0) > 2.5:
        r.cons.append("Invests in crit damage with low crit chance")

    speed = s.get("Speed", 0)
    if speed >= 5:
        r.pros.append(f"{speed:.1f} uses per second: fast, smooth to play")
    elif 0 < speed < 1.5:
        r.cons.append(f"Slow at {speed:.1f} uses per second: clunky to play")

    low = [f"{n} {s[k]:.0f}%" for n, k in (("fire", "FireResist"), ("cold", "ColdResist"), ("lightning", "LightningResist"))
           if s.get(k, RES_CAP) < RES_CAP]
    if low:
        r.cons.append("Uncapped resistances: " + ", ".join(low))
    elif all(k in s for k in ("FireResist", "ColdResist", "LightningResist")):
        r.pros.append("Elemental resistances capped")
    if s.get("ChaosResist", 0) < 0:
        r.cons.append(f"Negative chaos resistance ({s['ChaosResist']:.0f}%)")

    if s.get("EnergyShield", 0) > s.get("Life", 0):
        r.pros.append("Energy shield based: large pool that recharges")


def relative_notes(reports: list[Report]) -> None:
    """Pros and cons from comparing builds against each other."""
    if len(reports) < 2:
        return
    by_dps = sorted(reports, key=lambda r: -r.dps)
    top, bottom = by_dps[0], by_dps[-1]
    if top.dps > 0:
        nxt = by_dps[1]
        lead = top.dps / nxt.dps - 1 if nxt.dps else float("inf")
        top.pros.append(f"Highest damage ({lead:+.0%} over {nxt.name})")
        if bottom is not top:
            bottom.cons.append(f"Lowest damage ({bottom.dps / top.dps - 1:+.0%} vs {top.name})")
    by_ehp = sorted(reports, key=lambda r: -r.ehp)
    if by_ehp[0].ehp > 0 and by_ehp[0].ehp > by_ehp[-1].ehp * 1.1:
        by_ehp[0].pros.append(f"Tankiest ({by_ehp[0].ehp:,.0f} effective HP)")
        by_ehp[-1].cons.append(f"Squishiest ({by_ehp[-1].ehp:,.0f} effective HP)")


def compare(builds: list[dict], pob: PoB | None = None) -> list[Report]:
    if not 1 <= len(builds) <= MAX_BUILDS:
        raise ValueError(f"Give 1 to {MAX_BUILDS} builds")
    if pob is not None:
        reports = [evaluate(pob, b) for b in builds]
    else:
        # One PoB process per build, run side by side.
        def run(b):
            with PoB() as p:
                return evaluate(p, b)
        with ThreadPoolExecutor(max_workers=len(builds)) as ex:
            reports = list(ex.map(run, builds))
    for r in reports:
        absolute_notes(r)
    relative_notes(reports)
    return reports


def to_markdown(reports: list[Report]) -> str:
    def fmt(v):
        return f"{v:,.0f}"

    names = [r.name for r in reports]
    rows = [
        ("Main skill", [r.main_skill or "-" for r in reports]),
        ("Supports", [", ".join(r.supports) or "-" for r in reports]),
        ("Total DPS", [fmt(r.dps) for r in reports]),
        ("Hit DPS", [fmt(r.hit_dps) for r in reports]),
        ("Ailment / DoT DPS", [fmt(r.ailment_dps) for r in reports]),
        ("Uses per second", [f"{r.stats.get('Speed', 0):.2f}" for r in reports]),
        ("Crit chance", [f"{r.stats.get('CritChance', 0):.0f}%" for r in reports]),
        ("Life / ES", [f"{fmt(r.stats.get('Life', 0))} / {fmt(r.stats.get('EnergyShield', 0))}" for r in reports]),
        ("Effective HP", [fmt(r.ehp) for r in reports]),
        ("Fire / cold / lightning / chaos res",
         ["/".join(f"{r.stats.get(k, 0):.0f}" for k in ("FireResist", "ColdResist", "LightningResist", "ChaosResist"))
          for r in reports]),
    ]
    out = ["| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    out += [f"| {label} | " + " | ".join(vals) + " |" for label, vals in rows]
    for r in reports:
        out.append(f"\n**{r.name}**")
        out += [f"- + {p}" for p in r.pros] or ["- + (none found)"]
        out += [f"- - {c}" for c in r.cons] or ["- - (none found)"]
        out.append(f"- PoB code: `{r.code[:40]}...`")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("builds", help="JSON file with a list of 1-3 builds")
    ap.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    args = ap.parse_args()
    with open(args.builds) as f:
        builds = json.load(f)
    reports = compare(builds)
    if args.json:
        print(json.dumps([asdict(r) for r in reports], indent=2))
    else:
        print(to_markdown(reports))


if __name__ == "__main__":
    main()
