"""API checks with fake job runners, so they run in seconds."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

SPEC = {"class": "Monk", "ascendancy": "Invoker", "skill": "Tempest Flurry", "weapon_type": "Staff",
        "weapon_subtype": "Warstaff"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_DB", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("MAX_ACTIVE_JOBS_PER_CLIENT", "2")
    import api.app as app_module

    release = threading.Event()
    calls = []

    def fake_guide(req):
        calls.append(req)
        release.wait(5)
        return {"spec": req["spec"], "stages": []}

    def fake_compare(req):
        return {"builds": [{"name": b["skill"]} for b in req["builds"]]}

    monkeypatch.setattr(app_module, "run_guide", fake_guide)
    monkeypatch.setattr(app_module, "run_compare", fake_compare)
    monkeypatch.setattr(app_module, "MAX_ACTIVE_JOBS_PER_CLIENT", 2)
    with TestClient(app_module.app) as c:
        c.release, c.calls = release, calls
        yield c
        release.set()


def wait(c, job_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"/jobs/{job_id}").json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_health_and_catalog(client):
    assert client.get("/health").json()["ok"]
    cat = client.get("/catalog").json()
    assert "Tempest Flurry" in cat["skills"]
    assert "Staff" in cat["weapon_types"]
    assert [b["key"] for b in cat["budgets"]] == ["free", "budget", "medium", "high", "unlimited"]


@pytest.mark.parametrize("change,msg", [
    ({"class": "Wizard"}, "Unknown class"),
    ({"ascendancy": "Lich"}, "not a Monk ascendancy"),
    ({"skill": "Fireballz"}, "Unknown skill"),
    ({"weapon_type": "Banana"}, "Unknown weapon type"),
])
def test_validation(client, change, msg):
    r = client.post("/guides", json={"spec": {**SPEC, **change}})
    assert r.status_code == 400 and msg in r.json()["detail"]


def test_bad_budget_and_too_many_builds(client):
    assert client.post("/guides", json={"spec": SPEC, "budget": "mirror"}).status_code == 422
    assert client.post("/compare", json={"builds": [SPEC] * 4}).status_code == 422


def test_job_lifecycle_and_cache(client):
    client.release.set()
    j = client.post("/guides", json={"spec": SPEC, "budget": "budget"}).json()
    done = wait(client, j["id"])
    assert done["status"] == "done" and done["result"]["spec"]["skill"] == "Tempest Flurry"
    again = client.post("/guides", json={"spec": SPEC, "budget": "budget"}).json()
    assert again["cached"] is True and again["id"] == j["id"]
    assert len(client.calls) == 1, "cached request should not run the engine again"


def test_same_request_while_running_joins_the_job(client):
    a = client.post("/guides", json={"spec": SPEC, "budget": "free"}).json()
    b = client.post("/guides", json={"spec": SPEC, "budget": "free"}).json()
    assert a["id"] == b["id"]
    client.release.set()
    wait(client, a["id"])


def test_rate_limit_per_client(client):
    ids = [client.post("/guides", json={"spec": SPEC, "budget": b}).json()["id"] for b in ("free", "budget")]
    r = client.post("/guides", json={"spec": SPEC, "budget": "medium"})
    assert r.status_code == 429
    client.release.set()
    for i in ids:
        wait(client, i)


def test_compare(client):
    j = client.post("/compare", json={"builds": [SPEC, {**SPEC, "skill": "Falling Thunder"}], "budget": "budget"}).json()
    done = wait(client, j["id"])
    assert [b["name"] for b in done["result"]["builds"]] == ["Tempest Flurry", "Falling Thunder"]


def test_unknown_job(client):
    assert client.get("/jobs/nope").status_code == 404


def test_generate_and_feedback_plan(client, monkeypatch):
    import api.app as app_module

    result = {"request": {"budget": "budget"}, "ranked": [
        {"skill": "Snap", "ascendancy": "Invoker", "cls": "Monk", "weapon_type": "Staff", "weapon_subtype": None,
         "offhand_type": None, "score": 100, "dps": 100},
        {"skill": "Snap", "ascendancy": "Martial Artist", "cls": "Monk", "weapon_type": "Staff",
         "weapon_subtype": None, "offhand_type": None, "score": 80, "dps": 80}]}
    monkeypatch.setitem(app_module.app.state.jobs.runners, "generate",
                        lambda req: {"result": result, "plan": {}, "options": {}})
    assert client.post("/generate", json={"class": "Wizard"}).status_code == 400
    j = client.post("/generate", json={"damage": ["lightning"], "class": "Monk", "budget": "budget"}).json()
    early = client.post(f"/generate/{j['id']}/plan", json={"ascendancy": "Martial Artist"})
    assert early.status_code in (200, 409)
    wait(client, j["id"])
    plan = client.post(f"/generate/{j['id']}/plan", json={"ascendancy": "Martial Artist"}).json()
    assert plan["spec"]["ascendancy"] == "Martial Artist" and plan["vs_recommended"] == pytest.approx(0.2)
    assert client.post(f"/generate/{j['id']}/plan", json={"ascendancy": "Lich"}).status_code == 400
    assert client.post("/generate/nope/plan", json={}).status_code == 404


def test_boss_skill_spec_is_validated(client):
    r = client.post("/guides", json={"spec": {**SPEC, "boss_skill": "Not A Skill"}})
    assert r.status_code == 400 and "boss skill" in r.json()["detail"]


def test_website_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Forge my build" in r.text and "Not affiliated with" in r.text


def test_client_id_prefers_cloudflare_header():
    """Behind the Cloudflare Tunnel a faked X-Forwarded-For must not dodge the per-client limit."""
    from starlette.requests import Request
    from api.app import _client

    def req(headers):
        return Request({"type": "http", "client": ("172.18.0.3", 5000),
                        "headers": [(k.encode(), v.encode()) for k, v in headers.items()]})

    assert _client(req({"cf-connecting-ip": "203.0.113.7", "x-forwarded-for": "1.2.3.4, 203.0.113.7"})) == "203.0.113.7"
    assert _client(req({"x-forwarded-for": "198.51.100.2, 10.0.0.1"})) == "198.51.100.2"
    assert _client(req({})) == "172.18.0.3"


def test_parse_prompt(client):
    out = client.post("/parse", json={"text": "lightning minion build for a monk, 5 div"}).json()
    assert out["request"]["class"] == "Monk"
    assert out["request"]["damage"] == ["lightning"] and out["request"]["kinds"] == ["minion"]
    assert out["request"]["budget"] == "budget"
    # The parsed request fits /generate's schema as is.
    from api.app import GenerateRequest
    GenerateRequest.model_validate(out["request"])
