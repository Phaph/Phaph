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

| # | Step | Status |
|---|---|---|
| 1 | **Pin PoB.** `POB_REF` in `engine/setup.sh` is commit `601768bd` (PoB 0.23.1, dev on 2026-11-10), the same one live runs. `/health` shows `pob_commit`. | Done |
| 2 | **Preflight** (`engine/tools/preflight.py`, also run by `tests/test_preflight.py`). It checks every name and stat our code relies on against the installed PoB. On today's PoB: 0 errors. It also gives 4 warnings about stale picture names (companion gems, renamed uniques) that are harmless. | Done |
| 3 | **Catalog snapshot and diff** (`engine/tools/catalog_diff.py`). The snapshot of today's PoB is in `engine/data/catalog_snapshot.json`: 961 gems, 443 uniques, 1505 bases, 1385 tree nodes. `diff` lists what's new, removed or reworked, plus skill tags no prompt word reaches. | Done |
| 4 | **Baseline** (`engine/tools/baseline.py`): 15 fixed prompts end to end, saved to `engine/data/baseline/prompts_0.23.1.json`, then the sweep of every ascendancy to `sweep_0.23.1.json`. `baseline.py compare old new` flags anything a player didn't get. The item audit baseline is from 2026-11-15 (see below). | Running |
| 5 | **Staging** (`docker-compose.staging.yml`): a second app on http://127.0.0.1:8001, off the tunnel, with its own database, built from any PoB commit. | Done |
| 6 | **Site notice.** A banner at the top of the page, read from `/data/notice.txt` on every health check, so it needs no redeploy. | Done |
| 7 | **Your in-game PoB codes.** Two or three characters to compare against on 1.0, using `engine/tools/accuracy_check.py`. | Kyle |

Item audit on 2026-11-15: every item in all 8 builds is real and readable. The issues left are attribute shortfalls, mostly at leveling, in 5 of 8 builds (e.g. Twister Amazon leveling Int 33 of 86 needed). The crafter doesn't yet enforce a unique's "Limited to: N".

### Commands

```bash
# Staging with a new PoB (1.0): build, open http://127.0.0.1:8001, tear down
POB_REF=<commit> docker compose -f docker-compose.staging.yml -p phaph-staging up -d --build
docker compose -f docker-compose.staging.yml -p phaph-staging down

# Checks, inside the staging container (docker exec -it phaph-staging-app-1 sh, then cd engine)
python tools/preflight.py
python tools/catalog_diff.py diff
python tools/baseline.py run && python tools/baseline.py compare data/baseline/prompts_0.23.1.json data/baseline/prompts_<new>.json

# Site notice on / off (live)
docker exec phaph-app-1 sh -c 'echo "Path of Exile 2 1.0 is out. Builds are being updated for it; results are from 0.4 until then." > /data/notice.txt'
docker exec phaph-app-1 sh -c 'rm /data/notice.txt'

# Before switching live: keep the old image for rollback
docker tag poe2-optimizer poe2-optimizer:pre-1.0
```

To roll back: `docker tag poe2-optimizer:pre-1.0 poe2-optimizer`, then `docker compose up -d app` (no `--build`).

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
