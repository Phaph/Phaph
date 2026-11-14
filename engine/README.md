# Engine: headless Path of Building

Runs the PoE 2 Path of Building calculation engine without its window, so we can score thousands of build variants automatically.

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
- `demo.py`: command-line demo.

## Commands
`new`, `load_xml`, `save_xml`, `set_class`, `set_level`, `add_item`, `add_skill`, `try_skill`, `remove_skill`, `clear_skills`, `set_main`, `set_config`, `alloc_nodes`, `calc`, `list_gems`, `list_classes`, `list_uniques`.

## DPS numbers
Total DPS = hit DPS + damage over time (bleed, ignite, poison, DoT skills). We don't use PoB's CombinedDPS as the headline because it leaves DoT out for some skills (e.g. Rake).

## Known gaps
- Pros and cons are rule-based for now (damage split, accuracy, speed, crit, resistances, tankiness). The AI layer will add context later.
- Tree optimiser is greedy: it can miss a big node that sits behind weak ones further than 6 points away. No jewels, no weapon-set passives, no attribute requirements yet.
- Speed: about 35s per build for supports + tree + supports again on 4 CPU cores. Caching and smarter candidate lists will cut this.
- Support rules: the optimiser rejects any combo that triggers a PoB rule warning (e.g. lineage copy limit). Pass `exclude` for gems used in other skills.
- Conditional supports (Hit and Run, Glory gems, combo finishers; 12 in total) are skipped by default because PoB counts their bonus but not their downtime.
- Gear is rares only. Uniques need price data (poe.ninja) to place them in the right budget stage. Budgets in divines are estimates until then.
- No mapping vs bossing switch yet.
- Leveling stage is one snapshot at level 55, not a step-by-step leveling route.
- New 1.0 content (Shadow, new gems, daggers' new skills) needs a PoB update first.
