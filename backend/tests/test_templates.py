import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel import create_engine

from backend import db, prompts
from backend.schemas import INDUSTRIES, STRATEGIES, AnalysisRequest, IdeaInput
from backend.services.analyzer import Analyzer
from backend.llm.fake import FakeLLM
from backend.tests.conftest import parse_sse

BASE = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}


@pytest.mark.parametrize("key", list(INDUSTRIES))
def test_every_industry_template_exists(key):
    assert prompts.load(f"industries/{key}")


@pytest.mark.parametrize("key", list(STRATEGIES))
def test_every_strategy_template_exists(key):
    assert prompts.load(f"strategies/{key}")


def test_auto_adds_nothing():
    assert prompts.strategy_system(IdeaInput(**BASE)) == prompts.strategy_system()


def test_templates_added_to_system_prompts():
    data = IdeaInput(**BASE, industry="restaurant", strategy="expansion")
    for system in (prompts.strategy_system(data), prompts.clarify_system(data), prompts.chat_system({}, data)):
        assert "Food Cost" in system
        assert "فرنشايز" in system


def test_unknown_template_rejected():
    with pytest.raises(ValidationError):
        IdeaInput(**BASE, industry="mining")


async def test_analyzer_uses_templates():
    llm = FakeLLM()
    req = AnalysisRequest(**BASE, industry="saas", strategy="funding")
    await Analyzer(llm).clarify(req)
    _ = [x async for x in Analyzer(llm).analyze(req)]
    assert all("MRR" in system and "المستثمر" in system for _name, system, _user in llm.calls)


def test_templates_endpoint(client):
    body = client.get("/api/templates").json()
    assert {i["key"] for i in body["industries"]} == set(INDUSTRIES)
    assert {s["key"] for s in body["strategies"]} == set(STRATEGIES)


def test_report_keeps_template_choice(client):
    with client.stream("POST", "/api/analyze", json={**BASE, "industry": "retail", "strategy": "turnaround"}) as r:
        rid = parse_sse(r.read().decode("utf-8"))[0][1]["id"]
    full = client.get(f"/api/reports/{rid}").json()
    assert (full["industry"], full["strategy"]) == ("retail", "turnaround")


def test_old_database_gets_new_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE report (id INTEGER PRIMARY KEY, created_at DATETIME, idea VARCHAR, "
                          "goals VARCHAR, answers JSON, sections JSON, status VARCHAR)"))
        conn.execute(text("INSERT INTO report (idea, goals, answers, sections, status) "
                          "VALUES ('x', 'y', '[]', '{}', 'done')"))
    db._add_missing_columns(engine)
    with engine.begin() as conn:
        row = conn.execute(text("SELECT industry, strategy FROM report")).one()
    assert tuple(row) == ("auto", "auto")
