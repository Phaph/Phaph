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
