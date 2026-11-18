# Moving Whetstone to the Contabo server (started 2026-11-17)

Kyle is ordering a Contabo Cloud VPS 8 (8 cores, 24 GB RAM, NVMe, Ubuntu 24.04, monthly term). It replaces the PC as
the always-on home of the engine, and replaces the laptop kit plan. The website stays on Cloudflare Pages; code stays
on GitHub (this branch).

## What goes where
| Thing | Where it lives after the move |
|---|---|
| Code | GitHub, cloned on the server at `/opt/phaph` |
| Website | Cloudflare Pages (push to deploy), unchanged |
| Engine + PoB + build database (`jobs.sqlite3`) | Docker on the server, volume `phaph_jobs` |
| Tunnel (api.phaphofbuilding.com) | `phaph-tunnel-1` on the server, same token, so the PC's tunnel must be stopped |
| `.env` (API key, tunnel token) | the server only, never GitHub |
| Claude sessions | on the server over SSH (laptop: Claude desktop app, SSH session; phone: Remote Control or claude.ai/code) |

## The private transfer folder (`C:\AI\Phaph-transfer`, NOT in git)
`.env`, `jobs.sqlite3` (export of 2026-11-17, 102 jobs), `prompt_log.jsonl`, `memory/` (Claude's notes), and
`ssh/whetstone_vps` + `.pub`: the key Claude uses to log in. Kyle copies the folder to a USB stick or private cloud
drive for the laptop. Refresh `jobs.sqlite3` right before the PC goes off if builds were made after the export.

## Steps
1. Kyle: order the server (root password in his password manager, never in chat). Send Claude the IP.
2. Kyle runs once, in a terminal (types the root password into the prompt itself):
   `type $env:USERPROFILE\.ssh\whetstone_vps.pub | ssh root@<IP> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"`
   On the laptop, use the key from the transfer folder (`ssh -i <folder>\ssh\whetstone_vps root@<IP>`).
3. Claude: secure the server (updates, a non-root user with the key, password login off, firewall: SSH only;
   the tunnel needs no open ports), install Docker, clone the repo, copy `.env` and the database into place,
   `docker compose up -d --build`. Set `GENERATE_WORKERS`/`JOB_WORKERS`/`APP_CPUS` for 8 cores.
4. Switch over: stop the PC's tunnel and app, start the server's, check `https://api.phaphofbuilding.com/health`
   and make a build on the live site.
5. Install Claude Code on the server, put `memory/` in its project memory folder, and work from there.

## Open work when the move happens (also in PC_TODO.md)
- Culling fix: the mapping score counts Culling Strike at the normal-monster threshold (35%), so Deathblow reads
  as +54% mapping damage. Count it at the rare threshold (10%). Not started.
- Mageblood: judged with hand-picked Legacy rolls (about 1 in 1,600). Judge it by an average random roll; show the
  legacies to hunt for. Not started.
- A-to-Z sweep: stopped on 2026-11-17 after 4 of ~32 builds. Build #5 ("Deadeye build") hung: two PoB processes
  spun for 7.5 hours of CPU with no result. Find the loop and add a time limit per build, then re-run the sweep
  on the server (`SWEEP=1 python tools/az_test.py run`).
- Then: why Hexblast (32% of open searches) and Blood Mage (24%) win so often (`/learn/winners`).
