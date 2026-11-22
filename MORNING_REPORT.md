# Morning report, Sunday 2026-11-22

## Overnight
- **No new nightly sweep.** It skipped again because the Breaker queue was busy. That is the 4th night in a row
  (19th to 22nd). The latest sweep results are still the ones from 11-19.
- **Running now:** the full blind re-run (our picks compared with the ladder's top builds). It started at 06:53
  server time and takes about 12 hours, so expect results around 19:00 Berlin (about 11:00 your time).
- **No messages were held back** during quiet hours.
- I couldn't `git pull` this morning because the command needed an approval nobody was there to give. This report
  is based on the server's local copy.

## Finished by the server session (all on 11-22)
- Trigger scan: nothing strong enough to be a lead. The only fast trigger it found is the Mjölner build
  everyone already knows about.
- The new "full build" test is now the bar a lead has to pass. Leopold's and Maligaro's pairs both failed it.
- Combo leads checked as full builds: Bonestorm fed by Coiling Bolts held up (+11%). Armour Piercing Rounds
  breaking armour itself (+1%) and Dark Effigy with poison (+1%) didn't.
- Patch-notes practice: the tool read the 0.5.1 and 0.5.2 changes correctly without seeing the answers.
- Fixed a bug that made combo builds look about twice as weak as they are.
- Skill leads, first 3: Bonestorm still beats Comet by about 2x on Lich. Rain of Arrows and Wind Serpent's Fury
  lost to the popular skills.
- Started a check on how often the tool's top skill pick turns out to be the wrong one in a full build.

## Last sweep we have (11-19, 23 builds)
- **0 builds passed every check.** Every build that finished was flagged "slow" (35 to 43 minutes each).
- **4 builds hung** and were cut off at 45 minutes: Smith of Kitava, Stormweaver, Spirit Walker and Ritualist.
  Their results weren't saved because of a file permission bug. That bug has been fixed since, so the next sweep
  should record hung builds.
- 1 build was short on strength: Witchhunter, crossbow at Mid Endgame.
- These numbers come from before several fixes (Ember Fusillade, Oil Barrage, attributes), so they're out of date.

## Leads and possible bugs
- Bonestorm on Lich is still the strongest skill lead.
- The nightly sweep keeps losing its slot to the queue, so we have no fresh health check of the main app since
  11-19.

## 3 most useful next steps
1. When the blind re-run lands tonight, write it up and run the remaining skill leads through the full-build test.
2. Give the nightly sweep a real slot (for example, right after the queue finishes) so we get a fresh check on
   today's engine and see whether the 4 hung builds still hang.
3. Build speed: every build still takes about 40 minutes. Cutting that would help the sweep, the queue and the
   live site.

## Waiting for you
- Cloudflare Pages: switch the production branch to `main`.
- Lodestone page: OK to make two small text fixes?
- Lodestone page: make it public or keep it unlisted?
