# Morning report, Thu 2026-11-26 (08:00 Mazatlan)

## Server session
- Finished since yesterday: task 39 closed (the search's top pick is the best full Uber build in 5 of 6 classes), task 49 live (engine 2026-11-26.1, ranged distance), task 50 live, `asccond` merged (task 48's scan tool), task 42 ticked, task 53 prepared (needs the live game).
- Now: tonight's sweep is running. Task 48's scan (~15 hours, my estimate from the notes) starts by itself when the sweep ends.
- Waiting for Kyle: nothing blocking. Two open questions, both optional: (1) several gear orders in Whetstone guides (about 3x slower, up to +39% boss damage); my recommendation is no by default. (2) What the class-weapon rule costs players.
- Held-back messages: none (pending list was empty).

## Nightly sweep (one fifth of the classes, 5 builds)
- Started 09:38 UTC. 4 of 5 builds finished; the 5th (Acolyte of Chayula) was still running when I checked. It is not hung yet: each build may take up to 2 hours.
- **Passed every check: 0 of 4.**
- Builds: Bonestorm Infernalist 8.84M, Bonestorm Chronomancer 3.53M, Rapid Shot Tactician 2.67M, Rain of Arrows Pathfinder 0.97M DPS.
- Most common failures:
  - "Made-up gem: Fire Spell on Melee Hit": 3 of 4 builds, in every stage the check looks at. This support was added on purpose on 11-21 (task 15). So most likely the check doesn't know about it, or this PoB version doesn't have the gem. This is a guess: I didn't check which one it is.
  - Slow: all 4 builds took 68-85 minutes.
  - A Megalomaniac jewel in the Uber stage gives nothing (PoB reads no mods on it): 3 of 4 builds.
- Timed out (hung): none so far.

## Possible bugs and leads
- Fire Spell on Melee Hit, above: either the check is wrong or the guides suggest a gem players can't get. It needs a look before anyone trusts those guides.
- The Megalomaniac jewel takes up a slot and adds nothing. Probably a bug.
- No new Lodestone leads tonight.

## 3 next steps
1. Check whether Fire Spell on Melee Hit is a real gem in this PoB version. Fix either the check or the guides.
2. Find out why the Megalomaniac jewel has no mods, and stop putting empty jewels in builds.
3. Let the sweep finish, then make sure task 48's scan really starts (~/task48.log).

Not checked: the sweep's JSON file (I used its log) and anything in the queue log after the sweep started.
