# Morning report: Wednesday 2026-11-25 (8 am Mazatlan)

## The server session
- **Finished and live since yesterday's report:**
  - Support gems are now also tried without the ones that block ailments: 2 of 24 saved setups gain (+42%), none lose.
  - Temporary minions are no longer overcounted (an Unearth build showed a false 15.6M).
  - Uniques are checked again at the end of gearing. In the test, 5 of 12 builds changed: boss damage up in all 5
    (x1.02 to x3.09). One lost 25% toughness in that test; rebuilt on current code, it gained 18%.
  - Support choices for side skills now keep at least 90% of the build's toughness.
- **Finished measuring:**
  - Lodestone's grade on old patches failed: 2 of 11 known cases found, 11 real finds against 129 false alarms.
    The page's claim was narrowed.
  - The launch-day rehearsal took 24 minutes. After fixes, a test patch had all 3 made-up changes found, no false alarms.
  - The biggest damage moves since Nov 18 were traced to our own fixes.
- **On now: a live bug in ascendancy points.** Some choices are never tried (such as the Gemling +2 skill levels),
  Abyssal Lich spends 0 of its 8 points, and other classes leave points unspent. The fix is written but not merged.
  Its first test run had 2 failures (put down to the new tests); the second run is under way. Of the 5 before/after
  builds, 2 are built with the fix; none of the "before" builds yet, so there is no verdict.
- **Also running:** a check of the search's picks against full builds (4 of 6 searches done, builds next).
- **Waiting for you (nothing blocking):** (1) Should Whetstone guides try several gear orders? Best of 3 gave 0-39%
  more boss damage on 4 builds, for about 3x the Uber stage's time. The session suggests not by default. (2) The Whetstone
  class-weapon rule, once there are cost numbers.
- **Held messages:** none.

## The A-to-Z sweep
- **No sweep ran last night: the queue was busy.** 0 new builds finished, passed or timed out.
- The files still hold yesterday's run, already reported: 4 finished, 0 passed every check, 0 timed out. Most common
  failures: too slow (4), a made-up gem (3, all Abyssal Lich), an unreadable jewel (1), missing Act 1 supports (1).

## The Breaker queue
- **Per-ascendancy scan: on 20 of 23** (19 walked through). No results to quote: Infernalist mixes old and new data,
  and the ascendancy bug affects the whole set, so it must be redone after the fix.
- No failures or timeouts logged in this run. Invoker had been going about 45 minutes at check time, against 15-30 for
  the others. The server is busy, so it may just be slow. I did not check whether it is hung.

## Bugs and leads
- **Bug:** the ascendancy points problem above. It touches live builds and every comparison between ascendancies.
- **Still listed in the notes' last sweep, no fix seen:** the made-up gem, the unreadable jewel, the missing supports.
- **Leads (re-run in 3 gear orders each, 8 of 8 done):** none clearly strong and new.
  - Bonestorm beats Comet in all 3 orders (+18% to +82%), but is marked as already known.
  - Dark Effigy with poison gains 42% in all 3 orders, but is weak overall (1.03M).
  - Rain of Arrows wins all 3 orders, but rests on our guess of its hit radius: unconfirmed.
  - These runs predate the ascendancy fix.
- **Order luck is smaller, not gone:** 3 of 4 test builds still vary by more than 10%.

## The 3 most useful next steps
1. **Finish the ascendancy fix test,** and merge only if no build loses.
2. **Then redo the per-ascendancy scans and the blind test,** since today's numbers have the bug in them.
3. **Let a nightly sweep run on the fixed version,** and fix the made-up gem, the jewel and the missing supports.

Note: git pull was not allowed in this check-in. The local copy matched its last known remote.
