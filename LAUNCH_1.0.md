# Updating Whetstone for PoE 2 1.0

1.0 brings a new passive tree, new and reworked skill and support gems, and new and reworked items. This is how the app moves to it without breaking the live site.

## How the app gets its game data

Most of the game knowledge comes from Path of Building (PoB), not from our code:

| Data | Where it comes from | What 1.0 needs |
|---|---|---|
| Skills, supports, gem levels, skill tags | PoB's gem data, read through `runner.lua` (`skill_catalog`) | Nothing in our code, once PoB has 1.0 |
| Passive tree, ascendancies | PoB's tree data | The same, plus a check that the tree optimiser still works on the new layout |
| Item bases, affixes, mod tiers | PoB's item and mod data | The same, plus a review of our crafting rules in `gear.py` |
| Uniques | PoB's unique list | The same |
| Which bases drop | `data/base_availability.json` (trade site) | Run again in the 1.0 league |
| Pictures | `data/icons.json` | Run again, for new bases, gems and uniques |
| Unique prices | `data/unique_prices.json` (poe.ninja) | Run again once the 1.0 economy settles |
| Cast on X energy | `data/trigger_rules.json` | Check the numbers again in-game |
| Rating scale | `data/rating_calibration.json` | Run the sweep again |

So the update is mostly: **move to PoB's 1.0 version, rerun the data tools, then check everything still makes sense.** The risk is in the smaller set of names and rules we wrote ourselves. That covers:
- the ailment supports "Bleed I–V";
- the skill tags behind prompt words, such as Warcry, Herald and AppliesCurse;
- the weapon pairings;
- the Cast on Critical gem name;
- the jewel bases Ruby, Emerald and Sapphire;
- the stat names behind focuses, such as CritChance and BlockChance;
- skill aliases such as "coc";
- the crafting rules.

Any of these can be renamed or removed in 1.0.

## Safety rules for the whole update

1. **The live site never runs untested 1.0 code.** 1.0 is built and tested in a second container on the PC (staging). The live container keeps running the old version until staging passes everything.
2. **Keep the old version one command away.** Tag the current image before switching, so going back is `docker tag` plus a restart.
3. **Cached builds update themselves.** The cache key is the PoB version plus `ENGINE_VERSION`, so once 1.0 is live every old build is rebuilt on its next request. Nobody gets a pre-1.0 build marked as 1.0.
4. **Only change things on purpose.** PoB is currently pulled from its `dev` branch with no fixed commit, so any rebuild could change the engine without warning. Pin it to a commit now, and move to 1.0 by changing that one line.

## Before 1.0 (now to Dec 11)

| # | Step | Who |
|---|---|---|
| 1 | **Pin PoB.** Set `POB_REF` in `engine/setup.sh` to the commit running today, and show it on the site's health check. | Claude |
| 2 | **Game-data preflight tool** (`tools/preflight.py`). It checks that every name and stat our code relies on exists in the installed PoB: ailment support tiers, skill tags, weapon types, jewel bases, trigger gem names, aliases, focus and output stats, classes and ascendancies, and that the unique prices, pictures and base names match PoB's lists. It prints whatever is missing. Run it once now; it should come back clean. | Claude |
| 3 | **Catalog snapshot and diff tool** (`tools/catalog_diff.py`). Save today's skills, supports, uniques, bases and tree summary. On 1.0, it lists what is new, removed or changed, so new skill types and mechanics get prompt words and nothing quietly disappears. | Claude |
| 4 | **Baseline results.** Save today's numbers: the item audit, a sweep of every main skill (DPS, or why it failed), and about 20 test prompts run through `tools/check_prompt.py` (bleed crossbow crit, minions, CoC and so on). This is what 1.0 gets compared against. | Claude |
| 5 | **Staging container.** `docker-compose.staging.yml` runs a second app on another port, not on the tunnel, with its own job database. | Claude |
| 6 | **Day-one site notice.** A banner that is switched on by a setting: "Path of Exile 2 1.0 is out. Builds are being updated; results are from 0.x until then." No redeploy needed to turn it on or off. | Claude |
| 7 | **Your in-game PoB codes.** Two or three characters to compare against on 1.0. `tools/accuracy_check.py` already does the comparison. | Kyle |

## Launch week, in order

PoB usually gets a 1.0 update within a few days of the patch, tree first and full gem and item data after. Until it does, the site stays on 0.x with the notice on.

| # | Step | Passes when |
|---|---|---|
| 1 | Turn on the site notice. | Banner is live |
| 2 | Point `POB_REF` at PoB's 1.0 commit and build the **staging** image. | Image builds, engine starts |
| 3 | Run `tools/preflight.py`. Fix every missing name (e.g. "Bleed I–V" renamed, a skill tag split). | Nothing missing |
| 4 | Run `tools/catalog_diff.py`, then: add prompt words and skill kinds for new skill types; add aliases for new gems; check the weapon pairings and ascendancy list; check whether new mechanics such as a new ailment or damage type need a theme. | Every new or removed entry reviewed |
| 5 | Tree: `tools/tree_bench.py` on the new tree. Check that ascendancy nodes, attribute nodes and jewel sockets are found, and that leveling stages still path from the class start. | Trees spend all points and score sensibly |
| 6 | Items: review the crafting rules in `gear.py` against 1.0 crafting, such as new currency or new limits on mods per item. Run the item audit in strict mode. | Every item real, readable and usable |
| 7 | New league data: `fetch_bases.py` (new league name; wait about 2 days so listings exist), `fetch_icons.py`, and `fetch_prices.py` once poe.ninja has enough listings (about 3–7 days). Until prices exist, an unpriced unique only goes into unlimited-budget builds (this is already how `gear.py` works), so the other budgets get rares until prices land. | Files refreshed for the 1.0 league |
| 8 | Run `tools/trigger_check.py` for Cast on X, and re-check the energy numbers in-game. | Rules match, or are marked unverified |
| 9 | Full checks: pytest, the item audit, the skill sweep (`tools/sweep.py` and `tools/why_empty.py` for skills that make no build), and the 20 test prompts. Compare against the baseline. Big DPS changes are expected from the reworks; zeros, crashes and requests that didn't make it into the build are not. | All green; every prompt still delivers what it asked for |
| 10 | `tools/accuracy_check.py` against your 1.0 PoB codes. | Our numbers match the PoB app |
| 11 | Re-calibrate the rating from the new sweep. | `rating_calibration.json` updated |
| 12 | **Switch live.** Tag the old image, bump `ENGINE_VERSION`, deploy 1.0 to the live container when no builds are running, then turn the notice off. | Site shows the 1.0 PoB version |
| 13 | Watch the first day of real prompts. Unread words and builds that changed what was asked show which prompt words to add. | Fixes go through staging first |

## What can't be fully automated

- **Numbers only the game shows.** Cast on X energy and anything else PoB doesn't model need an in-game check by you.
- **PoB's own bugs on day one.** If PoB 1.0 gets a skill wrong, our build is wrong too. The accuracy check against your characters is how we catch it, and PoB fixes usually arrive within days.
- **Prices in the first week.** Unique prices are thin and swing a lot, so budget tiers are least reliable then.
