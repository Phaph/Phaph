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
- `demo.py`: command-line demo.

## Commands
`new`, `load_xml`, `save_xml`, `set_class`, `set_level`, `add_item`, `add_skill`, `try_skill`, `remove_skill`, `clear_skills`, `set_main`, `set_config`, `alloc_nodes`, `calc`, `list_gems`, `list_classes`, `list_uniques`.

## Known gaps
- Passive tree: can allocate named nodes, no tree optimiser yet.
- Support rules not enforced yet: lineage support limits, one copy of each support per character.
- Conditional supports (e.g. Hit and Run) use PoB's default config, which may assume their condition is met.
- Gear is whatever we put in. Budget-tier gear comes with the build data step.
- New 1.0 content (Shadow, new gems, daggers' new skills) needs a PoB update first.
