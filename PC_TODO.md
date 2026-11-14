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
1. **Get the engine running on Windows.** `setup.sh` needs bash and gcc, so use WSL or Docker Desktop, whichever the PC has.
2. **Check accuracy.** Load your PoB code in the engine and in the PoB app, and compare DPS, life, EHP and resistances. Fix any gaps.
3. **Pull real data from poe.ninja** (the PC's network isn't blocked):
   - top builds as starting points for the optimiser
   - unique prices, so uniques go into gear plans at the right budget
   - real divine prices to replace the budget estimates
4. **Set realistic enemy settings** for bosses and maps in PoB, so DPS numbers are closer to in-game.
5. **Add a mapping vs bossing switch** to each guide.
6. **Move the code to the new repo.**
7. **Build the web API:** a request for a guide or a comparison, a job queue, and a cache so repeated builds load instantly.
8. **Build the prompt layer** with the Claude API: "lightning minion Monk, 5 divine" becomes a build spec.
9. **Build the website** on top of the API.
10. **Test making a Mobalytics page** through Chrome, and find out whether the passive tree can be entered.
11. **Set up scheduled checks** for patches, PoB updates and ladder data.

## Engine gaps to work through
- Jewels and attribute requirements aren't handled.
- The tree optimiser is greedy, so it can miss a strong node behind weak ones.
- The leveling stage is a single snapshot, not a step-by-step route.
- It's too slow for a website. A full guide takes about 2.5 minutes; needs caching and smaller candidate lists.

## 1.0 launch day (Dec 11)
1. Update PoB as soon as it supports 1.0 and the Shadow.
2. Run the Shadow dual wield dagger bleed build through guides and comparisons, at each budget.
3. Check the results in game and tune.
