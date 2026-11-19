# Morning report: Thursday 2026-11-19, 7 am Mazatlan

## Night tasks (server session)
- Finished: 1 (spirit overdrawn at Uber), 2 (attribute shortfalls), 3 (Detonate Dead limit), 4 (build speed, measured
  only), 5 (matrix report by skill family), 6 (Lodestone page, unlisted), 8 (in-game test list), 13 (pairs fix).
  14 half done: ailment combos (Dark Effigy + poison +69% on pinnacle bosses; shock can't be kept up on bosses).
- Now: running on its own with no Claude, to save usage until the Friday ~5 am reset. Blind test (7) and the
  per-ascendancy re-runs (12) are queued to start after the current jobs.
- Waiting for Kyle: should the Lodestone page go public (link from the home page)? It is live but hidden.

## Held-back message from last night
- 9:16 pm: Breaker queue finished the condition scans for 23 ascendancies and the unique x skill matrix, 0 failed.

## Nightly A-to-Z sweep (still running: 18 of 23 done)
- Builds finished: 14. Passed every check: 0.
- Most common failure: "slow". Every finished build took 35-43 minutes (limit for a pass is lower).
- One real gap: Witchhunter at Mid Endgame is 10 Strength short for its crossbow (79 of 89).
- Timed out (hung past 45 min): 4 of 18: Smith of Kitava, Stormweaver, Spirit Walker, Ritualist.
- The 4 o'clock sweep was skipped because this one was still running (expected).
- Top damage: Tactician Rapid Shot 6.5M, Lich Bone Cage 6.4M, Blood Mage Ember Fusillade 5.5M.

## Looks like a bug
1. When a sweep build times out, the sweep can't write it into its results file (permission denied). So those 4
   timeouts are missing from the results file, only in the log.
2. The Breaker queue's per-ascendancy matrix results ran fine (23 of 23) but hit a git clash on one file
   (Oracle) when saving. They may not have been pushed; the server repo may be stuck mid-merge.
3. Note: last night's matrix run was before the ascendancy fix (task 5 found the scans skipped ascendancy passives),
   so it gets redone anyway in task 12.

## 3 most useful next steps
1. Fix the git clash in the Breaker folder on the server and push the matrix results, so the queued re-runs
   (tasks 7 and 12) start from a clean state.
2. Fix the file permission on the sweep results so timeouts get recorded.
3. Build speed: all builds are near the 45-minute limit on the server; 4 of 18 hung. Try the idea from task 4
   (check fewer supports for extra skills) after the reset.

(This check-in could not pull the latest changes or read some server logs without permission; numbers above are from
the files it could read.)
