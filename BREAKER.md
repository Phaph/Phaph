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
**Unique changes (2026-11-22):** `patch_unique` (a unique's line replaced, removed or added in PoB's unique database;
undone by patch_reset), used by PATCH_FILE entries {"unique": ..., "replace": [[old, new]], "add": [...]}. Test:
Leopold's Applause "-50%" -> "-30%" and back. Passive-tree changes are still to do.

### Combo leads in full builds: a pipeline problem first (2026-11-22, task 30 -> 33)
Armour Piercing Rounds breaking its own armour (Tactician), full Uber Endgame: the combo build's note says 2.39M with
the combo vs 1.79M for APR alone in that build (+34%: the combo itself works), but the plain build is 3.92M. The
combo build is ~2x weaker before the combo, so the combo path changes the build somewhere (task 33). A first cause
fixed on the way: score_combo used PoB's raw numbers, without the setups / extra stat sets the plain boss number gets
(Bonestorm's explosion), now scaled the same. Combo leads stay unconfirmed until 33 is done.
**Cause found (2026-11-22, task 33):** not the combo path, the plain build. auto_config turned on "enemy Armour
Broken" for ANY build that breaks armour on hit, as if the boss were always Fully Broken (no time to break). So the
plain APR Tactician (3.92M) had the Armour Broken bonus free; the combo build measured APR unbroken (1.79M) and
modelled the real break (2.39M). Fixed in runner.lua auto_config: Armour Broken only when the build fully breaks the
boss's armour in <= 1.33 s (Fully Broken 90% of the time, the ailment rule's bar), with the break time in its reason.
Every armour-breaking build's boss number changes with this; the combo leads get re-run on it.

### Blind test on engine 2026-11-21.5 (stage rules only) (2026-11-22)
data/breaker/blind_2026-11-21.5.txt: still 3/20 (Comet, Ice Shot, Rend), Spearman +0.19. The stage rule made
**Bonestorm #1 on all 7 Witch/Sorceress ascendancies** (5-12M vs ~1-1.7M next), at 0.85% of the ladder. Checked: PoB
and the guides agree (up to 20 spikes per channel, each its own hit + small impact explosion, extra projectiles charge
it faster, channel to full on bosses), so it's a lead, not a plain bug: leads.json "Bonestorm at full channel".
Open: how many of the 20 spikes hit one boss, and whether the explosion needs Power Charges. This run predates
partners, minion counts, Oil Barrage, infusions, extra stat sets, exposure and the armour fix: the full re-run on
all of them is next in the queue.
**More change types (2026-11-22):** patch_gem `level` (a per-level field such as critChance or cooldown set at every
level), `require_types` (what a support may support: "no longer restricted to Attacks"), and `id` (PoB's skill id,
for a triggered part such as a curse's shockwave). For the 0.5.1 practice: Repulsion's wave base crit 6%, the three
Attunements and Ice Bite I no longer attack-only.

### Patch-notes practice on 0.5.1 (2026-11-22, task 31 step 3)
PoB v0.18.0 (before 0.5.1) and v0.19.0 ("Update skills with 0.5.1 changes") fetched to ~/pob_versions/ (LuaJIT from
our image; `POB_VENDOR=...` runs the engine on either; our runner works on both). Changes file written from the notes
alone (poe2db.tw/Version_0.5.1), before looking at PoB's update: data/patches/0_5_1.json.
- **Read right: 2 of 2 number changes** match PoB's update exactly (Conductive Runes base crit 7%, Repulsion's
  triggered wave 6%, at every gem level; v0.18 had none). DPS can't show it here: both are attacks that use the
  weapon's crit in PoB, in v0.19 as well.
- **Not expressible yet: 16 of the 18 gem / item lines.** Most balance notes add or reword stats rather than change a
  number: "no longer limited to Attacks; now Gain 25% of Damage as Extra Cold" (Attunements, Ice Bite, Innervate),
  "20% more Area of Effect" (Stampede), rules (Refutation's cooldown), ascendancy and unique rewrites.
**Next for patch day:** (1) an "add stat" change (a gem stat by its PoB name, e.g. gain-as-extra, appended to a stat
set), (2) unique lines are already text (patch_unique works), (3) ascendancy/keystone text via the tree (passive
changes), (4) practise on a bigger numeric patch (0.4 -> 0.5 skill reworks) once those exist. Ladder check still
needs poe.ninja from the PC.
**Combo leads re-run (2026-11-22, after the Armour Broken fix):** APR breaking its own armour: combo 3.50M vs plain
3.47M (+1%: dead, the plain build breaks fast enough itself). Coiling Bolts breaking armour for Bonestorm (Lich):
9.78M vs 8.82M (+11%: real, small). Dark Effigy + poison still needs ailment combos in the guide.
**Add / remove / rename stats (2026-11-22):** patch_gem `add` {stat: value}, `remove` [stat], `rename` {old: new}
(flags a stat PoB has no mapping for). PoB's own 0.5.1 update for the Attunements was: Damage added to what they
support, and the gain stat renamed from "..._gain_as_cold_with_attacks" to "..._gain_as_cold". With those in
0_5_1.json, **Fireball + Cold Attunement on v0.18.0 + our file = 57 DPS, exactly PoB v0.19.0's 57** (75 unpatched:
the support didn't apply to spells). So 5 of the 18 lines are now reproduced exactly; next: Ice Bite / Innervate's
timed gain-as buffs, Stampede's area, passive/ascendancy changes.
**Grading tool (2026-11-22):** `tools/patch_check.py` (runner gem_dump): per gem in a changes file, its supported
skill types, constant stats, crit / cooldown / damage multiplier, in the patched old PoB vs the real new one.
0.5.1: **8 of 8 gems match PoB v0.19.0 exactly** with our file (0 of 8 unpatched, so the check sees differences).
Covered: Conductive Runes, Repulsion's wave, the 3 Attunements, Ice Bite I/II, Innervate. Not covered: Stampede's
area (not in PoB's update either), Refutation's cooldown rule, ascendancy/unique/rune rewrites. Honest note: only the
2 crit lines were written blind; the other 6 were added after seeing what change types were missing (their content
is from the notes, but the stat names came from knowing PoB's update). Next practice must be fully blind.
**Passive changes (2026-11-22):** `patch_node` (a notable / ascendancy passive's lines reworded or added by name,
re-parsed as PoB does on load; PATCH_FILE entries {"passive": ..., "replace": [[old, new]], "add": [...]}). Test:
Forbidden Path "5% reduced maximum Life" -> 50%: Life 890 -> 490, reset 890. Keystones apply through PoB's keystone
table, so rewording a keystone isn't covered yet. Next: a fully blind practice on 0.5.2 (PoB v0.20.0 -> v0.21.0,
passive tree changes only).

### Blind practice on 0.5.2 (2026-11-22)
Written from the notes (poe2db.tw/Version_0.5.2) and the BEFORE game only (PoB v0.20.0), without looking at PoB's
update: data/patches/0_5_2.json. Graded against PoB v0.21.0 ("Add 0.5.2 Passive tree changes"):
**2 of 2 passive changes match** (Ice Storm, Lightning Storm: the removed "Unaffected by ... Ground" line and both
new lines; only the line order and one letter's case differ). Not expressible: Zarokh's Gift's socket type, base item
defences (Runemastered bases). 0.5.2 had no skill number changes.
**Patch-notes mode, where it stands:** gem numbers, per-level fields, stats added / removed / renamed, what a support
may support, unique lines, passive nodes: all apply before PoB updates (PATCH_FILE, breaker_day.sh PATCH=), graded on
two real patches (0.5.1: 8/8 gems; 0.5.2: 2/2 nodes, blind). Not yet: keystones (PoB's keystone table), sockets and
base item numbers, rule changes ("cooldown no longer recovers while..."), and the ladder side of the practice (did
our scans call the right builds broken / nerfed: needs poe.ninja history from the PC).
**Bonestorm lead, evidence (2026-11-22):** all 20 spikes can hit one big boss (Mobalytics: "can all Shotgun and hit
the same target"; guides: channel to full on bosses, less on small targets); the impact explosion is on every spike
(PoB data: own base damage; Power Charges only add area). Nothing checkable without the game contradicts PoB:
Bonestorm Lich, full Uber Endgame, 8.8M boss DPS (9.8M with Coiling Bolts breaking armour), 0.85% of the ladder.

### The full-build bar, all leads so far (2026-11-22, tasks 16 and 30)
| Lead | Detector said | Full build vs plain (same engine) |
|---|---|---|
| Leopold's Applause + Fire Penetration I | +16% (pairs) | -10% |
| Maligaro's Virtuosity + Pinpoint Critical | +42% (pairs) | +7% |
| Armour Piercing Rounds breaking its own armour | +42% (combo finder) | +1% |
| Coiling Bolts breaks armour for Bonestorm | +23% (combo finder) | +11% |
| Frost Darts poisons for Dark Effigy | +69% (combo finder) | +1% (+15% inside the combo build) |
**Pattern: every interaction lead shrinks to 0-11% once a full build is optimised around it.** The detectors
measure on round-1 builds (no tree, crafted gear, one swap), where any interaction looks big; a finished build
gets most of it another way. Use for the Breaker: the detectors find candidates, lead_builds.py is the filter, and
only a full-build win counts. The one lead that survives as big is a skill, not an interaction: Bonestorm at full
channel (the strongest caster in full builds, 0.85% of the ladder).

### Temporary minions (2026-11-22)
The full blind re-run's first Witch results put **Unearth** and **Wardbound Minions** at #2-4 behind Bonestorm. Both
are temporary minions (Unearth's Bone Constructs come from corpses, which a boss leaves none of; Wardbound Minions
from spent Runic Ward), and the minion-count fix counted them at their full limit. Now only persistent minions
(SkillType Persistent: Wolf Pack, skeletons...) are counted at their limit (runner sync_minion_counts
persistent_only, used by the search and the guide); temporary ones stay at one. Engine 2026-11-21.12. The running
blind re-run predates this: read its Unearth / Wardbound ranks as over-rated.

### Skill leads through the full-build bar (2026-11-22, task 34)
Full Uber Endgame builds, same engine, our pick vs the skill the ladder plays on that ascendancy:
| Ascendancy | Our pick | Popular skill | Result |
|---|---|---|---|
| Lich | Bonestorm 8.82M | Comet 4.45M | **2.0x: holds** (lead stays) |
| Deadeye | Rain of Arrows 657k | Ice Shot 1.15M | **-43%: dead** |
| Amazon | Wind Serpent's Fury 1.50M | Lightning Spear 1.69M | **-11%: dead** |
Rain of Arrows and Wind Serpent's Fury show the search can rank skills in a different order than full builds do
(task 35: tools/rank_check.py measures how often, on 6 ascendancies).

### Full blind re-run on engine 2026-11-21.11 (2026-11-22, all fixes from 11-21/22)
data/breaker/blind.txt. **Still 3/20 of the ladder's top skills in some top 5** (Comet #4 Stormweaver, Ice Shot #3
Deadeye, Rend #4 Oracle); Spearman **+0.01** (was +0.25 / +0.19). What changed:
- **Bonestorm now tops all 7 Witch/Sorceress ascendancies at 9.5-22M**, 7-15x every other class's best (its
  explosion counted on top of the full channel). That alone wrecks the ascendancy order (Spearman): our scores say
  "play a caster", the ladder spreads over everything. It is our strongest lead and it passed the full-build bar
  (2x Comet), but such a gap also says: re-check Bonestorm's per-spike numbers before trusting the size.
- Titan / Smith / Warbringer: Supercharged Slam #1 (full stages + aftershock), Earthquake #2 on Titan.
- Oracle / Shaman: Oil Barrage gone (power-charge limit), Flame Breath #1. Engine is deterministic: unchanged
  classes (Mercenary, Monk, Huntress) reproduce their earlier scores exactly.
- Unearth #2 on Infernalist: this run predates the persistent-minion fix (12): over-rated here.
**Why recall stays 3/20:** the misses are the same groups as before: setup skills listed as "main" (Frost Bomb, Frost
Wall, Orb of Storms, Verisium, Oil Grenade), Druid (Tornado, Entangle, Wolf Pack score low on their own), Huntress'
Whirling Slash / Twister (the combo helps only +23%), and plain spells behind Bonestorm. And ranking itself is off
for full builds (task 35: the search's #1 is the best full build on 1 of 3 ascendancies checked so far).
So the blind test now measures two things we know are wrong in different ways: our model's view of strength, and
the ladder's mix of strength, mapping comfort, gear access and fashion. Next: finish rank_check (35) and decide the
decider round; then re-run the blind test once more on engine 2026-11-21.12+.

### Per-ascendancy truth from poe.ninja (2026-11-22, via Kyle's laptop)
engine/data/meta_pairs.json: Forbidden Rites, each ascendancy's share of characters using each skill (any skill, so
buffs and heralds appear too). The blind run on 21.11 finds **7 of 69** of each ascendancy's top 3 in its top 5
(10%). The main reason is the class-weapon rule (Kyle 2026-11-18: classes keep to their intended weapons unless
Off-meta): the ladder plays across classes everywhere: Titan/Smith on shields (Shield Wall, Earthshatter),
Warbringer on grenades (crossbow), Gemling on Whirling Slash/Twister (spear), Martial Artist on Rend/Devour
(talisman), Acolyte on Poisonburst/Vine Arrow (bow), Ritualist/Oracle/Shaman on Spark/Comet/Frostbolt (spells),
Abyssal Lich on Entangle/Thunderstorm, Tactician and Disciple on Wolf Pack. Also: **Bonestorm is used by 36% of
Abyssal Liches** (overall 0.85%): the lead is a known build on that ascendancy, so not a new break there.
Running: the blind test with the class lock off (`blind_test.py run --unlock`, not Off-meta, which would bring in
poe.ninja popularity), ~12 h -> data/breaker/blind_unlocked.txt.
**Lodestone has no class-weapon rule (Kyle, 2026-11-22):** that rule is Whetstone's only (guides that suit the
class). Removed from the per-ascendancy condition and matrix scans, the blind test (any weapon is now the default;
`--class-weapons` tests Whetstone's rule) and lead_builds' combo lookup. The 11-20 per-ascendancy scans skipped
skills outside each class's weapons: re-run queued as task 37.

### Light vs full Uber builds for the endgame pick (2026-11-22, task 36a)
rank_check --light (one tree pass, no jewels, no boss-support search) vs the full Uber builds, same finalists:
| Ascendancy | Full builds' winner | Light builds' winner |
|---|---|---|
| Deadeye | Ice Shot 1.15M | Ice Shot 506k: same |
| Titan | Supercharged Slam 5.67M | Supercharged Slam 2.12M: same |
| Amazon | Fangs of Frost 2.20M | Lightning Spear 924k (Fangs 689k): **different** |
| Tactician | Rapid Shot 6.30M | Plasma Blast 439k (Rapid Shot 242k): **different** |
| Martial Artist | Killing Palm | Siphoning Strike: **different** |
| Oracle | Flame Breath | (Oil Barrage's numbers predate its fix) |
A light build misses what makes some skills strong at endgame (jewels, boss supports, the deep tree): it picks the
wrong winner on 3 of 5. **The endgame pick uses full Uber builds** (generate.ENDGAME_LIGHT = False); to save time
the winner's Uber stage should be reused by the guide instead of being built again (next).

**Unlocked blind run, first ascendancies (2026-11-22 night):** with any weapon allowed, Bonestorm is #1 on Infernalist
AND on Titan, Warbringer and Smith of Kitava. A skill that wins every class by 7-15x while 0.85% of the ladder plays
it (36% of Abyssal Liches) is more likely over-rated by our model than a hidden break: the Bonestorm per-spike sanity
check is first tomorrow (spikes per channel vs projectiles, PoB's dpsMultiplier = stages, the explosion per spike,
and whether all spikes land on one boss).
**Bonestorm sanity check, step 1 (2026-11-22 night):** PoB's spike maths is consistent with the game rule (max 20
spikes; extra projectiles prepare more per channel tick): at 20 stages, 1 / 3 / 5 projectiles -> 20 / 7 / 4 ticks of
0.125 s -> 0.40 / 1.14 / 2.00 releases a second, DPS 262 / 749 / 1,311 on a bare build: no double counting. **The
suspect is time PoB doesn't count:** the release. PoB's use time is the channel ticks only (5 projectiles: a 20-spike
volley every 0.5 s), but the gem has a release animation (skill_animation_duration_multiplier_override 6) and a 300 ms
minimum channel. If a release takes ~0.5 s in game, PoB over-rates Bonestorm ~2x. Next: the real release time
(guides / videos / PoB issues), then a USAGE_LIMITS rule like Rain of Arrows'.
**Step 2:** no PoB issue found, but a build author on PoB Archives warns "POB does not calculate bonestorm DPS
correctly" (pobarchives.com/build/CXHUyphJ). Planned rule (tomorrow, after tonight's deploy): USAGE_LIMITS Bonestorm,
each release adds the release animation (skill_animation_duration_multiplier_override 6 x the 0.125 s base cast =
0.75 s, scaled by cast speed): releases/s = 1 / (1 / HitSpeed + 6 / Speed). 5 projectiles: x0.40; 1 projectile: x0.77.
**Step 3 (2026-11-23):** done: USAGE_LIMITS Bonestorm (releases/s = 1 / (1 / HitSpeed + 6 / Speed)), test in
tests/test_usage_limits.py; engine 2026-11-23.1. Re-check its lead build vs Comet and the unlocked blind rows after.
**Keystones in patch-notes mode work (2026-11-23):** patch_node changes a keystone's lines in the tree node and
PoB's keystone table (the same node), and its parsed mods follow (runner `node_debug`). The earlier "Chaos
Inoculation stays at 1 Life" was the test case: PoB also turns its other line into a ChaosInoculation flag that sets
Life to 1 elsewhere. Left for patch day: socket types, base item numbers, rule changes.
**Bonestorm result (2026-11-23):** with the release time counted, full Uber Endgame Bonestorm Lich 2.72M vs Comet Lich
4.45M (**-39%**; was 8.82M, 2x Comet). The lead was PoB's uncounted release: status "fixed" (a modelling gap). Even
at half our release estimate it stays behind Comet. **Lodestone has no standing break now**: every lead so far was a
modelling gap (fixed) or an interaction that fades in a full build. That is the honest state before 1.0: the tools
are sharper (and the search finds what it should), the broken builds will have to come from 1.0's changes.
**Base items in patch-notes mode (2026-11-23):** runner `patch_base` (a base's armour / weapon / req / flask / charm
numbers in PoB's data; new items use them; patch_reset puts them back), PATCH_FILE entries {"base": ..., "armour":
{...}}. Covers 0.5.2's Runemastered base changes. Left: socket types, rule changes.
**Bonestorm, corrected (2026-11-23):** the -39% compared Bonestorm on a Wand with Comet on a Staff (my mistake in the
lead's spec). Both on a Staff, release time counted: **Bonestorm Lich 6.03M vs Comet Lich 4.45M (+35%)** at Uber
Endgame. A moderate lead again (unconfirmed): it rests on the release estimate (6 casts per volley) and on 20 spikes
landing on one boss. The search still rates it 5-6x Comet at every step (round 1, with tree, mid or end gear), so
the search over-rates it vs full builds; the endgame pick corrects that for players. Also checked: scoring round 1
at end-stage gear gives the same order as mid-stage, and today's round 1 picks the full-build winner on 4 of 6.

### Blind test with no class-weapon rule (2026-11-23, engine 2026-11-23.1)
data/breaker/blind_unlocked.txt. **Bonestorm #1 on all 23 ascendancies; every top 5 is the same staff spells**
(Bonestorm, Coiling Bolts, Comet 23/23, Fireball 20, Firestorm 17). 1/20 of the ladder's top skills, 5/69 per
ascendancy, Spearman +0.20. Full builds don't agree: at Uber Endgame Bonestorm Lich 6.0M, Supercharged Slam Titan
5.7M, Rapid Shot Tactician 6.3M are level, while the search scores Witch spells ~10x the Titan's best. So the
search's scores aren't comparable across weapon kinds: staff spells over-rated, attacks under-rated. With
Whetstone's class weapons it matters less (each class compares like with like); for Lodestone (any class, any
weapon) it buries every attack build. Being measured: search-style scores vs full builds per skill kind (task 38).
**Measured (task 38):** search-style boss estimate (end gear, quick tree) vs the full Uber build: Bonestorm 11.0M vs
6.03M (x1.83), Supercharged Slam 4.07M vs 5.67M (x0.72), Rapid Shot 2.56M vs 6.30M (x0.41). The error is per skill
(gear, jewels, boss supports, Fresh Clip...: what only the full build has), a 4.5x spread, so no single weapon-kind
factor fixes it. Whetstone: the endgame pick (top 3 by full builds) covers it. **Lodestone plan:** shortlist the best
~2 skills per weapon type by search score, then rank the finalists by full Uber builds (rank_check-style); weekly,
on the server's free time or the PC.

### First cross-class finalist, and a free PoB bonus (2026-11-23, task 38 trial)
Crossbow finalists (weapon_finalists.py, no class rule): the search picks **Acolyte of Chayula** as Rapid Shot's best
ascendancy; full Uber build 9.26M boss DPS. Checked: PoB's config defaults Acolyte's Purple Flames to 10 stacks
(Into the Breach), and nothing of ours touched it: 12.0M with 10 flames, **7.02M with 0** (x1.7 free). auto_config now
sets them to 0 for every build (only bonuses a build keeps up itself); engine 2026-11-23.2. Even at 0 flames Rapid
Shot Acolyte beats Rapid Shot Tactician (6.30M): a lead (unconfirmed), 0.1% of Acolytes play it.

### Player build time with the endgame pick (2026-11-23)
One real request through the live API, server otherwise idle (fire Infernalist, all 7 stages): **76 min** (search +
endgame pick 41 min, leveling plan + 7 stages 35 min); before the endgame pick ~25-45 min. The pick changed the
answer again (Firestorm 8.1M / 7.1M map over the search's #1 Fireball 6.0M / 2.7M). The nightly sweep's 45-min limit
killed every build: raised to 2 h. Found on the way: the leveling filter compared all tags, not damage types
("Spell" in common let physical Bonestorm level a fire Firestorm build): fixed, engine 2026-11-23.3.
**Finalists run, first weapons (2026-11-23):** Bow -> Poisonburst Arrow / Rain of Arrows, both on Invoker (1.78M /
1.25M boss); Crossbow (redone after the Purple Flames fix) -> Rapid Shot on Deadeye 5.32M: the Acolyte lead was the
free flames (status fixed). Caution for the ranking: finalists take the search's ascendancy, which can be off too
(Poisonburst Arrow on Deadeye reached 2.57M in today's player-build test vs 1.78M on Invoker here).

### More free PoB defaults (2026-11-23)
After Purple Flames, the other config defaults that hand out bonuses: **Inexorable Critical's "seconds since crit"
defaults to 10** (always at its +100% crit chance cap); it resets on every crit, so a build that crits often barely
builds it. auto_config now sets it from the build's own time between crits (min(10, 1 / (crit chance x hits/s)),
refined once), with the reason listed. Many searched builds pick Inexorable Critical I, so crit builds were
over-rated. Checked and harmless: Flicker Strike "Bypass CD" (no cooldown in PoE 2 data). Others are skill-specific
and only if used (Demon Form stacks, Glorious Madness, Corrupting Cry stacks). Engine 2026-11-23.4; the finalists
run restarts on it.
**Invoker (2026-11-23):** the no-class-rule search keeps picking Invoker for bows, crossbows and spears: its crits ignore
non-negative elemental resistances ("Sunder my Enemies...") + 10% extra lightning / cold. Guides confirm it, and
players already run crossbow and bow Invokers (Mobalytics). **Lodestone rediscovered a known cross-class build
blind**: status "known". A good sign for the no-class-rule search; not a new break.

### Full DPS added up skills that are never used together (2026-11-23, engine 2026-11-23.5)
Found while checking score_combo's setup DPS. `full_dps_all` (run by every build through optimise_spirit) put *every*
skill group in Full DPS: the weapon's own basic attack (Mace Strike, Bow Shot, Spear Stab + Spear Throw; kit_out even
gave it supports), the boss skill, the clear skill, the combo setup, and the spells in a Cast on X gem as if cast by
hand. Saved Uber builds, old total -> main skill + what really works alongside (same gear; not re-optimised):
APR Tactician 4.69M -> 3.11M, Rain of Arrows Deadeye 257k -> 69k, Wind Serpent's Fury Amazon 1.66M -> 848k, Leopold's
Fireball 1.13M -> 291k, Coiling Bolts / Bonestorm 3.43M -> 2.07M, Dark Effigy 1.06M -> 802k, Bonestorm 2.56M -> 2.36M,
minion Lich unchanged. Only Rain of Arrows and Wind Serpent's Fury were measured on the final fix, the rest on its
first version: re-measure. The boss / clear skill double count is read from the code, not measured. Cast on X spells
now count as 0 in the total, so some builds may read low. (These are mapping-config codes, so not the boss numbers quoted elsewhere.)
Fix (runner.lua `worksAlongside`, `setMainGroup`): Full DPS = the main skill + minions, totems, persistent skills
(heralds, once each) and item-triggered skills; changing the main skill moves the count with it.
What it puts in doubt: every attack vs spell comparison (Comet's Staff adds little, a spear adds two attacks),
rank_check, the endgame pick (not measured on the Deadeye pick itself; a Poisonburst Arrow *Invoker* finalist,
2.30M, had 1.76M from a second button, Rain of Arrows), all combo results (the payoff phase included the setup's damage; setup DPS was the whole
build), the trigger leads, and gear / tree choices made on the inflated total. **All earlier full-build numbers
(leads, "x0.41 to x1.83 per skill" in task 38) need a re-run before they are quoted.** Not checked yet: the search's
own rounds, where they call use_full_dps, and how much picks change.

### Where every total comes from; on-death explosions out (2026-11-24, engine 2026-11-24.1)
Every stage now keeps `sources` (map) and `boss_sources` from PoB's own Full DPS list (runner `dps_sources`; usage
limits taken off the main skill). On the 8 saved lead builds it sums to the total. The finalists report marks any
boss-fight source other than the main skill at 10%+. Its first catch: **Fiery Death** ("chance to explode on death") was
82% of the Maligaro's Skeletal Sniper Lich, four times over; on-death explosions (Fiery Death, Plague Burst) do no damage
now: 1.33M -> 168k. (So "minion Lich unchanged" above was right about the Full DPS fix, but its total was never real.)
**Skeletons counted as zero (found by the same list, bug since 2026-11-17):** skeleton skills have no limit stat (each
copy reserves spirit again), and sync_minion_counts set their count to the limit, 0: no damage and no spirit reserved.
Now the main skeleton skill gets as many as the spirit left over pays for, an extra one counts once (`fitCopies`). So
every earlier result that ranked or built a skeleton skill is wrong. Open: copies are taken before auras, not traded
against them; Dark Effigy's damage is listed as Vile Effusion; Combust (Infernal Cry) not checked.

### Grading on past patches: first result (2026-11-24, task 40)
Patch 0.1 (PoB v0.5.0) condition scan, all 119 skills, default thresholds: Lightning Conduit vs Shocked is row 1 of 35
(+500%; the next skill is +41%). The case was seen in a compatibility test first, so it is marked not blind. The same
threshold flags 35 rows over 26 skills, so unless most of the other 25 were also cut in 0.2 (not judged yet), the
proposed bar of one false alarm per real find fails for this detector at its default threshold. Not tuned.
tools/grade_old.py grades finished scans only; matrix (cases 1.3, 1.9) is running.

**False alarms on 0.1, judged (2026-11-24):** by PoB's data for 0.1 vs 0.2 (the official notes could not be read): of 26
flagged skills 6 were cut (Lightning Conduit's multiplier; 5 by base damage, one of those also lost its cooldown), 13 were
not, 7 can't be compared. **About 2 false alarms per real find, with a lenient definition of real: the detector fails the
1:1 bar at its default threshold.** Flagged skills were base-cut more often than unflagged ones (5 of 19 vs 7 of 82), but
that is small numbers and a base cut isn't about the flagged condition; on a strict reading only Lightning Conduit is a
proper find. A stricter threshold (+60% above usual) is written into the key before the 0.2-0.4 scans, as its own column.
Bow finalists: "Poisonburst Arrow Invoker" 1.75M boss is 97% its boss skill, Rain of Arrows (which as a main skill is 945k
in its own build); its map DPS (1.63M) is doubled by the extra stat sets on top of the 800k in `sources`.

### Extra stat sets counted too much (2026-11-24, engine 2026-11-24.2)
partners.apply_extra_sets added a skill's second part as the whole Full DPS of the build with that part on: (1) heralds and
minions were added again, for all 12 skills in EXTRA_SETS; (2) parts the game marks "no hit" (Poisonburst Arrow's burst,
Gas Grenade's cloud) were given the arrow's hit: on the saved Poisonburst Invoker x2.03 instead of x1.03 (map 1.63M ->
~0.83M). Now: the skill's own damage only; no-hit parts add their damage over time only. It is used in the search, the
guide and the endgame pick, so the Deadeye's Poisonburst Arrow pick (2.57M boss / 6.37M map, engine 2026-11-22.1) is
suspect. Open: Fireball's explosion and Supercharged Slam's aftershock show exactly the first part's numbers in PoB (x2);
whether both really land on one target rests on the gem text.

**Patches 0.1 and 0.2 so far (2026-11-24):** 0.1: 1 of 3 (Archmage, Gemling attributes missed: their pieces gained under 5%
on a plain build). 0.2 condition scan: Glacial Cascade vs Frozen missed; "Spearfield" counts as found by the key's literal
rule (row 58 of 65, +17% vs Armour Broken), but that is not its hidden multiplier: a right name for the wrong reason,
read it as a miss. The strict column on 0.2 flags Lightning Conduit (known) and four others (Raise Zombie, Skeletal Reaver, Skeletal
Sniper, Unearth, all vs Armour Broken), none of them in the key. stack_scan.py (piece x piled-up stat) was written
after the 0.1 misses; only the 0.3 cases test it.

**Retraction (2026-11-24 04:30):** the 0.1 matrix scan above was invalid. The old-PoB shim in runner set_custom_mods only
wrote the mod box on its first call, so no unique's mods were ever applied (keystones were: they go in as nodes). Archmage
and Gemling attributes were NOT tested; "1 of 3" is withdrawn, the graded score is Lightning Conduit only (0.1), plus the
0.2 condition cases. Condition scans don't use that box and stand; the live site (current PoB) was never affected. Fixed
(flag decided once); checked on v0.5.0, v0.12.2 and current. The stack scan's first smoke run (0 flagged) was the same bug.
0.1 and 0.2 matrix scans are being redone. The answer key and thresholds are unchanged.

**0.2 condition false alarms, judged (2026-11-24):** tools/old_skill_verdicts.py (PoB data, next patch; its cuts agree with the hand-made
0.1 verdicts on all 19 judged skills, Lightning Conduit by its printed multiplier). Of 39 flagged skills: 2 real (Frost
Bomb, base x0.51; Sunder, which lost its guaranteed crit vs broken armour), 25 not cut, 12 unjudged (minion skills and reworks).
Two patches now read 2 and 12 false alarms per real find against a bar
of 1: the default threshold is not usable as a "this will be nerfed" list. The strict column (+60%) on 0.2 flags only four besides
Lightning Conduit: Raise Zombie, Skeletal Reaver, Skeletal Sniper (unjudged) and Unearth (not cut), so 0 confirmed real.
Spearfield is not a real find either: the hidden multiplier went, but its base rose x4.16. Caveats: "not cut by the
next patch" is not "was not broken", and PoB data is not the notes. Matrix, stack and 0.3-0.4 scans still to come.

**0.1 stack scan (2026-11-24, not blind for 0.1):** 2 pieces flagged. Archmage with mana (+91% on Cold Snap) is a true find:
0.2 halved its lightning gain at gem level 20 (6% to 3% per 100 mana). Irongrasp with strength (+98%) was unchanged in 0.2: a
false alarm, though it is a strong piece. Gemling attributes missed (Pillar is a weapon, ascendancies are not scanned).
So 1 real per false alarm on 2 rows: too few to say more. 0.3 (Rathpith, Indigon, Hollow Palm) is the blind test.

### Off-hands are empty (2026-11-24, not fixed on main yet: task 41)
`craft_gear` fills Weapon 2 only when a spec names an off-hand, and the search names one only for skills that need a
shield, block builds and anchor off-hands. So bows have no quiver, wands and sceptres no focus, one-handed weapons
nothing. Checked: all finalists so far and all 8 saved lead builds have an empty Weapon 2. Bow, wand, sceptre and
one-handed numbers are therefore low against staves, crossbows and other two-handers; how much is being measured.
Staff Bonestorm's 6.99M vs wand 3.00M is not a fair comparison until then. (The x1.77 over its own source list is the
explosion added after the list, as designed.) Also: the Quarterstaff finalists search found nothing, because staff
spells filled the ranking before the filter.

**Off-hand measured (search-style, end gear, 2026-11-24, branch offhand):** Ice Shot bow +43%, Lightning Arrow bow +46%, Skyfall
wand +64%, Bonestorm wand +79% with a quiver / focus. Not full builds; a staff still gets its two-handed rolls.

**0.3 condition scan (task 40):** case 3.6 (Tactician vs Immobilised) missed: 0.3's PoB gave Siege Cascade / Siege Ballista no
gain vs an immobilised enemy at all (today's PoB doubles Siege Cascade), so the detector had nothing to read. False
alarms: 41 skills flagged, 1 real (Lightning Conduit, cut again 20 to 10, known), 34 not cut, 6 unjudged. Strict: Lightning Conduit, two skeletons
(unjudged) and Unearth (not cut). Three patches, same result: the condition scan on its own fails the bar.

**Off-hand, first full builds (2026-11-24):** Ice Shot Invoker 1.75M -> 2.56M boss (+46%, as the quick A/B). Rain of Arrows Invoker
945k -> 849k (-10%) although it now holds a quiver: the greedy gear / tree / supports took another route (Rearguard quiver,
Choir of the Storm, a crit-damage build with half the EHP, 6.2k vs 11.3k). So the full-build optimiser's own path luck is
at least ~10% in one step, probably more (it lost the quiver's gain as well): don't read single full-build differences
under ~20-30% as real (the +11% / -11% lead verdicts are inside that). Open: a second start (best of two gear orders), or
keeping the earlier build as a candidate, would show how much is left on the table.

**0.3 matrix scan (task 40, 2026-11-24):** 0 of 4 cases found. Two were never testable: The Whispering Ice is a weapon (known),
and Rathpith Globe is a focus, which breaker.UNIQUE_TYPES leaves out with shields and quivers (not noted in the key: the
key is wrong to call it matrix-calculable; the 3.2 case also lists Kaom's Heart, a body armour, which was in the catalogue
but has no row). Indigon and Hollow Palm gained under 5% on plain builds, as their stat isn't piled up there. 15 pieces
flagged: 0 cut by 0.4, 14 not, 1 unjudged (Maligaro's). Several flags are skills nobody builds damage on (Fortifying Cry,
Seismic Cry). The stack scan uses the same catalogue, so Rathpith can't be found there either; Indigon and Hollow Palm can.
Fix after the grade (a new column, not the main score): add Focus, Quiver and Shield uniques to the catalogue.

**Path luck, first result (task 42, 2026-11-24, run still going):** the same Rain of Arrows Invoker spec gives 849k boss as is and
3.46M with the gear slots crafted in reverse order (x4.1). One spec and one pair of orders, so the typical spread isn't known
yet; Rapid Shot, Ice Shot and Bonestorm have only their first order. Moving single items from the 3.46M build into the
849k build: quiver +104% damage (it wore Rearguard), amulet +36% (Choir of the Storm), ring 1 +25%, gloves +18%. Those
four also score higher on the gear score itself, so the optimiser's own rule prefers them: a unique is picked one slot
at a time and never checked again. All gear swapped: 520k -> 776k in the same boss config. So gear is the smaller part on its own;
the rest of the x4 is tree, gems and heralds built around that gear (not split yet). The bad build also ends at
66% elemental resistances (target 75): with 9 of 10 slots unique there is no rare left to fix them. The other direction (bad items into the good
build) wasn't measured: PoB exited after about a dozen load_xml calls in one process (cause unknown; restart it per slot).
Until the run is read: no full-build comparison between skills is safe to quote, not only those under 20-30%.

**Path luck, more orders (task 42, 13:30; 9 of 12 builds in):** boss damage by order: Rapid Shot 4.76M / 5.04M (+6%), Ice Shot 2.56M /
2.61M (+2%), Bonestorm 6.99M / 4.17M (-40%), Rain of Arrows 849k / 3.46M / 3.57M. No order is reliably the better one. Two are
small, two are large: it isn't a uniform ~10%.
**Bonestorm's gap isn't (mainly) uniques.** The two builds wear almost the same gear; mapping is 17% apart (3.86M / 3.30M), boss 68%.
Swapping gloves moves 13-17%, boots nothing, Demon Form nothing. The full boss support search on the saved builds gives 4.05M /
2.42M raw, so the gap is in the build (13 of 128 passives differ; not split further).
**Support search holds conditions fixed (task 44):** see NIGHT_TASKS.md.
**Filler supports reserved 76% of life (task 43, live bug):** fit_supports fills empty sockets without looking at toughness and put
Atziri's Communion (spirit skills reserve life instead) on Herald of Ash: EHP 12.6k -> 3.2k (Rapid Shot), 24.2k -> 7.8k (Ice Shot),
23.7k -> 6.5k (Rain of Arrows reversed), no damage of its own. 13 of 18 finalists and 7 of 9 path-luck builds hold it. Taking
it out leaves the build ~100 spirit over, so fit_spirit will turn a skill off: the damage after the fix may be lower and isn't measured.
**Rejected:** "the last mapping search re-uses a stale shortlist" (a full search gained 1-16% on 7 of 9 saved builds, nothing on
the 2 Bonestorms). Nearly all of it is Execute III, +30% on Low Life, which these builds only are because of Communion.

**Path luck, complete (task 42, 2026-11-24, engine 2026-11-24.3, 4 specs x 3 slot orders):** spread (best / worst boss damage - 1): Ice Shot
+5% (2.56M / 2.61M / 2.67M), Rapid Shot +22% (4.76M / 5.04M / 5.78M), Bonestorm +68% (6.99M / 4.17M / 4.41M), Rain of Arrows
+320% (849k / 3.46M / 3.57M). "as is" is the best order once and the worst order three times; no order wins everywhere.
4 hand-picked specs, so this is not an average over skills. The old lead rule ("under ~20-30% isn't real") is too lenient for at
least two of the four. A best-of-N start would have lifted Rapid Shot 22% and Rain of Arrows 320% over the default order,
Bonestorm 0%, Ice Shot 5%, at N times the build time.

**0.3 stack scan (task 40, 2026-11-24 15:00):** flagged one piece, Irongrasp on Bonestorm (strength), unchanged in 0.4: a false alarm (as in 0.1).
Testable cases: Indigon and Hollow Palm both missed; Rathpith was never in the catalogue. Stack scans so far (0.1, 0.3): 1 known case
found of 4 testable (Archmage; Gemling, Indigon, Hollow Palm missed), 2 false alarms (Irongrasp twice). Whole grade so far: 2 of 8
graded cases found (one not blind, the other at row 58 of 65), plus Archmage by the stack column, against a bar of half
found. 3 cases wait on scans (0.1 / 0.2 matrix). If all three hit that is 5 of 11 (below half), or 5 of 9 without the 2 untestable cases
(above half), so the hit half of the bar is still open. The false-alarm half isn't: at most one per real find was the bar, and the
condition scans alone stand at 9 real vs 72 false, the matrix at 0 vs 14. So the claim has to be narrowed as agreed.

**Grade, 0.1 matrix (task 40, 2026-11-24 17:05):** Archmage and Gemling attribute stacking both missed. Found so far 2 of 10 graded
cases (1.4 not blind; 2.2 at row 58 of 65); one case left (2.1). Best possible: 3 of 11, or 3 of 9 without the 2 cases the scans
can't test. That is below the agreed half, and false alarms were already over the bar, so the grade fails whatever 2.1 does. The stack
scan's Archmage is the only case found by more than a low-ranked row or a case we had already looked at (1.4). What the scans missed (Glacial Cascade vs Frozen, Indigon,
Hollow Palm, immobilise) is not explained here beyond the two untestable cases and the 0.3 PoB gaps noted above.

**Filler fix on full builds (task 43):** Ice Shot and Rain of Arrows rebuilt on 2026-11-24.4 with the same spec: boss and map damage unchanged
to the digit; EHP 7,758 -> 24,203 and 6,345 -> 7,853. Rapid Shot and Bonestorm still building.

**Off-hand finalists (task 41c, complete 2026-11-24 18:50, code of branch offhand = 2026-11-24.3 without the later fixes):** Unearth Sceptre 15.6M boss is
FALSE: 84% of it is 30 Bone Constructs, temporary minions made from corpses, counted at their limit. The persistent-only rule (2026-11-22) was
passed by the search and the guide's start but not by use_full_dps (which the guide calls later) or the spirit search, so live guides with Unearth (and
perhaps other temporary minions) were affected too. Fixed on branch `tempminions` (2026-11-24.6: the rule is the default). It also
means Unearth being picked over other Sceptre skills isn't established. Rows 2-12 are one slot order each (spread up to 320%, task 42), so no
ranking is quoted. Earthquake's 9.7M boss vs 0.7M in its sources is by design: the Aftershock is added after the list.
No other finalist counts more than one minion except Wolf Pack (7, persistent).

**Grade complete (task 40, 2026-11-24 20:05):** 0.2 matrix done: 2.1 missed as the key expected (weapon uniques aren't scanned). Final: **2 of 11 found**
(1.4 not blind; 2.2 at row 58 of 65), or 2 of 9 without the 2 cases the scans can't test (2.1 is one more the key itself expected to miss). The
stack column adds Archmage. The 0.2 matrix flagged 38 pieces: 2 real (Crown of Eyes 150% -> 100%, Maligaro's Virtuosity 300% -> 250%, both cut in 0.3), 35 false, 1
unjudged (Hyrri's Ire, reworked). Condition and matrix scans together, 0.1-0.3: 11 real vs 129 false: about 12 false alarms per real find (bar: 1). The
claim on the page was narrowed the same day. Caveats: "unchanged" is PoB's text, "real" is lenient (a cut, not proof of why).

**Armour Broken combos on engine 2026-11-24.8 (replaces Nov 18):** 166 skills, 32 payoffs (was 30). Best edges: Wolf Pack + Rampage +49%, Skeletal Reaver + Whirlwind
Lance +45%, Armour Piercing Rounds itself +42%, Armour Breaker itself +41%, Skeletal Sniper + Vaulting Impact +35%, Unearth + Rend +30%. Minion
rows are new since minions are counted at their limit; they assume the player's setup skill leaves the minions' own damage out while breaking (conservative)
and that the break time estimate holds. Quick round-1 builds: no full-build check on any of them (Armour Piercing Rounds was +1% as a full build).
**Best of 3 orders (42):** Sceptre: Unearth 2.75M / 5.47M / 5.06M, Skyfall 2.95M / 2.98M / 2.90M. Unearth's own hits are 4% of its boss damage (ignite 65%, Skyfall 30%);
the finalists report now flags builds whose skill deals under half.

**Path luck on 2026-11-24.7 (task 42, complete, 12 of 12; path_luck_7.json):** spread Ice Shot 5%, Rapid Shot 22%, Rain of Arrows 39%, Bonestorm 50% (before the re-check: 5 / 22 /
320 / 68). Every boss number equals AB3's (2026-11-24.3 base), so .4 to .6 moved no boss damage on these 4 specs. Best of 3 over the default order: Ice Shot +5%, Rapid Shot
+22%, Rain of Arrows +39%, Bonestorm 0%: 4 hand-picked specs, at 3x the Uber stage's time. Still over the 10% bar for 3 of 4: a lead needs best-of-3 on both sides
(finalists do this; lead_builds.py doesn't yet).

**Lead re-run, single order (2026-11-24.8, stopped after 2):** Leopold's + Fire Penetration 1.38M vs 1.40M without (-1%: stays dead). Dark Effigy + Frost Darts 834k vs
591k plain (+41%; it was +1% on 2026-11-22, and both numbers fell). One order per side can't judge it. Re-run with 3 orders per side: lead_builds_orders.

**Ailment combos on 2026-11-24.8:** as on Nov 19: Dark Effigy + Frost Darts poison +72% (was +69%), Flame Breath +3% (+6%), Lightning Conduit no combo. Full-build check running.

**Launch-day rehearsal (task 40, 2026-11-25):** `breaker_day.sh` with PATCH=0_5_2.json: 24 min 14 s (1,454 s) on 6 of 8 cores, with the lead re-run on 3 others: text scan and diff
under 10 s, condition scan (166 skills, 0 errors) nearly all the rest. It did NOT test detection: this PoB (0.23.1) already has 0.5.2, and the file's lines were added a second time
to Ice Storm and Lightning Storm. A made-up patch then showed a real gap: a patched passive never reached the text diff (it read the tree file on disk). Fixed, with tests: passives
show in the diff; a line the game already has is reported "already there" and not added; uniques sharing a name (Grand Spectrum) are all read (the scan was random there,
so a diff could show false news); SUMMARY.md lists the changes applied; the run no longer stops at `git pull` with uncommitted files. Not tested: notes -> changes file (Claude's
part), and the ~12 h blind search. Still missing: a gem's number change shows nowhere but the raw dps, and conditions.json's dps is from Nov 18 (87 of 166 moved over 2%).

**Launch-day detection test (task 45, 2026-11-25):** a made-up patch (Earthquake +20%, a line on Leopold's Applause, a line on Ice Storm) through the whole breaker_day.sh, both games
scanned with the same engine code: all three shown, nothing else (text diff 2 lines; damage diff 1 of 158 skills, Earthquake 24,736 -> 29,682). 8 of 166 skills have no damage
to compare. One easy patch: no new skills, no changes smaller than 5%, and the two lines were worded to match a text rule. Runtime with a stale baseline: 86 min on 3 cores (two scans).
conditions.json is now this run's unpatched scan (it was Nov 18), so a same-code patch run needs only one scan. Keystones: 32 of 33 change the numbers when patched (Chaos Inoculation
pins life at 1). 87 of 158 skills moved 5%+ since the Nov 18 scan (Flameblast x11.4, Bonestorm x6.9,
Wolf Pack x4.9): the old scan has no engine or PoB stamp, so the causes aren't known; not checked yet (task 46).

**Why the condition baseline moved since Nov 18 (task 46, 2026-11-25):** 18 skills (top 15 movers + Arc, Spark, Ice Shot) re-scored on the last engine of each day Nov 18-24, today's
PoB: all 18 equal the Nov 18 file on the Nov 18 engine, and Nov 24 equals the fresh baseline, so these 18 moves are ours, not PoB's. By change:
- Nov 21 full stages (c0b0214): Flameblast 7.7k -> 41k, Bonestorm 28.7k -> 156k (landed the same day; not split by commit). Nov 23 release limit: Bonestorm -> 83k (other Nov 23 fixes not split out).
- Nov 21 minions counted: Wolf Pack 3.5k -> 12.0k, Unearth 7k -> 97.6k (the temporary-minion error, gone on the 22nd).
- 6f1e272 on-death explosions out: Wolf Pack 12.0k -> 17.2k: the search stopped picking Fiery Death and took Brutality / Heft (likely it had misled the search; not tested).
- c3c2541 skeleton copies: Skeletal Reaver 316 -> 8,345.
- 390aa1e off-hands (41): Bonestorm 83k -> 199k, Unearth 6.4k -> 23.4k. On today's engine, emptying Weapon 2 of the finished build: focus x2.1-2.6 (Unearth x3.5), quiver x1.8, second mace x2.4-2.8.
  That is larger than the +64-79% / +43-46% of task 41's A/B: not reconciled (removal from a finished build is not a rebuild; the supports and the weapon's affixes suit the off-hand).
- The other mace / spell movers jumped on Nov 24 too; only 11 skills had the removal test.
Flameblast: PoB times it by cooldown only (Atziri's Impatience halves it: x2, and its 25% life cost isn't counted); up to ~x1.6 high if the cooldown starts on release (unknown).
Dual-wield slams: PoB hits with both weapons, each -30% (the -30% is the game's stat), so two bare maces are x1.3-1.4. That both hit one boss is PoB's reading, unchecked.
Not a ranking bug found; the remaining open point is Flameblast's cycle.

**Web check (2026-11-25):** dual wield: the wiki's mace skill list and Game8 (search snippets, pages not read) say "While Dual Wielding, both weapons hit with 30% less damage" for Rolling Slam,
the same -30% for Earthquake: PoB's reading fits; Sunder's own line not found. Flameblast: 10 s cooldown (15 s before 0.4) confirmed, no source says whether it starts on use or
release: stays open, no usage limit added.
