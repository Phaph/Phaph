"""Web API for the build optimizer.

Endpoints:
  GET  /health
  GET  /catalog              classes, ascendancies, skills, weapon types, budgets, stages
  POST /guides               build guide for one spec -> job
  POST /compare              compare 1-3 specs at a budget -> job
  GET  /jobs/{job_id}        job status and result

Jobs run in the background (each one starts its own PoB processes). Results are cached in
SQLite by request + PoB version, so a repeated request returns instantly.

Run:  .venv/bin/uvicorn api.app:app --port 8000
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from gear import BUDGET_ORDER, BUDGETS, STAGE_DEFS  # noqa: E402
from pob import PoB  # noqa: E402

from .jobs import JobStore  # noqa: E402

Budget = Literal["free", "budget", "medium", "high", "unlimited"]
StageKey = Literal["leveling", "early", "mid", "end"]
MAX_ACTIVE_JOBS_PER_CLIENT = int(os.environ.get("MAX_ACTIVE_JOBS_PER_CLIENT", "2"))


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

    model_config = {"populate_by_name": True}

    def as_engine_spec(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        return d


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
        bases = pob.send("bases")["bases"]
        version = pob.version
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
    for t in filter(None, [spec.weapon_type, spec.offhand_type]):
        if t not in catalog["weapon_types"]:
            raise HTTPException(400, f"Unknown weapon type '{t}'")


def run_guide(req: dict) -> dict:
    from guide import build_guide

    spec = {**req["spec"], "budget": req["budget"]}
    guides = build_guide(spec, req["stages"], log=lambda *a: None)
    return {"spec": spec, "stages": [asdict(g) for g in guides]}


def run_compare(req: dict) -> dict:
    from compare import compare

    reports = compare(req["builds"], budget=req["budget"], stage=req["stage"])
    return {"budget": req["budget"], "stage": req["stage"], "builds": [asdict(r) for r in reports]}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.catalog = load_catalog()
    app.state.jobs = JobStore(
        db_path=os.environ.get("JOBS_DB", str(ROOT / "jobs.sqlite3")),
        workers=int(os.environ.get("JOB_WORKERS", "1")),
        version=app.state.catalog["pob_version"],
        runners={"guide": run_guide, "compare": run_compare},
    )
    yield
    app.state.jobs.shutdown()


app = FastAPI(title="PoE 2 Build Optimizer", lifespan=lifespan)


def _client(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0]


def _submit(request: Request, kind: str, payload: dict) -> dict:
    jobs: JobStore = request.app.state.jobs
    client = _client(request)
    cached = jobs.cached(kind, payload)
    if cached:
        return cached
    if jobs.active_for(client) >= MAX_ACTIVE_JOBS_PER_CLIENT:
        raise HTTPException(429, "Too many builds running for you at once. Wait for one to finish.")
    return jobs.submit(kind, payload, client)


@app.get("/health")
def health(request: Request):
    return {"ok": True, "pob_version": request.app.state.catalog["pob_version"]}


@app.get("/catalog")
def catalog(request: Request):
    return request.app.state.catalog


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
def get_job(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "No such job")
    return job
