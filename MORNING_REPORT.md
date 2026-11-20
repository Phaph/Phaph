# Morning report, 2026-11-20

## Overnight
- The Lodestone queue finished at about 3:20 am Mazatlan with nothing failed. It ran three jobs: the blind test against the ladder's top builds, the condition scan for all 23 ascendancies, and the unique and keystone scan for all 23. These were the first scans to include ascendancy passives. All three were saved to the repo.
- There was no nightly A-to-Z sweep on either night (19th and 20th), because the queue was busy both times. The newest sweep results are still the ones from the 19th.
- Messages held back during quiet hours: only the "queue finished" note above.

## Task list
- Done: tasks 1-6, 8, 13 and 18. Task 18 was the Ember Fusillade fix. It now gets 10 embers per cast and then waits, and the fix is committed.
- Next: after the fix, a follow-up script runs the test suite, deploys the engine and re-runs the blind test. Its logs are still empty, so it hasn't reported anything yet.
- Tasks 7 and 12 have their scans finished. They still need their write-up in BREAKER.md and their boxes ticked.
- Waiting for Kyle: should the Lodestone page go public? It is live but unlisted.

## Last A-to-Z sweep (19th, 23 builds)
- 19 builds finished. **None passed every check.**
- The most common failure was speed: all 19 took 35-43 minutes each. One Witchhunter build was also short on Strength for its Mid Endgame crossbow (79 of 89 needed).
- 4 builds hung and were stopped: Smith of Kitava, Stormweaver, Spirit Walker and Ritualist. Their timeouts weren't recorded in the results file because of a file permission problem. This is already on the list as a known bug.

## Leads and possible bugs
- The blind test from before the fix picked Ember Fusillade for every ascendancy, so it matched only 2 of the ladder's top 20 skills (Spark and Comet). This was a modelling bug, not a lead. The re-run will show whether the fix helped.
- Ember Fusillade and Bone Cage also won most caster builds in the sweep. That points the same way: Ember Fusillade was rated too high before the fix.

## 3 most useful next steps
1. Check that the follow-up script ran: tests green, engine deployed and the blind test re-run. Then compare the new blind test with the old 2 out of 20.
2. Fix the sweep's file permission problem so hung builds get recorded. Then run a fresh A-to-Z sweep now that the queue is free.
3. Work on build speed, since every build fails the time check. The best idea so far is to test extra skills only with the supports made for them.
