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
- 2026-11-17 (later): **Whirling Assault lead explained: a measurement artefact, not a real multiplier.** The build's
  damage is PoB's Full DPS, the sum of several skills: Quarterstaff Strike 593k, Whirling Assault 179k, Lightning Warp
  22k and smaller ones (1.37M). The scan read "speed" from the main skill, Whirling Assault, whose speed barely moves:
  its use time is about 1 s of fixed duration plus 1 / attack rate (PoB: base 1.49/s x 1.62 increased, yet 0.71 uses/s),
  so +100% attack speed gives it only +12.6% speed, while Quarterstaff Strike gets +62% speed and +62% damage. Full DPS
  rose 50% against a "speed" that rose 12.6%: ln 1.50 / ln 1.126 = 3.43. Nothing multiplies. Fix: the scan now makes
  the build's biggest damage source the main skill first (`breaker.dominant_group`); this build now reads 0.85.
  The other "speed" flags (Rapid Shot, Skyfall, Flame Wall, Siege Ballista, Snap, Furious Slam) need a rescan with that
  fix before they count as leads.
  **Side finding (engine, not Breaker):** this guide's headline 1.37M adds Whirling Assault and Quarterstaff Strike
  together as if both ran all the time, but they are two attacks sharing one character's time. Full DPS should only sum
  skills that run alongside the main one (minions, totems, triggers, auras), not alternating attacks.
- Minion scalers added: minion damage ("Minions deal n% increased Damage", read on the minion's average damage), minion
  attack/cast speed, and minion count (+n to every minion limit stat PoB's skills use, as raw mods through
  `set_custom_mods raw=`, because PoB has no mod text for most limits; then `sync_minion_counts` so Full DPS counts
  them). Checked on Skeletal Sniper Lich and Skeletal Storm Mage Martial Artist: count elasticity 0.10 / 0.26, damage
  0.06, speed 0.07: in those builds the minions are a small part of the damage (the player's own skill dominates).
  Runner: new `outputs` command (every numeric output plus PoB's breakdown lines) for this kind of digging.
- Scaler scan rerun with the fixes (the Breaker now scores against a pinnacle boss, see below; biggest damage source as
  main skill; minion scalers): data/breaker/scan.json. Whirling Assault is gone. Left: **Rapid Shot Oracle 1.67 /
  Invoker 1.59**, Skyfall Stormweaver 1.41, Rain of Arrows Shaman 1.28; everything else is at or under 1.10.
  **Rapid Shot explained: a real multiplier (as PoB models it).** Fresh Clip II gives 1% more damage per crossbow bolt
  reloaded in the last 8 seconds, and PoB counts those as clip size x 8 / (firing time + reload time). Rapid Shot fires
  about 100 bolts a clip, so this build reloads ~184 bolts per 8 s (+184% more damage); +100% skill speed raises that to
  ~229, so speed buys both more bolts per second and more damage per bolt (+24% rate x +15.6% per bolt = +44%).
  Without Fresh Clip II damage per bolt doesn't move; Rapid Attacks II adds to it. Damage grows with roughly speed
  squared, with no cap in PoB's gem data. To check in game: does Fresh Clip have a hidden cap, and does Rapid Shot's
  clip count as "bolts reloaded" one by one? If both hold, a Rapid Shot speed-stacker with Fresh Clip is the first
  real Breaker lead. Skyfall and Rain of Arrows still to explain.
- Minion builds now read: Skeletal Storm Mage Martial Artist minion speed 0.40, damage 0.35, count 0.28; Skeletal
  Sniper Lich 0.13 / 0.11 / 0.16. Low because the player's own skill does most of the damage in these guides; a real
  minion build is needed to judge the minion scalers (none saved yet).
