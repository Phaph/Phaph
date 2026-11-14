# API

FastAPI service around the engine. Jobs run in the background; results are cached in SQLite by request + PoB version.

| Method | Path | What |
|---|---|---|
| GET | `/health` | Up check and PoB version |
| GET | `/catalog` | Classes, ascendancies, skills, weapon types, budgets, stages (for dropdowns and the prompt layer) |
| POST | `/guides` | `{"spec": {...}, "budget": "budget", "stages": ["early","end"]}` -> job |
| POST | `/compare` | `{"builds": [spec, spec], "budget": "medium", "stage": "end"}` -> job |
| POST | `/generate` | `{"damage": ["lightning"], "kinds": ["minion"], "class": "Monk", "budget": "medium", "mode": "balanced"}` -> job; result has `plan.spec` (post to `/guides`) and `options` |
| POST | `/generate/{id}/plan` | Feedback: `{"ascendancy": "Martial Artist"}` -> best build with that locked, plus how much damage it gives up. Instant |
| GET | `/jobs/{id}` | Status (`queued`/`running`/`done`/`failed`), queue position, result |

A spec: `{"class": "Monk", "ascendancy": "Invoker", "skill": "Tempest Flurry", "weapon_type": "Staff", "weapon_subtype": "Warstaff"}`.

## Run locally
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
engine/setup.sh
.venv/bin/uvicorn api.app:app --port 8000
```

## Run with Docker
```
docker build -t poe2-optimizer .
docker run -p 8000:8000 -v poe2data:/data poe2-optimizer
```

## Settings (environment variables)
- `JOB_WORKERS` (default 1): jobs at once. Each guide job starts one PoB process per stage, so keep this at about CPU cores / 4.
- `MAX_ACTIVE_JOBS_PER_CLIENT` (default 2): per-IP limit.
- `JOBS_DB`: SQLite file for jobs and cache.

## Tests
```
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests     # about 70 seconds
```
They also run on GitHub Actions on every push (`.github/workflows/test.yml`).
