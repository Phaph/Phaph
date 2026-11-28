# Morning report, Sat 2026-11-28 (08:00 Mazatlan)

Note: this check-in could not run `git pull` (it needed an approval nobody was there to give), so it read the
repo as it was locally. The newest commit seen was 2520c92 (task 58).

## What the server session did
- **Task 48 closed (10:20 Berlin):** the blind re-run without class rules is done. Bonestorm came out #1 for all
  23 ascendancies. It found 0 of the 69 ladder top-3 builds (the 11-23 run found 5). This is not a find:
  earlier checks showed the search over-rates Bonestorm about 1.8x against its full build.
- **Task 58 added:** a new bug the sweep found (see below).
- **Queued:** task 38's finalists re-run (all 17 weapons, best of 3 orders). It starts by itself when the sweep ends.
- **Waiting for you:** task 57, Mageblood / Megalomaniac rolls. Guides currently pick the best roll for the
  build. With a typical roll, boss damage moves -30% / +12% / -37% / -50% on the 4 builds tested, and the engine
  swaps Mageblood out for a rare belt in 9 of 12 rows. Should guides use a typical roll and list the best rolls
  as "hunt for"? Saying yes also means changing one line of page text.
- Messages held overnight: none (the pending list was empty).

## Saturday A-to-Z sweep (all 23 ascendancies)
- Started 10:10 Berlin. **6 of 23 builds finished so far**, the 7th (Titan) is running.
- **Passed every check: 0 of 6.** Every one was flagged "slow": 53 to 63 minutes each.
- **Timed out (hung): none** (the limit is 2 hours per build).
- Other failure: 1 of 6 (Deadeye, Rain of Arrows). Its Interludes body armour needs 46 Strength and the
  build has 37. That is task 58.
- Builds so far, boss damage: Bonestorm Infernalist 8.84M, Lich 4.68M, Abyssal Lich 4.57M, Blood Mage 3.49M;
  Rain of Arrows Pathfinder 0.97M, Deadeye 0.69M.
- At about 57 minutes a build, the last 17 builds need roughly 16 more hours. My estimate is that it ends
  around Sunday 08:00 Berlin. The plan in the notes said 17 hours in total, which looks too short.
- Breaker queue: it held the sweep back from 05:00 until the blind re-run freed the server at 10:10. No errors.

## Bugs and leads
- **Bug (task 58):** the last gear pass only puts a soft penalty on a slot that is short of attributes. So an
  armour piece the character can't actually wear can stay in the guide. This is the second time it has shown up
  (the first was 11-19).
- **Every build is "slow":** builds take about an hour each on 6 cores. This is known (task 4), but nothing
  passes the sweep while the slow check stays as it is.
- **No new Lodestone lead.** Bonestorm topping all 23 is most likely our search over-rating it (see above).

## 3 most useful next steps
1. Answer task 57 (typical or best roll for Mageblood / Megalomaniac). It is the only thing waiting on you.
2. Fix task 58: once the last gear pass is done, any slot still short of attributes gets a base the
   character can wear.
3. Decide what "slow" should mean, either a higher limit or faster builds. Right now it fails every build,
   so the sweep's pass count tells us nothing.
