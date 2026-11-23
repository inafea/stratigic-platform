from sqlmodel import create_engine

from backend import db
from backend.main import app, get_analyzer
from backend.schemas import SECTIONS
from backend.services.analyzer import Analyzer
from backend.tests.conftest import parse_sse
from backend.tests.fakes import FakeLLM

IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة",
        "answers": [{"question": "أين؟", "answer": "الرياض"}]}


def run_analysis(client) -> int:
    with client.stream("POST", "/api/analyze", json=IDEA) as r:
        events = parse_sse(r.read().decode("utf-8"))
    assert events[0][0] == "report"
    return events[0][1]["id"]


def test_report_saved_and_listed(client):
    rid = run_analysis(client)
    listing = client.get("/api/reports").json()
    assert listing[0]["id"] == rid
    assert listing[0]["status"] == "done"
    assert listing[0]["score"] == 72

    full = client.get(f"/api/reports/{rid}").json()
    assert [s["key"] for s in full["sections"]] == list(SECTIONS)
    assert full["answers"][0]["answer"] == "الرياض"
    assert full["messages"] == []


def test_partial_report_kept_on_error(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(FakeLLM(fail_on="Risks"))
    rid = run_analysis(client)
    full = client.get(f"/api/reports/{rid}").json()
    assert full["status"] == "error"
    assert [s["key"] for s in full["sections"]] == ["market", "swot", "competition"]


def test_get_missing_report_404(client):
    assert client.get("/api/reports/999").status_code == 404


def test_delete_report(client):
    rid = run_analysis(client)
    assert client.delete(f"/api/reports/{rid}").status_code == 204
    assert client.get(f"/api/reports/{rid}").status_code == 404


def test_reports_survive_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    db.set_engine(create_engine(url))
    db.init_db()
    from sqlmodel import Session
    with Session(db.get_engine()) as s:
        s.add(db.Report(idea="فكرة", goals="هدف", sections={"swot": {"strengths": ["x"]}}))
        s.commit()
    db.get_engine().dispose()

    db.set_engine(create_engine(url))  # "restart"
    with Session(db.get_engine()) as s:
        r = s.get(db.Report, 1)
        assert r.sections["swot"]["strengths"] == ["x"]
    db.get_engine().dispose()
