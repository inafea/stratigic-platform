from backend.main import app, get_analyzer
from backend.schemas import SECTIONS
from backend.services.analyzer import Analyzer
from backend.tests.conftest import parse_sse
from backend.llm.fake import FakeLLM

IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_clarify(client):
    r = client.post("/api/clarify", json=IDEA)
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 3


def test_clarify_validation(client):
    r = client.post("/api/clarify", json={"idea": "x", "goals": ""})
    assert r.status_code == 422


def test_clarify_llm_error_returns_arabic_502(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(FakeLLM(fail_on="ClarifyingQuestions"))
    r = client.post("/api/clarify", json=IDEA)
    assert r.status_code == 502
    assert r.json()["detail"] == "خطأ تجريبي"


def test_analyze_streams_sections(client):
    payload = {**IDEA, "answers": [{"question": "أين؟", "answer": "الرياض"}]}
    with client.stream("POST", "/api/analyze", json=payload) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(r.read().decode("utf-8"))
    sections = [d["key"] for e, d in events if e == "section"]
    assert sections == list(SECTIONS)
    assert events[-1][0] == "done"


def test_analyze_error_event(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(FakeLLM(fail_on="Risks"))
    with client.stream("POST", "/api/analyze", json=IDEA) as r:
        events = parse_sse(r.read().decode("utf-8"))
    assert [e for e, _ in events] == ["report", "section", "section", "section", "error"]
    assert events[-1][1]["message"] == "خطأ تجريبي"


def test_missing_api_key_returns_503(monkeypatch):
    from fastapi.testclient import TestClient

    from backend import main
    monkeypatch.setattr(main, "get_settings", lambda: type("S", (), {"llm_api_key": "", "llm_provider": "github"})())
    app.dependency_overrides.clear()
    from backend.tests.conftest import login_new_user, with_csrf
    r = login_new_user(with_csrf(TestClient(app))).post("/api/clarify", json=IDEA)
    assert r.status_code == 503


def test_frontend_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'dir="rtl"' in r.text
    assert client.get("/app.js").status_code == 200
