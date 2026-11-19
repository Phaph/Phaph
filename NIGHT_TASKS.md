# Unattended task list (Kyle away 2026-11-18 to ~11-20, on phone and laptop)

The "Whetstone server" session works through this list on its own, top to bottom, until the usage limit (resets
Friday ~5 am Mazatlan). Kyle wants to use the remaining usage fully: keep going task after task. Kyle can watch and
steer from the Claude app (Remote Control).

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
4. [ ] Build speed: every build takes 24-36 min on the PC, ~45+ on the server; Gemling Legionnaire timed out. Profile
   one build, cut the slowest steps without losing quality (compare DPS before/after on 3 builds).

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
7. [ ] Blind test against poe.ninja's top builds (tool built by this session earlier): run it, write the result into
   BREAKER.md (which of today's top builds the Breaker would have flagged, which it misses and why).
8. [x] In-game test requests: write TESTS.md entries for the strongest leads (Leopold's Applause penetration below 0;
   "not consumed" charge sources adding to 100% for Flicker Strike; Hexblast's real cast rate), each with the PoB
   code, what to buy, what to do, what result confirms or kills it. Ping Kyle once when TESTS.md is ready.
   Done 2026-11-19: TESTS.md with 5 requests (Rapid Shot + Fresh Clip II; Rapid Shot + Rampart Raptor, new lead;
   Leopold's below-0 penetration; Hexblast detonation rate; Ember Fusillade), codes in ingame/. "Not consumed"
   charges: dead (all sources ~45%). Correction: the pairs scan stacks uniques on top of the slot's own item, so
   Leopold's is worth +4% worn for real, not +38%.

### Whetstone features Kyle asked for
9. [ ] Build style choice on the forge: One button / Combo setup / Best (default), using the combo finder.
10. [ ] "How you play" card at the top of every build: Mapping: skill(s) | Bosses: skill(s) (+ "swap to weapon set 2"),
    or "one skill does both" and why.
11. [ ] Mageblood: judge by an average random roll; list legacies to hunt for; swap line for ticked goals ("Hunting
    for loot? Legacy of Gold (+45% rarity) can replace Stibnite: -X% toughness").

12. [ ] Re-run the per-ascendancy condition and matrix scans with ascendancy passives (fixed in task 5) once the
    Breaker queue is free: `JOBS="conditions_asc matrix_asc"` from ~/breaker after a pull.

## Waiting for Kyle
- Lodestone page public? It is live but unlisted (lodestone.html, noindex). Linking it from the home page or
  sharing it is your call.

## Done
