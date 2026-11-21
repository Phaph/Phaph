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
    assert "budgets" not in cat
    assert [s["key"] for s in cat["stages"]] == ["act1", "act2", "act34", "interludes", "early", "mid", "end"]
    assert [s["sockets"] for s in cat["stages"]] == [2, 3, 3, 3, 4, 5, 5]


@pytest.mark.parametrize("change,msg", [
    ({"class": "Wizard"}, "Unknown class"),
    ({"ascendancy": "Lich"}, "not a Monk ascendancy"),
    ({"skill": "Fireballz"}, "Unknown skill"),
    ({"weapon_type": "Banana"}, "Unknown weapon type"),
])
def test_validation(client, change, msg):
    r = client.post("/guides", json={"spec": {**SPEC, **change}})
    assert r.status_code == 400 and msg in r.json()["detail"]


def test_bad_stage_and_too_many_builds(client):
    assert client.post("/guides", json={"spec": SPEC, "stages": ["leveling"]}).status_code == 422
    assert client.post("/compare", json={"builds": [SPEC] * 4}).status_code == 422


def test_job_lifecycle_and_cache(client):
    client.release.set()
    j = client.post("/guides", json={"spec": SPEC}).json()
    done = wait(client, j["id"])
    assert done["status"] == "done" and done["result"]["spec"]["skill"] == "Tempest Flurry"
    # An old page still sending a budget gets the same build: the field is ignored.
    again = client.post("/guides", json={"spec": SPEC, "budget": "budget"}).json()
    assert again["cached"] is True and again["id"] == j["id"]
    assert len(client.calls) == 1, "cached request should not run the engine again"


def test_same_request_while_running_joins_the_job(client):
    a = client.post("/guides", json={"spec": SPEC}).json()
    b = client.post("/guides", json={"spec": SPEC}).json()
    assert a["id"] == b["id"]
    client.release.set()
    wait(client, a["id"])


def test_rate_limit_per_client(client):
    ids = [client.post("/guides", json={"spec": SPEC, "stages": st}).json()["id"] for st in (["act1"], ["end"])]
    r = client.post("/guides", json={"spec": SPEC, "stages": ["mid"]})
    assert r.status_code == 429
    client.release.set()
    for i in ids:
        wait(client, i)


def test_compare(client):
    j = client.post("/compare", json={"builds": [SPEC, {**SPEC, "skill": "Falling Thunder"}]}).json()
    done = wait(client, j["id"])
    assert [b["name"] for b in done["result"]["builds"]] == ["Tempest Flurry", "Falling Thunder"]


def test_unknown_job(client):
    assert client.get("/jobs/nope").status_code == 404


def test_generate_and_feedback_plan(client, monkeypatch):
    import api.app as app_module

    result = {"request": {}, "ranked": [
        {"skill": "Snap", "ascendancy": "Invoker", "cls": "Monk", "weapon_type": "Staff", "weapon_subtype": None,
         "offhand_type": None, "score": 100, "dps": 100},
        {"skill": "Snap", "ascendancy": "Martial Artist", "cls": "Monk", "weapon_type": "Staff",
         "weapon_subtype": None, "offhand_type": None, "score": 80, "dps": 80}]}
    monkeypatch.setitem(app_module.app.state.jobs.runners, "generate",
                        lambda req: {"result": result, "plan": {}, "options": {}})
    assert client.post("/generate", json={"class": "Wizard"}).status_code == 400
    j = client.post("/generate", json={"damage": ["lightning"], "class": "Monk"}).json()
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
    assert "Forge it" in r.text and "isn't affiliated with or endorsed by Grinding Gear Games" in r.text


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
    assert "budget" not in out["request"] and "budget_set" not in out
    # The parsed request fits /generate's schema as is.
    from api.app import GenerateRequest
    GenerateRequest.model_validate(out["request"])


def test_icons(client):
    r = client.get("/icons")
    assert r.status_code == 200
    assert set(r.json()) >= {"uniques", "bases", "gems"}


def test_cors_allows_the_website_only(client):
    ok = client.get("/health", headers={"Origin": "https://phaphofbuilding.com"})
    assert ok.headers.get("access-control-allow-origin") == "https://phaphofbuilding.com"
    preview = client.get("/health", headers={"Origin": "https://abc123.whetstone.pages.dev"})
    assert preview.headers.get("access-control-allow-origin") == "https://abc123.whetstone.pages.dev"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_helper_skills_reach_the_guide(client):
    """A buff kept beside the main skill (e.g. Charged Staff) must survive the API's spec schema."""
    client.release.set()
    j = client.post("/guides", json={"spec": {**SPEC, "with_skills": ["Tempest Flurry"]}}).json()
    done = wait(client, j["id"])
    assert done["result"]["spec"]["with_skills"] == ["Tempest Flurry"]
    assert client.post("/guides", json={"spec": {**SPEC, "with_skills": ["Not A Skill"]}}).status_code == 400


def test_site_notice(client, tmp_path, monkeypatch):
    import api.app as app_module
    notice = tmp_path / "notice.txt"
    monkeypatch.setattr(app_module, "NOTICE_FILE", notice)
    assert client.get("/health").json()["notice"] is None
    notice.write_text("Path of Exile 2 1.0 is out. Builds are being updated.\n", encoding="utf-8")
    assert client.get("/health").json()["notice"] == "Path of Exile 2 1.0 is out. Builds are being updated."


def test_parse_with_ai_falls_back_without_a_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/parse", json={"text": "lightning minion build for a monk", "ai": True})
    assert r.status_code == 200 and r.json()["request"]["damage"] == ["lightning"] and "reader" not in r.json()
    assert client.get("/catalog").json()["ai_reader"] is False


def test_gem_texts_for_hover_cards(client):
    gems = client.get("/gems").json()
    assert "Arc" in gems["Arc"]["desc"] or "Lightning" in gems["Arc"]["desc"]
    assert any(g["support"] for g in gems.values()) and len(gems) > 300


def test_full_gem_tooltip(client):
    lines = client.get("/gems/Arc").json()["lines"]
    text = [l.get("t", "") for l in lines]
    assert text[0] == "Arc" and text[1] == "Spell"
    assert any(t.startswith("Cost:") for t in text) and any("Chains" in t for t in text)
    assert not any("Not supported in PoB" in t for t in text)
    assert client.get("/gems/No Such Gem").status_code == 404


def test_lodestone_page_and_data(client):
    page = client.get("/lodestone.html")
    assert page.status_code == 200 and "noindex" in page.text and "noindex" in page.headers.get("x-robots-tag", "")
    d = client.get("/lodestone/data").json()
    assert set(d) >= {"leads", "payoffs", "combos", "pairs", "interactions", "queue"}
    assert d["leads"] and all(l["status"] in {"unconfirmed", "to_test", "confirmed", "known", "dead", "fixed"} for l in d["leads"])
    assert d["combos"] and all(c["edge"] > 0 for c in d["combos"])
