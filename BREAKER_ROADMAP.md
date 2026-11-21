# Breaker game plan (roadmap to PoE 2 1.0, Dec 11 2026)

Agreed with Kyle on 2026-11-18. When Kyle says "the game plan" or "the roadmap" for the Breaker, he means this file.
The Breaker's job: find broken, over-powered builds nobody has found yet, and have them ready for 1.0 before
Mobalytics and poe.ninja do. Status and leads live in `BREAKER.md`; this file is the plan.

## What the Breaker is (vs Whetstone)
| | Whetstone build | Breaker |
|---|---|---|
| Starts from | A player's request ("lightning minion monk") | No request: it hunts on its own |
| Question | What's the strongest build for this? | Where does the maths break? |
| Method | Tries skills, weapons, ascendancies; keeps the best; gear, tree, 7 stages | Pokes finished builds one stat (or pair) at a time and flags outsized jumps |
| Output | A finished guide | Leads, which become full builds and in-game test requests |

What it can find, once fully built:
| Kind | Finds it? |
|---|---|
| Multiplier stacking, below-0% penetration, one stat scaling without limit | Yes, on its own (PoB calculates these exactly) |
| Trigger loops, free casts | Yes, with our own trigger-rate estimates (rough; confirm in game) |
| Chain reactions, overlapping hits | Likely ones, with our own estimates (confirm in game) |
| 3+ piece combos | More of them via wider overnight searches; can't try everything |
| In-game bugs | Mostly no; it can only flag suspicious spots and look for outside evidence |
| Brand-new 1.0 mechanics | Claude theory from patch notes until PoB supports them |

## Timeline
| When | What gets built | Who works |
|---|---|---|
| Week 1 (Nov 18-24) | Research: every past PoE 2 patch's broken builds, sorted by why they broke (`research/broken_builds.md`). Blind test: can the Breaker find poe.ninja's top builds without seeing them? | Claude sessions with Kyle + overnight research |
| Week 2 (Nov 25-Dec 1) | New detectors from the research: trigger loops, chain reactions, 3-piece combos, unique + support combos. Leads become full Whetstone builds automatically; the best get evidence checks (TESTS.md). | Sessions with Kyle; overnight scans test them |
| Week 3 (Dec 2-8) | Patch-notes mode, practised on a past patch (notes -> exact number changes -> scan the "patched" game -> compare with what really happened). Discoveries page and launch-day playbook. | Same |
| Patch notes drop (2-7 days before 1.0) | Kyle hands over the notes. Overnight scans on patched data, Claude theory for new mechanics, test requests for the strongest leads. | Automatic overnight; Kyle tests in game |
| Launch day | Re-check every lead on real 1.0 data, publish what holds up (ask Kyle first). | |

## How the automation works
- Nights: the engine runs scans and sweeps on the server (no Claude usage), plus 1-2 short Claude check-ins and a
  morning report (`MORNING_REPORT.md`, one ntfy ping at 8 am Mazatlan at the earliest).
- Building the Breaker itself (new detectors, patch-notes mode) happens in sessions where Kyle can steer.
- Lead checks (Kyle 2026-11-21: no in-game tests possible): Claude checks leads from game data, web evidence and
  ladder data (`TESTS.md`); what none of them settles is shown as "PoB says, not confirmed in game", cautious number.
- Usage: Kyle is on Pro. If the build-out weeks hit the limit, upgrading to Max for 1.0 month is his call.

## Progress
- 2026-11-18: research done (`research/broken_builds.md`: 10 groups of why builds broke). Text scanner built
  (`engine/text_scan.py`, risky wording, `diff` for patch day). Condition scan built (`engine/condition_scan.py`):
  rediscovered Lightning Conduit + Shock (a 0.1 broken build) blind, found the Armour Broken combo family. One-command
  patch-day run built (`engine/tools/breaker_day.sh`). Hexblast scoring fixed (usage limits). Still to do in week 1:
  blind test against poe.ninja's top builds. Week 2 starts with the combo finder's scoring (setup + payoff).
