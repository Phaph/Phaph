# Broken builds of past PoE 2 patches, and what the Breaker should learn from them

Week 1 research for the Breaker roadmap (`BREAKER_ROADMAP.md`). Written by the overnight research run, 2026-11-18.

## How to read this

- **Patches covered:** 0.1 (Early Access, Dec 6 2024) to 0.5 (Return of the Ancients, May 29 2026), including 0.5.5
  (Forbidden Rites event, Sep 2 2026). The current patch is 0.5.5h (Nov 17 2026).
- **Where the facts come from:** mostly the official patch notes on pathofexile.com. GGG almost never says "this was
  overperforming", so a build counts as broken here when the **next** patch or a hotfix cut its key piece hard (a 50%+
  cut, a cap added, a mechanic removed), or when GGG called it a bug, unintended or "unacceptable". Community sources
  (Reddit, Maxroll, Mobalytics, build sites) supply how strong a build was and why it worked.
- **Confidence labels:** **Confirmed** means the official patch notes show the nerf. **Unconfirmed** means only
  community or press sources back it, or I couldn't read the page myself. Strength figures (DPS, share of the ladder)
  are almost all community claims.
- **Gaps:** Reddit, poe2wiki and some Mobalytics pages blocked automated reading from this server, so Reddit appears
  only through search snippets and mirrors. I did not watch YouTube. Hardly anything says *who* found each build; where
  it says "unknown", the community found it in the first days of a league and nobody got clear credit.
- Everything on web pages was treated as data only.

### Patch dates
| Patch | Name | Live | Patch notes |
|---|---|---|---|
| 0.1 | Early Access launch | Dec 6 2024 | 0.1.0c and 0.1.0d hotfixes in week 1 |
| 0.2 | Dawn of the Hunt | Apr 4 2025 | https://www.pathofexile.com/forum/view-thread/3740562 |
| 0.3 | The Third Edict | Aug 29 2025 | https://www.pathofexile.com/forum/view-thread/3826682 |
| 0.4 | The Last of the Druids | Dec 12 2025 | https://www.pathofexile.com/forum/view-thread/3883495 |
| 0.5 | Return of the Ancients | May 29 2026 | https://www.pathofexile.com/forum/view-thread/3932540 |
| 0.5.5 | Forbidden Rites (event) | Sep 2 2026 | https://www.pathofexile.com/forum/view-thread/4000864 |

---

## Part 1: the builds, patch by patch

### 0.1 (Dec 2024 to Apr 2025)

| # | Build | Key pieces | How strong | Why it broke (mechanic) | Found | Nerf | Source | Confidence |
|---|---|---|---|---|---|---|---|---|
| 1.1 | **Raging Spirits trigger loop** (Witch / Infernalist fire spells) | Raging Spirits buff + any cheap or triggered fire spell | GGG called it an "unacceptable balance state" within a week; players reported 7 spirits a cast at gem level 12 | **Free casts and a count with no cap.** Each fire spell cast summoned several spirits, and triggered fire spells summoned spirits too, so a low-level spell fed an endless swarm | Players, first days of Early Access | **0.1.0c (Dec 10 2024):** 5 spirits a cast, none from triggered fire skills. **0.2:** 2 a cast, and Fireball can't bypass the limit. **0.5:** fixed fire skills used by Spell Totems still making spirits | https://maxroll.gg/poe2/news/raging-spirit-and-meta-gem-hotfix-announced | Confirmed |
| 1.2 | **Cast on Freeze Comet** (Sorceress) | Cast on Freeze, Comet, any cheap freezing skill | Players put the 0.1.0d loss at 84-95% | **Trigger energy loop.** Each freeze, even on trash mobs, gave a flat 100 energy, so a cheap freeze spammed Comet for free. GGG: "using low level skills with no investment is not an appropriate avenue to trigger copious amounts of high damage spells" | Players, week 1 | **0.1.0d (Dec 11 2024):** energy scales with Monster Power and the strength of the ailment; "all energy gain rebalanced". Reddit figures: 100 energy a freeze down to 10 x monster power, and Comet needs 300 instead of 158 | https://www.pathofexile.com/forum/view-thread/3621299 ; https://comicbook.com/gaming/news/path-of-exile-poe-2-update-patch-notes-cast-on-freeze ; https://lr.us.psf.lt/r/PathOfExile2/comments/1hcb0hv/010d_patch_notes/ | Mechanism confirmed; numbers unconfirmed (Reddit) |
| 1.3 | **Archmage mana-stacking Spark Stormweaver** (often with Chaos Inoculation + Mind over Matter) | Archmage, Spark, Stormweaver mana nodes, Ingenuity, Dream Fragments, Everlasting Gaze (mana as extra ES) | Stormweaver was about a third of all characters in 0.1 and under 1% in 0.2 | **One stat feeds damage and defence.** Archmage adds lightning damage per 100 max mana, so every point of mana was both damage and life (MoM) or ES (Everlasting Gaze). Spark's 6-14 projectiles overlapped on a single boss | Known from day 1 | **0.2:** Archmage bonus cut by 50-73% (Mobalytics) and its cost raised from 5.35% to 6.7% of max mana; Stormweaver % mana nodes removed; Raw Mana and Mana Blessing cut; mana caps lowered on most item slots; Everlasting Gaze from 20-30% down to 4-6%; Dream Fragments halved; Ingenuity 40-80% down to 20-30%; Spark 6-14 projectiles down to 4-9 | https://www.pathofexile.com/forum/view-thread/3740562 ; https://mobalytics.gg/poe-2/guides/0-2-0-archmage-nerf ; https://mobalytics.gg/poe-2/guides/dawn-of-the-hunt-class-buffs-nerfs | Confirmed (exact Archmage figure from Mobalytics) |
| 1.4 | **Lightning Conduit on stacked Shock** (Stormweaver with double Shock) | Lightning Conduit, high Shock magnitude, Strike Twice | Guides claim boss one-shots | **A "more" multiplier per unit of another stat.** 100% *more* damage for every 5% Shock effect, so stacking Shock magnitude grew damage geometrically | Unknown | **0.2:** 100% down to 20% more per 5% Shock; Strike Twice changed. **0.4:** down again to 10% | https://www.pathofexile.com/forum/view-thread/3740562 ; https://www.pathofexile.com/forum/view-thread/3883495 ; https://maxroll.gg/poe2/build-guides/spark-lightning-conduit-stormweaver | Nerf confirmed; strength unconfirmed |
| 1.5 | **Herald chain clears** (Ice Strike / Tempest Flurry Invoker, Herald of Ice + Herald of Thunder) | Herald of Ice, Herald of Thunder, freezing melee | "Blowing up the whole screen from a single strike" (Maxroll) | **Chain reaction.** A kill by a Herald explosion counted as an on-kill trigger for more Herald explosions, and Thunder's shocks and Ice's freezes kept each other going | Unknown | **0.2:** Herald on-kill effects no longer trigger from kills made by Herald skills; Herald of Ice radius 1.8 m down to 1.6 m; Ice Crystals can no longer apply on-kill effects (Herald of Ash, Trampletoe) | https://www.pathofexile.com/forum/view-thread/3740562 ; https://maxroll.gg/poe2/build-guides/shattering-palm-invoker-build-guide | Confirmed |
| 1.6 | **Hexblast curse detonation** (Witch) | Hexblast, multiple curses / Blasphemy | Unconfirmed | **Overlapping hits.** One cast detonated up to 9 explosions on the same target | Unknown | **0.2:** at most 3 explosions, and only curses at least 50% expired | https://www.pathofexile.com/forum/view-thread/3740562 | Nerf confirmed; build strength unconfirmed |
| 1.7 | **Poison cloud stacking** (Pathfinder: Gas Arrow, Toxic Growth, Gas Grenade) | Gas clouds, Toxic Growth arrows | Unconfirmed | **Count with no cap plus growing areas.** Unlimited clouds whose radius grew by up to +200% kept overlapping on a boss | Unknown | **0.2:** at most 6 clouds, growth 50%/s down to 20%/s with an 80% cap; Toxic Growth 8 arrows down to 6. (Toxic Growth was cut again in 0.4 and 0.5.) | https://www.pathofexile.com/forum/view-thread/3740562 | Nerf confirmed |
| 1.8 | **Infernalist Demon Form** | Demonic Possession / Demon Form | Unconfirmed | **Stack with no cap.** Demonflame stacks had no limit, and the life loss was a % of max life | Unknown | **0.2:** capped at 10 stacks; life loss became a flat amount per stack | https://www.pathofexile.com/forum/view-thread/3740562 | Nerf confirmed |
| 1.9 | **Gemling attribute stacking** | Enhanced Effectiveness (doubles what attributes give), Pillar of the Caged God, Astramentis, Hand of Wisdom and Action | 0.1 guides advertised 1.36M DPS | **A stat feeds damage, and an ascendancy doubles it.** Attributes turned into damage through Pillar and Hand of Wisdom and Action, and Gemling doubled what each attribute gave | Unknown | **0.2:** Gemling gets 20% less attributes; Pillar of the Caged God and Hand of Wisdom and Action halved; Astramentis lowered; Polymathy cut | https://www.pathofexile.com/forum/view-thread/3740562 ; https://mobalytics.gg/poe-2/builds/empyrians-attribute-stacker-gemling | Nerf confirmed; "broken" unconfirmed |
| 1.10 | **Free casts from cooldown and cost items** | Temporalis (-4 s cooldown), Melting Maelstrom (recover all mana), Flameblast (no cooldown), grenades, Cast on Shock (2 energy per Power), Cast on Minion Death (any minion) | Unconfirmed | **Free casts.** Cooldowns cut close to zero, a flask that refilled all mana, energy from minions that die constantly | Unknown | **0.2:** Temporalis down to -2/-1 s; Melting Maelstrom loses its full mana refill; Flameblast gets a 15 s cooldown; grenade cooldowns doubled; Cast on Shock 2 down to 1 energy; Cast on Minion Death only counts persistent minions; Eldritch Battery now doubles mana cost | https://www.pathofexile.com/forum/view-thread/3740562 | Confirmed |
| 1.11 | **ES and Spirit defence loops** (Invoker, Chayula, CI) | Lead me through Grace (Spirit from ES / evasion), Meditate, Ghostwrithe, Atziri's Disdain, instant mana leech (Ravenous Doubts) | Unconfirmed | **One stat feeds two things.** Defence stats bought Spirit, Spirit bought more buffs, and instant leech kept the mana-based defence full | Unknown | **0.2:** all of these cut, and Ravenous Doubts lost "Mana Leech is Instant" | https://www.pathofexile.com/forum/view-thread/3740562 | Nerf confirmed |
| 1.12 | **Firestorm / Rain of Arrows on big bosses** | Firestorm, Rain of Arrows | Unconfirmed | **Overlapping hits.** Large boss hitboxes took hits from every bolt or arrow at once | Unknown | **0.1.0d:** hit-rate limit against very large targets. **0.3:** Firestorm radius halved | https://www.pathofexile.com/forum/view-thread/3621299 | Confirmed |

### 0.2 Dawn of the Hunt (Apr to Aug 2025)

| # | Build | Key pieces | How strong | Why it broke | Found | Nerf | Source | Confidence |
|---|---|---|---|---|---|---|---|---|
| 2.1 | **Lightning Spear Amazon** | Lightning Spear, Tangletongue (forks crits), Volt, Frenzy Charges, Amazon accuracy-to-crit nodes | Amazon was over half of level 90+ characters by day 10; Lightning Spear was the signature build | **Multipliers stacked inside one skill.** Consuming a Frenzy Charge gave *more* damage and split the projectile into extra spears, which overlapped on a boss. Tangletongue forked crits, and the Amazon turned accuracy into crit | Streamers in the first week (exact person unknown) | **0.3:** no more damage from consuming Frenzy; extra projectiles fixed at 5 (IGGM); Tangletongue crit +10-20% down to +5-8%; martial weapon crit damage mod +39% down to +25%; fixed a bug where spells got crit chance from the Amazon node | https://www.pathofexile.com/forum/view-thread/3826682 ; https://www.iggm.com/news/poe-2-patch-0-3-0-winners-and-losers ; https://maxroll.gg/poe2/build-guides/lightning-spear-amazon | Nerf confirmed; share from Mobalytics |
| 2.2 | **Hidden delayed multipliers: Ice Shards (crossbow) and Spearfield** | Ice Shards, Spearfield | Unconfirmed | **A hidden "more" multiplier.** Ice Shards had 900% (later 700%) more damage after a shard existed for 0.5 s; Spearfield had an "unintentionally hidden" 300% more after 0.5 s. A boss standing in placed shards or spears always got it | Unknown | **0.2 hotfixes:** Ice Shards 900% down to 700%. **0.3:** both removed, replaced by 80% *less* damage in the first 0.5 s | https://www.pathofexile.com/forum/view-thread/3826682 ; https://www.pathofexile.com/forum/view-thread/3740562 | Confirmed (GGG's words for Spearfield) |
| 2.3 | **Shield Charge / block Warbringer** | Shield Charge, Turtle Charm, Glancing Blows, high-block uniques (Lycosidae, Oaksworn and others) | Unconfirmed | **A defence reaches its cap, and damage piggybacks on it.** Glancing Blows doubled block chance, so block hit its cap; Shield Charge did 303-906% collision damage | Unknown | **0.3:** Glancing Blows loses block doubling; Turtle Charm reworked; unique shield block cut by about half; Shield Charge collision down to 60-217% | https://www.pathofexile.com/forum/view-thread/3826682 | Nerf confirmed |
| 2.4 | **Rake + Blood Hunt bleed** (Ritualist / Amazon / Blood Mage) | Rake, Blood Hunt, Herald of Blood | Guides claim 2-shot pinnacle bosses | **Damage from the enemy's own state, not from the player.** The Blood Hunt explosion grew with the bleed already on the target, as damage nothing could reduce | Unknown | **0.3:** the explosion became Life Loss | https://www.pathofexile.com/forum/view-thread/3826682 ; https://www.pathofexile.com/forum/view-thread/3772343 | Nerf confirmed; strength unconfirmed |
| 2.5 | **Big single-skill outliers** | Electrocuting Arrow (302-572%), Cold Snap (gem 20 up to 1005), Frost Bomb, Eye of Winter, Glacial Cascade (350% vs frozen), Perfect Strike, Shockwave Totem, Supercharged Slam, Infernal Cry (empowered by Endurance Charges) | Unconfirmed | Mostly **plain overtuning**; Glacial Cascade's "more vs Frozen" was a condition that is always true vs a frozen boss | Unknown | **0.3:** all cut 30-70%; Infernal Cry now scales with enemy Power instead of the player's charges | https://www.pathofexile.com/forum/view-thread/3826682 | Confirmed |
| 2.6 | **Supports on totems and triggered skills** | Any support on totems or triggered skills | Unconfirmed | **Bug.** Many supports applied to totem and triggered skills that shouldn't get them | Unknown | **0.3:** fixed, and supports that affect skills "you use yourself" can no longer support Persistent skills | https://www.pathofexile.com/forum/view-thread/3826682 | Confirmed |
| 2.7 | **Deadeye doubling** | Called Shots (an extra Mark), Thrilling Chase (100% chance to double Frenzy Charge benefits) | Unconfirmed | **A doubler on a resource that already scales damage** | Unknown | **0.3:** Called Shots loses the extra Mark; Thrilling Chase down to a 50% chance | https://www.pathofexile.com/forum/view-thread/3826682 | Confirmed |
| 2.8 | **Evasion and life-flask immortality** | Hyrri's Ire ("evade all hits if not hit recently"), Acrobatics, Eternal Youth, Giant's Blood | Unconfirmed | **A defence reaching 100% under a condition that is easy to keep up** | Unknown | **0.3:** Hyrri's now doubles Evasion instead; Acrobatics removed; Eternal Youth and Giant's Blood cut | https://www.pathofexile.com/forum/view-thread/3826682 | Confirmed |
| 2.9 | **Engine bugs found in 0.2/0.3** | Ancestral Boost, Earthquake, skill costs | Unconfirmed | **Bugs:** several Ancestral Boosts on one Strike kept adding targets; Earthquake used area modifiers twice; skill costs could go partly unpaid | Unknown | Fixed in **0.3** | https://www.pathofexile.com/forum/view-thread/3826682 | Confirmed |

### 0.3 The Third Edict (Aug to Dec 2025)

| # | Build | Key pieces | How strong | Why it broke | Found | Nerf | Source | Confidence |
|---|---|---|---|---|---|---|---|---|
| 3.1 | **Lightning Arrow Deadeye** | Lightning Arrow, Lightning Rod (20 rods at once), Herald of Thunder, Tailwind, Wind Ward | 34% of top players picked Deadeye, and 80% of those ran Lightning Arrow (Maxroll) | **A free trigger plus overlapping hits.** Lightning Arrow hitting a Lightning Rod skipped the Rod's burst charge-up, so every arrow set off up to 20 rods for free. Wind Ward gave Deadeye cheap safety | Meta from league start | **0.4:** Lightning Arrow no longer skips the charge-up; at most 10 rods; Herald of Thunder cut by 15%; Tailwind cut; Wind Ward removed. **0.5:** Lightning Arrow beams can't chain back to the same target | https://maxroll.gg/poe2/meta/the-build-meta ; https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.2 | **Life-cost Blood Mage** (Fireball / Ember Fusillade / Bone Storm) | Rathpith Globe (crit and spell damage per 100 life), Atalui's Bloodletting (extra physical per 10 life spent), Undying Hate (Sacrifice of Blood: regen per life spent), Kaom's Heart, Black Flame | "Unmatched scaling potential" (Maxroll) | **One stat fed damage three ways, and the cost refunded itself.** Life raised crit and damage (Rathpith), spending life added damage (Atalui's), and Undying Hate regenerated the life that was spent | Ladder players, weeks 1-2 | **0.4:** Rathpith 5% down to 3% crit and 10% down to 6% damage per 100 life; Atalui's per 10 life down to per 20; Undying Hate regen halved. **0.5:** Rathpith / Covenant / Atziri's Rule life-cost efficiency cut | https://maxroll.gg/poe2/meta/the-build-meta ; https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.3 | **Indigon and Whispering Ice stacking** | Indigon (spell damage per 200 mana spent), The Whispering Ice (spell damage per 10 Int) | Unconfirmed | **A stat that feeds damage with no cap** | Unknown | **0.4:** Indigon 35-50% down to 10-15%; Whispering Ice 4% down to 2% per 10 Int | https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.4 | **Hollow Palm Technique** (unarmed Monk / Amazon / Deadeye) | Hollow Palm keystone: 1% more attack speed per 25 Evasion on gear | 0.3 guides: "one-shot bosses on 1 divine" | **A defence stat becomes "more" speed with no cap.** Stacking evasion gave both defence and multiplicative attack speed | Unknown | **0.4:** per 25 down to per 75 Evasion (base unarmed speed up as compensation). **0.5:** fixed the keystone *adding* unarmed damage on top of the base when it should replace it | https://www.pathofexile.com/forum/view-thread/3884131 ; https://www.pathofexile.com/forum/view-thread/3932540 ; https://mobalytics.gg/poe-2/builds/one-shot-bosses-on-1-divine-hollow-palm-deadeye | Confirmed |
| 3.5 | **Infinite ignite: Incinerate and ignited ground** | Incinerate, igniting auras and ground, Oil Grenade / Oil Barrage | "Infinite burn" builds | **Stacking with no cap.** Igniting auras and ground applied ignites that never ran out and kept compounding | Players; the mechanic still appears in 0.5.5 guides | **0.4:** "Igniting aura effects no longer apply infinite Ignites"; Incinerate's ignite damage cut by about 80%. **0.5:** ignites on Oil Ground can no longer compound | https://www.pathofexile.com/forum/view-thread/3883495 ; https://www.pathofexile.com/forum/view-thread/3932540 ; https://mobalytics.gg/poe-2/builds/jungroan-infinite-burn-oil-grenade-incinerator | Confirmed (0.5.5 status unconfirmed) |
| 3.6 | **Tactician immobilise bossing** | Artillery Ballista (immobilise buildup), Siege Ballista / Siege Cascade (bonus vs Immobilised), Death From Above (1140%) | Video titles: "Glacial Bolt deletes pinnacles (nerfed)" | **A conditional bonus that is always on vs bosses.** Ballistas immobilised the boss, and the bonuses "vs Immobilised" then applied all the time | Unknown | **0.4:** Artillery Ballista loses immobilise; Death From Above down to 763%; Siege Ballista bonus reworked. **0.4.0f:** further buildup cut | https://www.pathofexile.com/forum/view-thread/3883495 ; https://www.poebuilds.cc/poe2/build/nBMq49nlIaM | Confirmed |
| 3.7 | **Invoker Unbound Avatar** | Unbound Avatar, Unbound Fury (2 per Shock / Ignite) | Unconfirmed | **A buff kept up 100% of the time** because nothing limited it | Unknown | **0.4:** 12 s cooldown; 1 per ailment | https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.8 | **Ghost Dance** (evasion / ES) | Ghost Dance shrouds | Unconfirmed | **A defence loop:** a shroud every ~3 s, up to 5 at once | Unknown | **0.4:** at most 3, interval doubled. **0.5:** interval cut further | https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.9 | **Cooldown supports on non-cooldown skills** | Spark, Ancestral Cry, Ember Fusillade with cooldown supports | Unconfirmed | **Unintended support compatibility** (GGG's word: "unintended") | Unknown | **0.4:** removed | https://www.pathofexile.com/forum/view-thread/3883495 | Confirmed |
| 3.10 | **Whirling Slash / Twister, Fleshpiercer Spectres** | Whirling Slash, Spectres | Popular early 0.3 | Unconfirmed | Unknown | **0.3.0b:** Whirling Slash slowed; Spectres nerfed; Husk of Dreams changed from a 50% chance to not use flask charges to 50% fewer charges used | https://poe-vault.com/poe2/news/poe2s-patch-0-3-0b-fixes-the-fun-with-nerfs-to-popular-builds | Unconfirmed (press only) |

### 0.4 The Last of the Druids (Dec 2025 to May 2026)

| # | Build | Key pieces | How strong | Why it broke | Found | Nerf | Source | Confidence |
|---|---|---|---|---|---|---|---|---|
| 4.1 | **Walking Calamity Shaman** ("Freddy Fazbear") | Walking Calamity (meteors), Shaman ascendancy | "Pretty much immortal while raining destruction" (build round-ups) | **Count scaling and defence**, unconfirmed: meteors scaled with nearby enemies, and quality added a large meteor for every few meteors | Unknown | **0.4.0c (Dec 18 2025):** fewer meteors when few enemies are nearby; quality's large meteors removed | https://www.pathofexile.com/forum/view-thread/3893204 ; https://www.akrpg.com/news/1020--top-3-poe-2-04-best-builds-the-last-of-the-druids | Nerf confirmed; build description unconfirmed |
| 4.2 | **Lunar Blessing** (Druid) | Lunar Blessing moonbeams | Unconfirmed | **A free trigger and uptime:** moonbeams triggered from any hit, and the cooldown ticked down while the buff was active | Unknown | **0.4.0c:** cooldown 10 s up to 22 s; moonbeams only from melee attacks | https://www.pathofexile.com/forum/view-thread/3893204 | Confirmed |
| 4.3 | **Amanamu's Tithe immunity** (minion builds) | Amanamu's Tithe lineage support | Forum: "invincibility throughout its duration", stacking | **A bug giving full immunity.** Minion deaths gave the player an immunity aura | Players, week 1 | **0.4.0c:** "no longer grants players an immunity aura" | https://www.pathofexile.com/forum/view-thread/3893204 ; https://web.poecdn.com/forum/view-thread/3892472 | Fix confirmed; strength unconfirmed |
| 4.4 | **Fury of the Mountain without mana** | Fury of the Mountain | Unconfirmed | **A free cast (bug)** | Unknown | **0.4.0d (Jan 14 2026):** fixed | https://www.pathofexile.com/forum/view-thread/3905934 | Confirmed |
| 4.5 | **Uhtred supports counting Meta gems** | Uhtred's Augury / Omen (+3 levels when there are enough supports) | Unconfirmed | **A condition met cheaply:** Meta gems counted toward the support-count condition | Unknown | **0.4.0d:** fixed. **0.5:** +3 down to +2 levels | https://www.pathofexile.com/forum/view-thread/3905934 ; https://www.pathofexile.com/forum/view-thread/3932540 | Confirmed |
| 4.6 | **CoC Comet Oracle / Blood Mage, Vitality Siphon loop** | Cast on Critical, Comet, Vitality Siphon (life spent on casts made Life Flask charges) | Claims of 10M+ DPS for the Oracle | **A recovery loop.** Spending life refilled the flask that refilled the life, which was close to infinite recovery when casting fast (and could be automated) | Unknown | **0.5:** Vitality Siphon "Flasks do not recover life"; Comet damage cut | https://www.gamer.org/path-of-exile-2-patch-0-5-return-of-the-ancients-every-major-nerf-buff-and-change-explained/ ; https://www.pathofexile.com/forum/view-thread/3932540 | Comet nerf confirmed; loop description from press |
| 4.7 | **Totem Archmage** (Ancestral Bond) | Ancestral Bond, Spell Totem, Archmage | Unconfirmed | **A cost scaling off zero.** Press says totem casts cost nothing, so Archmage's %-of-mana cost never mattered while its damage did (another source says Ancestral Bond worked by Spirit reservation, not zero cost) | Unknown | **0.5:** Ancestral Bond reworked (totem limit doubled, 75 Spirit each); 0.5.1 fixed Spell Totem's more-life-per-Endurance modifier applying twice | https://www.gamer.org/path-of-exile-2-patch-0-5-return-of-the-ancients-every-major-nerf-buff-and-change-explained/ ; https://www.pathofexile.com/forum/view-thread/3949197 | Unconfirmed (sources disagree) |
| 4.8 | **Free crossbow reloads** | Arjun's Medal (100% chance to load a bolt on killing blow), Ratha's Assault | Unconfirmed | **Free casts:** ammo refilled itself | Unknown | **0.5:** Arjun's 100% down to 25%; Ratha's Assault cut | https://www.pathofexile.com/forum/view-thread/3932540 | Confirmed |
| 4.9 | **Leech stacking** | Several leech instances, instant leech, Vaal Pact | Unconfirmed | **Defence stacking with no cap** | Unknown | **0.5:** one leech instance per resource; hits over 40,000 capped for leech; instant leech removed; Vaal Pact reworked | https://www.pathofexile.com/forum/view-thread/3932540 ; https://www.gamer.org/path-of-exile-2-patch-0-5-return-of-the-ancients-every-major-nerf-buff-and-change-explained/ | Confirmed |
| 4.10 | **Overlap and interaction fixes in 0.5's notes** | Melee Splash, Lightning Arrow, Feral Invocation, Eternal Rage, minions and totems, Plaguefinger | Unconfirmed | **Overlapping hits:** Melee Splash applied more than once per damaging area; Lightning Arrow beams chained back to the same target. **Cooldown bypass:** Feral Invocation skipped socketed skills' cooldowns. **Weapon set:** Eternal Rage worked from one set. **Unkillable:** minions and totems under some effects couldn't die from overkill. **Unique:** Plaguefinger applied elemental ailments | Unknown | **0.5:** all fixed or removed | https://www.pathofexile.com/forum/view-thread/3932540 | Confirmed |
| 4.11 | **Bugs fixed in 0.4/0.5** | Charges, flask charges, Inhibitor, terrain chaining, energy | Unconfirmed | **Double-dipping:** charge-gain stats applied twice; Ambrosia and Concoct gave full benefit on partial charges; Inhibitor scaled per Infusion instead of per type; Thornskin stacked; Rend scaled twice with level. **Endless chaining:** projectiles chained forever from terrain. **Free energy:** triggered skills generated energy | Unknown | Fixed in **0.4 / 0.5** | https://www.pathofexile.com/forum/view-thread/3883495 ; https://www.pathofexile.com/forum/view-thread/3932540 | Confirmed |
| 4.12 | **Armour reducing hits to 0** | Armour | Unconfirmed | A defence formula reaching 100% | Unknown | A patch-history site says 0.4.0d; **not found** in the official 0.4.0d notes | https://poetrades.net/poe2-patch-notes/ | Unconfirmed |

### 0.5 Return of the Ancients and 0.5.5 Forbidden Rites (May 2026 to now)

| # | Build | Key pieces | How strong | Why it broke | Found | Nerf | Source | Confidence |
|---|---|---|---|---|---|---|---|---|
| 5.1 | **Martial Artist Hollow Form** (Whirling Assault / Twister / Whirling Bells) | Hollow Form (channel: astral projections copy your skill), Way of the Stonefist, power-charge gloves | "Widely considered broken in 0.5"; guide titles say "very broken" | **Copies multiply hits.** Every projection repeats the attack, so hits overlap. A movement exploit let players skip Hollow Form's movement penalty | Week 1 | **0.5.0b (May 30 2026):** movement exploit removed; channelled-skill tap trick fixed. Still strong in 0.5.5 | https://maxroll.gg/poe2/news/patch-notes-for-0-5-0b ; https://mobalytics.gg/poe-2/profile/nicktew/builds/0-5-twister-martial-artist-very-broken ; https://www.pathofexile.com/forum/view-thread/3935437 | Exploit fix confirmed; "broken" is community opinion |
| 5.2 | **Flicker Strike Chayula, close to immortal** | Flicker Strike, sources of "chance to not consume charges" | "Prevented a case of a nearly immortal build running rampant" (Vulkk), also botting concerns | **A chance stat reaching 100% gives unlimited free uses.** At 100% no-consume, Flicker could chain forever; the build is not targetable during Flicker (unconfirmed) | Week 1 | **0.5.0b Hotfix 12 (Jun 2 2026):** capped at 75% | https://www.pathofexile.com/forum/view-thread/3945119 ; https://vulkk.com/2026/06/08/path-of-exile-2-updates-expand-the-passive-tree-and-adjust-endgame-rewards/ | Cap confirmed; immortality detail unconfirmed |
| 5.3 | **Olroth's Resolve guard** | Olroth's Resolve flask (instant recovery, excess life as Guard) | Forum: "massive bug" | **A defence overflow** | Unknown | **0.5.1 (Jun 4 2026):** loses instant recovery and excess-life-to-Guard | https://www.pathofexile.com/forum/view-thread/3949197 | Fix confirmed; impact unconfirmed |
| 5.4 | **Sorcery Ward overflow** | Sorcery Ward with big defences | Unconfirmed | **An integer overflow bug:** with enough defences the barrier went *negative* and amplified hits | Unknown | **0.5.3 (Jun 18 2026):** capped at 32,000; "will be reviewing Sorcery Ward" | https://www.pathofexile.com/forum/view-thread/3968601 | Confirmed |
| 5.5 | **Weapon-set and snapshot exploits** | Second weapon set; Prism of Belief, From Nothing | Unconfirmed | **Bugs:** auras and supports from the inactive weapon set still applied; skills from the other set worked without swapping; Prism of Belief and From Nothing could be snapshotted | Unknown | **0.5.5 (Sep 2 2026):** fixed | https://www.pathofexile.com/forum/view-thread/4000864 | Confirmed |
| 5.6 | **Refutation** | Refutation buff | Unconfirmed | **Uptime:** the cooldown recovered while the buff was active | Unknown | **0.5.1:** fixed | https://www.pathofexile.com/forum/view-thread/3949197 | Confirmed |
| 5.7 | **Twister Spirit Walker, Ice Shot Deadeye** | Twister; Ice Shot | Top of 0.5 starter lists ("untouched by the nerfs") | Not explained | Unknown | None found yet | https://www.mmopixel.com/news/poe-2-0-5-strongest-league-starter-builds-right-now | Unconfirmed |

### How much the 0.4 and 0.5 cases were played (ladder, added 2026-11-26)
Measured from Wayback Machine copies of poe.ninja's build API (`engine/tools/ninja_archive.py`, data in `engine/data/ninja_archive/`):
% of all characters poe.ninja indexed that use the piece (`allskills`, unless marked). One snapshot every 1-7 days, so these are
points, not curves. Early in a league every endgame skill rises as characters level (Comet 4.8% -> 17.7% in Dec 2025 with no patch
reason), so a fall after a nerf fits the nerf but doesn't prove it. 0.4's snapshots have no key-passive data (4.7 Ancestral Bond,
4.9 Vaal Pact can't be read there).

| # | Piece | Before the fix | After the fix | Reading |
|---|---|---|---|---|
| 4.1 | Walking Calamity (Shaman class) | 11.65 / 12.02% Dec 15 / 17 (Shaman 20.0 / 18.0%) | 8.23% Dec 29, 6.30% Jan 18 (Shaman 12.2 / 9.4%) | Widely played; the only case that turns at its patch date (0.4.0c, Dec 18) |
| 4.2 | Lunar Blessing | 10.16% Dec 17 | 9.87% Dec 29, 7.83% Jan 18 | Widely played; no fall in the 11 days after its nerf |
| 4.3 | Amanamu's Tithe | 1.79% Dec 17 | 5.65% Dec 29, 5.68% Jan 18 | Kept rising after the immunity fix: used for something else too |
| 4.4 | Fury of the Mountain | 8.05% Dec 15, 2.27% Dec 29 | 1.72% Jan 18 (fix Jan 14) | Fell before its fix: likely a campaign skill people left (guess) |
| 4.5 | Uhtred's Augury / Omen | 0.97 / 1.25% Dec 29 | 2.99 / 3.50% Jan 18 (fix Jan 14) | Niche, and rose across the fix |
| 4.6 | Cast on Critical / Comet | 15.3 / 7.5% Dec 17 | 35.2 / 28.1% Jan 18 | The league's main build; the Vitality Siphon loop itself isn't in the data |
| 4.7 | Archmage (keystone not readable) | 1.59% Dec 17 | 11.19% Jan 18 | Rose all league |
| 4.8 | Arjun's Medal | 2.68% Dec 17 | 2.87% Jan 18 (fix was 0.5) | Niche, steady |
| 5.1 | Hollow Form / Martial Artist class | fix 0.5.0b May 30: no snapshot before it | 15.45% Jun 7, 12.38% Jun 27 (class 24.8 -> 23.4%) | The most played piece of 0.5 after the fix; Whirling Assault 21.3% Jun 7 |
| 5.2 | Flicker Strike | - | 3.17% Jun 7 -> 4.40% Jun 27 | Niche, rising |
| 5.3 | Olroth's Resolve (item) | fix 0.5.1 Jun 4: none before | 0.82% Jun 7 -> 3.98% Jun 27 | Rose after its fix |
| 5.4 | Sorcery Ward | 2.90% Jun 7, 2.26% Jun 17 | 1.75% Jun 27 (fix 0.5.3, Jun 18) | Already falling before; -23% after |
| 5.6 | Refutation | fix 0.5.1 Jun 4: none before | 15.20% Jun 7 -> 12.00% Jun 27 | Widely played even after the fix |
| 5.7 | Twister / Ice Shot (Spirit Walker / Deadeye class) | - | Twister 12.6%, Ice Shot 13.6% Jun 7 (classes 18.2 / 13.6%) | Matches "top of the starter lists" |
So "broken" by the ladder's measure: 4.1 and 5.1 (plus the meta 4.6, 5.7), played by 10%+ of characters, while 4.3, 4.5, 4.8, 5.2 were
niche (under ~5%). Most fixes left no visible mark on how much a piece was played.

---

## Part 2: grouped by why they broke

Ten groups. "Count" is how many of the builds above fall in each (some fall in two).

| Group | Why | Examples | Count | Can PoB calculate it? |
|---|---|---|---|---|
| A | **A "more" multiplier per unit of something** | Lightning Conduit per 5% Shock (1.4), Frenzy-consume more (2.1), hidden "after 0.5 s" more (2.2), Fresh Clip per bolt reloaded (our own lead) | 4 | **Yes**, when the mod is in PoB's data. Hidden mods (Spearfield) are invisible to PoB too |
| B | **One stat feeds damage and can be stacked** | Archmage mana (1.3), Gemling attributes (1.9), Rathpith / Atalui's life (3.2), Indigon, Whispering Ice (3.3), Hollow Palm evasion (3.4) | 6 | **Yes**, exactly. This is what the scaler scan already measures |
| C | **One stat feeds damage and defence** (a sub-case of B, the most-nerfed shape) | Mana with MoM / mana-as-ES (1.3), life with Blood Mage (3.2), evasion with Hollow Palm (3.4), ES / evasion buying Spirit (1.11) | 4 | **Yes** for damage and EHP separately; scoring both together is our job |
| D | **Trigger loops and free casts** | Cast on Freeze (1.2), Raging Spirits (1.1), Cast on Shock / Minion Death (1.10), Lightning Rod bypass (3.1), Lunar Blessing (4.2), Fury of the Mountain (4.4), Arjun's Medal (4.8), Flicker no-consume (5.2), cooldown bypass (4.10) | 9+ | **Partly.** PoB shows energy, cost and cooldown values but doesn't simulate trigger rate from kills or ailments. **Our own estimate** |
| E | **Counts without a cap, and overlapping hits** | Spirits a cast (1.1), Spark projectiles (1.3), Hexblast explosions (1.6), poison clouds (1.7), rods (3.1), Toxic Growth, Melee Splash, Lightning Arrow re-chain (4.10), Martial Artist projections (5.1), Firestorm on big bosses (1.12), Ancestral Boost targets (2.9) | 11+ | **Partly.** PoB uses config inputs ("projectiles hitting", "overlaps") that the user sets. We need **our own geometry estimate** |
| F | **Chain reactions** (a kill or ailment sets off more of the same) | Herald on-kill chains (1.5), Ice Crystals on-kill (1.5), infinite ignite / compounding ground (3.5), meteors per nearby enemy (4.1) | 4 | **No.** PoB is single-target. **Our own simulation** |
| G | **A defence reaching its cap or 100%** | Block doubling (2.3), Hyrri's evade all (2.8), Amanamu's immunity (4.3), leech stacking (4.9), Ghost Dance (3.8), Olroth's guard (5.3), Flicker (5.2), unkillable minions (4.10), armour to 0 (4.12, unconfirmed) | 9 | **Partly.** PoB computes block, evade, EHP and max hit. Uptime and immunity states are not modelled |
| H | **A conditional bonus that is always on vs bosses** | Tactician vs Immobilised (3.6), "after 0.5 s" vs a standing boss (2.2), Glacial Cascade vs Frozen (2.5), Unbound Avatar uptime (3.7), Refutation (5.6), "if not hit recently" (2.8) | 6 | **Yes**, if we know which conditions the build really keeps up. The engine already lists kept-up conditions (CLAUDE.md) |
| I | **Unique or support interaction** (two pieces together) | Tangletongue + Amazon (2.1), Rathpith + Kaom's / Atalui's (3.2), Uhtred + Meta gems (4.5), Plaguefinger elemental ailments (4.10), and our own Leopold's Applause lead | 5 | **Yes** for numbers. The interaction finder (`breaker.py pairs`) already does this |
| J | **Plain bugs** | Scaling twice (Rend, Earthquake, Hollow Palm add vs replace), supports in the wrong place (2.6), weapon-set auras (5.5), snapshotting (5.5), negative Sorcery Ward (5.4), charge double-dip, cost unpaid, endless terrain chaining | 12+ | **No.** PoB models the intended rule, not the bug. At best we can flag suspicious spots |

Patterns that matter most:
1. **About half of the big nerfs are groups B, C and E.** One stat or count grows with no ceiling. PoB can measure B and C exactly; E needs our overlap estimate.
2. **The fastest hotfixes (days, not patches) were always D, G or J:** free casts, immortality, bugs. GGG kills these mid-league; multiplier builds usually survive until the next patch. For the Breaker that means finding D, G and J pays off only in the first week. A, B, C and E finds last the whole league.
3. **New content breaks first.** 0.2's broken builds used the new Huntress class and spears, 0.4's the new Druid and lineage supports, and 0.5's the new Martial Artist ascendancy and Kalguuran items. On patch day, scan the new pieces first.
4. **GGG's fix is usually one of five moves:** cap the count, change "more" to "increased" or cut the per-unit value, add a cooldown, make it depend on Monster Power or rarity, or remove the conditional.
   A Breaker lead that is one of those five moves away from dead is high-risk to publish.

---

## Part 3: what a detector needs, group by group

| Group | What the detector checks | Uses | PoB or our own? | Status |
|---|---|---|---|---|
| A: "more" per unit | **Text scan:** every skill, support, unique and ascendancy mod matching `more .* per`, `per .* (stack\|charge\|bolt\|%)`, plus "after N seconds". Flag those whose "per" quantity can be stacked with no cap. Then add the quantity in PoB and measure **elasticity > 1** | catalog text + scaler scan | PoB | Scaler scan exists; text scan is new |
| B: stacked stat feeds damage | Scaler scan over every stat that appears in a "per X" or "X as extra" damage mod (mana, life, ES, each attribute, evasion, armour, Spirit, charges, rage, mana spent, life spent). Flag **elasticity > 1** or damage that grows with no cap | scaler scan, bigger stat list | PoB | Exists; stat list needs extending (life spent, mana spent, evasion, armour) |
| C: damage + defence from one stat | For each B lead, also measure EHP / max hit for the same stat. **Score = damage elasticity + defence elasticity.** Both above ~0.5 = the dangerous shape | scaler scan + EHP output | PoB | New, cheap: reuse the scan |
| D: trigger loops / free casts | For each trigger or meta gem, cost or cooldown mod, and "chance to not consume" mod: **our estimate of uses per second** = energy gained per second (hits/s x ailment chance x monster-power rule) / energy needed, plus cost after reductions. Flag a cost of **0 or below**, any "chance not to consume" at **100% or more**, cooldown below server tick, and **self-feeding loops** (a skill's output is its own trigger condition). Rank by triggered damage per second divided by player investment | catalog text, PoB outputs for hit rate / crit / ailment chance, our trigger model | Own estimate (rough) | New (week 2 plan) |
| E: counts / overlap | Text scan for counts with **no "maximum" / "limit"** stat (projectiles, spirits, clouds, rods, clones, explosions, chains), and for area or duration that keeps growing. Then our **overlap estimate:** how many of the N instances hit a pinnacle-sized target (boss radius, projectile spread, area radius). Compare with what PoB assumes | catalog + simple geometry model | Own estimate | New |
| F: chain reactions | Find on-kill / on-ailment effects whose output can cause the same trigger (Herald explodes → kills → explodes). Simulate a pack (e.g. 30 monsters at map density) for **average kills per player kill**; above 1 means the reaction keeps itself going | catalog + small simulation | Own simulation | New |
| G: defence caps | Per build, read block, evade, suppression-like stats, damage reduction, leech instances, guard and immunity uptime; flag any that **reach the cap** or **100% uptime**; flag "cannot die" / "immune" text paired with something that keeps it up | PoB defence outputs + text scan | Mostly PoB; uptime is ours | New |
| H: always-on conditionals | List every condition PoB turns on for the build (config) and check each is really kept up vs a pinnacle boss (immobilised, frozen, "not hit recently", buff uptime with no cooldown). **Damage with all conditions vs only the sure ones**; a big gap is a lead *and* a risk | PoB config + engine's kept-up list | PoB | Partly exists (kept-up conditions) |
| I: unique / support pairs | Interaction finder: synergy = (1+g(a+b)) / ((1+g(a))(1+g(b))). Already found the Leopold's floor-removal lead | `breaker.py pairs` | PoB | Exists. Extend to 3-piece and to "removes a floor or cap" items |
| J: bugs | Can't be calculated. Flag **suspicious spots** for Kyle to test: mods worded "instead of" / "replaces" (add vs replace bug), supports on totems / clones / triggers, effects from the inactive weapon set, anything that snapshots, and very large defence numbers (Sorcery Ward overflow) | text scan → TESTS.md | In game only | New: a "test this" list |

### Order to build (my recommendation)
1. **Text scanner over the catalog** (patterns for A, D, E, G, J). It's cheap, runs on patch day before PoB updates, and would have flagged most rows above from their item or gem text alone.
2. **Scaler scan with more stats, plus defence elasticity** (B and C): small changes to the existing scan.
3. **Trigger and free-cast estimator** (D): biggest group, fastest to get hotfixed, and PoB can't do it.
4. **Overlap estimator** (E), then the **chain-reaction simulator** (F).
5. **Defence cap checker** (G) and the always-on conditionals audit (H), which mostly reuse PoB outputs.

### Blind-test set for the rehearsal (roadmap step 4 and week 3)
If old PoB-PoE2 versions can be checked out (their git tags; not yet checked), these make good targets the Breaker should rediscover on their own patch. Each is a group PoB can calculate:
- 0.1: Archmage + mana stacking (B/C), Lightning Conduit + Shock (A), Gemling attributes (B)
- 0.2: Lightning Spear Frenzy consume + Tangletongue (A/I)
- 0.3: Rathpith + Atalui's + Undying Hate Blood Mage (B/C/I), Hollow Palm evasion (B/C), Indigon (B), Tactician vs Immobilised (H)
- 0.5 today: Martial Artist Hollow Form (E: needs the overlap estimate)

If the scan finds the 0.1 and 0.3 ones blind, the B/C detectors work. Raging Spirits, Cast on Freeze and Herald chains (D/E/F) test the new estimators.

---

## Sources

Official patch notes (pathofexile.com):
- 0.1.0d: https://www.pathofexile.com/forum/view-thread/3621299
- 0.2.0: https://www.pathofexile.com/forum/view-thread/3740562
- 0.3.0: https://www.pathofexile.com/forum/view-thread/3826682
- 0.4.0: https://www.pathofexile.com/forum/view-thread/3883495
- 0.4.0b: https://www.pathofexile.com/forum/view-thread/3890041
- 0.4.0c: https://www.pathofexile.com/forum/view-thread/3893204
- 0.4.0d: https://www.pathofexile.com/forum/view-thread/3905934
- 0.5.0: https://www.pathofexile.com/forum/view-thread/3932540
- 0.5.0b: https://www.pathofexile.com/forum/view-thread/3935437
- 0.5.0b Hotfix 12: https://www.pathofexile.com/forum/view-thread/3945119
- 0.5.1: https://www.pathofexile.com/forum/view-thread/3949197
- 0.5.3: https://www.pathofexile.com/forum/view-thread/3968601
- 0.5.5: https://www.pathofexile.com/forum/view-thread/4000864
- Patch notes index: https://www.pathofexile.com/forum/view-forum/2212

Community and press (used for strength and "why"):
- Maxroll: https://maxroll.gg/poe2/news/raging-spirit-and-meta-gem-hotfix-announced , https://maxroll.gg/poe2/meta/the-build-meta ,
  https://maxroll.gg/poe2/build-guides/spark-lightning-conduit-stormweaver , https://maxroll.gg/poe2/build-guides/shattering-palm-invoker-build-guide ,
  https://maxroll.gg/poe2/build-guides/lightning-spear-amazon , https://maxroll.gg/poe2/news/patch-notes-for-0-5-0b
- Mobalytics: https://mobalytics.gg/poe-2/guides/0-2-0-archmage-nerf , https://mobalytics.gg/poe-2/guides/dawn-of-the-hunt-class-buffs-nerfs
- Reddit 0.1.0d thread (via mirror): https://lr.us.psf.lt/r/PathOfExile2/comments/1hcb0hv/010d_patch_notes/
- Comicbook (Cast on Freeze): https://comicbook.com/gaming/news/path-of-exile-poe-2-update-patch-notes-cast-on-freeze
- IGGM 0.3 winners and losers: https://www.iggm.com/news/poe-2-patch-0-3-0-winners-and-losers
- Hollow Palm 0.4 forum thread: https://www.pathofexile.com/forum/view-thread/3884131
- poe-vault 0.3.0b: https://poe-vault.com/poe2/news/poe2s-patch-0-3-0b-fixes-the-fun-with-nerfs-to-popular-builds
- gamer.org 0.5 nerfs explained: https://www.gamer.org/path-of-exile-2-patch-0-5-return-of-the-ancients-every-major-nerf-buff-and-change-explained/
- Vulkk (Flicker Strike cap): https://vulkk.com/2026/06/08/path-of-exile-2-updates-expand-the-passive-tree-and-adjust-endgame-rewards/
- poetrades patch history (armour claim, unconfirmed): https://poetrades.net/poe2-patch-notes/
