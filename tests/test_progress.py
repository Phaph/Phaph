"""Job progress events and the damage mix. No PoB needed."""
import threading
import time

from api.jobs import JobStore
from guide import damage_split


def _wait(store, job_id, status, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        job = store.get(job_id)
        if job["status"] == status:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job never reached {status}")


def test_progress_is_reported_while_running(tmp_path):
    gate = threading.Event()

    def runner(req, progress):
        progress({"step": "gear", "dps": 100})
        progress({"step": "passive", "label": "Heavy Blade"})
        gate.wait(5)
        return {"ok": True}

    def plain(req):          # runners without a progress argument still work
        return {"plain": True}

    store = JobStore(str(tmp_path / "j.sqlite3"), workers=2, version="t", runners={"g": runner, "p": plain})
    job = store.submit("g", {"a": 1}, "c")
    end = time.time() + 5
    while time.time() < end and len(store.get(job["id"]).get("progress") or []) < 2:
        time.sleep(0.02)
    running = store.get(job["id"])
    assert [e["step"] for e in running["progress"]] == ["gear", "passive"]
    assert running["progress_next"] == 2
    assert store.get(job["id"], since=2)["progress"] == []
    assert store.get(job["id"], since=1)["progress"][0]["label"] == "Heavy Blade"
    gate.set()
    done = _wait(store, job["id"], "done")
    assert "progress" not in done and done["result"] == {"ok": True}

    assert _wait(store, store.submit("p", {}, "c")["id"], "done")["result"] == {"plain": True}
    store.shutdown()


def test_damage_split():
    stats = {"TotalDPS": 1000, "PhysicalHitAverage": 30, "LightningHitAverage": 70,
             "BleedDPS": 200, "FireDot": 50, "MinionDPS": 0}
    split = damage_split(stats)
    assert split == {"physical": 500.0, "lightning": 700.0, "fire": 50.0}


def test_damage_split_minions_and_empty():
    assert damage_split({"MinionDPS": 5000, "MinionDotDPS": 100}) == {"minion": 5100}
    assert damage_split({}) == {}
