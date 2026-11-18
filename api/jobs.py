"""Background jobs with a SQLite-backed cache.

A job's cache key is a hash of (kind, request, PoB version), so the same request returns the
stored result instantly, and a PoB update automatically invalidates old results.

Every job is labelled with the game patch, PoB version and engine version it ran on. A new patch never deletes
anything: old results stay (share links keep working, with an "older patch" note) and the learning in
api/learn.py reads only the current patch's builds.

Runners that take a `progress` argument can report steps while they work. Steps live in memory
only (they matter while someone is watching) and come back from get(job_id, since=n).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    cache_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    client TEXT,
    status TEXT NOT NULL,          -- queued | running | done | failed
    request TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created REAL NOT NULL,
    started REAL,
    finished REAL,
    game_patch TEXT,
    pob_version TEXT,
    engine_version TEXT
);
CREATE INDEX IF NOT EXISTS jobs_cache ON jobs (cache_key, status);
CREATE INDEX IF NOT EXISTS jobs_client ON jobs (client, status);
"""
LABELS = ("game_patch", "pob_version", "engine_version")


class JobStore:
    def __init__(self, db_path: str, workers: int, version: str, runners: dict[str, Callable[[dict], dict]],
                 labels: dict | None = None):
        self.db_path = db_path
        self.version = version
        self.labels = {k: (labels or {}).get(k) for k in LABELS}
        self.runners = runners
        self.lock = threading.Lock()
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        have = {r[1] for r in self.db.execute("PRAGMA table_info(jobs)")}
        for col in LABELS:
            if col not in have:   # databases made before labels existed
                self.db.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
                if col == "game_patch" and self.labels["game_patch"]:
                    # Builds made before labels were all made on the patch PoB has now (labels came in 2026-11).
                    self.db.execute("UPDATE jobs SET game_patch=?", (self.labels["game_patch"],))
        self.db.execute("CREATE INDEX IF NOT EXISTS jobs_patch ON jobs (game_patch, kind, status)")
        # Jobs that were running when the server stopped will never finish.
        self.db.execute("UPDATE jobs SET status='failed', error='server restarted' WHERE status IN ('queued','running')")
        self.db.commit()
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.progress: dict[str, list[dict]] = {}

    MAX_EVENTS = 6000   # live tree steps are ~130 per stage

    def _reporter(self, job_id: str, t0: float):
        def report(event: dict) -> None:
            with self.lock:
                events = self.progress.setdefault(job_id, [])
                if len(events) < self.MAX_EVENTS:
                    events.append({**event, "t": round(time.time() - t0, 1)})
        return report

    def key(self, kind: str, request: dict) -> str:
        blob = json.dumps({"kind": kind, "request": request, "version": self.version}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _row(self, row: sqlite3.Row | None) -> dict | None:
        if not row:
            return None
        out = {k: row[k] for k in ("id", "kind", "status", "error", "created", "started", "finished", *LABELS)}
        out["result"] = json.loads(row["result"]) if row["result"] else None
        if row["status"] in ("queued", "running"):
            out["position"] = self._position(row["id"]) if row["status"] == "queued" else 0
        return out

    def _position(self, job_id: str) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='queued' AND created <= (SELECT created FROM jobs WHERE id=?)",
            (job_id,)).fetchone()
        return row[0]

    def cached(self, kind: str, request: dict) -> dict | None:
        """A finished result, or a job already queued/running for the same request."""
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM jobs WHERE cache_key=? AND status IN ('done','running','queued') "
                "ORDER BY created DESC LIMIT 1", (self.key(kind, request),)).fetchone()
            res = self._row(row)
        if res:
            res["cached"] = res["status"] == "done"
        return res

    def active_for(self, client: str) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM jobs WHERE client=? AND status IN ('queued','running')",
                                   (client,)).fetchone()[0]

    def started_since(self, since: float) -> int:
        """Jobs created since a timestamp (for the daily cap). Cached results don't count."""
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM jobs WHERE created >= ?", (since,)).fetchone()[0]

    def submit(self, kind: str, request: dict, client: str) -> dict:
        job_id = uuid.uuid4().hex
        with self.lock:
            self.db.execute(
                "INSERT INTO jobs (id, cache_key, kind, client, status, request, created, game_patch, pob_version, "
                "engine_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (job_id, self.key(kind, request), kind, client, "queued", json.dumps(request), time.time(),
                 *(self.labels[k] for k in LABELS)))
            self.db.commit()
        self.pool.submit(self._run, job_id, kind, request)
        return self.get(job_id)

    def _run(self, job_id: str, kind: str, request: dict) -> None:
        with self.lock:
            self.db.execute("UPDATE jobs SET status='running', started=? WHERE id=?", (time.time(), job_id))
            self.db.commit()
        runner = self.runners[kind]
        try:
            if "progress" in inspect.signature(runner).parameters:
                result = runner(request, progress=self._reporter(job_id, time.time()))
            else:
                result = runner(request)
            status, error, payload = "done", None, json.dumps(result)
        except Exception as e:  # noqa: BLE001 - report any engine failure on the job
            status, error, payload = "failed", f"{type(e).__name__}: {e}", None
            traceback.print_exc()
        with self.lock:
            self.db.execute("UPDATE jobs SET status=?, result=?, error=?, finished=? WHERE id=?",
                            (status, payload, error, time.time(), job_id))
            self.db.commit()
            self.progress.pop(job_id, None)

    def get(self, job_id: str, since: int = 0) -> dict | None:
        """The job. While it runs, `progress` holds the steps after the first `since`, and
        `progress_next` is the `since` to send next time."""
        with self.lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            out = self._row(row)
            if out and out["status"] == "running":
                events = self.progress.get(job_id, [])
                since = max(0, min(since, len(events)))
                out["progress"], out["progress_next"] = events[since:], len(events)
            return out

    def shutdown(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.db.close()
