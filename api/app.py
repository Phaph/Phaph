"""Web API for the build optimizer.

Endpoints:
  GET  /health
  GET  /catalog              classes, ascendancies, skills, weapon types, budgets, stages
  GET  /icons                icon links for uniques, item bases and gems
  POST /guides               build guide for one spec -> job
  POST /compare              compare 1-3 specs at a budget -> job
  POST /parse                prompt text -> /generate request (instant, keyword based)
  GET  /jobs/{job_id}        job status and result

Jobs run in the background (each one starts its own PoB processes). Results are cached in
SQLite by request + PoB version, so a repeated request returns instantly.

Run:  .venv/bin/uvicorn api.app:app --port 8000
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from gear import BUDGET_ORDER, BUDGETS, STAGE_DEFS  # noqa: E402
from pob import PoB  # noqa: E402

from . import prompt_ai, writeup  # noqa: E402
from .jobs import JobStore  # noqa: E402

Budget = Literal["free", "budget", "medium", "high", "unlimited"]
StageKey = Literal["leveling", "early", "mid", "end"]
# Bump when the engine's results change shape or quality, so cached builds from before are rebuilt.
ENGINE_VERSION = "2026-11-17.5"
MAX_ACTIVE_JOBS_PER_CLIENT = int(os.environ.get("MAX_ACTIVE_JOBS_PER_CLIENT", "2"))
# PoB processes a search runs side by side (one CPU thread each).
GENERATE_WORKERS = int(os.environ.get("GENERATE_WORKERS", "8"))
# Keeps the bill predictable: new (uncached) builds allowed per rolling 24 hours, 0 = no cap.
DAILY_JOB_LIMIT = int(os.environ.get("DAILY_JOB_LIMIT", "300"))


class BuildSpec(BaseModel):
    name: str | None = Field(None, max_length=80)
    cls: str = Field(..., alias="class")
    ascendancy: str | None = None
    skill: str
    weapon_type: str
    weapon_subtype: str | None = None
    dual_wield: bool = False
    offhand_type: str | None = None
    support_slots: int = Field(5, ge=1, le=5)
    boss_skill: str | None = None          # a second skill for bosses
    boss_weapon_type: str | None = None    # set when the boss skill uses weapon set 2
    boss_weapon_subtype: str | None = None
    clear_skill: str | None = None         # a second skill for clearing packs, same weapon
    totems: dict[str, str] = Field(default_factory=dict, max_length=3)   # skill -> totem gem that places it
    ailment: Literal["bleed", "poison", "ignite"] | None = None   # optimise for this ailment
    goals: list[str] = Field(default_factory=list, max_length=8)  # beyond damage: goals.GOAL_LABELS
    # Skills the player asked for that boost the main skill instead of dealing damage (e.g. Charged Staff).
    with_skills: list[str] = Field(default_factory=list, max_length=3)
    with_types: list[str] = Field(default_factory=list, max_length=3)   # "warcry": the best one is picked
    # What the build is made around (engine/anchors.py), kept at every stage.
    anchor_unique: str | None = Field(None, max_length=80)
    anchor_keystone: str | None = Field(None, max_length=80)
    anchor_support: str | None = Field(None, max_length=80)
    off_meta: bool = False   # popular uniques score lower
    random: bool = False     # a random build: notes say the unique was rolled

    model_config = {"populate_by_name": True}

    def as_engine_spec(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        return d


class GenerateRequest(BaseModel):
    """Build from a theme. Every field is optional; class, ascendancy, skill and weapons lock choices."""
    damage: list[str] = Field(default_factory=list, max_length=5)   # e.g. ["lightning"]
    kinds: list[str] = Field(default_factory=list, max_length=5)    # e.g. ["minion"], ["melee"]
    ailment: Literal["bleed", "poison", "ignite", "shock", "chill", "freeze"] | None = None
    weapons: list[str] = Field(default_factory=list, max_length=5)
    cls: str | None = Field(None, alias="class")
    ascendancy: str | None = None
    skill: str | None = None
    budget: Budget = "high"
    mode: Literal["balanced", "mapping", "bossing"] = "balanced"
    goals: list[str] = Field(default_factory=list, max_length=8)  # beyond damage: goals.GOAL_LABELS
    with_skills: list[str] = Field(default_factory=list, max_length=3)   # kept beside the main skill (Cast on X, buffs)
    with_types: list[str] = Field(default_factory=list, max_length=3)    # "warcry", "curse"...: the best one is picked
    avoid: list[str] = Field(default_factory=list, max_length=5)   # "no minions": kinds or damage types never main
    deep: bool = False   # deep search: wider net, each skill on its own best ascendancies (slower)
    # Build around one thing (engine/anchors.py): a unique, a keystone or a support gem, by name.
    anchor_unique: str | None = Field(None, max_length=80)
    anchor_keystone: str | None = Field(None, max_length=80)
    anchor_support: str | None = Field(None, max_length=80)
    off_meta: bool = False   # skills, ascendancies and uniques many players use score lower (engine/meta.py)
    random: bool = False     # a random build within the filters, not the strongest
    seed: int | None = Field(None, ge=0, le=2**31)   # random builds: a new seed is a new roll (and a new cache key)

    model_config = {"populate_by_name": True}


class ParseRequest(BaseModel):
    text: str = Field(..., max_length=500)
    ai: bool = False   # let Claude read it (api/prompt_ai.py); the word lists answer if it can't


class PlanRequest(BaseModel):
    """The feedback option: lock an ascendancy and/or skill from a finished generate job."""
    ascendancy: str | None = None
    skill: str | None = None


class GuideRequest(BaseModel):
    spec: BuildSpec
    budget: Budget = "high"
    stages: list[StageKey] = Field(default_factory=lambda: list(STAGE_DEFS))


class CompareRequest(BaseModel):
    builds: list[BuildSpec] = Field(..., min_length=1, max_length=3)
    budget: Budget = "high"
    stage: StageKey = "end"


def load_catalog() -> dict:
    with PoB() as pob:
        classes = pob.list_classes()
        skills = sorted(g["name"] for g in pob.list_gems("active"))
        from generate import NOT_MAIN
        # Skills that boost another rather than dealing damage themselves (Cast on X, buffs, auras, heralds).
        helper_skills = sorted({s["name"] for s in pob.send("skill_catalog")["skills"] if set(s["types"]) & NOT_MAIN})
        bases = pob.send("bases")["bases"]
        version = pob.version
        from anchors import unique_slot
        # What a build can be made around: wearable uniques, keystones, support gems.
        uniques = sorted({u["name"].split(",")[0] for u in pob.list_uniques() if unique_slot(u)})
        keystones = sorted(k["name"] for k in pob.list_keystones())
        supports = sorted(g["name"] for g in pob.list_gems("support"))
    weapon_types: dict[str, set] = {}
    for b in bases:
        if b["type"] in {"Amulet", "Belt", "Body Armour", "Boots", "Charm", "Flask", "Gloves", "Helmet", "Jewel",
                         "Ring", "Fishing Rod", "Transcendent Limb", "Quiver"}:
            continue
        weapon_types.setdefault(b["type"], set())
        if b.get("subType"):
            weapon_types[b["type"]].add(b["subType"])
    return {
        "pob_version": version,
        "classes": sorted(classes, key=lambda c: c["name"]),
        "skills": skills,
        "helper_skills": helper_skills,
        "uniques": uniques,
        "keystones": keystones,
        "supports": supports,
        "weapon_types": {k: sorted(v) for k, v in sorted(weapon_types.items())},
        "budgets": [{"key": k, "label": BUDGETS[k].label} for k in BUDGET_ORDER],
        "stages": [{"key": k, "label": v[0], "level": v[1]} for k, v in STAGE_DEFS.items()],
    }


def validate_spec(spec: BuildSpec, catalog: dict) -> None:
    classes = {c["name"].lower(): c for c in catalog["classes"]}
    c = classes.get(spec.cls.lower())
    if not c:
        raise HTTPException(400, f"Unknown class '{spec.cls}'. Options: {', '.join(sorted(classes))}")
    if spec.ascendancy and spec.ascendancy.lower() not in {a.lower() for a in c["ascendancies"]}:
        raise HTTPException(400, f"'{spec.ascendancy}' is not a {c['name']} ascendancy. Options: "
                                 f"{', '.join(c['ascendancies'])}")
    if spec.skill not in catalog["skills"]:
        raise HTTPException(400, f"Unknown skill '{spec.skill}'")
    if spec.boss_skill and spec.boss_skill not in catalog["skills"]:
        raise HTTPException(400, f"Unknown boss skill '{spec.boss_skill}'")
    for s, g in spec.totems.items():
        if s not in catalog["skills"] or g not in ("Spell Totem", "Ancestral Warrior Totem"):
            raise HTTPException(400, f"Unknown totem setup '{g}' for '{s}'")
    _check_anchors(spec, catalog)
    if spec.clear_skill and spec.clear_skill not in catalog["skills"]:
        raise HTTPException(400, f"Unknown clear skill '{spec.clear_skill}'")
    for w in spec.with_skills:
        if w not in catalog["skills"]:
            raise HTTPException(400, f"Unknown skill '{w}'")
    _check_goals(spec.goals, spec.with_types)
    for t in filter(None, [spec.weapon_type, spec.offhand_type, spec.boss_weapon_type]):
        if t not in catalog["weapon_types"]:
            raise HTTPException(400, f"Unknown weapon type '{t}'")


def run_guide(req: dict, progress=None) -> dict:
    from guide import build_guide

    spec = {**req["spec"], "budget": req["budget"]}
    guides = build_guide(spec, req["stages"], log=lambda *a: None, progress=progress)
    out = {"spec": spec, "stages": [asdict(g) for g in guides]}
    if writeup.enabled():
        # Claude's overview of the finished build, written from its real data (api/writeup.py). Stored with the guide.
        if progress:
            progress({"step": "writeup", "label": "Writing the build overview"})
        try:
            out["writeup"] = writeup.write_up(spec, out["stages"])
        except Exception:  # noqa: BLE001 - an overview must never cost the player their build
            out["writeup"] = None
    return out


def run_generate(req: dict, progress=None) -> dict:
    from generate import generate, options, plan_build

    result = generate(req, workers=GENERATE_WORKERS, log=lambda *a: None, progress=progress)
    return {"result": result, "plan": plan_build(result), "options": options(result)}


def _check_goals(goals: list[str], with_types: list[str]) -> None:
    from generate import HELPER_TYPES
    from goals import GOAL_LABELS
    for g in goals:
        if g not in GOAL_LABELS:
            raise HTTPException(400, f"Unknown goal '{g}'. Options: {', '.join(GOAL_LABELS)}")
    for k in with_types:
        if k not in HELPER_TYPES:
            raise HTTPException(400, f"Unknown helper kind '{k}'. Options: {', '.join(HELPER_TYPES)}")


def _check_anchors(req, catalog: dict) -> None:
    for field, key, label in (("anchor_unique", "uniques", "wearable unique"), ("anchor_keystone", "keystones", "keystone"),
                              ("anchor_support", "supports", "support gem")):
        name = getattr(req, field)
        if name and catalog.get(key) and name.split(",")[0].strip().lower() not in {n.lower() for n in catalog[key]}:
            raise HTTPException(400, f"Unknown {label} '{name}'")


def validate_generate(req: GenerateRequest, catalog: dict) -> None:
    classes = {c["name"].lower(): c for c in catalog["classes"]}
    if req.cls and req.cls.lower() not in classes:
        raise HTTPException(400, f"Unknown class '{req.cls}'. Options: {', '.join(sorted(classes))}")
    if req.ascendancy and not any(req.ascendancy in c["ascendancies"] for c in catalog["classes"]):
        raise HTTPException(400, f"Unknown ascendancy '{req.ascendancy}'")
    if req.skill and req.skill not in catalog["skills"]:
        raise HTTPException(400, f"Unknown skill '{req.skill}'")
    for w in req.with_skills:
        if w not in catalog["skills"]:
            raise HTTPException(400, f"Unknown skill '{w}'")
    _check_goals(req.goals, req.with_types)
    _check_anchors(req, catalog)
    for w in req.weapons:
        if w not in catalog["weapon_types"]:
            raise HTTPException(400, f"Unknown weapon type '{w}'")


def run_compare(req: dict, progress=None) -> dict:
    from compare import compare

    reports = compare(req["builds"], budget=req["budget"], stage=req["stage"], progress=progress)
    return {"budget": req["budget"], "stage": req["stage"], "builds": [asdict(r) for r in reports]}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.catalog = load_catalog()
    app.state.gem_tips = load_gem_tooltips()   # ~1 MB, half a second: the page's gem hover cards
    app.state.jobs = JobStore(
        db_path=os.environ.get("JOBS_DB", str(ROOT / "jobs.sqlite3")),
        workers=int(os.environ.get("JOB_WORKERS", "1")),
        # Cached results are reused only for the same PoB and engine version, so engine changes show up at once.
        version=f'{app.state.catalog["pob_version"]}+{ENGINE_VERSION}',
        runners={"guide": run_guide, "compare": run_compare, "generate": run_generate},
    )
    yield
    app.state.jobs.shutdown()


app = FastAPI(title="PoE 2 Build Optimizer", lifespan=lifespan)

# The website is served by Cloudflare Pages (phaphofbuilding.com, or a *.pages.dev preview) and calls this engine at
# api.phaphofbuilding.com, so those origins may read its responses. Local runs serve both from one host.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://phaphofbuilding.com", "https://www.phaphofbuilding.com"],
    allow_origin_regex=r"https://([a-z0-9-]+\.)?whetstone[a-z0-9-]*\.pages\.dev",
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
    max_age=86400,
)


def _client(request: Request) -> str:
    # Behind Cloudflare (tunnel or proxy) CF-Connecting-IP is the visitor's real IP, set by Cloudflare.
    # X-Forwarded-For's first entry is whatever the visitor sent, so it is only a fallback.
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()


def _submit(request: Request, kind: str, payload: dict) -> dict:
    jobs: JobStore = request.app.state.jobs
    client = _client(request)
    cached = jobs.cached(kind, payload)
    if cached:
        return cached
    if jobs.active_for(client) >= MAX_ACTIVE_JOBS_PER_CLIENT:
        raise HTTPException(429, "Too many builds running for you at once. Wait for one to finish.")
    if DAILY_JOB_LIMIT and jobs.started_since(time.time() - 86400) >= DAILY_JOB_LIMIT:
        raise HTTPException(429, "We've hit today's limit for new builds. Builds other people already made still "
                                 "load instantly, so try a common one, or come back tomorrow.")
    return jobs.submit(kind, payload, client)


STATIC = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
def index():
    """The website: one page that talks to this API."""
    return FileResponse(STATIC / "index.html")


@app.get("/how.html")
def how_page():
    return FileResponse(STATIC / "how.html")


@app.get("/lavabug.js")
def lavabug_js():
    return FileResponse(STATIC / "lavabug.js", media_type="text/javascript", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/treeview.js")
def treeview_js():
    return FileResponse(STATIC / "treeview.js", media_type="text/javascript", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/tree.html")
def tree_page():
    return FileResponse(STATIC / "tree.html")


@app.get("/tree/data")
def tree_data(v: str | None = None):
    """The passive tree from PoB's data, compacted for the browser (engine/tree.py)."""
    from fastapi.responses import JSONResponse
    from tree import compact

    return JSONResponse(compact(v), headers={"Cache-Control": "public, max-age=86400"})


@app.get("/icons")
def icons():
    """Icon links for uniques, item bases and gems (GGG's image server). Built by engine/tools/fetch_icons.py."""
    path = ROOT / "engine" / "data" / "icons.json"
    if not path.exists():
        return {"uniques": {}, "bases": {}, "gems": {}}
    return FileResponse(path, media_type="application/json", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/health")
def health(request: Request):
    commit = ROOT / "engine" / "vendor" / "POB_COMMIT"   # written by engine/setup.sh
    return {"ok": True, "pob_version": request.app.state.catalog["pob_version"], "engine": ENGINE_VERSION,
            "pob_commit": commit.read_text().strip() if commit.exists() else None, "notice": site_notice()}


# A notice shown at the top of the site, switched on and off without a redeploy (LAUNCH_1.0.md):
#   docker exec phaph-app-1 sh -c 'echo "Path of Exile 2 1.0 is out..." > /data/notice.txt'
#   docker exec phaph-app-1 sh -c 'rm /data/notice.txt'
NOTICE_FILE = Path(os.environ.get("NOTICE_FILE", "/data/notice.txt"))


def site_notice() -> str | None:
    try:
        text = NOTICE_FILE.read_text(encoding="utf-8").strip()[:400]
    except OSError:
        return None
    return text or None


@app.get("/gems")
def gem_texts(request: Request):
    """What each gem does (PoB's description and tags), short. Fetched once by the page."""
    if not hasattr(request.app.state, "gem_texts"):
        with PoB() as pob:
            request.app.state.gem_texts = pob.send("gem_texts")["gems"]
    return request.app.state.gem_texts


def load_gem_tooltips() -> dict:
    """Every gem's full tooltip, as Path of Building draws it (runner.lua gem_tooltips), at top gem level, quality 0.
    PoB's "(Not supported in PoB yet)" becomes a flag the page shows as a grey line; supports lose "Cast Time"."""
    with PoB() as pob:
        pob.new()
        tips = pob.send("gem_tooltips")["gems"]
    for lines in tips.values():
        support = len(lines) > 1 and lines[1].get("t") == "Support"
        keep = []
        for ln in lines:
            t = ln.get("t", "")
            if ln.get("k") == "unsupported":
                ln["t"] = t.replace("(Not supported in PoB yet)", "").strip()
            if support and t.startswith("Cast Time"):
                continue
            keep.append(ln)
        lines[:] = keep
    return tips


@app.get("/gems/{name}")
def gem_tooltip(name: str, request: Request):
    """One gem's full tooltip lines for the page's hover card: [{"t": text, "k": kind}, ...]."""
    tips = getattr(request.app.state, "gem_tips", None)
    if tips is None:
        tips = request.app.state.gem_tips = load_gem_tooltips()
    if name not in tips:
        raise HTTPException(404, "No such gem")
    return {"name": name, "lines": tips[name]}


@app.get("/catalog")
def catalog(request: Request):
    return {**request.app.state.catalog, "ai_reader": prompt_ai.available()}


@app.post("/guides")
def create_guide(req: GuideRequest, request: Request):
    validate_spec(req.spec, request.app.state.catalog)
    payload = {"spec": req.spec.as_engine_spec(), "budget": req.budget, "stages": req.stages}
    return _submit(request, "guide", payload)


@app.post("/compare")
def create_compare(req: CompareRequest, request: Request):
    for b in req.builds:
        validate_spec(b, request.app.state.catalog)
    payload = {"builds": [b.as_engine_spec() for b in req.builds], "budget": req.budget, "stage": req.stage}
    return _submit(request, "compare", payload)


@app.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request, since: int = 0):
    """Job status and result. While running, `progress` lists the steps after `since`."""
    job = request.app.state.jobs.get(job_id, since=since)
    if not job:
        raise HTTPException(404, "No such job")
    return job


@app.post("/parse")
def parse(req: ParseRequest, request: Request):
    """Prompt mode: "lightning minion build for a monk, 5 div" -> the fields for POST /generate, plus what each
    recognised phrase was read as. No job and no PoB work, so the website can call it as the player types."""
    from prompt import parse_prompt

    if req.ai and prompt_ai.available() and _ai_allowed(_client(request)):
        read = prompt_ai.read_prompt(req.text, request.app.state.catalog)
        if read:
            return _amount_budget(read, req.text, request.app.state.catalog)
    return parse_prompt(req.text, request.app.state.catalog)


def _amount_budget(read: dict, text: str, catalog: dict) -> dict:
    """An amount the player typed ("900 div", "300 ex") sets the budget by the site's own bands, not by Claude's
    reading of it (Claude once read 900 divines as "high" when it is above 100, so "no limit")."""
    from prompt import CURRENCY, _norm, parse_prompt
    import re
    if not re.search(CURRENCY, _norm(text)):
        return read
    budget = parse_prompt(text, catalog)["request"].get("budget")
    if not budget or read["request"].get("budget") == budget:
        return read
    req = {**read["request"], "budget": budget}
    found = [f for f in read.get("found", []) if "budget" not in f.get("means", "").lower()]
    m = re.search(CURRENCY, _norm(text))
    return {**read, "request": req, "budget_set": True, "found": [*found, {"text": m.group(0).strip(), "means": f"Budget: {budget}"}]}


# Claude readings cost about a cent each: a cap per player per hour and for the whole site per day keeps the bill
# small. Over a cap, the word lists read the prompt instead (the player still gets a build).
AI_PER_CLIENT_HOUR = int(os.environ.get("AI_PER_CLIENT_HOUR", "30"))
AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "1000"))
_ai_calls: dict[str, list[float]] = {}
_ai_day: list[float] = []


def _ai_allowed(client: str) -> bool:
    now = time.time()
    mine = [t for t in _ai_calls.get(client, []) if now - t < 3600]
    _ai_day[:] = [t for t in _ai_day if now - t < 86400]
    if len(mine) >= AI_PER_CLIENT_HOUR or (AI_DAILY_LIMIT and len(_ai_day) >= AI_DAILY_LIMIT):
        _ai_calls[client] = mine
        return False
    _ai_calls[client] = [*mine, now]
    _ai_day.append(now)
    return True


@app.post("/generate")
def create_generate(req: GenerateRequest, request: Request):
    """Find the strongest skill, weapon and ascendancy for a theme. The result holds a ready
    guide spec (plan.spec, post it to /guides) and the alternatives for the feedback option."""
    validate_generate(req, request.app.state.catalog)
    payload = req.model_dump(by_alias=True, exclude_none=True)
    return _submit(request, "generate", payload)


@app.post("/generate/{job_id}/plan")
def replan(job_id: str, req: PlanRequest, request: Request):
    """Feedback: "I love this build, but I want the other ascendancy". Returns the best build
    with that choice locked and how much damage it gives up. Instant: it reuses the search."""
    from generate import plan_build

    job = request.app.state.jobs.get(job_id)
    if not job or job["kind"] != "generate":
        raise HTTPException(404, "No such generate job")
    if job["status"] != "done":
        raise HTTPException(409, "That build is still being generated")
    try:
        return plan_build(job["result"]["result"], ascendancy=req.ascendancy, skill=req.skill)
    except ValueError as e:
        raise HTTPException(400, str(e))
