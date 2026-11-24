# START HERE (handoff, updated 2026-11-22 evening)
Fresh session? Read this block, then CLAUDE.md and BREAKER.md's last sections. Sessions are short now (Kyle,
2026-11-20): one task or working block per session, write state back here before stopping.
- **Running (2026-11-24 03:30 Berlin):** engine 2026-11-24.2 live (224 tests), finalists restarted at 03:29 with 3 builds at once. How: ~/after_fulldps.sh: full suite -> if green deploy engine 2026-11-24.2 (extra
  stat sets fix) and restart ~/after_sweep.sh from scratch with --builds 3 (finalists; commit .json + .txt; then task
  37). Result: ~/after_fulldps_deploy.log. Task 40: engine/tools/old_patch.sh (2 cores, ~/old_patch.log) on PoB of 0.1-0.4;
  grade with tools/grade_old.py. The old-patch scans from 0.2 on pick up the fixed engine, 0.1's did not.
- **Task 41 (found 2026-11-24 07:00): nothing fills Weapon 2.** Live engine too: bows have no quiver, wands / sceptres no
  focus, one-handed weapons no shield or second weapon, unless a skill or anchor asks. So every bow / one-hand number
  is low against two-handers (finalists, all saved leads but staves and crossbows). Fix for bow / wand / sceptre on
  branch `offhand` (worktree ~/phaph_offhand, not pushed or merged): ~/offhand.sh runs A/B (~/offhand_ab.log), then the
  suite (~/offhand_tests.log). Do NOT merge into ~/phaph or push main until ~/old_all.sh has finished: each old-patch
  scan copies ~/phaph/engine when it starts, and the grade needs one engine. Same branch: Quarterstaff search fix.
- Task 39: Cast on X is settled (guides already add triggers.py's estimate beside the total; no engine change). Lead
  re-run queued: ~/after_leads.sh (2 cores, after old_all.sh) -> data/breaker/lead_builds_fulldps, log ~/after_leads.log;
  then update leads.json from it. Left in 39: rank_check and combos after the finalists.
- Task 40: 0.1 stack scan judged (Archmage real, Irongrasp false alarm); 0.3 scans running.
- Task 40: 0.2 condition false alarms judged (2 real, 25 false, 12 unjudged; tools/old_skill_verdicts.py does 0.3+ the same way).
- Task 40 runs now from ~/old_all.sh (2 cores, log ~/old_patch.log): stack 0.1, then 0.3 (condition, matrix, stack),
  matrix 0.1 + 0.2 again (the first 0.1 matrix was invalid: custom mods never applied), 0.4. Grade: tools/grade_old.py,
  then false alarms of matrix / stack pieces: python3 engine/tools/old_verdicts.py (next patch's PoB text; unchanged =
  false alarm, changed = read the lines) -> old/verdicts.json. 0.5 gets no case set: its known broken builds (5.1-5.7)
  are copies, charge loops and bugs PoB can't calculate, so there is nothing to grade there; left for 40 after the
  scans: the grade, ordinary builds (false-alarm check), the launch-day rehearsal timing.
- weapon_finalists.py now builds 3 finalists beside the next search (--builds; takes effect at the next run, speed not
  measured yet; the run going now is the serial version).
- **Leads now:** none to quote: every full-build number before engine 2026-11-23.5 needs a re-run (Bonestorm Lich +35%
  included). Invoker elemental crit = known (rediscovered blind).
- **Waiting for Kyle:** whether to trim the endgame pick further (finalists without herald/mark/movement supports,
  ~-7 min, can slightly change the pick). Not blocking.
- **Done 2026-11-20 (session):** task 12 written up (BREAKER.md); PoB gap fixed (Oracle Forced Outcome + Maligaro's
  x2.73 -> +2%); sweep chown fix (tonight's 10 pm sweep should record hung builds).
- **Plan (agreed with Kyle 2026-11-22):**
  - Sun 22 (rest of day): rank_check lands -> does a light Uber stage rank skills like the full one? -> task 36:
    endgame-first pick + leveling rule (endgame skill from Act 1 if it works, else max 3 same-theme skills, swap on
    unlock when clearly better) -> tests -> deploy. Unlocked blind run going overnight (~12 h).
  - Mon 23: (done 01:30: Bonestorm release time -> -39% vs Comet, lead fixed) Bonestorm's release time (BREAKER.md step 2: USAGE_LIMITS releases/s = 1 / (1/HitSpeed + 6/Speed),
    tests, deploy; then re-check its lead build vs Comet and the unlocked blind run's Bonestorm rows); write up the unlocked blind run (vs 7/69 per ascendancy); queue task 37 (per-ascendancy scans without
    class rules); new skill leads from it through the full-build bar (34); Bonestorm per-spike sanity check.
  - Tue 24-Wed 25: (playbook done early: BREAKER_PLAYBOOK.md, 2026-11-23) patch-notes gaps (keystones, rule changes, base items); Whetstone class-rule cost
    for Kyle.
  - Thu 26-Fri 27: week 2 leftovers (mapping chain reactions, 3-piece combos if worth it), build speed (exposure
    step cost), Mobalytics leveling-skill counts (laptop session). Usage resets Fri 5 am Mazatlan.
- **Open check:** guide.score_combo's setup DPS reads the same as the main skill (weapon set 2 group); see Credit plan.
- **Server time (Kyle 2026-11-23):** Lodestone first. The nightly Whetstone sweep is one rotating fifth of the
  ascendancies on weekdays (~3-4 h) and all 23 on Saturday nights (~17 h) (~/routines/nightly_sweep.sh).
- **Rules that matter:** no website front-end work for now; Lodestone first; ntfy only per memory rules; heavy jobs
  `--cpus 6` and via the Breaker queue; cron times are Berlin (server clock).
- **Waiting for Kyle:** nothing blocking.

# Unattended task list (Kyle away 2026-11-18 to ~11-20, on phone and laptop)

The "Whetstone server" session works through this list on its own, top to bottom, until the usage limit (resets
Friday ~5 am Mazatlan). Kyle wants to use the remaining usage fully: keep going task after task. Kyle can watch and
steer from the Claude app (Remote Control).

## Credit plan until the Friday ~5 am reset (Kyle, 2026-11-19) -- OVER
**2026-11-21, Kyle: "We should have something going constantly."** keepalive.sh now nudges an idle session every
30 min (skips only if the session was active in the last 20 min), also while server jobs run. Keep the server busy:
when a task needs a long run, start it through the Breaker queue and work on a light task meanwhile. The old notes
below are history.
Usage is nearly out. Automated jobs carry the work; Claude check-ins stay tiny:
- Running unattended (no Claude): `combo_scan.py ailments` (container whetstone-ailments, ~2 h, writes
  engine/data/breaker/combos_ailments.json in ~/phaph, not committed yet), then ~/lodestone_chain.sh after the
  current queue: blind test (task 7), conditions_asc + matrix_asc fresh (task 12), each committed by the queue.
- keepalive.sh (2026-11-19 night): no nudge while any queue/chain/engine job runs, and at most one nudge per 4 h.
- On a keepalive: run status.sh once. If jobs are still running, stop there (no new work). When the ailment scan
  has finished: commit its json + `ailments-report` text, add the top payoffs to leads.json, then stop.
- Bigger tasks (14 rest, 15, 16) wait for the reset.
- Done 2026-11-20 (night_sweep.sh chowns the results file back after each build). Was: the sweep's results file is written by Docker as root, so the host-side timeout handler can't record
  hung builds (chmod'd by hand 2026-11-19; make night_sweep.sh run the container as the host user).
- Combo play style (engine only, not deployed) tested 2026-11-19: Rend Titan end + Armour Breaker on weapon set 2:
  boss 59,214 -> 72,621 (+23%), break 1.4 s, up 90%. To check after the reset: score_combo's setup DPS equals the
  main skill's (set_main on a weapon set 2 group may not switch the calc), so the break rate may be Rend's.

## Rules
- Read CLAUDE.md, BREAKER_ROADMAP.md, BREAKER.md, PC_TODO.md first, and your memory notes (pc-server-split,
  phone-notifications, in-game-tests).
- One task at a time. For each: do it, run the relevant tests (full suite before any engine deploy), commit with a
  clear message, push, tick it here with one line of what changed.
- Engine deploys (`docker compose up -d --build app` in ~/phaph) only with all tests green; bump ENGINE_VERSION. The
  site shows "rebuilding the forge", and only Kyle and friends use it, so a restart is fine. Page changes deploy when
  pushed (Cloudflare Pages): check them in a browser first if you can, bump PAGE_VERSION.
- Heavy runs: `docker run --cpus 6`. Don't touch the Breaker queue running from ~/breaker (status.sh shows it); add
  jobs after it finishes, never stop it. Never start a second tunnel.
- Phone (ntfy, topic in ~/phaph/.env): only for a finished milestone, an in-game test request, a decision you need,
  or something broken. Never 10 pm - 8 am Mazatlan (write to ~/routines/pending.txt instead). Short lines.
- A decision that is Kyle's (product direction, publishing anything publicly): write it under "Waiting for Kyle" below,
  ping once, and move on to the next task.
- If a task is blocked or too big, write why, split it, move on.

## Tasks
### Whetstone (from the 2026-11-18 A-to-Z sweep, PC_TODO.md)
1. [x] Spirit overdrawn at Uber Endgame on 17 of 22 sweep builds (-80 to -120): find why the safety net misses the
   "end" stage and fix. Test on 3 ascendancies.
   Done 2026-11-19: Uber uniques that grant spirit skills (The Coming Calamity: 3 heralds) overdrew spirit; the safety
   net only knew optimiser-picked buffs. Gear scoring now punishes overdrawn spirit, kit_out trims supports on spirit
   skills instead of overdrawing, and a new runner `fit_spirit` turns off what still doesn't fit (after gear and at the
   end). Deadeye/Amazon/Lich/Stormweaver end + Titan act2: all fit now (+10 to +100 left).
2. [x] Attribute shortfalls (Int 43 of 45 for Loreweave + Ornate Ringmail at Interludes; Int 31 of 40 for support gems
   in Act 1): the gear/support picks must meet requirements at each stage.
   Done 2026-11-19: each support needs 5 of its colour's attribute summed over all skills, and fit_gems could only
   lower gem levels: it now takes supports of the short colour off extra skills first (noted on the build). A unique
   the character can't equip is skipped in the final gear pass, and goes back to a rare if re-balancing the rares
   takes its attribute away. Oracle/Blood Mage/Titan/Witchhunter campaign stages: no shortfalls (Titan interludes
   86k -> 62k DPS without the Loreweave it couldn't wear).
3. [x] Usage limit for Detonate Dead (needs a corpse each cast; bosses leave none) in runner.lua USAGE_LIMITS, like
   Hexblast; check Ember Fusillade too. Detonate Dead won Blood Mage, Lich, Oracle, Shaman.
   Done 2026-11-19: Detonate Dead capped at 0.25 casts/s against bosses (a corpse from adds every ~4 s, estimate),
   uncapped on maps. Lich round-1 boss DPS 145k -> 31k: behind Bone Cage and Ember Fusillade now. Ember Fusillade
   checked, no limit: PoB ignores both its 10-ember cap + 1.3 s delay (~x0.7) and +5% more per ember fired (~x1.5).
4. [x] Build speed: every build takes 24-36 min on the PC, ~45+ on the server; Gemling Legionnaire timed out. Profile
   one build, cut the slowest steps without losing quality (compare DPS before/after on 3 builds).
   Done 2026-11-19 (profile only, nothing shipped): Uber Endgame stage, Deadeye, 827 s on 2 cores: kit_out 303 s
   (1,725 PoB calls: supports for marks, heralds, movement), passive tree 110 s, gear 103 s, main supports 97 s,
   triggers 72 s, jewels 46 s. A lighter beam for kit_out (1 / top 5 vs 3 / top 15) gave the same DPS on Deadeye,
   Lich, Titan but saved only ~3%: the cost is screening every fitting support per extra skill, not the beam.
   Next idea (Whetstone, when it's a priority again): screen extra skills only on supports made for their kind
   (fit_supports' lists), or reuse one screen per skill across stages. Stages already run in parallel, so wall time
   is the slowest stage on enough cores.

### Breaker (the game plan, BREAKER_ROADMAP.md)
5. [x] Matrix within-family report: compare each unique's gain with skills of the same family (same skill types /
   weapon), not all skills, so "best-in-slot for crossbows" isn't flagged and true one-skill interactions are. Apply
   to data/breaker/matrix.json and matrix_asc/ (being filled by the queue).
   Done 2026-11-19: `matrix_scan.py report` compares each gain with the skill's family (same kind, same weapon for
   attacks, a shared damage type) and lists pieces strong on 6+ skills separately as best-in-slot. matrix.json:
   141 flags -> 17 true one-skill interactions (Wildsurge on storm/plant skills, Temporalis on Detonate Minion,
   Blueflame Bracers on Skyfall, Snakebite on Hexblast...); all files in data/breaker/matrix_family.txt.
   **Found on the way: the per-ascendancy scans never had ascendancy passives** (round-1 builds take no tree), so
   every ascendancy of a class read the same (matrix_asc and conditions_asc). Fixed (breaker.ascendancy_passives);
   both need a re-run once the queue is free (queued below as task 12).
6. [x] Breaker page on the website, called **Lodestone** in public (Kyle 2026-11-18: "Breaker" stays the internal
   code name): an unlisted page (phaphofbuilding.com/lodestone.html, no link from the home page,
   noindex) showing the latest Breaker results in plain English: leads with status (to test / confirmed / dead),
   condition payoffs, unique and keystone interactions, the combo finder's top combos, and what's queued on the
   server. Data from a new API endpoint reading the committed Breaker files. Same look as the main site. Kyle checks
   it from his phone; making it public waits for Kyle (put it under Waiting).
   Done 2026-11-19: phaphofbuilding.com/lodestone.html (noindex, no link from the home page). Leads with status
   (curated in engine/data/breaker/leads.json: 6 to test, 1 confirmed, 1 rediscovered, 2 bugs fixed, 1 explained
   away), top combos, condition payoffs, one-skill interactions (+ best-in-slot list), multiplying pairs, and the
   server queue. API GET /lodestone/data (api/lodestone.py) reads the Breaker files mounted read-only from the
   server repo, so a pull updates it without a redeploy. Engine 2026-11-19.4.
7. [x] Blind test against poe.ninja's top builds. Done 2026-11-21: first true per-ascendancy run, 3/20 of the
   ladder's top skills found (Comet, Ice Shot, Rend), Spearman +0.25; misses written up in BREAKER.md (setup skills
   counted as main, Druid weapon rule, Huntress spear skills, no infusions). Follow-ups: tasks 20-22.
8. [x] In-game test requests: write TESTS.md entries for the strongest leads (Leopold's Applause penetration below 0;
   "not consumed" charge sources adding to 100% for Flicker Strike; Hexblast's real cast rate), each with the PoB
   code, what to buy, what to do, what result confirms or kills it. Ping Kyle once when TESTS.md is ready.
   Done 2026-11-19: TESTS.md with 5 requests (Rapid Shot + Fresh Clip II; Rapid Shot + Rampart Raptor, new lead;
   Leopold's below-0 penetration; Hexblast detonation rate; Ember Fusillade), codes in ingame/. "Not consumed"
   charges: dead (all sources ~45%). Correction: the pairs scan stacks uniques on top of the slot's own item, so
   Leopold's is worth +4% worn for real, not +38%.

### Whetstone features Kyle asked for
**Deferred 2026-11-19 (Kyle: no more website front-end work for now; focus on Lodestone).** Engine parts that
Lodestone uses are kept; page edits for 9 and 10 are shelved in design/pending_ui_style_howplay.patch.
9. [ ] Build style choice on the forge: One button / Combo setup / Best (default), using the combo finder.
10. [ ] "How you play" card at the top of every build: Mapping: skill(s) | Bosses: skill(s) (+ "swap to weapon set 2"),
    or "one skill does both" and why.
11. [ ] Mageblood: judge by an average random roll; list legacies to hunt for; swap line for ticked goals ("Hunting
    for loot? Legacy of Gold (+45% rarity) can replace Stibnite: -X% toughness").

12. [x] (done 2026-11-20: written into BREAKER.md; found and fixed a PoB gap, Oracle Forced Outcome + Maligaro's x2.73 -> +2%) Re-run the per-ascendancy condition and matrix scans with ascendancy passives (fixed in task 5) once the
    Breaker queue is free: `JOBS="conditions_asc matrix_asc"` from ~/breaker after a pull.

### Lodestone build-out (added 2026-11-19, after Kyle's note)
13. [x] Pairs scan fix: a unique tried as a pair must replace the slot's current item, not stack on top of it
    (Leopold's looked +38%, is +4% worn). Rescore the existing pairs.json report with the slot's item removed.
    Done 2026-11-19: the bench empties a unique's slot first (runner clear_slots / restore_slots); `breaker.py
    rescore` redid the report worn (pairs_worn.json). Leopold's + Fire Penetration still +31% (Leopold's alone +4%):
    the below-0 lead holds. Maligaro's + Pinpoint +42%. Most other pairs were the stacking artefact (Rondel + Considered
    Casting +52% -> -16%). The Lodestone page shows the worn numbers.
14. [ ] (ailments done 2026-11-19: Dark Effigy + poison +69%, the only strong one vs a pinnacle boss; Lightning
    Conduit's shock can't be kept up on bosses. Left: immobilised family for Siege Cascade, mapping combos.) Combo finder, more condition families: Shocked / Electrocuted / Frozen / Poisoned / immobilised (Siege
    Cascade, Dark Effigy, Lightning Conduit), each with its own setup rate and uptime model.
15. [x] (2026-11-22: (a) Thundergod's Wrath + Fire Spell on Melee Hit; (b) trigger_scan.py, 51 feeders, best 0.13
    casts/s vs a boss at mid gear, no lead; endgame Supercharged Slam ~1/s = the known Mjölner build; (c) 2 mapping kill
    chains in leads.json; BREAKER.md) ((a) done 2026-11-21: Thundergod's Wrath + Fire Spell on Melee Hit in triggers.py, energy on every hit with
    the threshold ratio; (b) tools/trigger_scan.py built, full run going (~/trigger_scan.sh,
    writes data/breaker/triggers.json/.txt, not committed yet); (c) loop graph done: 2 mapping chains in
    leads.json (Bursting Fen Toad, Earthbound); next: read triggers.txt, (d) leads from feeders) Trigger and loop detector (roadmap week 2): from the text scan's group D lines, find skills/supports whose
    triggers can feed each other; estimate the rate; leads + test requests.
    Plan (2026-11-20): build on engine/triggers.py (energy maths for Cast on Critical / Elemental Ailment, numbers in
    data/trigger_rules.json). (a) add the other meta gems from PoB data (Cast on Dodge, Minion Death, Block, Melee
    Kill, Melee Stun, Charm Use) to METAS + rules; (b) new trigger_scan.py: for each meta gem, the cheapest feeder
    skill (energy per second per point of investment) and casts/s of a big spell, flag > 1 cast/s from a level-1
    feeder (the Cast on Freeze Comet shape); (c) loop graph from text_scan group D lines: a triggered skill whose output
    is its own trigger's event (crit, kill, ailment, minion death) = self-feeding, check against the 0.4/0.5 rule
    "triggered skills generate no energy"; (d) leads.json + TESTS.md for anything over the bar.
16. [x] (2026-11-22: tools/lead_builds.py builds a lead around its pieces + the same build without them; Leopold's
    pair -10%, Maligaro's pair +7% in full builds: both dead. It is now the bar for a lead) Leads to full builds: the top Lodestone leads become full Whetstone guides automatically (anchor the piece),
    saved with their codes, so test requests come with a complete build.

17. [x] (2026-11-22: done. Cloudflare Pages deploys from main (Kyle switched it); ~/phaph and ~/breaker on main;
    the old branch is retired with a README pointing to main) (2026-11-22: main fast-forwarded to the branch; ~/phaph pushes to BOTH branches (remote.origin.push x2); docs
    updated. Left: ~/breaker the same once the queue is idle, then local checkouts to main; old branch README after
    Kyle switches Cloudflare Pages) (after the reset, when no queue job is running) Rename the working branch to `main` (Kyle agreed
    2026-11-19): merge claude/poe2-shadow-build-mobalytics-85ym0e into main, push, switch ~/phaph and ~/breaker to
    main, update scripts that name the branch (grep the repo + ~/routines), set the old branch's README to point at
    main. Kyle then sets Cloudflare Pages' production branch to main; keep pushing the old branch too until he has.

18. [x] (2026-11-20: Ember Fusillade limited to 10 embers per cast-then-wait volley; suite, deploy and blind
    re-run chained in ~/after_ef.sh) FIRST after the reset: the blind test (engine/data/breaker/blind.txt) picked Ember Fusillade on all 23
    ascendancies, so it found only 2 of the ladder's top 20 skills (Spearman +0.16). Ember Fusillade is a modelling
    bug, not a lead: give it a usage limit (10 embers per cast cycle, 1.3 s launch delay) like Hexblast, then re-run
    the blind test (queue job `blind`, delete blind.json first).

19. [x] (2026-11-22: Bench replaces the weakest support; Leopold's + Fire Pen +31% -> +16%, Maligaro's + Pinpoint
    +42% holds; pairs_weakest.json, leads.json, TESTS.md) Fairer pairs numbers: `breaker.Bench` adds a support as an extra gem
    (a socket the build doesn't have); make it replace the skill's weakest support instead, then `breaker.py rescore`
    the leads (Leopold's + Fire Penetration +31%, Maligaro's + Pinpoint +42%) and update leads.json / TESTS.md.
    Optional: also compare a damage-only rare in the unique's slot (our rare balances damage and defence).

20. [x] (2026-11-21: tried Staff + Sceptre for Druid, made the blind test worse, reverted; engine 2026-11-21.3;
    see BREAKER.md: Tornado/Entangle/Wolf Pack score low in round 1, folded into task 22) Druid weapons (from the blind test): data/class_weapons.json gives Druid only Talisman, so Tornado, Entangle
    and Wolf Pack (the ladder's Druid skills) never reach a Druid search. Make Druid intended = Talisman + Staff,
    close + Wand, Sceptre; re-run the blind test for Oracle, Shaman only (`--only Oracle,Shaman`).
21. [x] (2026-11-21: partners.apply_infusion: Ice Nova + Frost Bomb x1.16, Arc + Orb of Storms x1.06; runner
    set_part; found task 26 on the way) Infusion family in the combo finder: Frost Bomb, Orb of Storms, Powered by Verisium (GeneratesInfusion) feed
    Comet / Spark / Arc. Model the infusion rate and the payoff skill's gain; the blind test should then find Arc,
    Ice Nova and the setup skills as part of a combo.
22. [x] (2026-11-21: Twister x4.2 when it consumes a 3-stage whirlwind from Whirling Slash, a combo we never set
    up; stages never set either (Flameblast x5.45 at max); BREAKER.md; follow-up task 23) Huntress spear skills (+ Druid's Tornado, Entangle, Wolf Pack, task 20): Whirling Slash (12.8% of the ladder) and Twister (10.9%) don't make Huntress' top 10.
    Find why (stages, elemental ground, round-1 setup) in PoB, fix what is a modelling gap, re-run `--only Amazon,
    Ritualist,Spirit Walker`.

23. [x] (23b done 2026-11-21: runner STAGE_RULES, Flameblast/Bonestorm/Supercharged Slam at full stages; (c) = the
    full blind re-run chained in ~/after_stages.sh; Oil Barrage + Wolf Pack checks moved to task 25) (23a done 2026-11-21: engine/partners.py scores Twister through Whirling Slash's whirlwind in every search
    round: x1.23, real but small; BREAKER.md. Left: (b), (c), Oil Barrage, Wolf Pack) Whirlwind combo + stage rules (from task 22): (a) combo finder family "whirlwind": Whirling Slash sets up,
    Twister pays off (PoB config whirlwindStages / twisterCold|Fire|Lightning), setup rate = slashes per stage;
    (b) per-skill stage rules with runner `set_stages` (Flameblast, Bonestorm, Supercharged Slam: stages held per use,
    channel time counted); (c) re-run the blind test for the Huntress ascendancies. Check Oil Barrage's 6.8 uses/s and
    Wolf Pack's companion DPS on the way.

24. [x] (2026-11-21: done from game data + web: Leopold's confirmed; Fresh Clip rediscovered (known); Hexblast and
    Rain of Arrows limits supported; Ember Fusillade, Rampart Raptor, Siege Cascade unconfirmed; Rampart Raptor
    cancels Fresh Clip (no reloads, no stacks). TESTS.md + leads.json) (Kyle 2026-11-21: no in-game tests possible) Check the six TESTS.md leads without the game: game data in
    vendor/PathOfBuilding-PoE2 (Fresh Clip II cap, Rampart Raptor's "Reloaded Recently", Hexblast's half-expired rule,
    Ember Fusillade's cap), then web evidence (WebSearch / api/research.py: wiki, patch notes, Reddit, guides), then
    ladder data. Write the verdict and source under each TESTS.md entry; update leads.json (confirmed / dead /
    unconfirmed); unconfirmed leads keep the cautious number.

25. [x] (2026-11-21: Oil Barrage limited to the spit's rate without Power Charges (x1/4.5); Wolf Pack pack size
    mapped (7 wolves) and minion counts now synced in the search (all minion skills were ranked with 1 minion);
    engine 2026-11-21.6; BREAKER.md) Two round-1 numbers that look off (task 22): Oil Barrage at 6.8 uses/s (Talisman, Druid's top pick, 0.77% of
    the ladder) and Wolf Pack's companion at 1.4k DPS (11% of the ladder). Check PoB's numbers against the gem data
    and web evidence; fix or explain.

26. [x] (2026-11-21: partners.apply_extra_sets adds 12 skills' always-landing second sets in the search: Earthquake
    x13, Glacial Cascade, Essence Drain x2, Coiling Bolts, Bonestorm, Fireball...; left: the finished guide shows set
    1 only, task 28) Extra damage stat sets (from task 21): Frost Darts Explosion, Fireball Firebolts, Ball Lightning / Incinerate
    Ignited Ground, Firestorm bolts, Ember Fusillade Beam, Comet/other: PoB scores each stat set on its own and the
    engine only counts set 1. Per skill (gem text + PoB data): does the set happen on every use (add it, e.g. as a
    second Full DPS group with that stat set) or instead of set 1? Check Incinerate's x11 ground first. Then a blind
    re-run. Likely the biggest ranking fix left.
27. [x] (2026-11-21: partners.apply_exposure; bare Comet x1.04 net, but penetration (Rakiata's Flow) and
    Exposure don't stack, so it loses on our searched builds; BREAKER.md) Frost Bomb as an Exposure setup: it inflicts Elemental Exposure each pulse (ladder 16.8%, the #1 "main
    skill"). auto_config only turns Exposure on when the build's own text says so; model Frost Bomb (and other
    Exposure appliers) as a setup for cold/fire/lightning payoffs (uptime from its duration and 6 s cooldown).

28. [x] (2026-11-21: partners.apply_all used by the search and the guide; the guide's boss DPS includes setups +
    extra stat sets, mapping DPS the extra sets, with a note per setup; left: the PoB export still opens on stat set
    1) (also: partners.py setups (Whirling Slash, Frost Bomb, Orb of Storms) are only in the ranking, not in the
    finished guide's skills: add them as weapon-set or extra skills with their reason) The finished guide counts only stat set 1 (task 26 made the search count the sum): add the extra sets as a
    mirrored Full DPS group (same gems, stat set k) in guide.py so the build page and PoB export show the real total;
    check Earthquake and Coiling Bolts end to end.

29. [ ] (2026-11-22: draft rules with sources in data/immobilise_rules.json, all unverified; the blocker: how much a
    boss's threshold rises after each immobilise is not published; 2026-11-22: 3 sources agree it rises and decays back,
    none gives numbers: needs a datamine or game-file source, or the PC's PoB/game files) Immobilise buildup model (from task 14): Freeze, Heavy Stun, Pin and Electrocute fill by damage against a
    threshold (cold vs ailment threshold; physical/melee vs stun threshold; projectile physical for Pin; lightning
    with Electrocute supports), and bosses resist (less buildup, immunity after). PoB gives no buildup output. Find
    the rules with sources (poe2wiki, patch notes), write them to data/immobilise_rules.json like trigger_rules.json,
    then score Siege Cascade (+101% vs immobilised) and other payoffs with time-to-immobilise and uptime.

30. [x] (2026-11-22: all combo leads through the full-build bar: APR +1%, Bonestorm <- Coiling Bolts +11%, Dark
    Effigy + poison +1% (guide now plays ailment combos); BREAKER.md table) (2026-11-22 results: APR self-break +1% (dead), Bonestorm <- Coiling Bolts +11%; left: Dark Effigy + poison
    (needs ailment combos in the guide); lead_builds.py takes a written spec + combo flag; APR Tactician and Bonestorm Lich <- Coiling Bolts
    running (~/lead_builds.sh); Dark Effigy + poison needs ailment combos in the guide first) Full-build bar for the "confirmed" combo leads (from task 16: pairs faded in full builds): Dark Effigy +
    poison (combo finder +69% vs a boss) and the Armour Broken combos. Build each as a full guide with its setup
    (guide combo style) and the plain build on the same engine; keep the lead only if the full build wins.
31. [x] (2026-11-22: patch-notes mode built and graded: 0.5.1 8/8 gems, 0.5.2 2/2 passives blind; left for the PC:
    the ladder side (poe.ninja history); later: keystones, sockets, base items, rule changes) (2026-11-22: 0.5.1 8/8 gems match PoB's update via tools/patch_check.py (6 not blind); passive changes done (patch_node);
    next: a fully blind practice on 0.5.2 (PoB v0.20.0 -> v0.21.0, passive changes), then a skill-heavy patch;
    step 3 done on 0.5.1: 2/2 number changes read right, 16/18 lines not expressible (new stats,
    rules, ascendancy/unique rewrites); next: "add stat" change type, passive changes, a bigger patch; step 3 plan: practise on 0.5.1: PoB v0.18.0 (before) vs v0.19.0 ("Update skills with 0.5.1
    changes"); notes at poe2db.tw/Version_0.5.1. Needs two more change types first: per-level gem fields (Repulsion's
    wave base crit 6%) and support restrictions (Cold/Fire/Lightning Attunement, Ice Bite I no longer attack-only).
    Then: PoB v0.18.0 in a second vendor dir (setup.sh POB_REF), our 0_5_1.json applied, compare changed skills' DPS
    with v0.19.0. Ladder check needs poe.ninja (PC). step 2 done 2026-11-22: PATCH_FILE applies a changes file in every PoB process; breaker_day.sh PATCH=...;
    step 1: runner patch_gem / patch_reset; plan in BREAKER.md: changes file, PATCH= in the day
    run, practice on PoB's commits around a past patch) Patch-notes mode, practice run (roadmap week 3): take a past patch (0.3 -> 0.4 or 0.4 -> 0.5): its notes ->
    the exact number changes -> apply them to the current data (custom mods / gem stat edits) -> scan -> compare our
    "this got broken / nerfed" calls with what happened on that patch's ladder. Start: what engine/tools/
    breaker_day.sh already does, then a notes -> changes parser (Claude reads the notes; changes as JSON).
32. [ ] Lodestone page text: leads marked "unconfirmed" show without a colour and the intro still says "needs
    checking in the real game" (front-end paused: ask Kyle before touching the page; put it under Waiting).

33. [x] (2026-11-22: cause = auto_config gave every armour-breaking plain build "always Fully Broken"; now only when it
    breaks a boss in <= 1.33 s; combo leads to re-run (task 30)) Combo builds read ~2x weaker before the combo (task 30): APR Tactician combo build: combo 2.39M vs 1.79M
    "alone" inside it, but the plain build is 3.92M. So the combo path changes the build itself (gear / tree /
    supports / boss setup) or score_combo's "alone" leaves something out. Diff the two builds (lead_builds/ codes:
    supports, gear, tree, config) and fix; then re-run the combo leads. Until then combo leads stay unconfirmed.

34. [ ] (2026-11-22 first 3: Bonestorm 2x Comet (holds), Rain of Arrows -43% vs Ice Shot, Wind Serpent's Fury -11% vs
    Lightning Spear; rest after the full blind re-run) Skill leads through the full-build bar (from tasks 16/30: interaction leads fade, a strong skill survives):
    after the full blind re-run, for each skill it ranks top 3 while under 1% of the ladder plays it (Bonestorm, Wind
    Serpent's Fury, Rain of Arrows, Supercharged Slam...), a full Uber Endgame build (lead_builds.py with a written spec)
    vs a full build of a skill the ladder plays a lot on that class (Comet, Spark, Lightning Spear, Ice Shot...). A
    lead = our skill's full build clearly beats the popular one; then evidence checks (TESTS.md) like Bonestorm's.

35. [x] (2026-11-23: answered by 36: the search's #1 was the best full build on 2 of 6; light builds wrong on 3 of 5;
    the endgame pick uses full Uber builds) (2026-11-22: tools/rank_check.py; ~/rank_check.sh queued after the lead builds: top 3 of Deadeye, Titan,
    Amazon, Tactician, Martial Artist, Oracle as full Uber builds, ~6 h -> data/breaker/rank_check.json) Search vs full build disagree (from task 34): the search's #1 Deadeye skill (Rain of Arrows) is 43% weaker
    than Ice Shot once both are full Uber Endgame builds (657k vs 1.15M). The search ranks on a mid-game build with a
    quick tree; the guide's gear, jewels, supports and endgame stage reorder skills. Measure how often the search's
    top pick isn't the best full build (top 3 finalists per ascendancy as full end-stage builds, a sample of 5-6
    ascendancies), then decide: a final "full build of the top 2-3" round in generate (cost: ~20 min per build on 2
    cores, so maybe only the Uber stage, light), or a better ranking stage. Whetstone quality, not just Lodestone.
    Design notes (2026-11-22, while the check runs): build_guide already runs the 7 stages in parallel, so the
    site's wall time is the slowest stage. Option A, "decider round": after the search, build the Uber stage for
    the top 3 skills in parallel (3 extra end-stage builds, ~+15 min wall time on 8 cores), keep the winner, then
    the other stages for it only (its Uber stage is reused). Option B, cheaper: the decider round on a light end
    stage (one tree pass, no jewels) if that orders skills the same as the full one (check on the rank_check
    data). Option C: make the search's own ranking stage closer to endgame (end-stage gear and tree depth) and
    accept the cost on every candidate: more expensive than A. Recommend A, or B if it ranks the same.

36. [x] (2026-11-23: live since engine 2026-11-22.1 (ENDGAME_DECIDER + LEVELING on). End-to-end Deadeye: picked
    Poisonburst Arrow (Uber 2.57M boss / 6.37M map) over Ice Shot and the search's #1 Rain of Arrows (657k); leveling
    'Poisonburst Arrow from Act 1' (no swap); ~2 h search+pick and 32 min guide on 2 shared cores. (a) code done 2026-11-22: generate.endgame_decider + api hook behind ENDGAME_DECIDER=1 (off), tests; waiting on
    rank_check --light (~/rank_light.sh) to pick light vs full; then set it on + deploy; (b) code done: engine/leveling.py (candidates same kind / weapon / damage type, unlock level from the catalog,
    choose(): endgame skill within 20%, swap at +30%, max 3), guide uses spec["leveling"] per campaign stage with swap
    notes, page shows a stage's own skill ("Leveling"), API behind LEVELING=1 (off). Trial 2026-11-22: Bonestorm Lich:
    Bonestorm from Act 1; Ice Shot Deadeye: Poisonburst Arrow (Acts 1-2) -> Rain of Arrows (3-4, Interludes) -> Ice
    Shot; 6 min on 2 workers after a mid-campaign shortlist. Both switched on in docker-compose; deploy after the suite)
    Endgame-first builds (Kyle 2026-11-22, replaces the decider-round question in 35): "when someone is looking
    for a build they are really looking for an endgame build ... they will use whatever gets them to late fastest
    then swap." (a) The final pick among the search's top 3 is made on their Uber Endgame builds (light version first
    if it ranks the same as rank_check's full builds); (b) leveling (Kyle: "not swapping spells every act", then "maybe 3
    max? or 4? depends what other builds on mobalytics say. As you level up and unlock better skills of course you
    should swap to the better new one if it makes sense"): swap when a newly unlocked gem is clearly better (~30%+
    faster clear), same theme / element / weapon, at most 3 skills across the campaign incl. the endgame skill (4 if
    Mobalytics guides for that archetype do: a laptop session can check), endgame skill by Early Endgame at the
    latest. Front-end: the build page
    already shows stages; a stage's own skill name has to show there (check before deploying; page work is paused,
    so ask Kyle if it needs more than the skill name).

37. [ ] (queued 2026-11-23: ~/after_unlock.sh runs conditions_asc + matrix_asc after the unlocked blind run; the scans
    resume, so only skills the rule skipped get scanned; ~16-20 h; then read for cross-class payoffs) Re-run the per-ascendancy condition and matrix scans without the class-weapon rule (Kyle 2026-11-22:
    Lodestone has none; the 11-20 runs skipped skills outside each class's weapons). Queue `conditions_asc matrix_asc`
    after the unlocked blind run.

38. [ ] (2026-11-23: the error is per skill (x0.41 Rapid Shot to x1.83 Bonestorm), no single factor; plan: Lodestone
    shortlists ~2 skills per weapon type by search score, ranks finalists by full Uber builds (tools/rank_check.py
    style), weekly) The search's scores across weapon kinds (from the unlocked blind test, 2026-11-23): staff spells score ~10x
    attacks in the search while full Uber builds have them level (Bonestorm 6.0M, Supercharged Slam 5.7M, Rapid Shot
    6.3M). Find what the search's quick build gives spells and not attacks (crafted weapon, +levels, supports, the
    quick tree) and calibrate, so a no-class-rule Lodestone search can compare a Gemling Spark with a Titan slam.

39. [ ] (2026-11-23: suite green, 219 passed; engine 2026-11-23.5 live, finalists restarted; 2026-11-24: per-source breakdown done, on-death explosions out, engine 2026-11-24.1; skeletons counted 0 since 11-17: fixed; Cast on X settled; left: re-run leads (queued), rank_check, combos) Full DPS fix
    (BREAKER.md last section): suite green -> commit, deploy engine 2026-11-23.5, clear finalists.json and restart
    ~/after_sweep.sh (its results are from the buggy engine). Then a per-source damage breakdown check on every build,
    and re-run leads, rank_check and combos before quoting any older full-build number.
40. [ ] (2026-11-24: PoB tags back to 0.1 run on our runner; Lightning Conduit vs Shocked reads +500% / +115% / +116% / +68% on 0.1-0.4,
    in step with the nerfs; answer key written first; scans started; left: a v0.17.1 (0.5) case set, ordinary builds, scalers and pairs on old
    patches, then the grade) (agreed with Kyle 2026-11-23, by ~Dec 1) Grade Lodestone on known answers: 15-20 past broken builds plus
    ordinary ones on patch data we can load; hit rate and false alarms. Proposed bar: at least half found, at most one
    false alarm per real find; if missed, narrow what Lodestone claims. Then time a launch-day rehearsal (notes ->
    ranked leads); label each lead's nerf risk (bug / extreme outlier = first hit) and re-run on every hotfix.

41. [ ] Off-hands (see START HERE): (a) read the A/B and the suite on branch `offhand`; (b) once old_all.sh is done: merge,
    bump ENGINE_VERSION, deploy, stop nothing in the queue; (c) re-run finalists for Bow, Spear, Quarterstaff, Wand,
    Sceptre (the rest of today's run is comparable only within itself); (d) one-handed martial weapons: try shield and second weapon and keep the better by score (dual wield is the
    Shadow build's case); (e) weapon set 2 (craft_weapon) has no off-hand either; (f) lead re-run (~/after_leads.sh)
    starts right after old_all.sh: make it wait for the merge. Saved builds and earlier A-to-Z / blind rankings of
    bow / wand / sceptre skills read low.

## Waiting for Kyle
- Class-weapon rule for Whetstone's default search: after blind_unlocked lands, show what the rule costs a player
  (Lodestone has no class rules: Kyle 2026-11-22) and ask whether Whetstone should change.
- Lodestone page: two small text fixes (task 32: 'unconfirmed' has no colour; the intro still mentions in-game
  checks). Front-end is paused, so only with your OK.

## Done
