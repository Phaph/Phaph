# Morning report: Tuesday 2026-11-24 (8 am Mazatlan)

## The server session
- **Finished and live:** bows, wands, sceptres and other one-handed weapons now get an off-hand item (quiver, focus,
  shield or second weapon). In early tests a quiver added 43-46% damage and a focus 64-79%. Also live: a fix for
  a filler support gem that could eat most of a build's life (its effect on damage is not measured yet).
- **Finished measuring:**
  - Same build, gear made in a different order: damage changes by 5% (Ice Shot), 22% (Rapid Shot), 68% (Bonestorm)
    and 320% (Rain of Arrows). The target was 10%.
  - Enemy-condition check: 1 of 8 builds gains from it (Bonestorm, +42%); the other 7 gain nothing.
- **On now:** testing a fix for that order luck. At the last note (5 of 12 builds done) it was not a clean win:
  Rain of Arrows went from 849k to 3.66M one way, but from 3.46M down to 1.74M the other way. Not merged.
- **Also in progress:** grading Lodestone on old patches, and the off-hand finalists run with the per-ascendancy
  rescans after it. The notes list these as running or queued; I did not check that they are still alive.
- **Waiting for you (nothing blocking):** (1) whether to trim the endgame pick (saves about 7 minutes, can slightly
  change the pick); (2) the Whetstone class-weapon rule, once there are cost numbers; (3) two small Lodestone page
  text fixes, only if you OK page work.
- **Held messages:** the missing off-hands (since fixed and live), and "Breaker queue finished: sweep (0 failed)".

## The A-to-Z sweep (one fifth of the ascendancies)
- **4 of 4 builds finished, 0 passed every check, 0 timed out.** Yesterday the first 4 all hit the 45-minute limit;
  the limit is now 2 hours.

| Build | Damage | Time | Problems |
|---|---|---|---|
| Abyssal Lich, Bonestorm | 3.77M | 48 min | 5 |
| Smith of Kitava, Supercharged Slam | 3.38M | 50 min | only slow |
| Spirit Walker, Lightning Spear | 1.15M | 72 min | 2 |
| Martial Artist, Flicker Strike | 1.93M | 59 min | only slow |

- **Most common failures:** too slow (all 4; other jobs shared the server, so some of this may be load), then a
  made-up gem ("Fire Spell on Melee Hit") 3 times, all in the Abyssal Lich build.
- "0 failed" in the queue message means the job ran to the end. It does not mean the builds passed.
- The queue log's per-ascendancy results for this run are the 4 builds above. It waited over 5 hours for another scan.

## Bugs and leads
- **Likely bugs:** a gem players can't get is put in the Abyssal Lich build; a Megalomaniac jewel with no readable
  stats in its endgame; Lightning Spear has no support gems in Act 1.
- **No leads to quote.** Order luck can move a build's damage up to 4 times, so close rankings can't be trusted yet.
- **Lodestone grade so far is weak:** on 0.3, the main scan found 0 of 4 known cases (2 could not be tested) with 14
  false alarms. The stack scan's one flag was a false alarm.

## The 3 most useful next steps
1. **Finish the order-luck test** and find out why Rain of Arrows lost half its damage before merging anything.
2. **Fix the made-up gem, the empty jewel and the missing Act 1 supports.** They can reach players' guides.
3. **Cut Lodestone's false alarms,** or narrow what it claims, before the early December grade.

Note: git pull was not allowed in this check-in. The local copy matched its last known remote, and its newest
commit is from 15:26 server time.
