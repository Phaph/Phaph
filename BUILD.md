# Shadow: Dual Wield Dagger Bleed (PoE 2 1.0, day one)

Status: **pre-launch draft v0.1** (Nov 14, 2026). 1.0 launches Dec 11, 2026.
Everything below is from ExileCon coverage. Nothing is final until the patch notes and gem data are out.

## Target
- Class: Shadow. Melee, dual wield daggers, bleed (crit bleed if the numbers support it).
- Goal: highest sustained DPS for endgame mapping, with enough tankiness to farm high-tier maps.
- Benchmark: compare against the best bleed builds on other classes, not just other Shadow builds.

## What's known so far
| Topic | What we know | Confidence |
|---|---|---|
| Release | 1.0, Dec 11, 2026. Shadow and Duelist are new classes. | Confirmed |
| Shadow | Dex/Int hybrid. Daggers and traps. | Confirmed |
| Ascendancies | Assassin and Infiltrator. Node lists not public. | Names confirmed |
| Stealth | You see enemy vision cones. Hitting from outside them gives large bonuses. | Shown at ExileCon |
| Darkness | Resource built in stealth. Buffs damage when you leave stealth. Numbers unknown. | Shown, vague |
| Shroud | Shadow skill. Dash, needs a dagger in the offhand. | One source |
| Dagger skills | New dagger gems and supports. Ethereal Knives and Blade Vortex return. Full list not public. | Partial |
| Daggers | Hits impale enemies with daggers that can be ripped out for extra effects. | One source |
| Dual wield | ExileCon Q&A: dual wield penalties changed for a number of skills. No numbers. | Unconfirmed |
| Bleed | Listed among reworked mechanics. One unofficial claim of 8s duration and 30% per tick. | Rework confirmed, numbers not |
| Duelist bleed | Blood Stance, Bloodied Blade, Haemorrhage (compresses bleed, causes Blood Loss), Rending Dash. | Shown at ExileCon |

## Build directions to test on day one
1. **Crit bleed (likely Assassin).** Big crit hits from a fast dagger attack. Bleed magnitude scales with hit damage, so crit scales bleed too. Verify in 1.0.
2. **Stealth opener bleed.** Leave stealth with a Darkness-boosted hit to apply one huge bleed, then reposition. Strong if bleeds don't stack and only the biggest one counts. Verify the stacking rules.
3. **Impale and rip bleed.** Use the impaled daggers' rip-out effect to reapply or boost bleed. Depends on what the rip effects actually do.
4. **Non-crit bleed.** Flat physical and bleed magnitude instead of crit. A fallback if crit doesn't feed bleed well.

Ascendancy choice waits until the node lists are out. Infiltrator may pair better with stealth, Assassin with crit.

## How the comparison will run
- Pull every dagger skill, support, unique dagger and passive cluster from the patch notes, poe2db and the wiki.
- Score each skill, support and weapon combination on: bleed DPS against bosses, clear speed, uptime and ease of applying bleed, defences, and gear cost.
- Use my own damage model until Path of Building supports the Shadow, then switch to headless PoB.
- Benchmark the winner against Duelist bleed (Haemorrhage/Blood Loss) and other top bleed builds from poe.ninja once ladder data exists.

## Check on day one
- [ ] Bleed formula, duration and stacking rules in 1.0
- [ ] Whether crits raise bleed magnitude
- [ ] Dual wield rules: damage, attack speed, which hand applies bleed
- [ ] Full dagger skill and support gem list
- [ ] Assassin and Infiltrator nodes
- [ ] Stealth and Darkness numbers
- [ ] Unique daggers and their stats
- [ ] Whether the PoE 2 Path of Building fork supports the Shadow

## Changelog
- v0.1 (Nov 14, 2026): first draft from ExileCon coverage.
