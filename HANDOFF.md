# PoE 2 Shadow build project: handoff

Goal: a day-one 1.0 (Dec 11, 2026) Shadow build. Melee, dual wield daggers, bleed (maybe crit bleed). Find the highest DPS version for endgame mapping, then publish and maintain it as a Mobalytics build page.

## How we work
- Run locally on Kyle's PC, not in the cloud.
- Research from the patch notes, poe2db, the wiki and poe.ninja. Compare skills, supports, unique daggers and both ascendancies (Assassin, Infiltrator).
- Use Path of Building headless (PoE 2 fork) to model and rank variants. Use my own damage model until PoB supports the Shadow.
- Drive Mobalytics through Claude in Chrome. Ask before publishing or overwriting the live page.
- Scheduled runs check for patches, PoB updates and ladder data, then re-run the comparison.

## Dry run on the live patch (next step)
1. Get PoB running headless and check its numbers match the PoB window.
2. Run a small bleed comparison (a few gems and weapons) to test the pipeline.
3. Make a test Mobalytics page through Chrome. Check whether the passive tree can be entered.
4. Set up scheduled runs and confirm they fire.
