# START HERE (handoff, 2026-11-20 morning)
Fresh session? Read this block, then CLAUDE.md and BREAKER.md's last sections. Sessions are short now (Kyle,
2026-11-20): one task or working block per session, write state back here before stopping.
- **Running (no Claude, 2026-11-21 ~12:00 Mazatlan):** ~/after_stages.sh = full suite, deploy engine 2026-11-21.5
  (stage rules) if green, then the full blind test re-run (~12 h, commits blind.txt). Next session: task 21
  (infusions) or 25 while it runs; when blind.txt lands, compare with the 3/20 run and write it into BREAKER.md.
- **Done 2026-11-20 (session):** task 12 written up (BREAKER.md); PoB gap fixed (Oracle Forced Outcome + Maligaro's
  x2.73 -> +2%); sweep chown fix (tonight's 10 pm sweep should record hung builds).
- **Next tasks, in order:** 21 infusions; 25 Oil Barrage / Wolf Pack; 15 trigger/loop detector;
  unsupported-unique-lines check (BREAKER.md, new idea); 16 leads -> full builds; 14 rest; 17 branch rename.
- **Open check:** guide.score_combo's setup DPS reads the same as the main skill (weapon set 2 group); see Credit plan.
- **Rules that matter:** no website front-end work for now; Lodestone first; ntfy only per memory rules; heavy jobs
  `--cpus 6` and via the Breaker queue; cron times are Berlin (server clock).
- **Waiting for Kyle:** Lodestone page public?, Cloudflare branch switch (task 17).

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
15. [ ] Trigger and loop detector (roadmap week 2): from the text scan's group D lines, find skills/supports whose
    triggers can feed each other; estimate the rate; leads + test requests.
    Plan (2026-11-20): build on engine/triggers.py (energy maths for Cast on Critical / Elemental Ailment, numbers in
    data/trigger_rules.json). (a) add the other meta gems from PoB data (Cast on Dodge, Minion Death, Block, Melee
    Kill, Melee Stun, Charm Use) to METAS + rules; (b) new trigger_scan.py: for each meta gem, the cheapest feeder
    skill (energy per second per point of investment) and casts/s of a big spell, flag > 1 cast/s from a level-1
    feeder (the Cast on Freeze Comet shape); (c) loop graph from text_scan group D lines: a triggered skill whose output
    is its own trigger's event (crit, kill, ailment, minion death) = self-feeding, check against the 0.4/0.5 rule
    "triggered skills generate no energy"; (d) leads.json + TESTS.md for anything over the bar.
16. [ ] Leads to full builds: the top Lodestone leads become full Whetstone guides automatically (anchor the piece),
    saved with their codes, so test requests come with a complete build.

17. [ ] (after the reset, when no queue job is running) Rename the working branch to `main` (Kyle agreed
    2026-11-19): merge claude/poe2-shadow-build-mobalytics-85ym0e into main, push, switch ~/phaph and ~/breaker to
    main, update scripts that name the branch (grep the repo + ~/routines), set the old branch's README to point at
    main. Kyle then sets Cloudflare Pages' production branch to main; keep pushing the old branch too until he has.

18. [x] (2026-11-20: Ember Fusillade limited to 10 embers per cast-then-wait volley; suite, deploy and blind
    re-run chained in ~/after_ef.sh) FIRST after the reset: the blind test (engine/data/breaker/blind.txt) picked Ember Fusillade on all 23
    ascendancies, so it found only 2 of the ladder's top 20 skills (Spearman +0.16). Ember Fusillade is a modelling
    bug, not a lead: give it a usage limit (10 embers per cast cycle, 1.3 s launch delay) like Hexblast, then re-run
    the blind test (queue job `blind`, delete blind.json first).

19. [ ] (before Kyle's in-game tests, ~11-27) Fairer pairs numbers: `breaker.Bench` adds a support as an extra gem
    (a socket the build doesn't have); make it replace the skill's weakest support instead, then `breaker.py rescore`
    the leads (Leopold's + Fire Penetration +31%, Maligaro's + Pinpoint +42%) and update leads.json / TESTS.md.
    Optional: also compare a damage-only rare in the unique's slot (our rare balances damage and defence).

20. [x] (2026-11-21: tried Staff + Sceptre for Druid, made the blind test worse, reverted; engine 2026-11-21.3;
    see BREAKER.md: Tornado/Entangle/Wolf Pack score low in round 1, folded into task 22) Druid weapons (from the blind test): data/class_weapons.json gives Druid only Talisman, so Tornado, Entangle
    and Wolf Pack (the ladder's Druid skills) never reach a Druid search. Make Druid intended = Talisman + Staff,
    close + Wand, Sceptre; re-run the blind test for Oracle, Shaman only (`--only Oracle,Shaman`).
21. [ ] Infusion family in the combo finder: Frost Bomb, Orb of Storms, Powered by Verisium (GeneratesInfusion) feed
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

25. [ ] Two round-1 numbers that look off (task 22): Oil Barrage at 6.8 uses/s (Talisman, Druid's top pick, 0.77% of
    the ladder) and Wolf Pack's companion at 1.4k DPS (11% of the ladder). Check PoB's numbers against the gem data
    and web evidence; fix or explain.

## Waiting for Kyle
- Lodestone page public? It is live but unlisted (lodestone.html, noindex). Linking it from the home page or
  sharing it is your call.

## Done
