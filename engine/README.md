# Engine: headless Path of Building

Runs the PoE 2 Path of Building calculation engine without its window, so we can score thousands of build variants automatically.

## Reproducible results
LuaJIT is built with fixed PRNG and string ID seeds (see setup.sh), so the same request always gives the same build. Without that, table order changes every run and so do tied picks.

## Setup
```
./setup.sh        # clones PoB (PoE 2) and builds LuaJIT + lua-utf8 into engine/vendor
```
Needs git, make and gcc. PoB needs LuaJIT at commit 2460b3ff or newer (it uses `a += 1`).

## Pieces
- `runner.lua`: runs inside PoB. Reads JSON commands on stdin, replies with `@@{json}` lines.
- `pob.py`: Python client. One `PoB()` is one long-running PoB process (about 2.5s to start, then ~20ms per recalculation).
- `optimize.py`: support gem beam search. Screens every support, then builds the best set one gem at a time.
- Passive tree: `optimise_tree` (in runner.lua) greedily spends passive and ascendancy points using PoB's fast what-if calculator. Each step scores every reachable node by (DPS gain + 0.25 x EHP gain) per point.
- `compare.py`: evaluate 1 build or compare up to 3. Gives a DPS/defence table and basic pros and cons. Builds can be PoB codes or recipes, and can ask the optimiser to pick supports. Example: `python3 compare.py examples/compare_three.json`.
- `gear.py`: crafts a rare for every slot from PoB's affix tables, per stage. Picks the best base, then damage and defence affixes, then only the resistances still needed, then fills the rest. Output is a per-slot shopping list (base + affixes in priority order with target values).
- `guide.py`: full build guide. One spec becomes 4 stages: Leveling (lvl 55, free), Early maps (lvl 75, 0-5 div), Mid maps (lvl 90, 5-30 div), Endgame (lvl 95, 50+ div). Each stage: supports, gear, passive tree, supports again. Example: `python3 guide.py examples/tempest_flurry_invoker.json` (output in `examples/tempest_flurry_invoker_guide.md`, about 2.5 minutes).
- Budget: players pick one up front, `free`, `budget` (<=5 div), `medium` (5-30), `high` (30-100) or `unlimited`. No stage's gear goes above it: a 5 divine player still gets mid maps and endgame versions, built with 5 divine gear. `python3 guide.py spec.json --budget budget`, `python3 compare.py examples/compare_specs.json --budget budget`.
- `tools/sweep.py`: smoke test that builds one stage for all 23 ascendancies (about 9 minutes on 4 cores). Run it after a PoB update.
- `generate.py`: the build generator. A theme (damage types, kinds like minion or melee, an ailment, weapons, optional class/ascendancy/skill locks, budget) becomes a ranked list of skill + weapon + ascendancy builds. `plan_build()` turns it into a guide spec, adding a boss skill (on weapon set 2 if needed) when one hits 25%+ harder; with a lock it reports the damage given up ("10% less than the recommended Invoker"). `options()` lists the alternatives for the feedback screen.
- `spirit.py`: fills spirit with the auras, heralds, buffs and extra minions that help most.
- `tools/end_to_end.py`: theme -> generate -> plan -> guide in one command.
- `demo.py`: command-line demo.

## Commands
`new`, `load_xml`, `save_xml`, `set_class`, `set_level`, `add_item`, `add_skill`, `try_skill`, `remove_skill`, `clear_skills`, `set_main`, `set_config`, `alloc_nodes`, `calc`, `list_gems`, `list_classes`, `list_uniques`.

## Mapping vs bossing
Gear and passives are built for mapping. Each stage (except leveling) then gets two support setups: mapping, and a bossing swap.
- Bossing: total DPS vs a pinnacle boss (PoB's default enemy).
- Mapping: PoB has no clear speed stat, so we score (hit DPS + half of DoT) x sqrt(area) x sqrt(projectiles) vs normal monsters. This is our heuristic, not PoB's, and is worth tuning against real play.

## DPS numbers
Total DPS = hit DPS + damage over time (bleed, ignite, poison, DoT skills). We don't use PoB's CombinedDPS as the headline because it leaves DoT out for some skills (e.g. Rake).

## What a build takes into account
- Main skill, chosen from every gem that fits the theme, on every weapon it can use (shield skills get a shield off hand; attacks with staves get quarterstaves, spells caster staves).
- Ascendancy, chosen by testing each one with passives spent.
- Supports for mapping and for bossing, limited to supports PoB's own rules allow on the skill.
- Passive tree and ascendancy points.
- Gear for every slot: crafted rares, and uniques where they beat the rare (budget-gated).
- Spirit: auras, heralds, buffs and extra minions.
- A second boss skill, on weapon set 2 when it needs another weapon.
- Conditional bonuses the build keeps up (`auto_config`): hit/used skill recently, killed recently while mapping, enemy ailments kept up 90%+ of the time, crit recently at 40%+ crit, charges the build says it gains, armour break, exposure. Each guide lists them with the reason.
- Damage from every source through PoB's Full DPS (minions with their counts, heralds, both skills).

Not yet: jewels, flasks and charms, weapon-set passive points, unique-granted skills, item prices (uniques without a known price are only suggested at medium budget and above), attribute requirements, meta/trigger setups (Cast on X).

## Minions
Minion damage lives in PoB's separate minion output; the engine exposes it as `MinionDPS` / `MinionDotDPS` and counts it in every score.

## Known gaps
- Pros and cons are rule-based for now (damage split, accuracy, speed, crit, resistances, tankiness). The AI layer will add context later.
- Tree optimiser is greedy: it can miss a big node that sits behind weak ones further than 6 points away. No jewels, no weapon-set passives, no attribute requirements yet.
- Speed: a full 4-stage guide takes about 2.5 minutes on 4 CPU cores (one stage per core). Repeat requests come from the API cache instantly.
- Tree search is greedy: from the same start, a different path choice once gave 138k DPS instead of 120k. A look-ahead search could find those.
- Support rules: the optimiser rejects any combo that triggers a PoB rule warning (e.g. lineage copy limit). Pass `exclude` for gems used in other skills.
- Conditional supports (Hit and Run, Glory gems, combo finishers; 12 in total) are skipped by default because PoB counts their bonus but not their downtime.
- Gear is rares only. Uniques need price data (poe.ninja) to place them in the right budget stage. Budgets in divines are estimates until then.
- Leveling stage is one snapshot at level 55, not a step-by-step leveling route.
- New 1.0 content (Shadow, new gems, daggers' new skills) needs a PoB update first.
