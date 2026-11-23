import re
from pathlib import Path

from backend import i18n
from backend.llm.client import LLMError
from backend.main import app, get_analyzer
from backend.services.analyzer import Analyzer
from backend.llm.fake import FakeLLM
from backend.tests.conftest import parse_sse

EN = {"X-Lang": "en"}
IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}
ARABIC = re.compile(r'"([^"\n]*[؀-ۿ][^"\n]*)"')


def user_messages() -> set[str]:
    """Arabic strings passed to HTTPException/LLMError/sse errors in the backend code."""
    found = set()
    root = Path(__file__).resolve().parents[1]
    for path in [root / "main.py", root / "auth.py", *(root / "llm").glob("*.py")]:
        if path.name == "fake.py":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "JSON" in line and "المخطط" in line:  # prompt text, not a message
                continue
            found.update(m for m in ARABIC.findall(line) if m != "Mustashar — مستشار")
    return found


def test_every_server_message_has_english():
    missing = user_messages() - i18n.EN.keys()
    assert not missing, f"add English for: {missing}"


def test_tr():
    assert i18n.tr("التقرير غير موجود.", "en") == "Report not found."
    assert i18n.tr("التقرير غير موجود.", "ar") == "التقرير غير موجود."
    assert i18n.tr("رسالة غير معروفة", "en") == "رسالة غير معروفة"


def test_404_in_english_and_arabic(client):
    assert client.get("/api/reports/999", headers=EN).json()["detail"] == "Report not found."
    assert client.get("/api/reports/999").json()["detail"] == "التقرير غير موجود."


def failing_llm(message: str) -> FakeLLM:
    llm = FakeLLM()

    async def boom(*_a, **_k):
        raise LLMError("boom", message)
    llm.complete_json = boom
    return llm


def test_llm_error_translated(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(failing_llm("تعذر الاتصال بخدمة الذكاء الاصطناعي."))
    r = client.post("/api/clarify", json=IDEA, headers=EN)
    assert r.status_code == 502
    assert r.json()["detail"] == "Could not connect to the AI service."


def test_stream_error_translated(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(failing_llm("تم تجاوز حد الطلبات. يرجى المحاولة بعد قليل."))
    with client.stream("POST", "/api/analyze", json=IDEA, headers=EN) as r:
        events = parse_sse(r.read().decode("utf-8"))
    assert events[-1] == ("error", {"message": "The AI service's request limit was reached. Please try again shortly."})


def test_rate_limit_in_english(client, monkeypatch):
    from backend import ratelimit as main
    settings = main.get_settings().model_copy(update={"rate_limit": "1/minute"})
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    client.post("/api/clarify", json=IDEA, headers=EN)
    r = client.post("/api/clarify", json=IDEA, headers=EN)
    assert r.status_code == 429
    assert r.json()["detail"].startswith("Too many requests")
