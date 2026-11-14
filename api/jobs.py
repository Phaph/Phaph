"""Background jobs with a SQLite-backed cache.

A job's cache key is a hash of (kind, request, PoB version), so the same request returns the
stored result instantly, and a PoB update automatically invalidates old results.
"""
from __future__ import annotations

import hashlib
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
    finished REAL
);
CREATE INDEX IF NOT EXISTS jobs_cache ON jobs (cache_key, status);
CREATE INDEX IF NOT EXISTS jobs_client ON jobs (client, status);
"""


class JobStore:
    def __init__(self, db_path: str, workers: int, version: str, runners: dict[str, Callable[[dict], dict]]):
        self.db_path = db_path
        self.version = version
        self.runners = runners
        self.lock = threading.Lock()
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        # Jobs that were running when the server stopped will never finish.
        self.db.execute("UPDATE jobs SET status='failed', error='server restarted' WHERE status IN ('queued','running')")
        self.db.commit()
        self.pool = ThreadPoolExecutor(max_workers=workers)

    def key(self, kind: str, request: dict) -> str:
        blob = json.dumps({"kind": kind, "request": request, "version": self.version}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _row(self, row: sqlite3.Row | None) -> dict | None:
        if not row:
            return None
        out = {k: row[k] for k in ("id", "kind", "status", "error", "created", "started", "finished")}
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

    def submit(self, kind: str, request: dict, client: str) -> dict:
        job_id = uuid.uuid4().hex
        with self.lock:
            self.db.execute(
                "INSERT INTO jobs (id, cache_key, kind, client, status, request, created) VALUES (?,?,?,?,?,?,?)",
                (job_id, self.key(kind, request), kind, client, "queued", json.dumps(request), time.time()))
            self.db.commit()
        self.pool.submit(self._run, job_id, kind, request)
        return self.get(job_id)

    def _run(self, job_id: str, kind: str, request: dict) -> None:
        with self.lock:
            self.db.execute("UPDATE jobs SET status='running', started=? WHERE id=?", (time.time(), job_id))
            self.db.commit()
        try:
            result = self.runners[kind](request)
            status, error, payload = "done", None, json.dumps(result)
        except Exception as e:  # noqa: BLE001 - report any engine failure on the job
            status, error, payload = "failed", f"{type(e).__name__}: {e}", None
            traceback.print_exc()
        with self.lock:
            self.db.execute("UPDATE jobs SET status=?, result=?, error=?, finished=? WHERE id=?",
                            (status, payload, error, time.time(), job_id))
            self.db.commit()

    def get(self, job_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return self._row(row)

    def shutdown(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.db.close()
