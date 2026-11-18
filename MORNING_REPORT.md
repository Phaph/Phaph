# Morning report, Nov 18 2026

**The overnight A-to-Z sweep is still running.** It started at 07:20 UTC and has reached build 10 of 23 (Stormweaver). Each build takes about 42 to 45 minutes, so the rest will take roughly 10 more hours.

## So far (9 builds)
- **5 finished:** Infernalist, Lich, Abyssal Lich, Deadeye, Pathfinder.
- **None passed every check.** The only problem on all 5 was "slow": each one took 41 to 45 minutes, just under the 45-minute limit.
- **4 timed out (stopped at 45 minutes):** Blood Mage, Titan, Warbringer, Smith of Kitava. The finished builds came in only just under the limit, so these are probably just slow too, not stuck.
- Best final damage: Infernalist at 13.3 million. The others ended between 5.2 and 7.3 million.
- The old problems ("spirit overdrawn", "abyssal" not understood) did not come back. "Abyssal Lich" is now read correctly. The "2 of N pass" lines in the log still count leftover results from the old budget-based run, so ignore those.

## Looks like a bug
- **Every build picked the same thing: Hexblast with a staff.** That includes the Ranger builds (Deadeye, Pathfinder), which should almost never end up on a Witch spell with a staff. Their Act 1 damage is also very low (258, compared with about 850 for the Witches). The step that picks the skill and weapon seems to fall back to one default.
- No new Breaker leads tonight.

## Tonight's research
`research/broken_builds.md` covers broken builds from patches 0.1 to 0.5.5. It sorts them into 10 groups and finds that about half of the big nerfs came from one stat or count that could grow with no limit. It recommends building a text scanner over the game data first.

## 3 most useful next steps
1. **Fix the skill and weapon picker** so each class gets its own skill. Until then the sweep only tests Hexblast.
2. **Make each build faster.** 45 minutes per build makes the sweep take about 17 hours, and the slow ones time out. Find the slowest step, probably the late-game tree or gear passes.
3. **Start the Breaker text scanner** that the research recommends. It is cheap and can run on patch day.
