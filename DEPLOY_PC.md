# Running Whetstone on the PC

Docker runs the site; a Cloudflare Tunnel puts it online without opening router ports. Steps marked **Kyle** need your accounts, admin rights or a purchase.

## 1. Install Docker Desktop (Kyle, once)
This PC has virtualization on in the BIOS but no WSL or Docker yet.
1. Open PowerShell **as administrator** and run `wsl --install`, then restart the PC.
2. Install Docker Desktop for Windows from docker.com (WSL 2 backend, the default). Start it once and accept its terms.
3. In Docker Desktop > Settings > General, tick "Start Docker Desktop when you sign in" so the site comes back after a reboot.

## 2. Build and try it locally
From `C:\AI\Phaph`:
```
docker build -t poe2-optimizer .
docker run --rm -p 127.0.0.1:8000:8000 poe2-optimizer
```
Open http://127.0.0.1:8000. The first build takes several minutes (it compiles LuaJIT and clones PoB).

Run the full test suite inside the image (the engine tests can't run on bare Windows):
```
docker run --rm -v "${PWD}/tests:/app/tests" poe2-optimizer sh -c "pip install -q pytest==8.3.4 && python -m pytest -q tests"
```
(PowerShell syntax. GitHub Actions also runs the suite on every push.)

## 3. Accuracy check (go-public step 4)
1. In the PoB app, open one of your builds and export it (Import/Export Build > Generate). Save the code into `my_build.txt` in this folder.
2. Run:
   ```
   docker run --rm -i poe2-optimizer python engine/tools/accuracy_check.py < my_build.txt
   ```
3. Compare each line with PoB's sidebar, with the same main skill selected. The first line shows the engine's PoB version; if it differs from the app's, update one so they match before reading anything into gaps.
4. Paste the output (not the code, if you'd rather keep the build private) back to Claude to chase any gap.

## 4. Domain and tunnel (Kyle)
1. Make a free Cloudflare account. Buy a domain through Cloudflare Registrar (Domain Registration > Register), about $10/yr for a `.com`. Buying it there puts it on Cloudflare DNS straight away.
2. Zero Trust > Networks > Tunnels > Create a tunnel > Cloudflared. Name it `whetstone`.
3. On the install screen pick Docker and copy the token (the long string after `--token`). Don't paste it in chat.
4. Copy `.env.example` to `.env` and put the token after `TUNNEL_TOKEN=`.
5. Add a public hostname: your domain (or `www`), Service type `HTTP`, URL `app:8000`.

## 5. Start it
```
docker compose up -d --build
docker compose logs -f tunnel
```
The tunnel log should say "Registered tunnel connection". Then open your domain.

Stop with `docker compose down`. Build jobs and the result cache live in the `jobs` volume and survive restarts and rebuilds.

## Limits (in `.env`)
| Setting | Default | What it does |
|---|---|---|
| `DAILY_JOB_LIMIT` | 100 | Most build jobs the site starts per 24 h. Cached results don't count. Raise it after the friends beta. |
| `MAX_ACTIVE_JOBS_PER_CLIENT` | 2 | Running jobs per visitor (by `CF-Connecting-IP`, which Cloudflare sets). |
| `JOB_WORKERS` | 2 | Jobs at once. Each guide uses up to 4 cores. |
| `APP_CPUS` | 8 | Cores the container may use, out of this PC's 20. |

After changing `.env`, run `docker compose up -d` again.

## Refreshing unique prices
```
python engine/tools/fetch_prices.py
docker compose up -d --build
```
Picks the newest softcore trade league on poe.ninja. Run it after a new league's economy settles (a few days in), not more than daily.

## Refreshing icons
```
python engine/tools/fetch_icons.py
docker compose up -d --build
```
Collects links to item, unique and gem art on GGG's image server (from poe.ninja's price lists and 10 public characters from each ascendancy, spaced out; poe.ninja only lists level 80+ characters, so campaign bases fall back to a silhouette). Only links are stored, in `engine/data/icons.json`; the site loads the images from GGG's server. Existing entries are kept, so run it once per league or patch to add new items and gems.
