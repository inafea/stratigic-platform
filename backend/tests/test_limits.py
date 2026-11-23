import logging

from backend import ratelimit as main  # the limiter reads its settings there

IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}


def test_rate_limit_returns_429(client, monkeypatch):
    real = main.get_settings()
    monkeypatch.setattr(main, "get_settings", lambda: real.model_copy(update={"rate_limit": "2/minute"}))
    codes = [client.post("/api/clarify", json=IDEA).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert "الطلبات" in client.post("/api/clarify", json=IDEA).json()["detail"]


def test_non_llm_routes_not_limited(client, monkeypatch):
    real = main.get_settings()
    monkeypatch.setattr(main, "get_settings", lambda: real.model_copy(update={"rate_limit": "1/minute"}))
    assert all(client.get("/api/reports").status_code == 200 for _ in range(5))


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="mustashar"):
        client.get("/api/health")
    assert any("GET /api/health -> 200" in r.getMessage() for r in caplog.records)
