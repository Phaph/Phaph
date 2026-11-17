"""Full build guide: one build spec -> Leveling, Early maps, Mid maps and Endgame versions.

Each stage gets its own level, passive points, gear budget, support gems and passives:
    supports (bare) -> gear -> passive tree (jewel sockets valued with a stand-in jewel) -> supports again
    -> gear again -> a jewel for every socket taken
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

from anchors import find_unique, stage_notes
from gear import BUDGET_ORDER, STAGE_DEFS, Scorer, SlotPlan, add_trade_info, craft_gear, craft_weapon, make_stage
from jewels import craft_jewels, proxy_jewel
from triggers import best_cast_on_crit, cast_on_crit, find_groups
from generate import add_helpers, best_helper
from optimize import (CLEAR_FIELDS, MINION_AILMENT_FIELDS, MODE_CONFIG, clear_score, metric_for, optimise_supports,
                      seed_ailment,
                      score_of, total_dps)
from goals import GOAL_FIELDS, GOAL_LABELS, mobility_skills
from pob import PoB, PoBError
from rating import rate
from defence import fill_spare_spirit, optimise_defence
from goals import weights as goal_weights
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
    clear_skill: str | None = None     # a second skill for clearing packs, if the build has one
    clear_supports: list[str] = field(default_factory=list)
    clear_dps: float = 0.0
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
    # Cast on Critical setup when it pays: {"gem", "spell", "supports", "mapping": estimate, "bossing": estimate}.
    # Whetstone's estimate (engine/triggers.py), not Path of Building's; not part of dps / boss_dps.
    trigger: dict | None = None
    # Supports for every other skill in the build: [{"skill", "role": spirit/utility/movement, "supports"}]
    setups: list[dict] = field(default_factory=list)
    damage_split: dict = field(default_factory=dict)        # dps by type: physical, fire, ..., minion
    budget_key: str = "high"                                 # free / budget / medium / high / unlimited
    tree_nodes: list[int] = field(default_factory=list)      # allocated passive ids, for the tree viewer
    # The order to take passives: each pick (most value per point first) with the path that reaches it.
    tree_order: list[dict] = field(default_factory=list)
    tree_version: str | None = None
    jewels: list[SlotPlan] = field(default_factory=list)    # one per jewel socket taken, slot "Jewel <node id>"


DEFAULT_BUDGET = "high"


def condition_label(var: str) -> str:
    """conditionEnemyBleeding -> 'enemy bleeding', usePowerCharges -> 'power charges'."""
    import re
    name = re.sub(r"^(condition|use)", "", var)
    return re.sub(r"(?<!^)([A-Z])", r" \1", name).lower()


STAGE_SOCKETS = {"leveling": 3, "early": 4, "mid": 5, "end": 5}
SOCKET_ORB = {3: "a Lesser Jeweller's Orb", 4: "a Greater Jeweller's Orb", 5: "a Perfect Jeweller's Orb"}


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
    # Support sockets a player has by this stage: every skill gem starts with 2; a Lesser Jeweller's Orb (campaign) sets
    # it to 3, a Greater (early maps) to 4, a Perfect to 5. The same limit applies to every skill in the build.
    slots = min(spec.get("support_slots", 5), STAGE_SOCKETS.get(stage_key, 5))
    # The build's goal: e.g. a bleed build optimises bleed damage everywhere, not raw hits.
    map_metric = metric_for("mapping", spec.get("ailment"), spec.get("goals"))
    boss_metric = metric_for("bossing", spec.get("ailment"), spec.get("goals"))
    goals = list(spec.get("goals") or [])
    with PoB() as pob:
        catalog = pob.send("skill_catalog")["skills"]
        minion_build = any(s["name"] == spec["skill"] and "Minion" in s["types"] for s in catalog)
        pob.new()
        pob.set_class(spec["class"], spec.get("ascendancy"))
        pob.set_level(stage.level)
        skill = spec["skill"]
        pob.totem_for = dict(spec.get("totems") or {}) or None   # Spell Totem + Fireball: the gem goes in front
        # What the build is made around (anchors.py): the unique is always worn, the keystone always taken, the
        # support always on the main skill. Popular uniques score lower when the player chose off-meta.
        anchors = {"main": skill}
        if spec.get("anchor_unique"):
            anchors["unique"] = find_unique(pob.list_uniques(), spec["anchor_unique"])
        for key in ("keystone", "support"):
            if spec.get(f"anchor_{key}"):
                anchors[key] = spec[f"anchor_{key}"]
        pob.anchors = anchors if len(anchors) > 1 else None
        pob.off_meta = bool(spec.get("off_meta"))
        pob.anchor_notes = []
        group = pob.add_skill([skill], full_dps=minion_build)["group"]
        seed_ailment(pob, group, skill, spec.get("ailment"))   # so gear and tree chase the ailment from the start
        helpers = list(spec.get("with_skills") or [])   # skills the player asked for (Charged Staff, Cast on X)
        picked_helpers = []
        metas = {s["name"] for s in catalog if "Meta" in s["types"]} & set(helpers)
        add_helpers(pob, {"with_skills": helpers}, skill, metas=metas)
        # Kinds of helper the player asked for ("with warcries"): the best skill of each kind for this build.
        for kind in spec.get("with_types") or []:
            pick = best_helper(pob, catalog, kind, map_metric, spec["weapon_type"], spec.get("offhand_type"), skip=helpers)
            if pick:
                pob.add_skill([pick], main=False)
                helpers.append(pick)
                picked_helpers.append((kind, pick))
        clear_skill = spec.get("clear_skill") if stage_key != "leveling" else None
        clear_group = pob.add_skill([clear_skill], main=False)["group"] if clear_skill else None
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
        # The best jewel this build could socket: the tree weighs every socket as its path plus this jewel.
        jewel_score = Scorer(def_weight=dw_gear, mode="mapping", metric=map_metric, goals=goals)
        stand_in = proxy_jewel(pob, stage, jewel_score)
        def tree_live(ev):
            if progress:
                progress({"stage": stage_key, "step": "tree_live", "chosen": ev.get("chosen"), "name": ev.get("name"),
                          "type": ev.get("type"), "path": ev.get("path") or [], "considered": ev.get("considered") or [],
                          "scanned": ev.get("scanned", 0), "evals": ev.get("evals", 0),
                          "ascendancy": bool(ev.get("ascendancy")), "score": round(ev.get("score") or 0, 1),
                          "removed": ev.get("removed") or [], "added": ev.get("added") or []})

        tree = pob.optimise_tree(def_weight=dw_tree, metric=map_metric, goals=goals, jewel=stand_in,
                                 on_step=tree_live if progress else None)
        if progress:
            for s in tree["steps"]:
                if s["type"] != "Normal":
                    progress({"stage": stage_key, "step": "passive", "label": s["node"],
                              "ascendancy": bool(s.get("ascendancy")), "gain": round(s.get("gain_per_point", 0), 4)})
        report("tree", f"{sum(s['cost'] for s in tree['steps'])} passive points spent")
        pob.send("balance_attributes")   # "+5 any attribute" passives go where the gear and gems need them
        pob.auto_config("mapping")
        first = optimise_supports(pob, group, skill, slots=slots, metric=map_metric, log=quiet, shortlist=shortlist)
        report("supports", ", ".join(first[0].supports) if first else "")
        # Cast on Critical reserves 100 spirit, so it competes with spirit buffs: fill spirit both ways, keep the better.
        trigger = None
        before_spirit = pob.save_xml()
        spirit = optimise_spirit(pob, catalog, mode="mapping", minion_build=minion_build, metric=map_metric, log=quiet)
        if not minion_build:
            plain_score, plain_xml = score_of(pob.calc(STAT_FIELDS + CLEAR_FIELDS), map_metric), pob.save_xml()
            pob.load_xml(before_spirit)
            trigger = best_cast_on_crit(pob, group, catalog, mode="mapping", slots=slots, log=quiet)
            if trigger:
                spirit_t = optimise_spirit(pob, catalog, mode="mapping", minion_build=minion_build, metric=map_metric, log=quiet)
                est = cast_on_crit(pob, group, find_groups(pob)[0], mode="mapping")
                with_t = score_of(pob.calc(STAT_FIELDS + CLEAR_FIELDS), map_metric) * (1 + est["trigger_dps"] / max(est["attack"]["dps"], 1))
                if with_t > plain_score:
                    spirit = spirit_t
                    report("spirit", f"Cast on Critical + {trigger['spell']} (estimate)")
                else:
                    trigger = None
            if not trigger:
                pob.load_xml(plain_xml)
        # Defensive buffs (Wind Dancer, Scavenged Plating...): kept when the EHP is worth the damage they cost.
        spirit, defence = optimise_defence(pob, catalog, spirit, map_metric,
                                           def_mult=goal_weights(goals)["def_mult"], log=quiet)
        spirit += [d["skill"] for d in defence]
        # Spirit left over: the defensive buffs real builds run that PoB can't score (Ghost Dance, Time of Need...).
        spare = fill_spare_spirit(pob, catalog, spec["weapon_type"], spec.get("offhand_type"),
                                  set(spirit) | set(helpers), log=quiet)
        spirit += spare
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
        # Passives, supports and spirit moved damage and resistances around: re-craft gear to fit. Attribute passives
        # are balanced first, and this pass treats an unmet requirement as costly: an item you can't equip is useless.
        pob.send("balance_attributes")
        gear = craft_gear(pob, stage, **weapon, def_weight=dw_gear, mode="mapping", metric=map_metric, goals=goals,
                          log=quiet, attr_weight=0.25)   # a point short costs like 25% damage: usable first
        if boss_swap:
            gear.append(boss_weapon())
        # Each socket's jewel for real, now the tree, gems and gear are settled.
        jewels = craft_jewels(pob, stage, jewel_score, log=quiet)
        add_trade_info(pob, gear + jewels)
        report("gear", "Gear re-crafted to fit" + (f", {len(jewels)} jewels" if jewels else ""),
               slots=[g.unique.split(",")[0] if g.unique else g.base for g in gear + jewels])

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
            if trigger:
                trigger["bossing"] = cast_on_crit(pob, group, find_groups(pob)[0], mode="bossing")

        # Mapping setup last, so the PoB code and stats are the mapping version.
        pob.set_config(**MODE_CONFIG["mapping"])
        conditions = pob.auto_config("mapping")
        mobility = mobility_skills(catalog, spec["weapon_type"], offhand_type=spec.get("offhand_type"))
        best = optimise_supports(pob, group, skill, slots=slots, metric=map_metric, log=quiet,
                                 shortlist=shortlist)[0]
        if trigger:
            trigger["mapping"] = cast_on_crit(pob, group, find_groups(pob)[0], mode="mapping")
            trigger.pop("group", None)
        clear, clear_dps = None, 0.0
        if clear_group:
            # The clear skill gets its own supports (none the main skill already uses), scored on clearing.
            pob.send("set_main", group=clear_group)
            pob.auto_config("mapping")
            res = optimise_supports(pob, clear_group, clear_skill, slots=slots, metric=map_metric, log=quiet,
                                    )
            clear = res[0] if res else None
            clear_dps = total_dps(pob.calc(STAT_FIELDS))
            pob.send("set_main", group=group)
            conditions = pob.auto_config("mapping")
        alloc = pob.send("allocated")
        used = set(best.supports) | set(boss.supports if boss else []) | set(clear.supports if clear else [])
        skip = {skill, boss_skill, clear_skill, *(spec.get("totems") or {}).values()}
        if trigger:
            skip |= {"Cast on Critical", trigger.get("spell")}
        setups = kit_out(pob, group, spirit, utility + [{"skill": h} for h in helpers], mobility[:1], map_metric, slots,
                         used, log=quiet, skip={n for n in skip if n})
        for x in setups:
            if x["skill"] in {d["skill"] for d in defence} or x["skill"] in spare:
                x["role"] = "defence"
        report("kit", f"Supports for {len(setups)} more skills")
        # Every gem is in now: balance attributes once more; if that isn't enough, use lower-level extra gems; and say
        # plainly if anything is still short.
        fit = pob.send("fit_gems")
        short = fit.get("short") or {}
        lowered = fit.get("lowered") or {}
        stats = pob.calc(STAT_FIELDS + CLEAR_FIELDS + GOAL_FIELDS + SPLIT_FIELDS + ["BleedDPS", "PoisonDPS", "IgniteDPS"]
                         + MINION_AILMENT_FIELDS)
        guide = StageGuide(
            stage=stage.key, name=stage.name, level=stage.level, budget=stage.budget, budget_key=stage.budget_key,
            supports=best.supports,
            notables=[s["node"] for s in tree["steps"] if s["type"] != "Normal"],
            gear=gear, jewels=jewels, stats=stats, dps=total_dps(stats), code=pob.save_code(),
            ailment=spec.get("ailment"),
            boss_supports=boss.supports if boss else [], boss_dps=boss_dps,
            boss_skill=boss_skill, boss_weapon_set=2 if boss_swap else 1,
            clear_skill=clear_skill, clear_supports=clear.supports if clear else [], clear_dps=clear_dps,
            spirit=spirit, conditions=conditions, goals=goals, utility=utility, trigger=trigger,
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
            guide.rating = rate(boss_dps or total_dps(stats), guide.clear, stats.get("TotalEHP") or 0)
        if isinstance(lowered, dict) and lowered:
            guide.notes.append("Lower-level gems so the attributes work out: "
                               + ", ".join(f"{n} level {lv}" for n, lv in sorted(lowered.items())))
        for attr, gap in (short.items() if isinstance(short, dict) else []):
            guide.notes.append(f"Needs {gap:.0f} more {attr} than this setup has: add {attr} on gear or swap a gem.")
        for h in sorted(metas):
            guide.notes.append(f"{h}: {skill} is socketed in it. How often it triggers isn't modelled yet, so the "
                               f"damage shown is {skill} cast normally.")
        if slots < 5 and slots in SOCKET_ORB:
            guide.notes.append(f"{slots} supports per skill at this stage: skill gems start with 2 sockets and "
                               f"{SOCKET_ORB[slots]} sets them to {slots}. More sockets come in later stages.")
        for name in spare:
            guide.notes.append(f"{name} uses spare spirit for defence. Path of Building doesn't count what it does, so "
                               f"it isn't in the numbers.")
        for d in defence:
            guide.notes.append(f"{d['skill']} for defence: {d['ehp']:+.0%} effective HP, {d['dps']:+.0%} damage"
                               + (f" (in place of {d['replaced']})" if d["replaced"] else "") + ".")
        for k in ("unique", "keystone", "support"):
            if spec.get(f"anchor_{k}"):
                why = "picked at random" if spec.get("random") and k == "unique" else "you asked for it"
                guide.notes.append(f"Built around {spec[f'anchor_{k}'].split(',')[0]} ({why}).")
        guide.notes += stage_notes(pob.anchor_notes)
        for name, gem in (spec.get("totems") or {}).items():
            guide.notes.append(f"{name} is placed by {gem}: socket {name} in {gem}, and the totems use it.")
        for kind, pick in picked_helpers:
            guide.notes.append(f"You asked for a {kind}: {pick} adds the most to this build, so it's in the skills.")
        for issue in guide.theme_issues:
            guide.notes.append("Off theme: " + issue)
        for k, label in (("FireResist", "fire"), ("ColdResist", "cold"), ("LightningResist", "lightning")):
            if stats.get(k, 0) < 75:
                guide.notes.append(f"{label} resistance {stats.get(k, 0):.0f}%: cap it with jewels or by swapping a gear affix")
        for p in gear + jewels:
            if p.unique and p.price_note == "price unknown":
                guide.notes.append(f"{p.unique.split(',')[0]}: price not checked yet")
        log(f"{stage.name}: {guide.dps:,.0f} mapping DPS, {guide.boss_dps:,.0f} boss DPS")
        if progress:
            progress({"stage": stage_key, "step": "done", "label": f"{guide.dps:,.0f} mapping DPS",
                      "dps": round(guide.dps, 1), "boss_dps": round(boss_dps, 1)})
        return guide


def kit_out(pob: PoB, main_group: int, spirit: list[str], utility: list[dict], movement: list[str], metric: str,
            slots: int, used: set[str], log=lambda *a: None, skip: set[str] = frozenset()) -> list[dict]:
    """Supports for every skill besides the main one, so the build is complete, not just its main attack.

    Spirit and utility skills (auras, heralds, curses, banners) are scored by what they do for the main skill:
    the main skill stays main while their supports are tried (keep_main). The movement skill gets its own group
    and is scored on uses per second per mana spent. Skills the build gets from its ascendancy, passives or items
    (Life Remnants...) are listed too ("granted"). Any socket the scoring leaves empty is filled with supports made
    for that kind of skill (fit_supports), since PoB can't score what a buff or a remnant support does.
    A support may sit on several skills (PoE 2 allows it); PoB's own warnings stop a lineage support used twice.
    """
    groups = pob.send("groups")["groups"]
    by_skill = {g["gems"][0]: g["group"] for g in groups if g["gems"] and g["group"] != main_group}
    setups = []
    todo = [(n, "spirit") for n in spirit] + [(u["skill"], "utility") for u in utility]
    known = {n for n, _ in todo} | set(skip) | set(movement)
    todo += [(n, "granted") for n in by_skill if n not in known and not n.startswith(("Weapon", "Default"))]
    for name, role in todo:
        gid = by_skill.get(name)
        if not gid:
            continue
        try:
            res = optimise_supports(pob, gid, name, slots=slots, metric=metric, keep_main=True, log=log)
            chosen = res[0].supports if res else []
        except (PoBError, ValueError):
            chosen = []
        chosen = fit_supports(pob, gid, name, chosen, slots, keep_main=True)
        setups.append({"skill": name, "role": role, "supports": chosen})
    for name in movement:
        gid = pob.add_skill([name], main=False)["group"]
        res = optimise_supports(pob, gid, name, slots=slots, metric="movement", log=log)
        chosen = fit_supports(pob, gid, name, res[0].supports if res else [], slots)
        setups.append({"skill": name, "role": "movement", "supports": chosen})
        pob.send("set_main", group=main_group)
    return setups


_ALONE: set[str] | None = None


def _alone_supports(pob: PoB) -> set[str]:
    """Supports that only work with no other supports on the skill (their text says so: Uhtred's Exodus)."""
    global _ALONE
    if _ALONE is None:
        texts = pob.send("gem_texts")["gems"]
        _ALONE = {n for n, g in texts.items() if g.get("support") and "no other support" in (g.get("desc") or "").lower()}
    return _ALONE


FIT_MIN = 0.6   # a support counts as made for a skill when the skill type it needs is rarer than 60% of skills


def fit_supports(pob: PoB, group: int, name: str, chosen: list[str], slots: int, keep_main: bool = False) -> list[str]:
    """Fill the sockets the damage search left empty with supports made for this skill (most specific first), as
    long as PoB accepts them (supported, no rule warning). The group ends up holding the result."""
    chosen = list(chosen)
    alone = _alone_supports(pob)
    if any(c in alone for c in chosen):
        return chosen   # e.g. Uhtred's Exodus: only works with no other supports, so the other sockets stay empty
    fams = {}
    for s in pob.send("fitting_supports", group=group).get("supports") or []:
        fam = s.get("family")
        fams[s["name"]] = "/".join(fam) if isinstance(fam, list) else (fam or s["name"])
        if len(chosen) >= slots:
            break
        if s["name"] in chosen or s["name"] in alone or (s.get("specific") or 0) < FIT_MIN:
            continue
        if fams[s["name"]] in {fams.get(c, c) for c in chosen}:
            continue
        res = pob.try_skill(group, [name, *chosen, s["name"]], ["TotalDPS"], keep_main=keep_main)
        if res["supported"].get(s["name"]) and not res.get("warnings"):
            chosen.append(s["name"])
    pob.try_skill(group, [name, *chosen], ["TotalDPS"], keep_main=keep_main)
    return chosen


def build_guide(spec: dict, stages: list[str] | None = None, log=print, progress=None) -> list[StageGuide]:
    """All stages side by side. With progress, each finished stage is also sent at once as a "stage_result"
    event, so the website can show it while the others are still being built."""
    keys = stages or spec.get("stages") or list(STAGE_DEFS)

    def one(k: str) -> StageGuide:
        g = build_stage(spec, k, log, progress)
        if progress:
            progress({"stage": k, "step": "stage_result", "result": asdict(g)})
        return g

    with ThreadPoolExecutor(max_workers=len(keys)) as ex:
        return list(ex.map(one, keys))


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
        if g.clear_skill:
            out.append(f"**Clearing:** {g.clear_skill} + " + ", ".join(g.clear_supports))
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
        if g.trigger:
            t, m, b = g.trigger, g.trigger.get("mapping") or {}, g.trigger.get("bossing") or {}
            out.append(f"**Cast on Critical:** {t['spell']}" + (f" + {', '.join(t['supports'])}" if t['supports'] else "")
                       + f", about {m.get('trigger_dps', 0):,.0f} mapping / {b.get('trigger_dps', 0):,.0f} boss DPS on top"
                       + " (Whetstone's estimate, not Path of Building's)")
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
        if g.jewels:
            out.append("\n**Jewels** (one per socket):")
            for p in g.jewels:
                out.append(f"- **{p.slot}**: " + (f"{p.unique} (unique, {p.price_note})" if p.unique
                                                   else f"{p.base}. " + "; ".join(p.affixes)))
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
