# PoE 2 build optimizer

A free web app for Path of Exile 2. A player types a prompt like "lightning minion build for a monk" and gets the highest DPS version of that build, or a comparison of up to 3 builds. Builds come from real builds online and are tested in Path of Building (PoB) run headless.

Owner: Kyle. Day-one target: PoE 2 1.0 (Dec 11, 2026). First real test case is a Shadow dual wield dagger bleed build (see BUILD.md).

## Where things are
- `engine/`: headless PoB engine and optimisers. Read `engine/README.md` first.
  - `runner.lua` (JSON commands inside PoB), `pob.py` (client), `optimize.py` (supports),
    tree optimiser (`optimise_tree` in runner.lua), `gear.py` (rare crafting per slot and stage),
    `guide.py` (seven stage guides, Act 1 to Uber Endgame), `compare.py` (1-3 builds, pros/cons).
  - `engine/vendor/` is not in git. Run `engine/setup.sh` to build it (needs bash, git, gcc; use WSL on Windows).
- `api/`: FastAPI service (jobs + SQLite cache). `tests/`: pytest suite, also run by GitHub Actions.
- `design/`: UI concept board and the how-it-works explainer (published as private artifacts).
- `PC_TODO.md`: the current to-do list for Kyle and Claude. Start here.
- `BUILD.md`: pre-launch notes on the Shadow dual wield bleed build.

## Decisions already made
- Free app, not paid.
- No budget or prices (Kyle reversed the old budget picker on 2026-11-18). Gear and uniques follow what a player realistically has at each stage (`gear.STAGE_DEFS`, `UNIQUE_ACCESS`); poe.ninja data only measures how common a unique is and is never shown. Common uniques the build can use are allowed from Act 1 on (Kyle: uniques drop all through the campaign).
- Every build gets 7 Mobalytics-style stages: Act 1, Act 2, Acts 3-4, Interludes, Early Endgame, Mid Endgame, Uber Endgame. Act stages are light (one tree pass, no jewels, no boss setups); Uber Endgame builds for pinnacle bosses first, with best-in-slot uniques, more toughness and chaos resistance.
- Builds are chosen for endgame (Kyle, 2026-11-22): the skill is picked by its Uber Endgame build (players want the
  endgame build). Leveling stays close to what they asked for: swap to a better skill as new gems unlock when it
  clearly makes sense (~30%+ faster clear), same theme / element / weapon, at most 3 skills across the campaign
  including the endgame skill (4 if real guides for that archetype use 4: check Mobalytics), endgame skill by Early
  Endgame at the latest. Never a new skill every act.
- Compare takes up to 3 builds and shows DPS numbers plus basic pros and cons.
- Hosting plan: one Hetzner server (website + PoB workers), Claude API for prompts and write-ups.
- Total DPS = hit DPS + damage over time (PoB's CombinedDPS drops DoT for some skills). Builds with several damage sources (minions, heralds, a boss skill) use PoB's Full DPS.
- The tool picks skill, weapon and ascendancy itself (`engine/generate.py`); players can lock an ascendancy or skill afterwards and see the damage it costs.
- A theme's goal (e.g. bleed) drives every optimiser through one metric (`optimize.metric_for` / `score_of`).
- Builds include spirit buffs, uniques (by what each stage has access to), a boss skill on weapon set 2 when worth it, and only the conditional bonuses the build keeps up (each listed with its reason).

- The class-weapon rule (data/class_weapons.json: classes keep to their own weapons unless Off-meta / Random) is
  Whetstone's only, so guides suit the class. Lodestone has no class rules: any class with any weapon (if a Gemling
  stat-stack Spark build is the strongest, so be it). (Kyle, 2026-11-22)
- The build-breaking discovery tool is called **Lodestone** in public (pairs with Whetstone: Whetstone sharpens a build, Lodestone finds the builds nobody has found). "Breaker" stays as the internal code name (files, scripts, BREAKER*.md). (Kyle, 2026-11-18)

## Working rules
- Ask Kyle before publishing anything (Mobalytics pages, deploys).
- Never put API keys in chat or in the repo.
- The PoE sites (poe.ninja, poe2db, Mobalytics) were blocked in the cloud environment; they should work from the PC.
