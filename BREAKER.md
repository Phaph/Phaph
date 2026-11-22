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
- **Interaction finder built** (`breaker.py pairs`, `breaker.py report`). Per saved build (one per skill +
  ascendancy, end stage, vs pinnacle boss): every fitting support added to the main skill (~200), every keystone
  (applied as PoB's parsed node mods, so their conditions hold), every non-weapon unique at top rolls (~290) alone,
  then all pairs among the 30 best singles plus every keystone (~1,900 pairs, ~15 min a build on this PC with the
  A-to-Z sweep running). Output data/breaker/pairs.json, resumable. Fixes found on the way: keystone text split into
  lines lost its scope (Wildsurge's "Storm and Plant Spells:" read as a global 50% more); culling against normal
  monsters read as up to x2.2 damage (now scored vs boss); a runner crash in `warnings()` after Unleash silently
  dropped every later support.
  First outliers (synergy >= 1.10 and the pair worth 10%+), first 2 builds of the run:
  - Fireball Blood Mage: Leopold's Applause + Fire Penetration I, +10% and +10% alone, **+38% together (1.15)**.
    Same pair on Skeletal Sniper Lich: +10% / +8% -> +31% (1.10). To explain: two ways of lowering fire resistance
    should add, not multiply; likely Leopold's mods unlock or scale off penetration.
  - Skeletal Sniper Lich: Maligaro's Virtuosity + Pinpoint Critical, +22% / +9% -> +50% (1.14): crit chance x crit
    damage, the expected kind of multiplying, not a break.
  No keystone pair clears the bar yet; the strongest "synergies" between keystones (Avatar of Fire + Blackflame
  Covenant, CI + Resolute Technique) are both-negative overlaps, which `report` filters out.
  The full run (about 30 builds, ~8 h) is still going in container `whetstone-pairs`; rerun `report` when it ends.
- Next: explain Leopold's + Fire Penetration and the Skyfall / Rain of Arrows speed flags; test Rapid Shot + Fresh
  Clip in game; then part 3 (leads to full builds via anchors).

### Pairs run, full results (2026-11-17)

All 31 builds finished (one per skill + ascendancy, scored against a pinnacle boss). `python breaker.py report data/breaker/pairs.json` keeps pairs with synergy >= 1.10 that also gain at least 10% together:

| Synergy | Build | Pair | Alone | Together |
|---|---|---|---|---|
| 1.22 | Flicker Strike Acolyte of Chayula | Leopold's Applause + The Pandemonius | +10% / +8% | +45% |
| 1.17 | Snap Amazon | Considered Casting + Rondel of Fragility | +16% / +13% | +52% |
| 1.15 | Fireball Blood Mage | Leopold's Applause + Fire Penetration I | +10% / +10% | +38% |
| 1.14 | Skyfall Stormweaver | Plaguefinger + Atsak's Sight | +16% / +12% | +48% |
| 1.14 | Skeletal Sniper Lich | Maligaro's Virtuosity + Pinpoint Critical | +22% / +9% | +50% |
| 1.12 | Rapid Shot Oracle | Leopold's Applause + Avatar of Fire | +28% / -6% | +35% |
| 1.12 | Snap Amazon | Plaguefinger + Atsak's Sight | +6% / +6% | +26% |
| 1.11 | Entangle Shaman | Edyrn's Tusks + Crimson Assault | +10% / -3% | +19% |
| 1.10 | Skeletal Sniper Lich | Fire Penetration I + Leopold's Applause | +10% / +8% | +31% |

What they mean:
- **Leopold's Applause is the real lead (4 of 9 rows).** The gloves give 10% elemental penetration and let your hits penetrate resistances down to -50%. Normally penetration stops at 0% resistance, so a second source of penetration or resistance loss (Fire Penetration, The Pandemonius, Avatar of Fire turning damage into fire) is wasted once the boss is at 0. With Leopold's it keeps pushing below 0, so every extra point counts. This is a rule-break, not a PoB quirk. Worth checking in game that the -50% floor applies to bosses.
- **Plaguefinger + Atsak's Sight** shows up on two builds: both work on the same debuff, so each makes the other stronger. Expected stacking, not a rule-break.
- **Maligaro's + Pinpoint Critical** is crit chance times crit damage. Expected.
- **Considered Casting + Rondel of Fragility** and **Edyrn's Tusks + Crimson Assault** are not explained yet.

Dropped by the filter: the highest raw synergies (up to 2.22, e.g. Rakiata's Flow + Avatar of Fire on Hexblast Blood Mage) are all pairs that lose damage. Avatar of Fire wrecks a chaos skill like Hexblast (-78%), and a fire or penetration item wins back part of that loss once the damage is fire. The ratio looks big, but the build still loses 38% or more, so these are useless.

Next: check Leopold's Applause in game. Then search for more "removes a floor or cap" items like it (penetration past 0, resistance past the cap) and run them against every build.

### Text scanner and the Hexblast fix (2026-11-18)

**Text scanner built** (`engine/text_scan.py scan | diff | report`, step 1 of research/broken_builds.md). It reads
every gem stat line (with PoB's "not supported" flag), every unique mod and every notable, keystone and ascendancy
node, and flags wording that has broken the game before, by the research's groups: A "more" per unit, B a stat feeding
damage, D triggers / no cost / "not consumed", E counts and repeats, F explosions and on-kill, G caps and immunity,
H conditions, J "instead / converted / counts as" (add-vs-replace bugs). First run: 1,562 flagged lines, 256 of them
lines PoB can't calculate. Output data/breaker/text_scan.json. On patch day `diff` lists only new or changed lines.

First leads from it:
- **"Chance to not remove Charges but still count as consuming them"** on several pieces: Perpetual Charge (support)
  25%, The Fabled Stag (unique) 10%, Everlasting Infusions 10% (infusions). The research's group D: a "not consumed"
  chance that reaches 100% made past broken builds (Flicker no-consume). Next: list every source, see whether they add
  up to 100% for one skill (Flicker Strike, Falling Thunder, Charged Staff, Barrage), then an in-game test for Kyle.
  PoB can't calculate it.
- PoB-blind "more per unit" with no cap: Echoing Cry (100% more area per Echo), Electromagnetism (20% more per pulse),
  Cirel's Cultivation (10% more per allied totem). Need our own estimates.

**Hexblast fix (engine, found through the sweep and /learn/winners):** Hexblast won every search on every class
because PoB counts it as cast back to back (2.09 casts/s on a saved build), but it can only detonate a curse that is
half expired (Despair: 0.7 s cast + 1.5 s delay + 3.7 s = once per ~5.9 s per target, 0.17/s). New `USAGE_LIMITS` in
runner.lua caps the main skill's uses per second for skills like this, everywhere (search, supports, tree, gear).
Saved Stormweaver Hexblast: 4.34M -> 352K. Deadeye now picks Rain of Arrows with a bow. Next candidates for a usage
limit: Detonate Dead (needs a corpse each cast; bosses leave none; it became the Deadeye's boss skill) and Ember
Fusillade. Each limit is an estimate: in-game test requests to Kyle.

### Condition scan, first run (2026-11-18, server)
`engine/condition_scan.py run` built 166 main-capable skills the round-1 way and switched on each of PoB's 56 enemy
conditions alone (data/breaker/conditions.json; `report` separates general boosts, e.g. Shocked +20% for everything,
from payoffs that gain far more than usual).
- **It rediscovered a historical broken build blind: Lightning Conduit +68% vs Shocked** (usual +20%). The research
  lists Lightning Conduit per 5% Shock as a 0.1 broken build (group A). The detector shape works.
- **Armour Broken is the biggest combo family:** 39 physical skills gain +23% to +49% (Detonate Living, Unearth, Wolf
  Pack, Whirling Slash, Skeletal Reaver, Cull the Weak, Twister, Seismic Cry, Entangle, Blood Hunt, Flicker Strike...).
  Setup = an armour-breaking skill; payoff = these. First target for the combo finder's scoring.
- **Siege Cascade +101% vs any immobilised enemy** (frozen, pinned, electrocuted, heavy stunned): doubles damage.
- **Dark Effigy +100% vs Poisoned.**
- Gaps: Frozen moves only Siege Cascade, so PoB doesn't model "consume the Freeze" payoffs (Fragmentation Rounds etc.)
  through this condition; those need text-based pairing and our own estimate.
Next: combo finder step 2 (pair each payoff with skills that apply its condition, score setup time + uptime), then
plug into Whetstone (combo mode, boss/mapping picks) and run it on patch day.

### Combo finder step 2: setup + payoff scoring, Armour Broken (2026-11-18)
`engine/combo_scan.py run | report` (data/breaker/combos.json). PoB only ticks "Is the enemy Armour Broken?" (armour 0,
+20% physical damage taken from hits); it never works out how long breaking takes, and it records "X% of physical
damage dealt as Armour Break" (the Armour Break supports, some skills) as a flag with no amount. New runner command
`armour_break` reads the amounts (each such stat now also feeds a stat of our own) plus flat break per hit, Armour
Demolisher's more, hit damage per type, uses per second and the boss's armour (pinnacle: 8,063).
Scoring, our own estimate: time to Fully Break T = boss armour / (break per hit x hits per second); Fully Broken lasts
12 s; one cycle = T s of the setup skill, then 12 s of the payoff; +1 s per cycle when the setup needs weapon set 2.
**Edge** = combo DPS / the better of the two skills alone - 1: a combo only counts if it beats both (otherwise a slow
"setup" whose own damage carries it is just the stronger skill). Each skill is tried as a setup with Armour Break III +
Armour Demolisher II in place of its weakest supports, and as its own setup ("itself").
First run, 166 skills on round-1 builds (no tree), vs pinnacle boss: 104 can break armour, 30 payoffs (+10%+).
- Fastest breakers: Armour Breaker 0.4 s, Armour Piercing Rounds 0.4 s, Flicker Strike 0.6 s, Bonestorm 0.7 s,
  Bone Cage 0.9 s, Coiling Bolts 1.3 s (Detonate Dead 0.3 s, but it needs corpses a boss doesn't leave).
- Best combos: Armour Piercing Rounds or Armour Breaker breaking for themselves +41-42% (94-95% uptime);
  Bonestorm <-> Coiling Bolts +20-23% (same weapon); Flicker Strike + Armour Piercing Rounds on set 2 +20%;
  Thrashing Vines / Rend / Rampage / Entangle + Armour Breaker on set 2 +12-21%.
- **No Breaker lead here.** Armour Broken is a solid +20-45% payoff family, not a multiplier: the best combos land
  just under PoB's "always broken" number, as they should.
- Payoffs with no fast setup lose most of their PoB gain: Unearth +45% "always" -> +16% real (7 s to break),
  Twister +31% -> +9%, Whirling Slash +36% -> +3%. **Engine follow-up:** `auto_config` ticks Armour Broken only for flat
  break on hit and assumes 100% uptime; it ignores the Armour Break supports. It should use this uptime estimate.
- Not modelled yet: partial break before Fully Broken (helps every combo a little), hits per use beyond 1, minion
  setups, mapping (bossing only so far). Time to break needs an in-game check (one Armour Breaker hit on a pinnacle).
Next: the same scoring for the other payoff families from the condition scan (Shocked / Electrocuted / Frozen /
Poisoned / Immobilised: Siege Cascade, Dark Effigy, Lightning Conduit), then mapping combos.

### Blind test (2026-11-18, built, not run yet)
`engine/tools/blind_test.py run | report`: the search once per ascendancy ("<Ascendancy> build", off-meta off, no
head starts, so nothing from poe.ninja reaches it), top 15 kept, compared with the ladder: how many of poe.ninja's 20
most played main skills land in some ascendancy's top 5; Spearman of our best score per ascendancy vs its share of
players; skills we rank top 3 that under 1% play (leads or modelling bugs). Trial on Infernalist: **50 min on 3
cores** (server busy), picks Detonate Dead, Ember Fusillade, ...; Comet (14.6% of the ladder) ranks 4th. All 23
ascendancies is ~19 h on the server's 3 spare cores, a few hours on the PC: run it there
(`python tools/blind_test.py run --workers 6`). Detonate Dead winning again is the known suspect (needs corpses a
boss doesn't leave; next candidate for a usage limit) and will skew the test until it has one.
**poe.ninja changed its API (seen 2026-11-18):** `data/index-state` no longer lists snapshot versions, so
`tools/fetch_meta.py` fails, and the builds page now shows a Cloudflare check to the server. The test uses
data/meta_usage.json (Nov 17, overall shares only). Per-ascendancy truth (data/meta_pairs.json, {ascendancy: {skill:
share}}) needs the new endpoint, found from the PC's browser.

### In-game test requests and a pairs correction (2026-11-19)
TESTS.md: five requests for Kyle (Rapid Shot + Fresh Clip II speed scaling; Rapid Shot + Rampart Raptor, a new text
scan lead: 100% chance to not expend ammunition after a reload; Leopold's Applause below-0 penetration on bosses;
Hexblast's real detonation rate; Ember Fusillade PoB vs real), PoB codes in `ingame/`.
**Correction to the pairs table above:** `breaker.py pairs` applied uniques as extra mods on top of the build, so a
unique also kept the item it would replace. Fixed (the bench now empties the unique's slot first) and the report
rescored with the items really worn (`breaker.py rescore`, data/breaker/pairs_worn.json):
| Build | Pair | Worn: alone / alone -> together | Stacked (old) |
|---|---|---|---|
| Fireball Blood Mage | Leopold's Applause + Fire Penetration I | +4% / +10% -> **+31%** | +38% |
| Skeletal Sniper Lich | Maligaro's Virtuosity + Pinpoint Critical | +15% / +9% -> **+42%** | +50% |
| Skeletal Sniper Lich | Fire Penetration I + Leopold's Applause | +10% / +3% -> **+25%** | +31% |
| Snap Amazon | Plaguefinger + Atsak's Sight | +1% / +1% -> +14% | +26% |
| Skyfall Stormweaver | Plaguefinger + Atsak's Sight | +10% / -11% -> +9% | +48% |
| Entangle Shaman | Edyrn's Tusks + Crimson Assault | +0% / -3% -> +8% | +19% |
| Rapid Shot Oracle | Leopold's Applause + Avatar of Fire | +1% / -8% -> +4% | +35% |
| Flicker Strike Acolyte | Leopold's Applause + The Pandemonius | +0% / -18% -> +1% | +45% |
| Snap Amazon | Considered Casting + Rondel of Fragility | +16% / -38% -> -16% | +52% |
Leopold's + penetration survives (the below-0 mechanic multiplies); most other pairs were the stacking artefact.
"Not consumed" charges: all sources add to ~45% (Perpetual Charge 25%, The Fabled Stag 10%, Hollow Form 10%): dead.

### Per-ascendancy scans with ascendancy passives (2026-11-20, tasks 7 prep and 12)
The queue re-ran the condition scan and the unique/keystone matrix for all 23 ascendancies, this time with each
ascendancy's own passives (`breaker.ascendancy_passives`). Compared ascendancy by ascendancy within each class:
- **Oracle + Maligaro's Virtuosity read +173% to +190% on every spell** (Shaman: +10-18%). Cause: Forced Outcome
  (Inevitable Critical Hits: 100% crit, less bonus per reroll) plus the gloves' fixed "Critical Damage Bonus is 250%",
  whose override also wiped the reroll penalty. In game the gloves also say "Your Critical Hit Chance cannot be
  Rerolled", which turns Forced Outcome off (GGG closed this combo in 0.3/0.4; poe2wiki). PoB doesn't read that line.
  **Fixed in runner.lua** (the line now switches off Inevitable Critical Hits; tests/test_pob_fixes.py): Oracle + the
  gloves is +2%. A PoB modelling gap, not a lead (leads.json: fixed).
- **Lesson for the detectors:** a unique line PoB marks as unsupported can make a fake lead. Next cheap tool: list
  every unique's unsupported lines (ModCache entries with no mods) and tag scan flags that involve those uniques.
- Expected ascendancy effects, no lead: Amazon +50-55% vs Open Weakness on all its attacks (its own notables);
  Blood Mage +12-37% vs Cursed / Moving on minion and cry skills; Infernalist + Blackflame Covenant on minions.
- Not checked yet, probably spirit (The Coming Calamity grants three heralds): Witchhunter Shockwave Totem + The
  Coming Calamity +89% (Tactician +0%), Acolyte of Chayula Whirling Assault + The Coming Calamity +50%.
- Warrior, Ranger, Sorceress, Monk, Mercenary and Druid conditions: the ascendancies of a class read the same; the
  ascendancy passives the greedy pick takes are mostly plain damage nodes at round 1 (no tree).
- 11 caster skills error out in the matrix (Animus Exchange, Bitter Dead, Frostflame Nova, Fortifying Cry, Powered by
  Verisium...): no damage of their own (StopIteration on the bench), harmless.

### Unique lines PoB can't read (2026-11-20)
`engine/tools/unsupported_lines.py run` (runner `item_lines` now returns `unsupported`): 197 uniques have at least
one line PoB can't read (data/breaker/unsupported.txt). Matrix reports tag them; the patch-day run lists the new ones.
Of the 26 uniques our scans flagged, 5 have such lines, none a fake lead: Scold's Bridle (its downside, mana costs
taken as physical damage, is ignored: its "strong on 9 skills" overstates it), Blackflame (Wither's extra fire damage
taken is missing: likely UNDER-rated), Edyrn's Tusks / The Pandemonius / Loreweave (defence or mapping lines only).

### Blind test re-run: it never searched per ascendancy (2026-11-21, task 7)
The re-run (after the Ember Fusillade fix) picked **Deadeye Rain of Arrows on all 23 ascendancies** with the same
score on 22 of them, and the same top 15 everywhere: 1 of the ladder's top 20 skills found (Ice Shot), Spearman
+0.16. Cause: `blind_test.py` passed `parse_prompt` a {name: skill} map instead of its catalog shape ({skills,
classes, helper_skills}), so "Titan build" read no ascendancy and every search was the same all-class search. The
first run (Ember Fusillade everywhere) had the same bug. **Fixed:** the tool builds the catalog like check_prompt.py,
stops if the prompt doesn't read the ascendancy, and rejects a result ranking other ascendancies; all 23 prompts
checked. So far the blind test has only ever measured the all-class search: per-ascendancy numbers need the re-run.
**Rain of Arrows was the all-class winner at 2x the next skill (554k boss DPS vs Glacial Lance 257k); 0.08% of the
ladder plays it.** Modelling gap: PoB scores it as a full hit on the target every 0.12 s (its per-enemy cap), however
many arrows land on it. In game one rain drops its arrows 80 ms apart (at most 12.5 a second, one rain at a time)
across a 3.6 m circle, each hitting within 0.7 m. New USAGE_LIMITS rule: hits/s = min(arrows/s x
((target radius + impact radius) / rain radius)^2, 8.33), target 1.5 m for a boss, 0.5 m on maps. Base gem: boss
8.33 -> 4.67 hits/s (x0.56); Concentrated Area raises the share. The usage-limit hook now also limits HitSpeed, not
only Speed. Estimates: an in-game check (TESTS.md) would pin down the boss share.

### Blind test, first real per-ascendancy run (2026-11-21, task 7 done)
All 23 ascendancies searched on their own (engine 2026-11-21.1, Rain of Arrows limited), nothing from poe.ninja in.
data/breaker/blind.txt. **3 of the ladder's 20 most played main skills land in some ascendancy's top 5** (Comet #1
Blood Mage, Ice Shot #2 Deadeye, Rend #4 Oracle); Spark #7 (Abyssal Lich) and Tornado Shot #8 (Deadeye) are close.
Spearman of our best score per ascendancy vs its share of players: **+0.25** (was +0.16 with the all-class bug).
Why the other 15 are missed, in four groups:
- **Setup skills the ladder lists as "main" (5 of 20: Frost Bomb, Frost Wall, Orb of Storms, Powered by Verisium,
  Oil Grenade).** Cooldown pieces that make infusions, exposure, ice crystals or ignited ground for another skill.
  We score each as a lone damage skill, so they can't rank. Not a miss of the build: its payoff skill (Comet, Spark)
  is found. Real gap: the combo finder has no **infusion** family yet (Frost Bomb / Orb of Storms / Verisium feed
  Comet, Spark, Arc). Queued as task 21.
- **Druid kept to Talismans (4 of 20: Tornado, Entangle, Wolf Pack, Twister-like casters).** class_weapons.json gives
  Druid only Talisman (close: Staff), but the ladder's Druids (Oracle 7.3%, Shaman 1.5%) mostly cast Tornado and
  Entangle from a staff/wand and summon Wolf Pack (Sceptre/Wand). Round 1 picks Talisman skills only (Oil Barrage,
  Flame Breath). Fix: Druid intended = Talisman + Staff, close + Wand, Sceptre (task 20).
- **Huntress' two big spear skills (Whirling Slash 12.8%, Twister 10.9%) not in Huntress' top 10.** The search
  tried them (spear skills, Huntress' own weapon) and they scored low. Both build stages / pick up elemental ground
  (Whirling Slash gains stages, Twister takes ground's element): likely a PoB modelling or round-1 setup gap. Check
  (task 22).
- **Plain spells behind Comet/Skyfall/Bone Cage (Arc, Ice Nova, Flameblast, Grim Pillars, Spark lower).** Round 1
  has no tree and no infusions; Arc and Ice Nova on the ladder are infused or Frost Wall / Frostbolt combos, and
  Flameblast is channel stages. Same root as the infusion gap.
- Snipe (4.7%, Bow) not in Ranger's top 10: channel with perfect timing, scored at its base hit.
**Ascendancy order:** the ascendancies of one class still read nearly the same (Tactician = Witchhunter, Titan =
Warbringer to the point; same top 10 within each class): round 1 has no tree, and ascendancy passives add mostly
plain damage. So the Spearman mostly measures class vs class. Gemling (32% of the ladder) is mid; Spirit Walker
(6.8%) is last.
**Top 3 by us, under 1% of the ladder (17):** leads or modelling gaps to check one by one. Strongest suspects of a
modelling gap: Bone Cage #1 on all three Sorceress/Witch casters (0.84%), Hammer of the Gods #1 Warrior (0.48%),
Oil Barrage #1 Druid (0.77%, partly the weapon rule), Wind Serpent's Fury #1 Amazon (0.20%), Rapid Shot #1 Tactician
(0.41%, already a test request), Rain of Arrows still #1 Deadeye after its limit (0.08%). Next blind-test run after
20-22: target 8+/20 found.
**Druid weapon trial (task 20, reverted):** Druid allowed Staff + Sceptre (engine 2026-11-21.2), Oracle + Shaman
searched again. Worse: their top 10 filled with Sorceress staff spells (Snap, Firestorm, Bone Cage, Comet), Oil Barrage
and Rend dropped out (found 2/20, Spearman +0.22), and Tornado, Entangle, Wolf Pack still don't reach the top 15.
So the weapon rule wasn't what hid them: they score low in round 1 (Tornado is DoT-only, Entangle a plant limit,
Wolf Pack a companion), the same gap as the Huntress spear skills. Reverted (engine 2026-11-21.3); blind.json/txt
restored to the Talisman run.

### Why the Huntress and Druid ladder skills rank low (2026-11-21, task 22)
Round 1 (no tree, crafted mid-game gear, Amazon / Shaman, bossing):
| Skill | Round-1 score | Note |
|---|---|---|
| Oil Barrage (Talisman) | 116,860 | 6.8 uses/s at round 1: suspiciously fast, check |
| Entangle | 33,377 | |
| Lightning Spear | 23,742 | |
| Tornado | 16,417 | DoT only |
| Wind Serpent's Fury | 9,867 | |
| Twister | 6,404 | alone; see below |
| Whirling Slash | 5,354 | its own hit doesn't scale with stages in PoB |
| Wolf Pack | 3,445 | companion, 1.4k minion DPS: likely under-modelled |
- **Whirling Slash + Twister is a combo PoB can score but we never set up.** PoB's config has "# of Whirlwind Stages"
  and "Twister gained Cold/Fire/Lightning"; we leave all of them at 0. Twister on the same build: x2.04 with a
  1-stage whirlwind, **x4.21 with a 3-stage whirlwind consumed**, x1.40 with one ground element, x2.20 with all three.
  So Twister's 6.4k is ~27k used the way the ladder plays it (Whirling Slash to build the storm, Twister through it),
  which puts it beside Lightning Spear, before the tree. This is the ladder's top Huntress pair (12.8% + 10.9%).
  Next: a "whirlwind" family in the combo finder (setup = Whirling Slash stages per second, payoff = Twister's
  WhirlwindStages multiplier; elements from ground the build makes) (task 23).
- **Stages are never set either.** New runner command `set_stages` (reads/sets the main skill's Stages box). At max
  stages vs our default of 1: Flameblast x5.45 (10 stages), Bonestorm x2.40 (20), Supercharged Slam x1.09 (3),
  Detonating Arrow x0.72 (4, lower: check), Incinerate x1.00. Each skill needs its own rule for how many stages it
  really holds per use (channel time vs damage), so no blanket max: part of task 23.
- Tornado / Entangle / Wolf Pack: no PoB setting is missing; they score low on their own. Wolf Pack's companion
  damage and Oil Barrage's use rate are the two numbers to check against the game next.

### Partner combos: Twister through Whirling Slash (2026-11-21, task 23a)
New `engine/partners.py`, used by every search round (`generate.evaluate`): a payoff skill whose damage needs a setup
skill used first is scored over the real cycle, n setup uses then one payoff use:
`(n x setup damage per use + payoff damage per use at n stages) / (n / setup speed + 1 / payoff speed)`, best n.
First rule: Twister after Whirling Slash (PoB config whirlwindStages, up to 3; guides play 3 slashes then Twister).
The setup gets the payoff's supports. Amazon round 1: Twister alone 7.6k at 1.95/s; x1.91 / x2.84 / x3.76 per use at
1 / 2 / 3 stages; Whirling Slash 3.8k at 1.71/s (1.3k with no supports, which made the combo lose). Best: 3 slashes,
**x1.23 over the cycle** (score 6.4k -> 7.9k). Real but small: Lightning Spear is 23.7k. So Twister's 10.9% of the
ladder is mostly not boss damage: the guides sell it as a full-screen mapping skill (more Twisters when one consumes a
whirlwind; projectiles everywhere), which our clear score (area^0.5 x projectiles^0.5) only partly sees. Not counted
yet: Twister's ground elements (x2.20 with all three, needs ground the build makes) and the extra Twister a consumed
whirlwind spawns. Next blind re-run waits for the stage rules (23b), since this alone doesn't move Twister into a top 5.

### Stage rules (2026-11-21, task 23b)
runner.lua STAGE_RULES: Flameblast, Bonestorm and Supercharged Slam are used at their full stages (PoB's default was
1). PoB already stretches each use's time with the stage count (channelTimeMultiplier / hitTimeMultiplier), so the
DPS at a stage count is per second: Flameblast x5.45 (10 stages, 10 s cooldown), Bonestorm x2.40 (20), Supercharged
Slam x1.09 (3). Detonating Arrow stays at 1 (x0.72 at 4 in PoB; its max-stage explosion isn't modelled). Applied
whenever a group's gems are set (add_skill, try_skill), so saved builds and exports carry the stage count.
Full blind re-run queued after the deploy (engine 2026-11-21.5): partners + stage rules together.

### Oil Barrage and Wolf Pack (2026-11-21, task 25)
- **Oil Barrage was over-rated ~4.5x without Power Charges.** PoB scores its fast channelled barrage (3 projectiles at
  the weapon's attack speed: 5.55 uses/s) with or without charges. In game the barrage consumes a Power Charge every
  1.5 s ([poe2db](https://poe2db.tw/us/Oil_Barrage)); guides: "for this to actually deal damage, you need power
  charges". Without them it only spits oil, with a 4.5x attack time (display_attack_time_+% 350, a stat PoB doesn't
  read). New USAGE_LIMITS rule: no Power Charge source = attack speed / 4.5 (Shaman round 1: 18.7k -> 4.4k). With a
  source PoB's number stands; how long the charges keep the barrage up isn't modelled yet.
- **Wolf Pack was under-rated up to 7x, and every minion skill was ranked with one minion.** (1) PoB has no mapping
  for skill_wolf_pack_size (3 wolves at gem level 1, 6 at 20), so the wolf limit read 0; runner.lua now maps it to
  WolfLimit (limit 7 with Feeding Frenzy). (2) The search (`generate.evaluate`) never synced minion counts, so ALL
  minion skills were scored with one minion while ranking (the guide's later spirit step synced them, so finished
  builds were right). Now synced in evaluate and right after the guide adds a minion main skill. Wolf Pack Shaman:
  1.4k -> 10.0k Full DPS. Minion skills will rank higher across Witch/Druid searches.
The overnight blind run (engine 2026-11-21.5) started before these fixes; ~/after_minions.sh re-runs the 6 Witch and
Druid ascendancies afterwards.

### Infusions, and a bigger find: skill stat sets (2026-11-21, task 21)
In PoE 2's PoB a skill's parts are **stat sets** (gem.statSet[id]); the engine always used set 1. New runner command
`set_part`. Infused stat sets per cast, Sorceress mid-game round 1: Ice Nova Cold-Infused x3.75, Arc infused (config)
x3.00, Ball Lightning Fire-Infused x2.24, Comet Fire-Infused x1.75, Frost Wall Lightning-Infused x0.70.
**Infusion cycle (partners.apply_infusion, every search round):** a generator leaves one Infusion per period (Frost
Bomb: cold, 6 s cooldown; Orb of Storms: lightning, 12 s); one cast per cycle is infused. Ice Nova + Frost Bomb
**x1.16**, Arc + Orb of Storms **x1.06**. Small: one infusion per cycle. Generator damage and Frost Bomb's Elemental
Exposure count as nothing yet. Fire infusions (Comet, Ball Lightning: Living Bomb, Siphon Elements, Verisium) not
modelled. So Frost Bomb's 16.8% of the ladder is more likely its Exposure than its infusion (task 27).
**Bigger gap found on the way (task 26): extra damage stat sets are never counted.** Several skills deal damage in a
second stat set that happens on every use, and we only score set 1: Frost Darts Explosion (set 2 = x1.45 of set 1),
Fireball Firebolts (x1.05), Ball Lightning Ignited Ground (x3.63), Incinerate Ignited Ground (x11: check), Firestorm
Ice/Lightning Bolts, Ember Fusillade Beam. Whether each adds to set 1 (both happen) or replaces it needs a per-skill
rule, then such skills rank higher in every search.

### Extra damage stat sets counted (2026-11-21, task 26)
`partners.apply_extra_sets` (every search round): for skills whose second stat set lands on the same single target
on every use (from each gem's own text), the search adds it to set 1. Mid-game round-1 numbers, set 1 -> set 2:
Earthquake impact 1.5k + Aftershock 17.8k (x13); Glacial Cascade bursts 2.5k + Final Burst 8.2k; Essence Drain hit
12.2k + its DoT 12.3k; Stampede footsteps 1.9k + Slam 5.9k; Gas Grenade 0.7k + cloud 2.8k; Coiling Bolts physical
10.8k + chaos 12.3k; Bonestorm spikes 37.6k + explosion 27.1k; Fireball, Supercharged Slam and Poisonburst Arrow
x2 (the second set equals the first in PoB's data); Entangle +vines 0.6k; Cluster Grenade +mini grenades.
Left out as conditional (infusion, charge, detonator, parry, other enemies, terrain): Frost Darts, Frostbolt,
Lightning Spear, Explosive Spear, Glacial Lance, Volcano, Sunder, Ice Shot shards, Lightning Arrow beams and more;
Incinerate's x11 Ignited Ground is infused-only, so it is not counted. Not done yet: the finished guide still
reports set 1 only (the search ranks with the sum); a mirrored Full DPS group would fix both (follow-up).

### Frost Bomb as an Exposure setup (2026-11-21, task 27)
`partners.apply_exposure` (every search round): Frost Bomb's Elemental Exposure (-20% all elemental resistances, a
debuff PoB applies from any active skill in the build) is up 100% of the time (4 s of pulses + 8 s duration, 6 s
cooldown); its 0.8 s cast every 6 s is paid out of the main skill's time (x0.87). Bare Comet: x1.20 damage, x1.04 net.
**But penetration and Exposure don't stack** (PoE 2 rule, PoB follows it): with Rakiata's Flow on the main skill
(our searches pick it for Comet, Spark, Lightning Spear), adding Frost Bomb LOWERS damage (Comet 163k -> 152k), and
leaving Rakiata's out to make room for Exposure is still worse. So in our numbers Frost Bomb pays only on builds
without a strong penetration support. Its 16.8% of the ladder is then mostly not boss damage: map clear (an area
spell with a big detonation), the Cold Infusion for Ice Nova/Spark (task 21), and players without Rakiata's Flow
(a rare lineage gem). Not counted: Exposure compounding (+2% per pulse up to 50 in game), Frost Bomb's own damage.

### Trigger detector, step (a): hit-based meta gems (2026-11-21, task 15)
PoB's meta gems listed (Cast on Dodge / Minion Death / Block / Melee Kill / Melee Stun / Charm Use, the Invocations,
Thundergod's Wrath, Fire Spell on Melee Hit). New in engine/triggers.py + trigger_rules.json: **Thundergod's Wrath**
(granted by the unique mace Mjölner) and **Fire Spell on Melee Hit** (an ascendancy gem): 3 energy per monster power
on EVERY melee hit (Cast on Critical: 1 per power, crits only), Lightning / Fire spells only, full energy = 100 per
second of the socketed spells' cast time. PoB's data has no ailment-threshold part, but the game text does
("modified by the percentage of the enemy's Ailment Threshold the Hit will deal", poe2db), so the energy uses the
same threshold ratio as Cast on Critical. Mid-game Boneshatter Titan vs a pinnacle boss: a hit is 3% of the boss's
threshold, so ~2 energy per hit and ~55 hits per Arc (0.02 casts/s): only huge single hits feed it on bosses, which
is how the public "Thor" builds play Mjölner (a known build: the detector should find it as known, not new).
Next (b-d): scan feeders per meta (energy per second for the strongest single hits: slams, Supercharged Slam,
Boneshatter's shockwave), the loop graph from text_scan group D, leads.
**Step (c), loop graph (2026-11-21):** the text scan's 467 trigger lines, kept only when uncapped (no "no more than
once", cooldown or "cannot be triggered") and the trigger deals damage: 28 lines. Most are one-way (the triggered
skill can't set off its own trigger, or, for meta gems, triggered skills generate no energy). Two self-feeding chains,
both mapping only, added to leads.json as unconfirmed: **Bursting Fen Toad** ("25% chance to Trigger this Skill on
Kill": runs away at 4+ kills per explosion) and **Earthbound** (Spark on killing a Shocked enemy; Spark shocks).
Bosses don't die repeatedly, so neither is a boss lead. Feeder scan (b) still running (~/trigger_scan.sh).
**Steps (b) and (d), feeder scan (2026-11-22):** `tools/trigger_scan.py`, 51 melee attacks on crafted mid-game gear
with no supports, data/breaker/triggers.txt. Best feeders vs a pinnacle boss: Supercharged Slam and Flicker Strike
(14 energy/s into Thundergod's Wrath or Fire Spell on Melee Hit: 0.13 Arcs a second), Hammer of the Gods, Falling
Thunder. Cast on Critical gets about 1/20 of that from the same attacks (crits only, 1 energy per power). **No lead
over the bar (1 cast/s vs a boss):** one hit is 6-30% of a boss's ailment threshold at this gear. With endgame hits
near the whole threshold, Supercharged Slam would fire about one Arc a second: that is the known Mjölner build, so
the detector agrees with what players found, and finds nothing new. Mapping counts one monster per hit
(conservative: area hits on a pack give energy per monster).

### Fairer pairs: a tried support replaces the weakest one (2026-11-22, task 19)
`breaker.Bench` now ranks the skill's own supports by the damage each adds, and a tried support takes the place of
the weakest (before, it was an extra socket the build doesn't have). `breaker.py rescore` -> data/breaker/
pairs_weakest.json. **Leopold's Applause + Fire Penetration I (Fireball Blood Mage): +16% together (was +31%)**,
Fire Penetration alone -3% (was +10%), synergy 1.15: the pair still multiplies, half as big. **Maligaro's
Virtuosity + Pinpoint Critical (Skeletal Sniper Lich): +42%, unchanged** (Pinpoint +8% alone): the strongest pair.
Skeletal Sniper + Fire Penetration + Leopold's +24% (was +25%). Unique-only pairs are unchanged (no support swapped).

### Leads to full builds (2026-11-22, task 16)
`tools/lead_builds.py`: a lead with a `build` entry (its job, the pieces to anchor) is built as a full Whetstone stage
around them, and the same spec without them on the same engine (the saved jobs ran on a much older engine, so they
can't be the baseline). Uber Endgame, data/breaker/lead_builds/:
| Lead | With the pieces | Without (same engine) | Pairs bench said |
|---|---|---|---|
| Leopold's Applause + Fire Penetration I, Fireball Blood Mage | 3.76M | 4.17M | **-10%** | +16% |
| Maligaro's Virtuosity + Pinpoint Critical, Skeletal Sniper Lich | 232k | 217k | **+7%** | +42% |
**Both pairs fade in a full build**: once gear, tree and supports are optimised around the build, other pieces do as
well or better. The bench's numbers (a finished build with one slot swapped) overstate pairs. Lesson for the Breaker:
a lead counts only when its full build beats the plain full build; lead_builds.py is now that bar (both leads ->
dead in leads.json). Leopold's below-0 penetration is still a real mechanic (confirmed), just not a break here.

### Patch-notes mode, step 1: applying number changes (2026-11-22, task 31)
Patch day before PoB updates needs our own way to put the notes' numbers into the game data. New runner commands:
`patch_gem` (a gem's constant stats, a per-level stat scaled, or its damage multiplier scaled, in PoB's loaded data)
and `patch_reset` (puts every change back). Test: Earthquake's damage multiplier x1.5 -> DPS x1.5, reset exact.
Plan for the rest:
1. A changes file per patch (data/patches/<patch>.json): one entry per note line that changes a number:
   {"gem": "Earthquake", "base_multiplier": 1.2, "note": "Earthquake deals 20% more damage"}; uniques as old -> new
   lines; passives later. Claude reads the notes and writes it (the notes are prose; every entry keeps its line).
2. `breaker_day.sh PATCH=<file>`: every scan runs with the changes applied (a scan reads the file and sends
   patch_gem before measuring), so the day run scans the patched game before PoB has it.
3. Practice on a past patch: PoB at a commit before that patch's data update (setup.sh POB_REF) = the old game;
   our changes file from its notes = our patched game; PoB after the update = the real patched game. Compare
   (a) our patched numbers with PoB's real ones (did we read the notes right), and (b) what our scans called
   broken / nerfed with what that patch's ladder played. Needs: the PoB commit around a patch, that patch's notes.
**Step 2 (2026-11-22):** `pob.apply_patch_file`: with PATCH_FILE set, every PoB process starts with the changes
file applied, so any tool runs on the patched game unchanged; `PATCH=engine/data/patches/<file>.json
engine/tools/breaker_day.sh` does the whole day run that way. Format: data/patches/example.json. Left: unique and
passive changes in the file, and the practice run on a past patch (step 3).
