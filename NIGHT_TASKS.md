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
  branch `offhand` (worktree ~/phaph_offhand, not pushed or merged): A/B in ~/offhand_ab.log; ~/offhand2.sh runs the full
  suite now (~/offhand_tests.log; also covers (d), one-handed martial: second weapon or shield by score; its 2 new tests pass). Suite green 2026-11-24 08:00 (226 passed).
  Old-patch scans now run a frozen engine (~/phaph_grade, worktree at 1820188), except the running 0.3 batch, so
  ~/merge_offhand.sh waits for the 0.3 stack scan to start, then merges, deploys 2026-11-24.3 and pushes
  (~/merge_offhand.log). Don't edit engine code in ~/phaph before it has. If it says failed, do it by hand. Same branch: Quarterstaff search fix.
- Task 39: Cast on X is settled (guides already add triggers.py's estimate beside the total; no engine change). Lead
  re-run queued: ~/after_leads.sh (2 cores, after old_all.sh) -> data/breaker/lead_builds_fulldps, log ~/after_leads.log;
  then update leads.json from it. Left in 39: rank_check and combos after the finalists.
- **10:18 engine 2026-11-24.3 live (off-hands), main pushed.** 10:30: the nightly sweep started on top of everything (the
  queue's wait matched image names, which a rebuild changes: fixed in breaker_queue.sh), so the finalists re-run was
  stopped and waits for the sweep (~/finalists_offhand.sh; resumes, finished builds kept), then task 37.
- 0.3 matrix graded: 0 of 4 cases (2 untestable: weapon and focus uniques aren't scanned), 0 real / 14 false. 0.3 stack
  running. After the grade: off-hand uniques into breaker.UNIQUE_TYPES (not before: frozen engine).
- **Task 43: merged, deployed 2026-11-24.4 and pushed 14:05** (228 passed). Left: 43 (b), (c). Damage after the fix not measured.
  Running: 12 revisit builds start after path-luck (~/revisit_ab.sh); task 44 measurement (condition swaps) in the session
  scratchpad cond.log, first row +0%.
- **Task 42, plain run done 14:08 (12 of 12):** spread by slot order: Ice Shot 5%, Rapid Shot 22%, Bonestorm 68%, Rain of Arrows 320%
  (3 of 4 over the 10% bar). `revisit` A/B running since 14:08 (path-luck-revisit). Queued after it: ~/fixcheck.sh (4 specs on main
  with the filler fix: ~/fixcheck_out/fixcheck.json, compare dps / TotalEHP / Communion with path_luck.json's "as is").
  finalists_offhand (hungry_nobel) runs one order per build, so its ranking has this luck in it: don't quote it.
- **15:00:** 0.3 stack scan graded: 1 flag (Irongrasp, unchanged in 0.4: false alarm); Indigon, Hollow Palm missed, Rathpith untestable.
  0.1 matrix running (then 0.2 matrix, 0.4). Revisit A/B so far, "as is": Rain of Arrows 849k -> 3.66M, Rapid Shot and Ice Shot
  identical to plain. Task 44: 0 of 10 rows gain anything; only Bonestorm is left to run.
- **15:35 task 44 measured (16 of 16 rows, Communion removed first, ~/cond_swaps.py):** 1 of 8 builds gains: Bonestorm "as is" +42% mapping and +42%
  boss (drops Elemental Focus, which blocks ailments and so the chilled / ignited conditions); the other 7 builds gain 0. Brute force
  takes 2-7 min per search, too slow. Try: re-score the search's final 3 sets, each with its own auto_config, plus the best set without
  ailment-blocking supports.
- **15:35 revisit A/B, 5 of 12: NOT a clean win.** As is: RoA 849k -> 3.66M, Bonestorm 6.99M -> 7.42M, Rapid Shot / Ice Shot same. But RoA reversed
  3.46M -> 1.74M (-50%). Don't merge on "as is" alone; see why that build got worse (code in ~/revisit_out/path_luck_revisit.json).
- **16:05 revisit, why it lost damage:** 9 of 12 in: every build it changed gained 136-330% EHP; RoA reversed -50% and rotated -66% boss, RoA
  as is +331%, Bonestorm as is +6% / reversed +118%, Rapid Shot and Ice Shot untouched. Likely (not proven): the linear score (d + 0.6 x EHP)
  accepts a big one-off swap that trades damage for EHP. Branch `revisit` now takes a swap only if its reverse scores as a loss (2 unit
  tests; the new one fails without the rule). ~/revisit_ab2.sh runs the 12 builds on it after ~/fixcheck.sh (path_luck_revisit2.json). Judge
  boss damage AND EHP per build against path_luck.json; merge if nothing loses much, else best-of-N orders.
  Note the running A/B's suite (~/revisit_tests.log) will test the new commit, not the old one.
  The same linear score picks single-unique swaps in _consider_uniques and affixes: one to look at if AB2 is still noisy.
- **16:40 revisit A/B 1 complete (12 of 12): spread RoA 201%, Rapid Shot 43%, Bonestorm 125%, Ice Shot 5% (plain: 320 / 22 / 68 / 5).**
  Not a fix for the spread; AB2 (symmetric rule) runs after fixcheck.
- **Task 44: branch `settle`** (worktree ~/phaph_settle, off main, not merged): guide.search_supports; 3 unit tests pass. A/B on the 12
  saved builds running (container settle-ab; script / log settle.py / settle.log in the session scratchpad). Then the full suite.
- **17:05 grade:** 0.1 matrix: Archmage and Gemling both missed (Archmage was found by the stack scan only). 2 of 10 graded cases found, 1 case
  left (2.1, 0.2 matrix): at most 3 of 11, or 3 of 9 without the 2 untestable: below half either way. Task 40's grade fails the bar on
  both halves; left: 2.1, ordinary builds (false alarms), launch-day timing, the narrowed claim (for Kyle).
- **17:05 filler fix on full builds:** boss and map dps identical, EHP RoA 6.3k -> 7.9k, Ice Shot 7.8k -> 24.2k (2 of 4 in, ~/fixcheck.log).
- Full suite on `revisit` with the symmetric rule: green, 229 passed 16:42. AB2 starts after fixcheck.
- **17:35 task 43 check done (4 of 4):** boss and map dps identical to the digit; EHP Rapid Shot 3.2k -> 12.6k, Ice Shot 7.8k -> 24.2k, RoA
  6.3k -> 7.9k, Bonestorm unchanged (never had Communion). 43 left: (b) and old cached guides. AB2 running since 17:06. settle-ab: 13 of 24, all +0%.
- **18:10 task 44 A/B done: 24 of 24 rows, 2 gain (+42%, Bonestorm "as is" map and boss), 22 +0.0%, 0 lose.** On saved builds only; a full
  guide with it isn't measured (the boss step probably avoided Elemental Focus already). ~/merge_settle.sh merges + deploys 2026-11-24.5 if
  the suite is green (~/settle_tests.log, ~/merge_settle.log).
- **18:10 correction to the 16:05 note:** RoA reversed is 1,736,171 in AB1 and AB2, so the symmetric rule did not act there: the "linear
  score trades damage for EHP in the re-check" explanation is wrong for that build. It is untested for RoA rotated. RoA as is went 3.66M (v1)
  -> 1.83M (v2), so there the rule did act, and cost damage. The re-check runs in the FIRST gear pass too, before the tree: other gear -> other tree is the
  next suspect (37 passives differ). Test: re-check only in the final pass (attr_weight set).
- **19:30: engine 2026-11-24.5 (task 44, settle) is live, 231 passed.** Finalists off-hand run done: Unearth 15.6M is false (30 temporary
  minions; live bug, BREAKER.md). Fix on branch `tempminions` (worktree ~/phaph_tempmin); ~/tempmin.sh runs the suite, then merges,
  deploys 2026-11-24.6 and pushes (~/tempmin_tests.log, ~/merge_tempmin.log): check it. After it: rebuild Sceptre finalists (drop
  that row from finalists_offhand.json and re-search Sceptre on the new engine). after_leads starts on whatever main is then.
- **Task 42, AB2 complete 19:06 (12 of 12), boss by order as is / reversed / rotated:** RoA 1.83M / 1.74M / 1.33M (+38% spread, but plain was 849k / 3.46M /
  3.57M: 2 of 3 orders lose about half or more); Rapid Shot rotated 6.79M (plain 5.78M); Bonestorm 7.42M / 9.09M / 3.94M (plain 6.99M / 4.17M / 4.41M), spread 131%;
  Ice Shot 5%. Don't merge. AB3 (re-check in the final gear pass only, commit on `revisit`) running since 19:06 -> ~/revisit_out/path_luck_revisit3.json.
  If it isn't clean either: best-of-N orders. Don't read "lower spread" as better where the level fell.
- Sceptre again on 2026-11-24.6: ~/sceptre.sh, after that deploy and AB3 -> data/breaker/finalists_sceptre.json, ~/sceptre.log (commit it).
- **20:05: 2026-11-24.6 live (231 passed), tempminions merged.** Sceptre finalists started now (3 cores were free). AB3 at 4 of 12: RoA as is 2.63M (plain 849k),
  reversed 3.46M (= plain), Rapid Shot and Ice Shot as is = plain: no loss so far.
- **20:30: branch `handuniques`** (worktree ~/phaph_hands): weapon and off-hand uniques in matrix / pair scans, worn for real in the hand that holds their
  kind. Probe (round-1 builds, 4 skills, 87 tries): base unchanged after the tries; only Sunsplinter +16% and Chernobog's Pillar +10% (Lightning
  Spear) gain; Tangletongue -69%, Rathpith -29%: both known cases would still be missed, so this does not change the grade. ~/hands.sh: full suite, then merge +
  push (no deploy) and ~/breaker pull for task 37 (~/hands_tests.log, ~/merge_hands.log).
- **20:40 AB3 (re-check in the final pass only), 7 of 12:** 2 builds change, both better: RoA as is 849k -> 2.63M (EHP 6.3k -> 6.6k), Bonestorm as is 6.99M -> 11.31M
  (map 3.86M -> 8.84M, EHP 7.0k -> 10.6k); 5 identical. ~/merge_revisit.sh: when 12 of 12, gate (~/revisit_gate.log: no loss over 5% in boss, map or EHP vs plain),
  main merged into `revisit`, full suite, then merge + deploy 2026-11-24.7 + push (~/merge_revisit.log). If the gate fails, decide by hand. AB3's base is
  2026-11-24.3 code (plain too), so the gain on .6 isn't measured. Its 66% resistances: Loreweave (both builds wear it) has a "Maximum Resistances are" line in PoB, so 66 is probably the cap and not a missing resist; unconfirmed on the build.
- **21:20 AB3 complete (12 of 12): 5 builds change:** boss x3.09 (RoA as is), x1.02 (RoA rotated), Bonestorm x1.62 / x1.80 / x2.41; 7 identical. Spread: RoA 320% -> 39%, Bonestorm 68%
  -> 50%, Rapid Shot 22%, Ice Shot 5% (unchanged). Gate FAILED on RoA rotated (EHP x0.75), nothing merged. By hand: that loss is Communion (both
  builds hold it; without it 10.6k -> 12.5k EHP). ~/merge_revisit2.sh rebuilds that spec on today's main and on revisit, runs the suite, and
  merges + deploys 2026-11-24.7 only if neither boss, map nor EHP is over 5% lower (~/merge_revisit2.log). Spread is still over the 10% bar for 3 of 4:
  42 stays open (best-of-N orders next).
- **handuniques merged 20:37 (232 passed).** **43(b): branch `kitehp`** (worktree ~/phaph_kitehp, 2026-11-24.8, 2 unit tests pass): side skills' support search keeps 90% of the
  toughness. How often it bites: ~/kit_freq.log (old finalists, so Communion is in it). Left: full suite after the revisit merge (merge main first;
  app.py version conflict: keep .8), then merge + deploy.
- **22:10: engine 2026-11-24.7 live (unique re-check in the final pass, 234 passed).** RoA rotated on current code, main vs revisit: boss x1.02, map x1.02, EHP x1.18.
  Sceptre on .6: Skyfall 2.95M, Unearth 2.75M (was 15.6M): finalists_sceptre.json. kit_freq (30 old finalists): 21 builds' worst EHP support is Communion; Her
  Declaration, Seraph's Heart, Healing Runes also cost 10%+ EHP, all next to Communion where looked at. **43b:** ~/kitehp.sh: suite, then merge + deploy .8
  (~/kitehp_tests.log, ~/merge_kitehp.log). **42, best of N:** weapon_finalists.py builds each finalist in 3 slot orders, keeps the best and prints the worst
  (Lodestone only: Whetstone guides would take ~3x longer, so that is a question for Kyle). Running: orders-sceptre (first use, finalists_orders.json),
  path-luck-7 (the 12 builds again on .7: the current spread, path_luck_7.json). Task 37 waits for all of these.
- **22:40 launch-day rehearsal queued** (task 40): ~/rehearsal.sh, after orders-sceptre, path-luck-7 and kitehp-tests: breaker_day.sh with PATCH=0_5_2.json on 6 cores in the
  clone ~/rehearsal (it can't push), timed -> ~/rehearsal.log; put the times in BREAKER_PLAYBOOK.md (0.4 scans use 2 other cores: say so). Known gap: with PATCH,
  breaker_day.sh overwrites and commits the baseline text_scan.json with the PATCHED game, so a later diff compares with our guess: keep the old one.
  Nerf-risk labels wait for the lead re-run. path-luck-7 first row: RoA as is 2.63M, the same as AB3.
- **23:05: 2026-11-24.8 live (43b, 235 passed).** 43 left: (c) guides cached before .4 (old engine versions). breaker_day.sh keeps the real baseline in PATCH mode
  (fix not run yet; the rehearsal uses it). Lead re-run started early (after-leads, 2 cores, engine .8). path-luck-7, 4 of 12: the four "as is" builds equal AB3.
- **23:35:** 0.4 scans done (no case set, committed ungraded). orders-sceptre, Skyfall best of 3: 2.98M (default order 2.95M). combos-8: Armour Broken combos
  again on .8 -> combos_8.json (~/combos_8.log); compare with combos.json (Nov 18), then replace it (the page reads it); the ailment combos after.
- **00:05 (11-25): orders-sceptre done (finalists_orders.json, committed):** Skyfall 2.98M (worst order 2.90M), Unearth 5.47M (worst 2.75M: a 99% spread on .7). Best-of-3
  changed the Sceptre winner, so it matters for rankings. Unearth's 5.47M: its boss sources are Ignite 62% (which skill lights it isn't checked), Skyfall 30%, Unearth's own hit 4%: not an Unearth lead; report should say so. path-luck-7 6 of 12, all equal to AB3. First lead re-run: Leopold's
  1.38M (its plain build still to come). ailments-8 (ailment combos on .8) started -> combos_ailments_8.json.
- **00:40:** combos.json is now the 2026-11-24.8 run (BREAKER.md; best edges are minions: none full-build checked). Finalists report flags builds whose skill
  deals under half their boss damage. Left running: ailments-8 (then compare with combos_ailments.json, old one untracked), after-leads, path-luck-7 (9 of 12, all equal
  to AB3), then the rehearsal.
- **01:05: path-luck-7 done (BREAKER.md).** Rehearsal running since 00:54 (~/rehearsal.log). Next for 42: lead_builds.py in 3 orders per side. after-leads so far: Leopold's
  1.38M, Dark Effigy 0.83M (single order each; not verdicts).
- **01:20:** lead_builds.py and weapon_finalists.py share path_luck.best_of (3 orders, best kept). after-leads stopped after 2 leads (BREAKER.md); ~/leads_orders.sh runs all
  (ailment combos done on .8: same picture.)   leads with 3 orders per side (3 cores, ~/leads_orders.log -> lead_builds_orders). Then update leads.json. Dark Effigy is the one to look at.
- **01:50: rehearsal done and timed (24 min, 6 cores; BREAKER.md, playbook).** It found that patched passives never reached the text diff: fixed (text_scan.py, runner.lua,
  breaker_day.sh), full suite green before 45(b) (unit-tested only, scan tool); pushed, not deployed. leads-orders still running, 0 leads finished. Next: task 45.
- **02:40:** patch-notes mode on keystones checked: 32 of 33 change the numbers (Chaos Inoculation pins life, untestable that way); test added, pushed. Detection run (45c): the wording
  half passes (both lines, nothing else); damage half scanning (~/detect.log, 2 scans on 3 cores).
- **03:35: task 45 done** (BREAKER.md). leads-orders: 3 leads have their first side, no plain builds yet, no verdicts. Left in 40: nerf-risk labels (after the leads).
- **05:10:** 45, 46 done. Waiting on leads-orders (5 leads fully done, both sides, verdicts in BREAKER.md; the earlier 'no plain builds' notes were wrong): then verdicts in leads.json, nerf-risk labels (40), 39 closes. 37 starts by itself after it.
- **05:40:** leads: Dark Effigy + poison +42% in all 3 orders (1.03M: weak in absolute terms), others dead or luck. 3 skill leads (Bonestorm, Rain of Arrows, Wind Serpent's Fury) left to
  build. Then update leads.json once, with the same-sign-in-all-orders rule.
- **06:10:** leads.json updated for 6 leads (Bonestorm ahead of Comet in all 3 orders, +18 to +82%). Rain of Arrows and Wind Serpent's Fury still to build.
- **06:40:** Rain of Arrows: wins all 3 orders but on our 1.5 m boss-radius estimate: unconfirmed. nerf_risk labels in leads.json (40's last item but 'every hotfix'). Left: Wind Serpent's Fury.
- **07:55: leads-orders done, 8 of 8** (BREAKER.md, leads.json). Closes 39's leads and combos; left in 39: rank_check on the current engine. 37's scans should have started: check
  ~/after_unlock_queue.log.
- **08:05: task 37 running (conditions_asc 1 of 23 since 07:52).** Its scans resume, and the files were from Nov 20 (no off-hands, wrong minion counts): old rows would mix with new. Old
  json moved to ~/asc_nov20 (also in git), so 22 ascendancies + the matrix scan fresh; Infernalist had started and is mixed: ~/infernalist.sh redoes it after the queue (it walks all 23
  again but finished ones are skipped). autoStash set in ~/breaker so its push survives. Expect much longer than 16-20 h. Engine code there is 203271a (before .7 / .8; round-1
  builds use neither). Don't read Infernalist or the group before both are done.
- **08:35: task 39, rank_check on the current engine running** (container rank8, 2 cores, ~/rank8.sh, ~/rank8.log): fresh search of 6 ascendancies on the live image
  (class weapons, as on Nov 22) -> blind_8.json, then top 3 each in 3 slot orders (new `rank_check.py --orders`) -> rank_check_8.json (54 builds, resumable). Then: search's #1
  vs full-build #1, read against each skill's spread between orders; write to BREAKER.md, close 39. 41(f) is covered by leads-orders.
- **09:10:** 37's condition scans are at 4 of 23 (~23 min each). Reader written: `python3 engine/tools/asc_read.py ~/breaker/engine/data/breaker/conditions_asc --skip Infernalist`
  (one ascendancy vs the median one; skip Infernalist until ~/infernalist.sh redoes it, and whichever file is still being written). First look, 3 files: Blood Mage
  ahead ~25-40% on many spells, no outlier over x1.45 outside Infernalist's mixed minion rows. Too few to conclude. rank8: still in its first search.
- **09:30:** rank8: 59 min into its first search (earlier runs took ~28-32 min each; now 2 workers on a full server), both workers at full CPU. Expect roughly 6 h of searches, then
  the builds. No results before the afternoon. If still no first line in ~/rank8.log by 10:30, suspect a hang. 37 is on 5 of 23.
- **15:10 TASK 47, live bug: ascendancy points.** (1) options of choice passives never tried (Gemling +2 skill levels, Deadeye Point Blank / Far Shot); (2) Abyssal Lich takes 0 of 8 in
  every build (its passives carry Lich's name); (3) points PoB sees no gain for stay unspent: saved Uber builds: Deadeye 1-2 of 8, Oracle 4, Tactician 4, Ritualist 5. Branch `ascpoints`
  (worktree ~/phaph_asc, 2026-11-25.1, not merged): all three fixed, 4 new test cases. Running: full suite ~/asc_tests.log; A/B ~/asc_ab.sh (5 full builds, branch then main, ~/asc_out/*.json,
  ~/asc_ab_*.log). Don't edit engine code in ~/phaph until the main half is done. Merge + deploy if the suite is green and no build loses (Invoker Ice Shot is the control).
- **Hit by it:** every per-ascendancy comparison: blind tests (Titan, Warbringer, Smith score identically, so do Tactician and Witchhunter), finalists, rank8's search, and task 37's scans (no ascendancy
  passive on any of 158 skills for Titan and Abyssal Lich, on 155 Warbringer, 144 Tactician, 130 Disciple). 37's condition scans are nearly done and stay as a "before"; after the merge
  they and matrix_asc need a redo (48). breaker_queue copies engine code per job from ~/breaker and pulls at each push: after a merge mid-queue, later scans mix code: check dates.
- 15:35: first suite run: 2 fails, probably task 47's own cases (zero-damage builds read as a 100% loss in the filler check; fixed, cases pass, committed; all 23 ascendancies spend 8 of 8). The suite
  was restarted at 15:36 (~/asc_tests.log). The A/B isn't affected (its builds have damage).
- 16:10: task 48's scan written: engine/tools/asc_cond.py on branch `asccond` (on top of ascpoints, worktree ~/phaph_asccond; 3 unit tests pass). Probe on Titan, 3 skills: finds Crushing Impacts / Heavy
  Stunned +25%, which the old scan can't see (a notable on another's path shows the same row: Mountain Splitter). ~40 min per ascendancy on 6 cores estimated, ~15 h for 23. Merge after ascpoints; don't
  start it before 37's queue is done. A/B, branch half so far: Deadeye Rapid Shot 5.76M, Gemling Rapid Shot 4.42M; main half not started.
- 17:00: task 47 suite green (245 passed). A/B branch half done (boss / map / EHP): Deadeye Rapid Shot 5.76M / 4.94M / 12.7k (on .7, path_luck_7: 4.76M / 4.03M / 12.6k = +21%), Gemling Rapid Shot 4.42M / 4.03M / 17.4k,
  Titan Earthquake 4.12M / 2.20M / 48.7k, Abyssal Lich Bonestorm 5.80M / 4.57M / 12.0k, control Invoker Ice Shot identical to .7. Main half running since 16:52 (it copied its code: engine edits in ~/phaph are fine now).
  Then merge ascpoints, deploy, merge asccond (no deploy). rank8 5 of 6 searches; 37 on 22 of 23.
- **17:40 A/B main half so far: Gemling Rapid Shot 5.21M boss / 3.74M map on main vs 4.42M / 4.03M on the branch (-15% boss, +8% map).** Same supports, other uniques (main Hyrri's Ire + Mageblood, branch Grip of Kulemak +
  The Coming Calamity): maybe slot-order luck (22% on this skill), not shown. ~/asc_ab2.sh (starts after asc_ab.sh): Gemling and Titan, reversed and rotated, branch then main -> ~/asc_out/orders_*.json. Judge best of 3 and
  all three signs; don't merge before. Deadeye main 4.76M = path_luck_7, branch +21%: that is about Point Blank's 20%, which PoB counts by the enemy distance (49).
- **18:15, A/B 4 of 5 (boss main -> branch, single order): Deadeye +21%, Titan +25%, Gemling -15%, Abyssal Lich Bonestorm 6.93M -> 5.80M (-16%, map -20%).** Abyssal's new passives cost it nothing (dropping any or all from the
  branch build: 0% damage, -10% EHP); it ended on other uniques. So full rebuilds mix the fix with gear luck (Bonestorm's orders spread 50%).
  **Paired test (respend only the ascendancy of 37 finished builds with the branch; ~/asc_pair.log, ~/asc_pair_rest.log, script ~/asc_out/pair2.py):** 1 loses damage (Wind Serpent's baseline -65%; the old code
  does the same there: greedy's blind spot). EHP falls on 3 (Gemling -8, Titan -11, Amazon Earthquake -4%) where damage rose +35 / +48 / +2%. Old code respent on 10 of them (~/asc_pair_old.log + 2 by hand): the fix
  itself is worth Deadeye +20% (Point Blank at 2 m), Gemling about +13% (+35 vs +19%), Abyssal Lich +12% EHP, Titan 0. The rest is respending late (50). Gate kept: best of 3 orders (asc_ab2) before merging.
- My probe's PoB grew to 12.8 GB over ~30 loaded builds and was OOM-killed at 18:11 (that process only; the other containers are up). Long probes: a new PoB per build, --memory 4g.
- 37's condition scans finished; matrix_asc runs (old code). Conditions: Infernalist is redone by ~/infernalist.sh after it.
- **19:00: A/B complete, control Invoker identical on both sides.** asc_ab2 running since 18:29 (branch half first; nothing finished yet at 19:00). Task 50 written: branch `respend` (worktree ~/phaph_respend, on ascpoints):
  engine/ascendancy.py, called after the final gear pass, kept only if the score rises, EHP stays over 90%, no attribute falls short and spirit fits; 2 tests pass. ~/respend_ab.sh waits for asc_ab2, then the full suite
  (~/respend_tests.log) and the 5 specs (~/respend_ab.log, ~/asc_out/respend.json; compare with asc.json). rank8: all 6 searches done, building (1 of 18 skills at 19:00).
- **20:00: asc_ab2 branch half done (boss / map): Gemling as is 4.42M / 4.03M, reversed 4.63M / 4.25M, rotated 5.42M / 5.04M; Titan as is 4.12M / 2.20M, reversed 4.29M / 2.16M, rotated 4.15M / 2.22M.** Main half running
  since 19:45 (main as is: Gemling 5.21M / 3.74M, Titan 3.30M / 1.83M). Merge ascpoints if best of 3 isn't lower.
  Task 49 code on branch `distance` (on top of respend, worktree ~/phaph_distance, no suite, no builds yet): auto_config sets 4 m for projectile skills (an estimate; ice spears and spells like Spark included),
  2 m for melee and minions; 15 skills checked: projectile ones get 4 m; Comet, Unearth (spells, not projectile) and Fangs of Frost stay at 2 m. Changes every ranged score, so test after 47 and 50 are in: suite, then search-vs-ladder and 5 builds.
- **21:00: engine 2026-11-25.1 live (task 47).** Gate (branch's best of 3 not lower): Gemling met (5.21M -> 5.42M), Titan missed by 3% (4.42M -> 4.29M), overridden: swapping only the passives between the two rotated Titan
  builds, main's gains 45% and the branch's loses 35%, and the branch's has 64k EHP vs 14k. Details in BREAKER.md. respend suite + builds running (~/respend_ab.sh). Next: 50, then 49, then merge `asccond` and start 48 (matrix_asc
  running in ~/breaker is old code: its result is a "before").
- rank8: 4 of 6 searches done 15:00 (~1.5 h each), builds next.
- **21:35:** respend suite green (247 passed, 1 warning in 2364.33s (0:39:24)); the 5 builds follow on their own (~/respend_ab.log). Task 50's code read: its put-back goes through load_xml, which guide.build_stage already uses mid-build
  in two places; no fault found. matrix_asc: Infernalist done, Blood Mage 143 skills in, ~2 h each, so ~40 h for the rest (see Waiting for Kyle). rank8: Deadeye's 3 skills done, ~1.5 h per skill with 2 workers.
- **23:05: task 50 A/B, 4 of 5 (without -> with respend, single order; only the respend step differs):** Gemling Rapid Shot boss 4.42M -> 5.12M, map 4.03M -> 4.71M, EHP same; Deadeye, Titan identical;
  Abyssal Lich damage same, EHP +1.6%, chaos res 75 -> 69. No damage or EHP loss. When the Invoker control lands (~/respend_ab.log) unchanged: bump ENGINE_VERSION to 2026-11-25.2, merge `respend`, deploy, push (suite green: 247). Then `distance` (49).
- **23:30: task 50 live as 2026-11-25.2** (A/B 5 of 5, control identical). Next: 49 (branch `distance`: merge main into it, suite, search-vs-ladder, 5 builds), then merge `asccond`, 48.
- 23:40: main merged into `distance`; suite (container distance-tests, ~/distance_tests.log) and, at the same time, ~/distance_ab4.sh: 5 specs (~/distance_ab.log, ~/asc_out/distance.json vs respend.json). Scores of ranged builds must drop (the model changed), so judge the search vs the ladder, not the size of the drop. The 23:30 deploy cancelled one generate job someone was watching (30bb3936).
- **matrix_asc stopped with Kyle's OK ("whatever you think is best"), and ~/infernalist.sh cancelled with it.** Old-code results kept in ~/asc_before47/matrix_asc (Infernalist, Blood Mage complete, Lich partial).
  ~/breaker cleaned 2026-11-26 00:00 (its uncommitted diff in ~/asc_before47/breaker_wip) and pulled to main. Start 48 after 49 is settled.
- **00:55 task 49:** suite 247 + 1 failed: test_style's combo test, failing on main too (the 11-25 combo re-run moved Rend's setups to Talisman / Bow / Spear); test fixed on main (picks any combo a Titan can use),
  merged into `distance`. A/B single order (respend -> distance, boss): Bonestorm, Earthquake identical (melee / spells untouched, as meant); Gemling Rapid Shot 5.12 -> 4.04M; Deadeye Rapid Shot 5.76 -> 8.12M, but
  same ascendancy (Point Blank), the new build is simply better at every distance (7.11M vs 4.94M at 2 m): rebuild luck. Invoker Ice Shot (bow, so not a control here) 2.56 -> 2.34M boss, 1.56 -> 1.13M map. So the A/B can't judge 49. Same build 2 m -> 4 m: -16%. Running: ~/distance_blind.sh,
  blind search Deadeye + Tactician, class weapons, main vs distance side by side (~/dist_blind/{main,distance}.json, 3 cores each, a few hours). Judge: ladder skills' ranks (Ice Shot, Tornado Shot, Snipe; Galvanic Shards,
  Wolf Pack, Stormblast Bolts) better or not. Merge if not worse; 4 m stays an estimate (note it on the lead page later).
- 01:35: main merged into `asccond` (clean; it only adds runner handlers get_config / asc_tries + tools/asc_cond.py + 1 test file); pushed. After 49 lands: suite on it, merge, then 48 from ~/breaker via the queue (asc_cond.py has no queue job yet: add one, or a script like rank8.sh).
- 02:30 task 49 blind check, Deadeye (main vs distance): top 3 same (Rain of Arrows 1.80 -> 1.59M search score, Ice Shot 2nd both, 440k -> 391k); Tornado Shot enters at 8 of 10 (was out); all bow skills fall ~10-17% alike, so within one class it hardly reorders. Its real effect is across weapon kinds (Lodestone, no class rules). Tactician pending.
- **03:55: task 49 live as 2026-11-26.1.** Blind check, class weapons, main vs distance: Deadeye top 3 same, Tornado Shot 8th (was out of 10); Tactician top 4 same, crossbow skills
  -6 to -17% except Explosive Grenade (+0%, not a projectile in PoB's types); ladder skills found 1 of 6 on both. So within a class it barely reorders; its effect is across weapon kinds (Lodestone), unmeasured.
  Next: suite on `asccond` (2 cores), merge, then task 48 (needs a run script); then 51 (re-grade).
- 04:50: /lodestone/how-it-works live (api/static/lodestone/how-it-works.html, noindex, linked from /lodestone; source design/lodestone-explained.html, numbers as of 11-26). Cloudflare Pages has no branch previews (404), and serves the home page for unknown paths with 200: check the title, not the code.
- **05:45 (11-26): task 48 queued: ~/task48.sh** (~/task48.log): waits for the asccond suite (2nd run, container asccond-tests2; the 1st failed only on the text-scan test fixed in 68b90bf), merges `asccond` + pushes if green (no deploy), freezes ~/phaph_48, waits for rank8 and the nightly sweep, then asc_cond.py on 23 ascendancies, 6 cores, --memory 18g -> ~/asc48_out/*.json (~15 h estimate; resumable). Read: `python3 engine/tools/asc_cond.py report ~/asc48_out`. Then 48's blind re-run, then 51. rank8 at Tactician (4 of 6 ascendancies built).
- **11:05: task 39 closed (BREAKER.md 'Search vs full builds on the current engine').** 5 of 6, in each order alone too; Amazon's miss is real (my 05:55 'luck' note was wrong). The nightly sweep started 10:38 after rank8; task48.sh starts when it ends.
- **07:00: `asccond` merged as 42515a9 and pushed (suite green, 251 passed; no deploy). ~/phaph_48 frozen there; task48.sh waits for rank8 (Tactician done: Plasma Blast 5.47M best of 3 but 2.97M as is, Rapid Shot 6.32M #1 = search #1; Martial Artist, Oracle left) and the sweep.**
- **06:05: the asccond suite (2nd run) died at ~28% with no result line (container gone between 05:30 and 06:00; probably went with the old session's shell), so task48.sh stopped (~/task48_try1.log).** Re-run detached: ~/asccond_tests3.sh (setsid, ~/asccond_tests3.log, ends with a 'done' line); ~/task48.sh restarted, now waits for that line. Start long jobs with setsid nohup, never from a foreground shell.
- **05:55 rank8 partial (4 of 6 ascendancies, 10 of 18 skills; not a verdict):** search's #1 = best full build (best of 3 orders) in Deadeye and Titan, not Amazon (Wind Serpent's Fury 1.03M vs Fangs of Frost 1.64M, but Fangs wins only its 'as is' order: reversed it is 0.96M, below both). Order spreads 6-85% per skill (median ~33%), so a #1 flip within that spread is luck, not the search. Finish after Tactician 2-3, Martial Artist, Oracle; write to BREAKER.md, close 39.
- **12:30 (11-26):** nightly sweep running (sweep-0-6, started 10:38); ~/task48.sh starts task 48's scan when it ends. Task 42 ticked (Lodestone uses best of 3; spread not fixed at the root). Task 53 prepared: engine/EXPORT_DRYRUN.md (exporter needs the live game, not the pre-launch torrent). Next: 48 runs ~15 h, then 48's blind re-run, 51, 38.
- **17:00 (11-26): task 48's scan started 16:39** (container asc48, 6 cores, ~7 GB of 18; code 42515a9 in ~/phaph_48), Infernalist first -> ~/asc48_out. Sweep finished 15:35 (0 failed). ~15 h estimate, so ~08:00 11-27.
- **19:20 (11-26):** task 48's scan 4 of 23 (Infernalist, Blood Mage, Lich, Abyssal Lich running; ~34 min each, so ~05:30 11-27). Meanwhile task 54 done: ladder history from the Wayback Machine (engine/tools/ninja_archive.py, data/ninja_archive; BREAKER.md 'Ladder history'). 0.4.0c: Walking Calamity 12.0 -> 8.2% in 11 days, the only case whose turn lines up with its patch.
- **21:05 (11-26):** task 48 at 7 of 23 (Warbringer running). Done since: 0.4 cases in the answer key + first 0.4 grade (4.7 missed, 2 of 13), 0.4 false alarms judged (1 real of 62 flagged). Next light task: 55 (needs the Wayback Machine back up).
- **23:40 (11-26):** task 48 at 11 of 23 (Disciple done 23:28; ~06:30 11-27 end). Task 55 closed (MAX_SKILLS stays 3). Every other open task waits for 48, Kyle's PC, or is shelved UI.
- **01:20 (11-27):** task 48's scan at 15 of 23 (~05:30 end). **~/after48.sh queued** (setsid, ~/after48.log): after 48's 'all done' and a free server (the 05:00 sweep runs first), freezes main in
  ~/phaph_51, runs task 51's old-patch scans there on 6 cores (0.1 + 0.3 condition/matrix/stack, 0.2 + 0.4 condition/matrix) into data/breaker/old51 (old/ kept; ~/old51_patch.log), grades
  (old51/grade.txt, verdicts shared from old/), commits; then 48's blind re-run (unlocked) -> blind_unlocked_51.json / .txt, commits. old_patch.sh / grade_old.py take ENGINE_DIR / OLD_DIR / OLD_LOG.
  Smoke test 01:03: current engine runs on 0.1's PoB (Arc scanned, no error; 1 skill only). New pieces flagged by the re-grade are unjudged: judge with old_verdicts.py / old_skill_verdicts.py before quoting false alarms. Then 48's read (`asc_cond.py report ~/asc48_out`), 38.
- **02:30 (11-27): asc_cond.py report fixed** (report only; scan files unchanged): a pair now counts only if notable + condition beats the better of the two alone (`pays`). Before, player-side Frozen /
  Chilled (the build's damage x~0.2) times a notable that cancels it (Pathfinder 'speed unaffected by Slows') topped the report at +233% on 68 skills with both together = the notable alone (+4%). 17 of 23 read
  (partial, not a verdict): top pairs Amazon Open Weakness +50%, Titan Heavy Stunned +25%, Warbringer Armour Broken +20%, Witchhunter low life +16%; skill outliers Flicker Strike Witchhunter +57% over the usual.
- 03:00 (11-27): task 48 at 19 of 23. Gemling done: no strong conditional passive (best: Integrated Efficiency vs Critical Weakness +4% on 46 skills; others +4-8% on 1 skill). Its implants pay plainly (task 47's fix), so for Gemling the blind re-run in after48.sh is what counts.
- **11:50 (11-27):** task 51's scans started 11:19 (after48.sh, 6 cores, frozen ~/phaph_51 at 2cbc6d6). Task 56(d), comma gem names, see the task line.
- **19:50 (11-27): task 51 done** (BREAKER.md). after48.sh's blind re-run waits for rolls-ab2 to end (its busy check counts any container). rolls-ab2: 12 of 16; typical reversed: RoA 1.55M, Ice Shot 2.87M (keep Mageblood), Rapid Shot 5.65M, Bonestorm 6.80M (drop it).
- **18:30 (11-27): rolls-ab2, best roll in all 3 orders done (8 of 16), all wear Mageblood.** Boss as is / reversed / rotated: RoA 2.65M / 1.30M / 0.65M, Ice Shot 2.34M / 2.15M / 2.56M, Rapid Shot 8.12M / 8.97M / 6.23M, Bonestorm 11.31M / 13.59M / 9.30M. Best of 3: 2.65M, 2.56M, 8.97M, 13.59M. Typical roll's 2 new orders next (8 builds).
- **16:10 (11-27): rolls-ab done, 8 of 8, "as is" order (~/rolls_ab/rolls_ab.json).** Typical vs best, boss / EHP: RoA 1.86M / 28.5k vs 2.65M / 8.4k (keeps Mageblood); Ice Shot 2.56M / 11.1k vs 2.34M / 37.5k; Bonestorm 3.88M / 15.1k vs 11.31M / 10.6k; Rapid Shot 5.10M / 9.3k vs 8.12M / 11.2k (all three drop Mageblood). So a typical roll drops Mageblood in 3 of 4 and boss damage moves -30% / +10% / -66% / -37%, single order each: not a verdict. Running: ~/rolls_ab2.sh (container rolls-ab2, 2 cores; rolls_ab.py --orders on branch rolls, 97b7e5d) adds reversed + rotated for both rolls (16 builds, several hours, estimate) -> ~/rolls_ab2/rolls_ab.json. Judge per spec on best of 3 orders, best roll vs typical.
- **15:30 (11-27):** rolls-ab 7 of 8 (Rapid Shot typical left). Typical vs best, boss / EHP: Ice Shot 2.56M / 11.1k vs 2.34M / 37.5k, drops Mageblood; Bonestorm 3.88M / 15.1k vs 11.31M / 10.6k (boss -66%), drops Mageblood; RoA keeps it (-30% boss, EHP x3.4). Single order each, and other gear means another tree (task 42's path luck), so Bonestorm's -66% may be partly luck: check its spec in 3 orders before quoting.
- **15:00 (11-27):** rolls-ab 5 of 8 (boss DPS / EHP): best roll RoA 2.65M / 8.4k, Ice Shot 2.34M / 37.5k, Rapid Shot 8.12M / 11.2k, Bonestorm 11.31M / 10.6k; typical RoA 1.86M / 28.5k (boss -30%, EHP x3.4) and still wears Mageblood. One typical row only: no verdict. 51: 0.1's PoB v0.12.2 matrix done 14:43, stack running.
- **14:05 (11-27):** nothing new started: the server is full (task 51's old-patch scans, 6 cores, at 0.1's PoB v0.12.2 matrix after 0.5.0's three scans; rolls-ab, 2 cores, 1 of 8 rows: Rain of Arrows best roll 2.65M). Every open task waits on these, on Kyle (57's roll question queued in pending.txt for 8 am Mazatlan) or on the PC. Looked at 14's 'mapping combos' and put it off: a setup-then-payoff cycle doesn't fit packs that die in one or two hits, and the one part that does fit (a payoff applying its own ailment on mapping enemies) needs CPU to measure. Next session: read rolls-ab when it's 8 of 8, then 51's grade.
- **08:20 (11-27): task 56 (sweep findings, Whetstone).** 48's scan done 05:42; nightly sweep (sweep-1-7) running, after48.sh waits for it. (a) Culling: branch `cull`
  (worktree ~/phaph_cull, engine 2026-11-27.1): mapping culls at 10% not 35%; ~/cull.sh = suite (cull-tests, 2 cores, ~/cull_tests.log) -> merge, deploy, push
  (~/merge_cull.log). (b) 'made-up gem Fire Spell on Melee Hit' was the check's fault: fixed on main 92a2bfb. (c) Megalomaniac: branch `enchants` (~/phaph_ench,
  test_pob_fixes 20 passed): after cull lands, merge main into it, add a cull unit test, full suite, deploy 2026-11-27.2.
  08:15: PoB does apply Megalomaniac's notables (7 of 59 sample picks change a bare Spark build, e.g. Potent Incantation x1.213): only the card text was wrong.
- Task 37's queue waits for the old-patch scans (0.2 matrix, then 0.4), so it starts late.
- **Task 42 (12:40):** Rain of Arrows Invoker: 849k boss as is, 3.46M with slots reversed (same spec, x4.1). Cause, part 1: once
  worn, a unique is never checked again (BREAKER.md). Fix on branch `revisit` (worktree ~/phaph_revisit, not pushed or
  merged; 1 new unit test passes): gear._revisit_uniques. ~/revisit_ab.sh waits for the path-luck container, then runs the
  same 12 builds on the branch (~/path_luck_revisit.log, ~/revisit_out/path_luck_revisit.json), then the full suite
  (~/revisit_tests.log). Next: compare both reports (`path_luck.py report`); judge on spread AND level per spec. If the
  "as is" builds rise and nothing falls, merge and deploy. If the spread stays > 10%, do best-of-two starts.
- Task 41 A/B: quiver +43-46%, focus +64-79% (search-style); suite running. 0.3 condition graded (3.6 missed; 1 real, 34 false).
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
- **Kyle 2026-11-24:** endgame pick trimming: leave as is. Lodestone claim and page fixes: Claude's call, done (task 32). Leads need more than one full build.
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

- **20:30 (11-27): task 57's 3-order A/B done** (engine/data/rolls/rolls_ab_3orders.txt): typical vs best roll, best of 3, boss -30% / +12% / -37% / -50%; typical keeps Mageblood in 3 of 12 rows. Waits on Kyle (Waiting for Kyle). Running: blind51 (task 48 blind re-run, 6 cores, started 20:28, ~/blind51.log; 4 of 23 by 23:00, ~36 min each one after another, so done ~10:30-11:00 Berlin 11-28 (estimate); after48.sh commits it). 01:00: 7 of 23 in, Bonestorm (Staff or Wand) is #1 in all 7 (Infernalist, Blood Mage, Lich, Abyssal Lich, Deadeye, Pathfinder, Titan). In the write-up, check whether that is the skill or our Bonestorm model (release-time estimate, 20 spikes + explosion all on one boss, BREAKER.md ~line 985) before calling it a find.

- **03:15 (11-28): blind51 at 10 of 23, Bonestorm #1 in all 10, same as the 11-23 run** (engine/tools/blind_diff.py old.json new.json). Changes vs 11-23: Bonestorm on a Wand now
  ~0.9-1.1x the Staff (was ~0.45x: task 41's focus), Earthquake One Hand Mace in the top 3 on 6 of 10 (second weapon / shield), Comet and Coiling Bolts out of the top 3. Not a find
  by itself: these are search scores, and task 38 measured the search over-rating Bonestorm x1.83 vs its full build (Rapid Shot x0.41). The Saturday sweep (cron 05:00)
  waits for blind51's container (breaker_queue.sh line 50), so it starts ~10:30 and runs ~17 h (estimate): the server stays full until ~Sun 03:30.
  Next: when after48.sh commits blind51, run blind_diff on all 23, write it up in BREAKER.md (task 48 closes), then 38's finalists re-run after the sweep.
- **10:20 (11-28): task 48 closed** (BREAKER.md). Bonestorm #1 23 of 23; ladder top 3 found 0 of 69 (11-23: 5). The Saturday sweep started 10:2x (sweep-0-1, ~17 h, estimate). Next: task 38's finalists re-run after the sweep; 57 waits on Kyle.
- **11:00 (11-28): task 38's finalists re-run queued: ~/finalists51.sh** (setsid, ~/finalists51.log): waits for a free server (after the sweep), freezes main in ~/phaph_38, all 17 weapons, top 2, best of 3 orders, 6 cores -> data/breaker/finalists_51.json / .txt, commits. Run time not measured for 17 weapons with 3 orders (many hours, estimate). Then: rank by full builds, compare with finalists_offhand / finalists_orders, read 34's candidates from it.

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

29. [ ] (2026-11-28: re-searched the web (poe2wiki Freeze, Mobalytics freeze guide, forum 3597221): still no number for the per-freeze threshold rise or its decay; still blocked on a datamine / game files) (2026-11-22: draft rules with sources in data/immobilise_rules.json, all unverified; the blocker: how much a
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
32. [x] (2026-11-24, Kyle's OK: text fixes and the narrower claim on the page; single-full-build leads re-labelled) Lodestone page text: leads marked "unconfirmed" show without a colour and the intro still says "needs
    checking in the real game" (front-end paused: ask Kyle before touching the page; put it under Waiting).

33. [x] (2026-11-22: cause = auto_config gave every armour-breaking plain build "always Fully Broken"; now only when it
    breaks a boss in <= 1.33 s; combo leads to re-run (task 30)) Combo builds read ~2x weaker before the combo (task 30): APR Tactician combo build: combo 2.39M vs 1.79M
    "alone" inside it, but the plain build is 3.92M. So the combo path changes the build itself (gear / tree /
    supports / boss setup) or score_combo's "alone" leaves something out. Diff the two builds (lead_builds/ codes:
    supports, gear, tree, config) and fix; then re-run the combo leads. Until then combo leads stay unconfirmed.

34. [ ] (2026-11-28: new under-1% top-3 skills from blind51: Skyfall Wand (0.40%), Earthquake One Hand Mace (0.16%), Coiling Bolts (0.22%); task 38's finalists re-run (best ~2 skills per weapon type, full Uber builds, best of 3 orders) builds these anyway: read them from it, no separate run) (2026-11-22 first 3: Bonestorm 2x Comet (holds), Rain of Arrows -43% vs Ice Shot, Wind Serpent's Fury -11% vs
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

37. [x] (2026-11-25: conditions done, matrix stopped with Kyle's OK; superseded by 48) (queued 2026-11-23: ~/after_unlock.sh runs conditions_asc + matrix_asc after the unlocked blind run; the scans
    resume, so only skills the rule skipped get scanned; ~16-20 h; then read for cross-class payoffs) Re-run the per-ascendancy condition and matrix scans without the class-weapon rule (Kyle 2026-11-22:
    Lodestone has none; the 11-20 runs skipped skills outside each class's weapons). Queue `conditions_asc matrix_asc`
    after the unlocked blind run.

38. [ ] (2026-11-26: the plan is built (tools/weapon_finalists.py, best of 3 orders); left: re-run all weapons on the engine after 47/49/50 (49 changes ranged vs melee across weapons, unmeasured), after 48's scan frees the server) (2026-11-23: the error is per skill (x0.41 Rapid Shot to x1.83 Bonestorm), no single factor; plan: Lodestone
    shortlists ~2 skills per weapon type by search score, ranks finalists by full Uber builds (tools/rank_check.py
    style), weekly) The search's scores across weapon kinds (from the unlocked blind test, 2026-11-23): staff spells score ~10x
    attacks in the search while full Uber builds have them level (Bonestorm 6.0M, Supercharged Slam 5.7M, Rapid Shot
    6.3M). Find what the search's quick build gives spells and not attacks (crafted weapon, +levels, supports, the
    quick tree) and calibrate, so a no-class-rule Lodestone search can compare a Gemling Spark with a Titan slam.

39. [x] (2026-11-26: rank_check on 2026-11-24.8 done: search's #1 = best full build in 5 of 6, Amazon the miss; BREAKER.md) (2026-11-23: suite green, 219 passed; engine 2026-11-23.5 live, finalists restarted; 2026-11-24: per-source breakdown done, on-death explosions out, engine 2026-11-24.1; skeletons counted 0 since 11-17: fixed; Cast on X settled; leads and combos re-run done 2026-11-25; left: rank_check (rank8 running)) Full DPS fix
    (BREAKER.md last section): suite green -> commit, deploy engine 2026-11-23.5, clear finalists.json and restart
    ~/after_sweep.sh (its results are from the buggy engine). Then a per-source damage breakdown check on every build,
    and re-run leads, rank_check and combos before quoting any older full-build number.
40. [x] (2026-11-25: grade failed and claim narrowed, rehearsal timed, labels done; the re-run on every hotfix stays in the playbook) (2026-11-24 20:05: GRADE DONE, failed: 2 of 11 found, 11 real vs 129 false; claim narrowed. Left: launch-day rehearsal timing; nerf-risk labels; off-hand / weapon uniques into breaker.UNIQUE_TYPES (the 0.4 scans still running are frozen code, no case set)) (2026-11-24: PoB tags back to 0.1 run on our runner; Lightning Conduit vs Shocked reads +500% / +115% / +116% / +68% on 0.1-0.4,
    in step with the nerfs; answer key written first; scans started; left: a v0.17.1 (0.5) case set, ordinary builds, scalers and pairs on old
    patches, then the grade) (agreed with Kyle 2026-11-23, by ~Dec 1) Grade Lodestone on known answers: 15-20 past broken builds plus
    ordinary ones on patch data we can load; hit rate and false alarms. Proposed bar: at least half found, at most one
    false alarm per real find; if missed, narrow what Lodestone claims. Then time a launch-day rehearsal (notes ->
    ranked leads); label each lead's nerf risk (bug / extreme outlier = first hit) and re-run on every hotfix.

41. [x] (2026-11-25: (f) done by leads-orders on 2026-11-24.8, which has the off-hands) Off-hands: (c) done 2026-11-24 (Sceptre redone). Was: (see START HERE): (c) running since 09:05: ~/finalists_offhand.sh (Bow, Spear, Quarterstaff, Wand, Sceptre, One Hand Mace) -> data/breaker/finalists_offhand.json, then it starts task 37 (after_sweep.sh stopped: its remaining weapons, claws to flails, have no skills in PoB yet). (a) read the A/B and the suite on branch `offhand`; (b) ~/merge_offhand.sh does it (version bumped on the branch); (c) re-run finalists for Bow, Spear, Quarterstaff, Wand,
    Sceptre and every other one-handed weapon (the rest of today's run is comparable only within itself); (d) done on the branch 2026-11-24: one-handed martial weapons try a second weapon and a shield by score (spear,
    flail: shield only; damage effect not measured yet); (e) done on branch `offhand2` (on top of offhand, worktree ~/phaph_offhand, not pushed): gear.craft_swap fills both hands of set 2; new test passes, full suite
    running (~/offhand3_tests.log). suite green (227 passed); ~/merge_offhand.sh now merges offhand2 (holds both) as 2026-11-24.3; (f) lead re-run (~/after_leads.sh)
    starts right after old_all.sh: make it wait for the merge. Saved builds and earlier A-to-Z / blind rankings of
    bow / wand / sceptre skills read low.

42. [x] (2026-11-26: closed. Measured: spread on 2026-11-24.7 Ice Shot 5%, Rapid Shot 22%, Rain of Arrows 39%, Bonestorm 50% (was 5 / 22 / 320 / 68 before the final-pass unique re-check, live .7). Still over the 10% bar for 3 of 4, so not fixed at the root: Lodestone works around it with best of 3 orders (path_luck.best_of in weapon_finalists, lead_builds, rank_check --orders). Whetstone guides stay single-order: question under Waiting for Kyle.) (2026-11-24 12:40: unique re-check on branch `revisit`, A/B queued, see START HERE) (running since 11:05: tools/path_luck.py, 4 specs x 3 slot orders, 3 cores, ~/path_luck.log -> data/breaker/path_luck.json) (found 2026-11-24, after 41) Full builds land in different local optima: Rain of Arrows Invoker lost 10% by gaining
    a quiver (BREAKER.md). Measure: the same spec built 3 times with small starting differences (gear slot order, first
    supports), 3 skills; if the spread is > 10%, try best-of-two starts for the Uber stage or a final pass that retries
    each unique slot with a rare and the next-best uniques once everything else is set. Needs free cores.

43. [x] (2026-11-24: fillers .4, side-skill search .8; the cache key has the engine version, so old guides aren't served to new requests, only by their old job) Atziri's Communion as a filler support (found 2026-11-24): BREAKER.md. (a) done 2026-11-24 14:05; (b) the
    damage search for spirit skills (kit_out -> optimise_supports) still ignores toughness: a life-reserving support picked
    there for damage isn't checked; (c) EHP of finished builds in finalists / path_luck (13 of 18, 7 of 9 hold it) and in guides
    cached before the fix is wrong; boss DPS is computed before the fillers, so it isn't affected.
44. [x] (2026-11-24: `settle` merged, live as 2026-11-24.5, 231 passed; 2 of 24 saved-build rows gain, none lose) Support search vs conditions (found 2026-11-24): conditions (enemy chilled, ignited...) are set from the supports in place
    and held fixed while the search swaps supports. Bonestorm Lich: from Elemental Focus the full search finds nothing better;
    swapping to Extraction and re-running auto_config gives +35% (4.37M -> 5.92M mapping score). Extraction is better in
    the saved mapping setup; how often this happens elsewhere isn't measured. Try: auto_config + search again until stable,
    or re-score the top few sets with auto_config run on each. After 42's A/B (so it measures one change).

45. [x] (2026-11-25 03:35: done; all 3 made-up changes found, no false alarms, fresh baseline in conditions.json; BREAKER.md) (2026-11-25 02:10: (b) written (condition_scan diff + code stamp; a stale baseline is re-scanned in PATCH mode); (c) end-to-end running: ~/detect.sh, ~/detect.log, clone ~/detect, its day/2026-11-25/SUMMARY.md must show Earthquake +~20%, Leopold and Ice Storm lines; (a) after leads-orders) (added 2026-11-25, from the rehearsal) Launch day: show gem number changes. (a) fresh conditions.json baseline on the current engine (~25 min on 6 cores, after
    leads-orders); (b) breaker_day.sh: dps per skill vs the baseline, moves over 5% listed in SUMMARY.md; (c) detection test: a made-up patch (gem, unique, passive, one buff big
    enough to matter) must show all of them. Needs the same engine on both sides, else the diff is ours, not the patch's.

46. [x] (04:45: done, BREAKER.md: every top mover traced to our own fixes, no ranking bug found; open: Flameblast's cooldown start, off-hand x2+ vs the A/B's +64-79%) (03:50: Flameblast explained, no change: x5.45 full stages (Nov 21 rule) x 2.0 Atziri's Impatience (cooldown 10 s -> 5 s); PoB times it by the cooldown only, so up to ~x1.6 high if the cooldown starts on release (unknown). The rest: ~/hist.sh re-scores 18 skills on each day's engine Nov 18-24, ~/hist.log, results in the session scratchpad hist/) (added 2026-11-25) Biggest moves of the fresh condition baseline vs Nov 18 (Flameblast 7.7k -> 88.6k, Bonestorm 28.7k -> 199k, Wolf Pack 3.5k -> 17.2k): explain the
    top 10 one by one (old file: git show 8031dcb:engine/data/breaker/conditions.json). Flameblast first: its stages / channel time may be counted as free. A wrong
    one is a live ranking bug.

47. [x] (2026-11-25 21:00: merged, live as 2026-11-25.1, 245 passed; A/B in BREAKER.md) Ascendancy points: choice options never tried, Abyssal Lich none, leftovers unspent. Left after the
    merge: cached guides on older engine versions; a guide line saying filler passives aren't in the numbers (steps carry `filler`; page work is paused).

48. [x] (2026-11-28 10:08: blind re-run done, BREAKER.md 'Blind re-run, no class rules, on the current engine': Bonestorm #1 23 of 23, 0 of 69 ladder top 3s (was 5), Spearman +0.39; no find) (2026-11-27 05:40: scan done, 23 of 23, BREAKER.md 'Conditional ascendancy passives'; left: the blind re-run, queued in ~/after48.sh after task 51's scans) (added 2026-11-25) Redo after 47: conditions_asc + matrix_asc, with conditional ascendancy passives seen: the scan takes passives on their plain gain, so "25% more vs Heavy Stunned" (Titan)
    is never taken and its condition reads 0. Per skill, also try each notable (path included) with each condition (override addNodes), or take the passives again under the condition. Then the blind
    test (unlocked) again: Gemling is 32% of the ladder and was scored without its implants.

49. [x] (2026-11-26: live as 2026-11-26.1; projectile skills at 4 m (an estimate), melee / minions / non-projectile spells at 2 m; blind check Deadeye + Tactician 1 of 6 ladder skills on both sides: not worse, not shown better) (2026-11-25 measured: PoB's default is 2 m. Saved builds not re-optimised, at 4 / 6 / 8 m: bow and crossbow -14 to -28 / -14 to -41 / -31 to -64%, spear -15 to -17 / -24 to -31 / -50 to -58%,
    Bonestorm 0 at all. So attacks are flattered against spells. Script ~/asc_out/dist.py) (added 2026-11-25) Enemy distance: PoB's default is what every ranged build is scored at (Point Blank at full value, ranged accuracy penalty small). Find the default, decide a fair one per
    skill kind (melee / projectile) for boss and map, measure what it moves on 5 saved builds. Wide effect: A/B before any merge.

50. [x] (2026-11-25: merged; Gemling Rapid Shot +16% boss / +17% map, 4 others no damage change, live as 2026-11-25.2) (added 2026-11-25) Respend the ascendancy at the end of a build, keep it only if the score rises (it must compare: greedy alone lost 65% on one). On finished builds, respending with the old code:
    Titan Earthquake +48% (EHP -11%), Gemling Rapid Shot +19% (EHP -18%), wand Bonestorm Infernalist +19%; most others 0. The points are chosen before gear, tree and supports are final. After 47.

51. [x] (2026-11-27 19:50: done, BREAKER.md 'Re-grade on the current engine': 3 of 13 in condition / matrix (was 2), 5 of 13 in any column (4 of 12 blind), below half; 16 real / 237 false / 35 unjudged) (2026-11-26 20:15: 0.4 cases added to the key before grading; 4.7 missed on the task-40 engine, now 2 of 13; 0.4 false alarms judged 21:00: condition 1 real / 34 false / 10 unjudged, matrix 0 / 16 / 1; Ancestral Bond was in 0.4's tree, a real miss) (added 2026-11-26, after Kyle: no overselling Lodestone) Re-grade Lodestone on the old patches (task 40's answer key, tools/grade_old.py) after 47, 49 and 48 are in, frozen engine.
    Until then every fix is unproven as far as finding broken builds goes. Report the hit rate and false alarms as they are, against the same bar.

52. [x] (2026-11-26: done, BREAKER.md 'How long PoB takes'; first release 0-3 days after each patch, fixes for 2-4 weeks) (added 2026-11-26) How long did PoB take on past launches? From the PoB PoE 2 repo history (releases, data commits) for 0.2, 0.3, 0.4, 0.5: hours from patch to the first
    release with the new data, and how many fix releases followed in the first week. Gives the real wait instead of "usually within days".
53. [ ] (2026-11-26 12:30: step list in engine/EXPORT_DRYRUN.md. PoB's docs: the exporter does NOT work on the pre-launch torrent (no Data section), so it only helps from launch until PoB's first 1.0 release; Windows GUI only) (added 2026-11-26, needs Kyle's PC with PoE 2 installed, after ~11-27) Our own export: PoB ships its exporter (src/Export, bun_extract_file.exe reads Content.ggpk, Windows).
    Dry run on the 0.5 client: export, load into our runner, compare with PoB's own data. On 1.0 day this gives new gems, uniques and tree from the game files before PoB's release;
    lines PoB's parser doesn't know stay unsupported (tools/unsupported_lines.py counts them). Also: notes -> changes file on a real past patch's notes (never tried).

54. [x] (2026-11-26: done, BREAKER.md 'Ladder history from the Wayback Machine'; dense for 0.4 and 0.5 only, not used in a grade yet) (added 2026-11-26) Ladder side of the patch practice (PC_TODO 11) without the PC: poe.ninja keeps no old leagues, the Wayback Machine has its API answers.
    Follow-up done 19:45: research/broken_builds.md 'How much the 0.4 and 0.5 cases were played': 4.1 and 5.1 at 10%+ of the ladder; 4.3, 4.5, 4.8, 5.2 under ~5%. The answer key has no 0.4 / 0.5 cases yet (0.4 scans committed ungraded): a 0.4 case set for task 51 must be written before anyone reads those scans.

55. [x] (2026-11-26 23:40: done, BREAKER.md 'How many skills real guides level with': 0 of 48 guides over 3 after hand checks, most use 2; MAX_SKILLS stays 3) (2026-11-26 22:55: 400 of 628 archived guides read: 30 have act + endgame variants; parser says 28 use <= 3 main skills, 2 over, both misreads by hand (3 alternative Act 1 starts; an aura with 4 supports as 'main'), so 0 of 30 over 3 so far. Rest fetching (~/moba_fetch2.log, unbuffered). Then report + hand-check every guide over 3, write up in BREAKER.md or PC_TODO, close) (2026-11-26 21:55: engine/tools/moba_leveling.py reads Wayback copies of Mobalytics guides (variants + skill gems from the page state); fetch running detached (~/moba_fetch.log, output buffered; progress = files in ~/.cache/moba_archive; data/moba_leveling.json saved every 10 guides; ~2-3 h for 400). Next: `moba_leveling.py report`, check a few guides' main-skill picks by hand (ties: first slot wins), then decide) (added 2026-11-26 21:05, from the plan's Thu-Fri leftovers) Leveling-skill counts from real guides: leveling.MAX_SKILLS is 3, "4 if guides for the archetype do" (CLAUDE.md), never checked. From the server: Mobalytics pages 403 (Cloudflare); its GraphQL (mobalytics.gg/api/poe-2/v1/graphql/query) answers but has introspection off;
    try Wayback copies of mobalytics.gg/poe-2/builds/* guide pages (archive was offline at 21:05). Count leveling skills per guide by archetype; change MAX_SKILLS per archetype only where most guides use 4.

56. [ ] (08:46: (a) live as 2026-11-27.1, 253 passed; (b) on main; (c) live as 2026-11-27.2, 255 passed; (d) 11:50: sweep lane 1 done (5 builds; started before the culling fix): Bonestorm Disciple of Varashta died after 79 min, 'no gems recognised in: Kelari, the Tainted Sands' (PoB's paste pattern has no comma; the 3 djinn gems). Live as 2026-11-27.3 (12:03, 256 passed). Left: next sweep, Deathblow share; Kyle question) (added 2026-11-27, from the nightly sweep; see START HERE 08:20) Sweep findings: (a) Deathblow (Culling Strike only) in 8 of 9 Act 3-4 builds:
    PoB counts culling vs a normal monster at 35% (x1.54) in the mapping score; count it at the rare threshold (10%). Bare-build check: Spark mapping
    x1.538 -> x1.111, Bonestorm Full DPS x1.700 -> x1.144, bossing unchanged. (b) made-up gem flag: gem list name vs skill name, check fixed. (c) Megalomaniac
    cards showed the wrong notables (enchants not read). Left after (c): re-read the next sweep for Deathblow's share; question for Kyle: Megalomaniac (and
    Mageblood) take the best 3 of 438 notables, a roll almost nobody has.

57. [ ] (20:30: 3-order A/B done, engine/data/rolls/rolls_ab_3orders.txt: best of 3 orders, typical vs best roll, boss -30% / +12% / -37% / -50% (RoA, Ice Shot, Rapid Shot, Bonestorm); typical keeps Mageblood in 3 of 12 rows, best in 12 of 12. Only Kyle's call is left.) (10:40: measured, engine/data/rolls/mageblood_rank_check_8.txt: CORRECTED 13:40: 16 of the 18 builds already wear Mageblood, so the test compares a typical roll with the engine's chosen roll: typical is lower on 17 of 18 (score -0.07 to -0.52). Whether a rare belt beats a typical Mageblood is NOT measured (the earlier 'Mageblood would mostly leave guides' was not shown). Lodestone: 84 of 102 saved full builds wear Mageblood, 19 Megalomaniac, all hand-picked rolls. A/B running since 13:55: container rolls-ab (2 cores, branch rolls, tools/rolls_ab.py, 4 path_luck specs x off/on, "as is" order) -> ~/rolls_ab/rolls_ab.json, .log; several hours (estimate). Branch `rolls` (~/phaph_rolls, pushed, not merged): gear.TYPICAL_ROLLS, off by default, + SlotPlan.hunt; full suite green 11:05 (256 passed). Waiting for Kyle: turn it on? + page text. Megalomaniac (3 builds, engine/data/rolls): best roll +19 to +26% score vs the build's own jewel, typical -9% (worth ~nothing). Not done: Lodestone numbers re-checked)
    (added 2026-11-27, from PC_TODO 'Mageblood (with the planned average-roll fix)', agreed with Kyle 2026-11-18) Uniques with random choices
    (Mageblood 4 of 14 Legacies, Megalomaniac 3 of 438 notables) are picked and shown with the best roll for the build. Plan: wear a typical roll
    (median per slot), list the best ones as "hunt for". Page text ("Choices for this build") would need a one-line change: UI is shelved, so ask Kyle.

58. [ ] (added 2026-11-28, Saturday sweep build 5) Attribute shortfall left in a finished stage: Rain of Arrows Deadeye, Interludes, Str 37 < 46 for a rare
    Gilded Vestments (body armour). The final gear pass only penalises a short slot (guide.py:328 attr_weight=0.25 per point, a soft cost) and has no
    hard check like the spirit safety net, so a base picked in earlier passes (attr_weight 0) stays when no single swap fixes it. Seen before once (11-19,
    Mid Endgame crossbow Str 79 < 89). Fix idea: after the final pass, any slot still short -> re-pick that slot's base among those the build can wear
    (or let balance_attributes run again), then re-check; unit test with a forced short base. Needs the full suite: after the sweep / finalists, or
    alongside them on 2 cores. Re-read the rest of the sweep for more cases first.

## Waiting for Kyle
- **Mageblood / Megalomaniac rolls (task 57, 2026-11-27):** guides wear the best Legacies for the build. On 18 saved Uber builds (16 already wearing
  Mageblood) a typical roll scores 7-52% below the chosen roll on 17. A/B done 20:30 (4 specs, best of 3 orders, engine/data/rolls/rolls_ab_3orders.txt): with a typical roll boss DPS moves -30% / +12% / -37% / -50% and the engine drops Mageblood for a rare belt in 9 of 12 rows. So Mageblood's place in our guides rests on hand-picked Legacies. Turn on typical rolls (gear.TYPICAL_ROLLS on branch `rolls`)? If yes, the
  page's "Choices for this build" line needs to read e.g. "Typical roll; hunt for: ..." (one line in api/static/index.html; UI is shelved, so asking).
- **Several slot orders in Whetstone guides?** Measured 2026-11-25 on 4 specs: best of 3 gains 0-39% boss damage over the default order (0, 5, 22, 39) at about 3x the Uber
  stage's time. Claude's recommendation: not by default; maybe as a slower "best" option later. Nothing is blocked on it.
- Class-weapon rule for Whetstone's default search: after blind_unlocked lands, show what the rule costs a player
  (Lodestone has no class rules: Kyle 2026-11-22) and ask whether Whetstone should change.

## Done
