# Feature ideas

These are what PoE 2 players most often want from build tools, matched against what Whetstone can already do. Effort is a rough guess for us, given what already exists.

## Best value first

| # | Feature | Why players want it | What we already have | Effort |
|---|---|---|---|---|
| 1 | **Upgrade path from my character.** Paste a PoB code (or import a character) and get "buy this next": the upgrades ranked by DPS gained per divine, with trade links. | The question every player asks after league start. Most tools show a finished build, not the steps from where you are. | PoB code loading, the crafter's scoring, trade links, unique prices | Medium |
| 2 | **Leveling checklist mode.** A phone-friendly page to tick off while playing: gems to pick up in each act, passive points in order, when to switch skills, when to respec. | People play with the guide on a second screen or a phone. | Tree point order (`tree_order`), gem levels per stage, the 4 stages | Small to medium |
| 3 | **Loot filter for the build.** Download a filter that highlights the build's bases, uniques and currency. | Saves time and is something people come back for. | We know every base and unique each stage uses | Small |
| 4 | **"What kills me" check.** Max hit by damage type, resistances, and a plain warning like "one-shot by a pinnacle boss's cold slam". | Deaths are the main complaint about online builds. | PoB's max hit and EHP numbers are already calculated | Small |
| 5 | **SSF and Hardcore modes.** SSF: only items you can make or find (no trade-only uniques). Hardcore: defence weighted much higher. | Large, loyal groups that most build sites ignore. | The "free" budget is close to SSF; there's already a defence weight | Small |
| 6 | **Divine slider instead of 5 budget tiers.** | Asked for earlier; feels more precise. | The budget caps are already in divines | Small |

## After launch

| # | Feature | Notes |
|---|---|---|
| 7 | **Patch impact on saved builds.** "Your build lost 12% DPS in 1.0.2: Bleed IV was nerfed." | Needs the catalog diff (`engine/tools/catalog_diff.py`), which exists now. |
| 8 | **Popular right now.** A page with the most-generated builds this week, already cached so they open instantly. | Uses our own job database. It also fills the cache with what people want. |
| 9 | **Share cards.** An image of the build (skill, ascendancy, DPS, rating) for Discord and Reddit. | Free advertising each time someone shares one. |
| 10 | **Boss tuning.** Pick a pinnacle boss and the build is tuned for its resistances and hits. | PoB has boss config presets. |
| 11 | **Respec cost between stages.** "Early to Mid maps: 14 points to refund, about 3 divine." | The tree difference between stages is already known. |
| 12 | **Price alerts.** "The unique your build wants dropped under 5 div." | Needs an account or email, which makes it a bigger step. |

## For us, not players

- **Log the words we didn't understand.** The site already shows them to the player. Saving them, without the full prompt or anything personal, gives a ready list of words to add.
- **Weekly A-to-Z run** (`engine/tools/az_test.py`) on a schedule, so a PoB update or price refresh that breaks something gets caught before players notice.
- **Thumbs up / down on each build.** One click, so we learn which picks people don't like.
