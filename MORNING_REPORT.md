# Morning report, Saturday 2026-11-21

**Note:** this check-in wasn't allowed to pull the latest changes from the server, so it read the copy already on this machine. The server session may have done more than what's listed here.

## Server session
- **Finished:** the blind test against poe.ninja's top builds (task 7), the Druid weapon trial (task 20, tried and undone because it made results worse), and the Huntress spear skills check (task 22). Task 22 found that Twister gets about 4x more damage when Whirling Slash builds up a whirlwind first, but we never set that combo up. Skills that charge up in stages (like Flameblast) were never charged either.
- **Working on:** a script running on its own runs the full test suite, then puts out engine 2026-11-21.3 if every test passes. After that comes task 23 (the whirlwind combo and the stage rules), then task 21 (infusions).
- **Waiting for Kyle:** should the Lodestone page go public? Also your in-game tests (TESTS.md, when you're back around 11-27) and switching the Cloudflare branch (task 17).

## Messages held overnight
- The Breaker queue finished two blind-test runs (11:04 and 13:05 server time), with nothing failing either time.

## Nightly A-to-Z sweep
- **The sweep was skipped all three nights (11-19, 11-20, 11-21)** because the Breaker queue was busy each time.
- The latest results are from 11-19: 19 builds finished, **0 passed every check**.
- **Most common failure: too slow.** All 19 builds took 35-43 minutes, over the time limit.
- One other failure: the Witchhunter Mid Endgame crossbow needs 89 Strength and the build has 79.
- **Hung builds:** none recorded.

## Breaker / Lodestone
- The queue is idle. Its last job was a blind test with nothing failing.
- Blind test score: 3 of the ladder's top 20 skills found (Comet, Ice Shot, Rend). Our ascendancy ranking matches how popular each one is only loosely (0.25, where 1 would be the same order).
- **Lead:** the Whirling Slash into Twister combo. Twister looks strong once it's set up properly, so it should show up in results after task 23.
- **Possible bug:** the combo checker may score the boss skill on the second weapon set the same as the main skill (open check in NIGHT_TASKS).

## 3 most useful next steps
1. Do task 23 (whirlwind combo and charge-up stages), then run the blind test again for the Huntress classes.
2. Get the nightly sweep running again: start it after the queue finishes instead of skipping when the queue is busy. Then fix build speed, since every build fails only on time.
3. Fix the Witchhunter Strength shortfall and confirm the boss-skill scoring check.
