from backend.main import app, get_analyzer
from backend.services.analyzer import Analyzer
from backend.tests.conftest import parse_sse
from backend.llm.fake import FakeLLM
from backend.tests.test_reports import run_analysis


def test_chat_streams_and_saves(client, fake_llm):
    rid = run_analysis(client)
    with client.stream("POST", f"/api/reports/{rid}/chat", json={"message": "ماذا لو خفضت السعر؟"}) as r:
        events = parse_sse(r.read().decode("utf-8"))
    assert [d["text"] for e, d in events if e == "delta"] == ["إجابة ", "تجريبية"]
    assert events[-1][0] == "done"

    system, user = fake_llm.calls[-1][1], fake_llm.calls[-1][2]
    assert "viability_score" in system          # report is in the context
    assert "ماذا لو خفضت السعر؟" in user

    msgs = client.get(f"/api/reports/{rid}").json()["messages"]
    assert msgs == [{"role": "user", "content": "ماذا لو خفضت السعر؟"},
                    {"role": "assistant", "content": "إجابة تجريبية"}]


def test_chat_includes_history(client, fake_llm):
    rid = run_analysis(client)
    for q in ["سؤال أول", "سؤال ثان"]:
        with client.stream("POST", f"/api/reports/{rid}/chat", json={"message": q}) as r:
            r.read()
    assert "سؤال أول" in fake_llm.calls[-1][2]
    assert "المحادثة السابقة" in fake_llm.calls[-1][2]


def test_chat_missing_report(client):
    assert client.post("/api/reports/999/chat", json={"message": "x"}).status_code == 404


def test_regenerate_section(pro_client, fake_llm):
    rid = run_analysis(pro_client)
    r = pro_client.post(f"/api/reports/{rid}/sections/swot/regenerate", json={"instructions": "ركز على التهديدات"})
    assert r.status_code == 200
    assert r.json()["key"] == "swot"
    user = fake_llm.calls[-1][2]
    assert "ركز على التهديدات" in user
    assert '"swot"' not in user.split("الأقسام التي تم إعدادها سابقاً")[1]  # own section excluded from context


def test_regenerate_saves(pro_client):
    rid = run_analysis(pro_client)
    other = {"strengths": ["جديد"], "weaknesses": [], "opportunities": [], "threats": []}

    class SwotLLM(FakeLLM):
        async def complete_json(self, system, user, schema):
            return schema.model_validate(other)

    app.dependency_overrides[get_analyzer] = lambda: Analyzer(SwotLLM())
    pro_client.post(f"/api/reports/{rid}/sections/swot/regenerate", json={})
    sections = {s["key"]: s["data"] for s in pro_client.get(f"/api/reports/{rid}").json()["sections"]}
    assert sections["swot"]["strengths"] == ["جديد"]


def test_regenerate_unknown_section(client):
    rid = run_analysis(client)
    assert client.post(f"/api/reports/{rid}/sections/nope/regenerate", json={}).status_code == 404
