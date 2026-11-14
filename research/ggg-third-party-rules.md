# GGG third-party tool rules, checked against Whetstone

Checked 2026-11-14 from the PC. This is a reading of GGG's published rules, not legal advice. GGG says it can't promise any tool is or will stay allowed, so the safe position is to stay well inside the lines below.

Sources:
- Developer docs, API policies and third-party requirements: https://www.pathofexile.com/developer/docs
- Terms of Use: https://www.pathofexile.com/legal/terms-of-use-and-privacy-policy
- Staff stance on tools (forum): https://www.pathofexile.com/forum/view-thread/3474232

## What the rules say

**Developer docs (third-party policy)**
- Websites and web apps are the lowest-risk kind of tool. Desktop apps are allowed but not encouraged. Apps that touch the game client or its files are banned outright.
- Every public tool must show this exact line somewhere visible: "This product isn't affiliated with or endorsed by Grinding Gear Games in any way."
- A tool must not look official or GGG-made, including by using GGG or game logos in a way that imitates official sites.
- GGG's IP can't be used to make commercial revenue (their examples: selling physical items, copying assets into other games).
- Anything that calls GGG's API must send a User-Agent like `OAuth {clientId}/{version} (contact: {contact})`, follow the `X-Rate-Limit-*` headers and `Retry-After`, and avoid bursts of 4xx errors. Breaking limits often gets the app's access revoked.
- OAuth: one registered application per product, credentials never in code. **New OAuth applications are not being accepted right now.**

**Terms of Use**
- 7(c) and 7(f): no bots or data extraction tools against GGG's website (scraping pathofexile.com, including the trade site, without the API).
- 7(g): no meta tags or hidden text using GGG's name or trademarks.
- 6: the licence is personal and non-commercial.
- 22: GGG's official APIs are the sanctioned way to get game data from them, under the API policies above.
- 24: links to GGG's site must not use GGG logos without approval.

## Where Whetstone stands

| Rule | Status |
|---|---|
| Non-affiliation line, exact wording | Done. Footer in `api/static/index.html` now uses GGG's sentence word for word. |
| Not presented as official | OK. Own name (Whetstone), no GGG or PoE logos. Keep it that way, including the favicon and any social preview image. |
| No commercial use of GGG IP | OK while the app is free with no ads. **Adding ads, a paid tier or donations-for-features later needs a fresh look**, because the app's output is built on GGG game data. |
| No scraping of GGG sites | OK. The app never calls pathofexile.com. Game data comes from Path of Building's bundled data; prices come from poe.ninja (`engine/tools/fetch_prices.py`). Don't add trade-site scraping. |
| Meta tags (7(g)) | OK. The `<title>` says "PoE 2" and the description says "Path of Building", both visible text describing what the site is for. Don't stuff GGG names into keywords or hidden text. |
| API rules (User-Agent, rate limits) | Not used yet. Only matters if we later call GGG's API. |
| Character import via OAuth | Not possible for now: GGG isn't accepting new OAuth apps. Players paste a PoB code instead, which needs no GGG access at all. |
| Item and gem icons | Shown on the site (gear plates, skills, supports). Loaded straight from GGG's image server (`web.poecdn.com`), never copied: the links come from poe.ninja (`engine/tools/fetch_icons.py`), the same links poe.ninja itself shows. GGG publishes no asset policy; this matches what major fan sites do. Keep the app free and the non-affiliation line, and don't use GGG art as the site's own branding (the logo and mark are original). Passive-tree icons aren't shown: no source gives ready links for them. |

## Other sources we depend on
- **Path of Building Community (PoE 2):** MIT licence. Credited and linked in the footer. Keep the licence file in the Docker image (it comes with the cloned repo in `engine/vendor`).
- **poe.ninja:** no published API terms; `robots.txt` only blocks `/dev/`. We fetch 6 category pages once per run with a pause between requests and an identifying User-Agent, and cache the result in `engine/data/unique_prices.json`. Run it at most daily. Crediting poe.ninja in the footer as the price source would be polite (added).
