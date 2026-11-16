# A-to-Z test report (PoB 0.23.1, run 2026-11-15)

16 prompts, each built at all 4 stages. For every prompt the test checks two things:

- **Asked for:** the weapon, class, skill kind, damage, ailment share, stat focus and "no X" from the prompt are all in the final build.
- **Real:** every item, base, unique and gem exists in the game, can be bought, fits the budget, and the character meets its attribute requirements.

## Result

**No made-up items.** All 14 "made-up gem" flags came from a bug in the test itself. They were Thorns, a skill every character gets for free, which PoB saves without a name. The test is fixed.

**12 of 16 delivered what was asked.** 4 had problems:

| Prompt | Got | Problem | Status |
|---|---|---|---|
| block energy shield build (high) | Detonate Dead, Infernalist, Staff | 0% block, 30% minimum. A staff can't block. | Fixed: block builds now hold a one-hand weapon and a shield |
| evasion crit bow build (high) | Rain of Arrows, Oracle, Bow | Evasion 2,848, just under the 3,000 minimum | Open: small miss |
| lightning arrow with heralds (medium) | Lightning Arrow, Invoker, Bow | Leveling stage is 3 Int short (32 of 35) for its supports | Open: small miss |
| tanky ignite build (high) | Detonate Dead, Infernalist, Staff | No build got most of its damage from ignite, so the rule was loosened (the site tells the player) | Open: worth a look |

Passed: crossbow crit bleed, lightning minions, cast on crit fire spells\*, poison bow, two hand mace slam, spear attack speed, chaos DoT witch, warcry, fire spells with no minions, sorceress cold, invoker, fast mapping with movement speed.

\* Cast on crit: the build keeps Cast on Critical, but PoB doesn't model how often it triggers, so the DPS shown is for the spell cast normally. The site says so.

## Found outside the test: "poison totem"

Kyle's "poison totem" prompt gave Sunder, which isn't a totem. The word "totem" was matched to skills a totem *could* use. It now matches skills that place a totem: Shockwave Totem, Siege Ballista, Artillery Ballista and Dark Effigy. "Trap" had the same bug, and PoE 2 has no trap skills yet, so the site now says that instead of returning a random skill.

## Fixed and live on 2026-11-16 (engine 2026-11-16.2)

| Problem | Before | After |
|---|---|---|
| "poison totem build" | Sunder, not a totem | Dark Effigy, a real totem. No totem build could be mostly poison, so poison was dropped and the page says so. |
| Totem skills scored 0 DPS | PoB scored the "place totem" part, so every totem skill was thrown out | Scored on what the totem does (Shockwave Slam, Ballista Bolt, Vile Effusion) |
| "block energy shield build" | Staff or bow, 0% block | Wand and shield, 50% block. Energy shield is 421 against its 1,000 target; the page tells the player. |
| Defensive buffs never picked | Damage buffs always won the spirit | Wind Dancer, Scavenged Plating, Iron Ward and others are kept when the EHP is worth the damage (Defence row) |
| One skill for everything | | A separate clear skill on the same weapon when it clears 25%+ better (Clearing row) |
| Passive-granted skills | Could be picked for any build | Never picked (Virtuous Barrier, Parry and others need their passive) |

### Mechanics check (74 prompts)

- **Fixed misreads:** "storm" (was lightning), "grenade build" (was the gem Grenade), "cast on freeze/ignite/shock" (now Cast on Elemental Ailment), "low life" (was read as more life), "shield build" (now block), "spectre", "corpse explosion", "electrocute".
- **Shown to the player as not understood:** mine, frenzy/power/endurance charges, rage, dual wield, unarmed, archon, infusion, ground effects, exposure, thorns, recoup, blood magic, flask, charm, glass cannon, one button.
- **Next for totems:** PoB scores Spell Totem, Ancestral Warrior Totem and Mortar Cannon with a skill socketed in them. Using them would let any totemable spell or slam be a totem build, which is how most PoE 2 totem builds work.
- **Defence limit:** PoB doesn't count Time of Need's healing or Ghost Dance, so those can't be picked yet.

## Worth a look later

Detonate Dead was picked for 4 of the 16 prompts (cast on crit fire, tanky ignite, block ES, fire spells with no minions). It may be legitimately strong in PoB, or PoB may be overrating it, for example by assuming a corpse is always there.
