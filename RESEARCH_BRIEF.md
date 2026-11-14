# Research brief (for a Claude session on the PC, with open internet)

The cloud session can't reach these sites. Save findings to `research/` in this repo as markdown, with source links, then commit.

## 1. Asset rules
- Grinding Gear Games' policy on fan sites and tools using item art, passive tree art and skill gem icons. Is there an official asset or fan-content policy? What do Mobalytics, poe.ninja and poe2db credit or link to?
- Where item and gem icon URLs come from (trade API, poe2db, web.poecdn.com) and whether hotlinking or self-hosting is expected.
- GGG's rules for third-party tools in general (API terms, rate limits, OAuth for character import).

## 2. Competitors (hands-on)
Try each with "lightning minion Monk, 5 divines" or the closest thing it supports. Note what it outputs, whether numbers come from Path of Building, accuracy, speed and price.
- poe2ai.com, poe2builds.ai, poe2skills-ai.com, cboyd421-max.github.io/poe2-forge, the "PoE2 Build Optimizer" MCP server on mcpmarket.com
- poe.ninja builds, Maxroll planner, Mobalytics builds and planner, pobb.in

## 3. Data for the engine
- poe.ninja: API endpoints for builds (skills, ascendancies, PoB codes) and item/currency prices. Rate limits and terms.
- Typical divine prices for common uniques by budget tier, to place uniques in the right stage.

## 4. Design references
- "Crawlers" by Slava Rybin (@rybinfx): find the piece, note the technique (procedural animation? IK? tool used?) and link it.
- 5-10 other interfaces or motion pieces in a similar spirit: procedural, physical, satisfying, not "AI-looking".
