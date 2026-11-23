# Lodestone launch-day playbook (PoE 2 1.0, Dec 11 2026)

What to do, in order, from the moment GGG posts the 1.0 patch notes until launch. Lodestone = the Breaker (code name).
Every step names its tool and what it writes. Claude runs it; Kyle decides anything public (CLAUDE.md: ask before
publishing). Times assume the server (8 cores); heavy runs go through the Breaker queue (`engine/tools/breaker_queue.sh`).

## 0. Before the notes (any day before)
- Engine and site on the latest PoB that loads (setup.sh POB_REF), full suite green, `status.sh` clean.
- Baseline for the diff: `engine/data/breaker/text_scan.json`, `unsupported.json` committed from the current game.
- `engine/data/patches/` has the format (example.json, 0_5_1.json, 0_5_2.json). The grading tool works
  (`tools/patch_check.py`). No in-game tests: evidence checks only (TESTS.md header).

## 1. Notes -> changes file (Claude, ~1-3 h, the day the notes drop)
1. Fetch the notes (poe2db.tw/Version_1.0 or the official forum post; a laptop session if the server is blocked).
2. Write `engine/data/patches/1_0.json`: one entry per note line that changes a number or a rule, the note line kept:
   - gems: `{"gem": ..., "base_multiplier" | "level" | "constant" | "scale" | "add" | "remove" | "rename" | "require_types"}`
     (`"id"` for a triggered part); uniques: `{"unique": ..., "replace": [[old, new]], "add": [...]}`;
     passives and keystones: `{"passive": ..., "replace": [[old, new]], "add": [...]}` (runner `node_debug` shows a
     node's lines and parsed mods before and after).
   - base items: `{"base": "Ornate Ringmail", "armour": {"Armour": 725}}` (also weapon / req / flask / charm).
   - What can't be written yet goes under `"not_expressible_yet"`: socket types, rule changes ("cooldown no longer recovers while ..."), brand-new skills and items.
3. Check it applies: `PATCH_FILE=engine/data/patches/1_0.json` + any small run; `pob.patched` lists every change.

## 2. Scan the patched game (no Claude, ~1-12 h)
- `PATCH=engine/data/patches/1_0.json engine/tools/breaker_day.sh` (text scan + diff vs the baseline, condition scan,
  unsupported lines; `SCALER=1` adds the scaler scan): writes `engine/data/breaker/day/<date>/` + SUMMARY.md.
- Blind-style search per ascendancy on the patched game: `PATCH_FILE=... python tools/blind_test.py run` (no
  class-weapon rule: Lodestone mixes any class and weapon), ~12 h on 6 cores.
- The 1.0-new things (new skills / uniques PoB doesn't have yet) can't be scanned: Claude reads them as theory
  (step 4) until PoB adds them.

## 3. Turn findings into leads (Claude)
- Candidates: text_new.txt (new or changed risky wording first: research/broken_builds.md pattern 3), condition
  payoffs, the blind run's "top 3 by us, under 1% played" list, anything the patch buffed hard.
- **The full-build bar** (`tools/lead_builds.py`, a `build` entry per lead in leads.json): a lead counts only if its
  full Uber Endgame build beats the plain build (or the popular skill: `vs_spec`) on the same engine. Interaction
  leads have faded to 0-11% every time so far (BREAKER.md table): don't announce anything that hasn't passed it.
- **Sanity first for anything that wins everywhere** (Bonestorm 2026-11-22: PoB didn't count its release time):
  look for time or uptime PoB doesn't count (usage limits: Hexblast, Detonate Dead, Ember Fusillade, Rain of
  Arrows, Oil Barrage, Bonestorm) and for unsupported unique lines (unsupported.txt) before calling it a break.
- Evidence checks (TESTS.md): game data, web (guides, forum, patch notes), ladder share. Status in leads.json:
  unconfirmed / confirmed / dead / fixed / known.

## 4. New mechanics without PoB support (Claude)
- Read each new skill / support / unique / keystone in the notes, write what it would multiply and with what
  (a short note per item in BREAKER.md), and flag the ones that look like past broken builds (broken_builds.md
  groups). Mark them "theory, not measured" on the Lodestone page.

## 5. When PoB adds 1.0 (usually within days)
- Staging first (LAUNCH_1.0.md for Whetstone): new POB_REF, full suite, the data tools again.
- Re-run step 2 on the real data without PATCH; compare with our patched predictions (`tools/patch_check.py`
  per gem) and re-check every lead through the full-build bar.

## 6. Launch day
- Re-check every open lead on real 1.0 data (lead_builds.py).
- Lodestone page stays unlisted (Kyle 2026-11-22); results live there and in BREAKER.md.
- Publishing anything (a build page, Mobalytics, a post): Kyle decides, case by case.

## Who does what
| Step | Runs | Kyle |
|---|---|---|
| 1 notes -> changes | Claude session | - |
| 2 scans | server queue, no Claude | - |
| 3-4 leads, theory | Claude session | reads the Lodestone page |
| 5 PoB update | Claude session + staging | OK the switch |
| 6 publish | - | decides |
