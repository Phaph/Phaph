# The Breaker: finding broken builds nobody has found yet

Second main use of Whetstone, to be **ready, working and live for PoE 2 1.0 (Dec 11, 2026)**. The first use is "build me
X"; this one is "find me something broken". Kyle's goal: be first, before Mobalytics and poe.ninja.

## What broken builds have in common

From PoE 2's patch history (what GGG nerfed, and fast):
- **A stat that feeds damage and can be stacked.** Archmage damage from maximum mana (massively nerfed in 0.2);
  energy shield, life and attribute stacking.
- **Trigger and energy loops.** Cast on Freeze / Cast on Shock (energy changes in 0.1.0d).
- **Counts with no cap.** Raging Spirits (capped at 5 per cast in 0.1.0c), Spark's projectiles, Spectres.
- **New items or supports interacting in ways nobody planned.** What hotfixes chase.

The common shape: **something that multiplies instead of adds.** The build optimiser picks the best piece at each step,
which finds the best version of a known build but never looks for multipliers. The Breaker does.

## Parts

### 1. Scaler scan (`engine/breaker.py scan`)
For each ascendancy and main skill, add a fixed amount of one stat at a time (max mana, max ES, max life, each attribute,
crit chance, cast/attack speed, spirit, projectile count, minion count, area) and measure how damage responds at 1x, 2x,
4x of that amount. Damage that grows **faster than the stat** (elasticity > 1) is a red flag. Output: per ascendancy,
the stats with the highest elasticity, and the skills where it happens.

### 2. Interaction finder (`engine/breaker.py pairs`)
Skill x (unique, keystone, support, ascendancy notable). For each pair: gain(a), gain(b), gain(a+b) on the same base
build. **Synergy = (1 + gain(a+b)) / ((1 + gain(a)) x (1 + gain(b)))**; above 1 means the pair does more together than
apart. Keep the outliers. Thousands of PoB calculations: overnight, resumable, results in a file.

### 3. Leads to full builds
Each lead becomes a real build with the existing tools: `anchor_unique` / `anchor_keystone` / `anchor_support` locks the
piece, deep search picks the rest, the guide builds all four stages. Score: the endgame rating against every
ascendancy's reference build (data/rating_calibration.json) = **broken score**; poe.ninja usage (engine/meta.py) =
**how new it is**; what PoB measured vs what is our estimate (triggers) = **confidence**.

### 4. Claude research (api/research.py, Claude API with web search)
- **Patch day:** reads the patch notes and `tools/catalog_diff.py`'s list of new and changed skills, supports, uniques
  and passives; proposes combos to test (they go straight into parts 2-3). Can start before PoB supports the patch.
- **Each lead:** explains why it works, flags results that may be a PoB miscalculation rather than real, and searches
  the web (Reddit, Mobalytics, poe.ninja) for whether it's already known.
- About $5-20 of API per full run.

### 5. Discoveries page (new page, `api/static/discoveries.html`)
Ranked finds, each with: broken score, how new it is, confidence, in-game status (unchecked / checked by Kyle), Claude's
write-up, and a link to its full guide. A "Find me a broken build" button on the main page leads here, with class and
budget filters; it serves the overnight results instantly.

### 6. Launch-day playbook
PoB supports 1.0 -> update the engine -> catalog diff -> Claude proposes combos -> overnight Breaker run -> publish.
Rehearse it first on the current patch: it must **rediscover today's known strong builds blind** (poe.ninja's top
builds, with off-meta turned off). If it can't find those, it won't find new ones.
Launch day needs reliable compute; Kyle's PC loses power, so consider a VPS for launch week only (Contabo VPS 12, $24).

## Limits
- It finds only what Path of Building models. Several historic broken builds came from things PoB doesn't model
  (trigger loops). Claude can raise those as ideas; they have to be checked in game.
- PoB's own bugs can look like broken builds. The guard against impossible numbers (optimize.broken_numbers) stays on,
  and Claude reviews every lead before it is published.

## Order
1. Scaler scan  2. Interaction finder  3. Leads to full builds  4. Rehearsal on the current patch (must rediscover the
known strong builds)  5. Claude research  6. Discoveries page  7. Launch-day playbook.

## Status
- 2026-11-17: plan written. Scaler scan built (`engine/breaker.py scan`, PoB custom modifiers via runner
  `set_custom_mods`) and run on the ~40 saved guides (data/breaker/scan.json). First lead: **Whirling Assault Martial
  Artist, speed elasticity 3.43** (damage grows 3.4x faster than speed): find out why. Smaller: Rapid Shot Oracle 1.67 /
  Invoker 1.59, Skyfall Stormweaver 1.47, Flame Wall 1.30, Siege Ballista 1.28. Mana scaling is dead everywhere
  (max 0.30), matching the 0.2 Archmage nerf. Minion builds read 0: the scan needs minion stats (minion damage, attack
  speed, count) for them. Next: explain the Whirling Assault lead, add minion scalers, then the interaction finder.
