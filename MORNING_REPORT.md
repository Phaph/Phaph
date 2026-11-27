# Morning report, Fri 2026-11-27

## Last night's test sweep (5 builds)
- **4 of 5 builds finished. 1 of 5 passed every check** (Witchhunter Rapid Shot, 5.2M damage at Uber). That 1 is on a loose reading: its only flag was "slow", and every build was slow.
- **The most common problems:**
  - All 5 were slow: 53 to 79 minutes each.
  - 3 builds (Blood Mage, Titan, Oracle) were flagged for a "made-up gem, Fire Spell on Melee Hit". The checker was wrong about this, not the builds. The server session fixed the checker this morning.
  - Blood Mage: Path of Building read no stats off a Megalomaniac jewel. The game does use the jewel. Only the jewel's description text was wrong, and that is fixed and live.
- **1 build crashed:** Disciple of Varashta Bonestorm died after 79 minutes. The engine couldn't read gem names that have a comma in them (the 3 djinn gems). Fixed and live since 12:03 Berlin time.
- **Nothing hung.** No build timed out.
- I haven't checked whether these fixes work on a full sweep yet. Tonight's sweep will show that.

## What the server session finished
- Task 48 (scan of conditional ascendancy passives): done 05:42.
- Task 56 (fixes from the sweep): the culling fix, the checker fix, the Megalomaniac text and the comma gem names are all live, now at engine 2026-11-27.3 with 256 tests passing. Still open: the next sweep and one question about Deathblow.
- Mageblood check: of the 18 saved top builds, 16 already wore Mageblood.

## What it's working on now
- Task 51: re-testing Lodestone on old patches. The server is full with this (6 cores).
- The Mageblood "typical roll" test: 7 of 8 done. On builds getting a normal roll instead of the best one, top damage drops 30% to 66%. That is one test run per build, so it's not a final answer yet.

## Waiting for you
1. **Mageblood and Megalomaniac rolls:** should guides show a typical roll and list the best rolls as "worth hunting for"? This needs a one-line page change, so it's your call.
2. Trying several gear orders in Whetstone guides: Claude says not by default (it takes about 3x as long). Nothing is blocked on this.
3. Class-weapon rule for Whetstone: still waiting on a test run before we ask you.

## Held messages (sent during quiet hours)
- Mageblood: 16 of 18 test builds already wore it. A typical roll scores 7-52% lower on 17 of 18. Switch to typical rolls?
- The Breaker queue finished last night's sweep with "0 failed". That means the job ran to the end. It does not mean the builds passed (see above).

## Lodestone leads
- Nothing new from the sweep.

## 3 most useful next steps
1. Answer the Mageblood question above.
2. Let tonight's sweep confirm the fixes, especially that Disciple of Varashta now finishes.
3. Look into why every build takes about an hour. That is far too slow for launch day.

Note: I couldn't pull the latest changes this morning (the command needed approval), so this report is based on the copy from about 15:30 Berlin time.
