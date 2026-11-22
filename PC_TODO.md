> **Where we stopped (2026-11-18, end of the long PC session):** Whetstone runs on the Contabo server; the PC is only
> for heavy batch jobs. The "Whetstone server" session (bypass mode, kept going by ~/routines/keepalive.sh) works
> through NIGHT_TASKS.md; the Lodestone (Breaker) queue runs engine-only scans from ~/breaker; nightly A-to-Z sweeps
> at 10 pm Mazatlan; 8 am report to Kyle's phone. Kyle is away ~10 days (phone + laptop). Next big items: the
> NIGHT_TASKS list, then BREAKER_ROADMAP.md weeks 2-3. Public name of the Breaker: Lodestone.

> **Moving to a Contabo server (2026-11-17):** see `SERVER_MOVE.md` for the steps and the open work.

# Go-public plan (current)

Cheapest path: picker form (no Claude API at launch), hosted on Kyle's PC with a free Cloudflare Tunnel, Hetzner later.

| # | Step | Who |
|---|---|---|
| 1 | Website: done (`api/static/index.html`, served at `/`) | Claude (cloud) |
| 2 | Start a local Claude Code session on the PC in this repo | Kyle |
| 3 | Done: 373 unique prices from poe.ninja (Forbidden Rites, 2026-11-14) in `engine/data/unique_prices.json`. Refresh with `engine/tools/fetch_prices.py`. Left: check names match PoB's unique list once the engine runs | Local session |
| 4 | Accuracy check: tool ready (`engine/tools/accuracy_check.py`, see DEPLOY_PC.md section 3). Waiting on Docker + one of Kyle's PoB codes | Kyle + local session |
| 5 | Done: `research/ggg-third-party-rules.md`. Footer now uses GGG's exact non-affiliation line and credits poe.ninja | Local session |
| 6 | Ready: `docker-compose.yml` (app + Cloudflare Tunnel), `.env.example` (`DAILY_JOB_LIMIT=100`), steps in DEPLOY_PC.md. Kyle: install WSL + Docker Desktop, Cloudflare account, domain, tunnel token | Kyle + local session |
| 7 | Friends beta, then public. Optionally pre-build popular themes overnight so most visits hit the cache | Kyle |

First message for the local session: "Read CLAUDE.md, PC_TODO.md and RESEARCH_BRIEF.md, then do steps 3-6 of the go-public plan."

---

# To do when back on the PC

## Kyle
1. **Start a session on the PC.** Claude desktop app, Code tab, new local session (not cloud). Clone `github.com/Phaph/Phaph`, open the folder, and check out branch `claude/poe2-shadow-build-mobalytics-85ym0e`.
2. **Show Claude `C:\ai\PoB`.** Point the session at it so Claude can see which PoB version is installed there.
3. **Make a new GitHub repo** for the app, e.g. `poe2-build-optimizer`. `Phaph/Phaph` is your profile repo.
4. **Get a PoB code from a character you play.** We use it to check the engine's numbers against the PoB app.
5. **Anthropic API key.** Create it at console.anthropic.com with a monthly spending limit. Save it as an environment variable on the PC, not in chat.
6. **Chrome.** Install the Claude in Chrome extension and sign into Mobalytics.
7. **Later, not urgent.** Pick hosting (Hetzner server, about $5-10/month, recommended) and optionally a domain.

## Claude
1. **Get the engine running on Windows** through WSL or Docker Desktop. The Docker image is built and tested (`docker build -t poe2-optimizer .`, then `docker run -p 8000:8000 poe2-optimizer`).
2. **Check accuracy.** Load your PoB code in the engine and in the PoB app, and compare DPS, life, EHP and resistances. Fix any gaps.
3. **Pull real data from poe.ninja** (the PC's network isn't blocked):
   - top builds as starting points for the optimiser
   - unique prices: done (`engine/tools/fetch_prices.py`)
   - icons for uniques, item bases and gems: done (`engine/tools/fetch_icons.py`, links to GGG's image server). Passive icons still missing: no ready-made links
   - real divine prices to replace the budget estimates
4. **Tune enemy settings and the mapping clear score** against real play. Mapping vs bossing is built: bossing uses a pinnacle boss, mapping uses normal monsters plus our own area and projectile weighting.
5. **Move the code to the new repo.**
6. **Web API: done** (`api/`), with background jobs and a SQLite cache. Left: hook up the website.
7. **Prompt layer.** Keyword version done (`engine/prompt.py`, `POST /parse`, prompt box on the site). Later: Claude API fallback for prompts the keywords miss.
8. **Build the website** on top of the API.
9. **Test making a Mobalytics page** through Chrome, and find out whether the passive tree can be entered.
10. **Set up scheduled checks** for patches, PoB updates and ladder data.

11. **Patch-notes practice: ladder side** (Breaker task 31): fetch poe.ninja's ladder from just before and after 0.5.1
    / 0.5.2 (or 0.4 -> 0.5), so we can check whether our scans on the patched game called the right builds broken or nerfed.

## Engine gaps to work through
- Jewels and attribute requirements aren't handled.
- The tree optimiser is greedy, so it can miss a strong node behind weak ones.
- The leveling stage is a single snapshot, not a step-by-step route.
- A full guide takes about 2.5 minutes on 4 cores. The API cache makes repeat requests instant; more cores make first requests faster.

## 1.0 launch day (Dec 11)
1. Update PoB as soon as it supports 1.0 and the Shadow.
2. Run the Shadow dual wield dagger bleed build through guides and comparisons, at each budget.
3. Check the results in game and tune.

## Mapping vs bossing (Kyle, 2026-11-18)
Every build must answer two questions: what clears maps fast (area), and what kills bosses (single target). Often the
same skill does both; often it is a mapping skill (or combo) plus a boss skill (or combo), sometimes on weapon set 2
(Kyle's Mercenary: Galvanic Shards for mapping; Lightning Rod from a bow on set 2 plus the skill it sets up, for
bosses). To do:
1. Combo finder: pair a skill that creates or applies something (rods, marks, curses, freeze, corpses, grenades) with
   one that consumes or detonates it (text_scan wording), and score the pair together as a mapping or boss combo.
2. A "How you play" card at the top of every build: Mapping: skill(s) | Bosses: skill(s) (+ "swap to weapon set 2"),
   or "one skill does both" with the reason.

## Learning from saved builds (built 2026-11-18, `api/learn.py`)
No model training: the saved builds (`jobs.sqlite3`) and the prompt log feed the search and Claude directly.
How to use (owner tools answer only on the PC, not through the tunnel):
- `curl localhost:8000/learn/winners`: win counts and flags for this patch.
- `curl localhost:8000/learn/misreads`: prompts to review; confirmed fixes go in `api/prompt_examples.json`.
- After a patch update: `docker exec phaph-app-1 python -m api.retest` (re-tests the top 200 old winners,
  writes `/data/retest_<old>_to_<new>.json` with buffed / nerfed lists, and seeds the new patch's head starts).
1. **Bug spotting (first).** Count how often each skill, ascendancy and unique wins. Flag anything that wins far too
   often (Hexblast, Detonate Dead now): either a modelling bug to fix or a real over-powered build for the Breaker.
2. **Head starts.** Start new searches from the strongest past results for similar requests (same theme, damage,
   weapon), so searches are faster and less likely to miss a strong build.
3. **Better prompt reading.** Find prompts Claude misread in `prompt_log.jsonl` ("Abyssal Lich build" read as Lich)
   and add them as worked examples to the reader's instructions.
4. **Memory for write-ups and the Breaker.** Give Claude the most similar past builds and Breaker findings as
   context.

### Patches: archive, re-test, never mix
Every saved result is tagged with game patch, PoB version and engine version. On a new patch nothing is deleted;
old results are archived and each use treats them differently:
- **Bug spotting and write-up memory:** current patch only, counts start from zero.
- **Head starts:** current patch only. Right after the update, the top ~200 old winners are re-tested on the new
  patch. That gives head starts on day one, plus a "who got buffed, who got nerfed" list for the Breaker.
- **Prompt examples:** kept (how people phrase requests doesn't change). Names the patch removed or renamed are
  checked against the new catalog.
- **Old share links:** still open, with a note "made on patch X, may be out of date" and a Rebuild button.

---

# 1.0 update

The plan and checklist for moving to PoE 2 1.0 (new tree, gems, items) without breaking the live site: `LAUNCH_1.0.md`.

## Mageblood (with the planned average-roll fix)
Kyle 2026-11-18: a "More loot" build with Mageblood got Jade + Stibnite (evasion, ~2x toughness) instead of Legacy of
Gold (+45% rarity): rarity is weighted low (goals.weights: +15% rarity ~ +6% damage). Kyle agreed the engine is right
(rarity is cheaper on rings/amulet, the legacies buy more power). Decision: legacies stay picked by score; when a goal
is ticked, the guide adds a swap line instead, e.g. "Hunting for loot? Legacy of Gold (+45% rarity) can replace
Stibnite: -X% toughness" (Faster mapping -> Quicksilver), with the real cost measured in PoB. Do it with the
average-roll fix.

## A-to-Z sweep 2026-11-18 (PC, Hexblast + class weapons fixes): what to fix
22 of 23 ascendancies built (Gemling Legionnaire timed out at 45 min). Classes now keep to their weapons (Hexblast is
gone). None pass every check:
1. **Spirit overdrawn at Uber Endgame on 17 of 22** (-80 to -120). A regression: the spirit safety net doesn't hold at
   the new "end" stage. Highest priority for Whetstone.
2. **Attribute shortfalls on 6** (e.g. Int 43 of 45 for Loreweave + Ornate Ringmail at Interludes; Int 31 of 40 for
   support gems in Act 1).
3. **Detonate Dead wins on 4 (Blood Mage, Lich, Oracle, Shaman)**: needs the corpse usage limit (no corpses on bosses).
4. **Huntress (Amazon, Spirit Walker, Ritualist) picks Rain of Arrows with a bow**, its "close" weapon, over a spear.
   Kyle to decide: is that fine, or should a class's intended weapon win unless the close one is clearly stronger?
5. **Every build takes 24-36 min** on the PC (slow check everywhere): find the slowest steps.
6. Gemling Legionnaire timed out: find where it spends 45+ minutes (the mace exception widens its search).
Results: engine/data/baseline/az_sweep.json (`python engine/tools/az_merge.py` prints the table).
