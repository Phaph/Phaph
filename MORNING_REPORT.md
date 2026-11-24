# Morning report: Monday 2026-11-23 (8 am Mazatlan)

## What the server did overnight
- **Finished:** the blind test without class rules (Lodestone style) ran to the end at about 12:20 server time.
  The results file is there. I could not confirm from git whether it has been committed.
- **Running now:** the nightly A-to-Z build sweep. It started late (11:24 UTC), because it waited for the blind test.
  Next in line: the weapon finalists run (task 38, ~12 h), then the per-ascendancy rescans (task 37).
- **Waiting for you (nothing blocking):** (1) should Whetstone keep its class-weapon rule? The cost numbers will come
  once the finalists run is done. (2) Two small text fixes on the Lodestone page, but only if you OK page work.
- No messages were held back overnight. The phone queue was empty.

## The A-to-Z sweep: a problem
- **0 builds finished so far. All 4 builds tried so far hit the 45-minute limit and were stopped:**
  Infernalist, Blood Mage, Lich, Abyssal Lich. Deadeye is running now.
- This looks like a setup problem, not a crash. This is the first sweep that uses the new "pick the skill by its
  endgame build" step plus the leveling plan. In a trial, one build with that step took about 2.5 hours on this
  server. The sweep still stops each build after 45 minutes, so every build will time out.
- If nothing changes, the sweep will spend about 17 hours making no builds, and it holds up the finalists run behind it.

## Blind test without class rules: Bonestorm everywhere
- Bonestorm with a staff was the top pick on all 23 ascendancies, even after last night's Bonestorm fix.
- It found only 1 of the ladder's 20 most played skills (Comet). The match with what players actually play is weak (0.20).
- This is the known problem from task 38: the quick search scores staff spells about 10 times higher than attacks.
  Full endgame builds put them about level. So it is a bug in how we score, not a real lead. The finalists run
  (full builds per weapon type) is the planned fix.

## The 3 most useful next steps
1. **Stop wasting the sweep:** give each build a time limit that fits the new endgame step (about 3 hours), or switch
   that step off for the sweep. Then restart today's slice. Otherwise the night is lost and the finalists run is stuck
   behind it.
2. **Let the finalists run go next:** it is the real test of which weapon and skill is strongest when the search
   can't be trusted across weapon types.
3. **Commit the blind test results** if they are not committed yet, and note in the write-up that Bonestorm sweeping
   every class is the scoring bug, not a find.

Note: this check-in could not run git here (the commands need approval), so it may not have the latest pushed notes.
