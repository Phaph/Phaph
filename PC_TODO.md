# Go-public plan (current)

Cheapest path: picker form (no Claude API at launch), hosted on Kyle's PC with a free Cloudflare Tunnel, Hetzner later.

| # | Step | Who |
|---|---|---|
| 1 | Website: done (`api/static/index.html`, served at `/`) | Claude (cloud) |
| 2 | Start a local Claude Code session on the PC in this repo | Kyle |
| 3 | Real unique prices from poe.ninja into `engine/data/unique_prices.json` (until then unpriced uniques only appear on "No limit") | Local session |
| 4 | Accuracy check: one of Kyle's builds in the engine vs the PoB app | Kyle + local session |
| 5 | GGG third-party tool rules; credits (PoB MIT, GGG trademark) are in the site footer | Local session |
| 6 | Run Docker on the PC + Cloudflare Tunnel + domain (~$10/yr). Set `DAILY_JOB_LIMIT` | Kyle + local session |
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
   - unique prices, so uniques go into gear plans at the right budget
   - real divine prices to replace the budget estimates
4. **Tune enemy settings and the mapping clear score** against real play. Mapping vs bossing is built: bossing uses a pinnacle boss, mapping uses normal monsters plus our own area and projectile weighting.
5. **Move the code to the new repo.**
6. **Web API: done** (`api/`), with background jobs and a SQLite cache. Left: hook up the website.
7. **Build the prompt layer** with the Claude API: "lightning minion Monk, 5 divine" becomes a build spec.
8. **Build the website** on top of the API.
9. **Test making a Mobalytics page** through Chrome, and find out whether the passive tree can be entered.
10. **Set up scheduled checks** for patches, PoB updates and ladder data.

## Engine gaps to work through
- Jewels and attribute requirements aren't handled.
- The tree optimiser is greedy, so it can miss a strong node behind weak ones.
- The leveling stage is a single snapshot, not a step-by-step route.
- A full guide takes about 2.5 minutes on 4 cores. The API cache makes repeat requests instant; more cores make first requests faster.

## 1.0 launch day (Dec 11)
1. Update PoB as soon as it supports 1.0 and the Shadow.
2. Run the Shadow dual wield dagger bleed build through guides and comparisons, at each budget.
3. Check the results in game and tune.
