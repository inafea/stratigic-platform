from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend import db
from backend.llm.fake import FakeLLM
from backend.main import app, get_analyzer, tier_settings
from backend.services.analyzer import Analyzer
from backend.tests.conftest import TEST_USER, give_plan, parse_sse

IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}


def analyze(c, **extra):
    with c.stream("POST", "/api/analyze", json={**IDEA, **extra}) as r:
        if r.status_code != 200:
            r.read()
            return r
        return parse_sse(r.read().decode("utf-8"))


def buy_pack(engine, key="pack_1", credits=1):
    with Session(engine) as s:
        user = s.exec(select(db.User).where(db.User.email == TEST_USER["email"])).one()
        s.add(db.CreditPack(user_id=user.id, pack_key=key, credits_total=credits, credits_left=credits,
                            expires_at=datetime.now(UTC) + timedelta(days=365)))
        s.commit()


# ---- monthly report quota ------------------------------------------------------------------

def test_free_user_gets_two_reports_then_402(client, fake_llm, memory_db):
    assert analyze(client)[-1][0] == "done"
    assert analyze(client)[-1][0] == "done"
    calls = len(fake_llm.calls)
    r = analyze(client)
    assert r.status_code == 402
    body = r.json()
    assert body["reason"] == "reports" and body["upgrade"] is True and "الترقية" in body["detail"]
    assert len(fake_llm.calls) == calls  # no AI call
    with Session(memory_db) as s:
        assert len(s.exec(select(db.Report)).all()) == 2  # nothing saved


def test_clarify_refused_when_quota_gone(client):
    analyze(client)
    analyze(client)
    r = client.post("/api/clarify", json=IDEA, headers={"X-Lang": "en"})
    assert r.status_code == 402 and r.json()["detail"].startswith("You've used all")


def test_plan_endpoint_tracks_usage(client):
    assert client.get("/api/me/plan").json()["reports_left"] == 2
    analyze(client)
    plan = client.get("/api/me/plan").json()
    assert (plan["plan"], plan["reports_used"], plan["reports_left"]) == ("free", 1, 1)


def test_plan_endpoint_needs_login(anon_client):
    assert anon_client.get("/api/me/plan").status_code == 401


def test_paid_plan_has_bigger_quota(pro_client):
    for _ in range(3):
        assert analyze(pro_client)[-1][0] == "done"
    assert pro_client.get("/api/me/plan").json()["reports_left"] == 37


def test_pack_used_after_quota(client, memory_db):
    analyze(client)
    analyze(client)
    buy_pack(memory_db)
    events = analyze(client)
    assert events[-1][0] == "done"
    with Session(memory_db) as s:
        report = s.get(db.Report, events[0][1]["id"])
        assert report.plan_key == "pack_1"
        assert s.exec(select(db.CreditPack)).one().credits_left == 0
    assert analyze(client).status_code == 402


# ---- refunds -------------------------------------------------------------------------------

def test_failed_report_with_no_sections_is_refunded(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(FakeLLM(fail_on="MarketAnalysis"))
    events = analyze(client)
    assert events[-1][0] == "error"
    assert client.get("/api/me/plan").json()["reports_left"] == 2


def test_partly_generated_report_is_charged(client):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(FakeLLM(fail_on="Risks"))
    analyze(client)
    assert client.get("/api/me/plan").json()["reports_left"] == 1


# ---- chat, regenerate, templates ------------------------------------------------------------------

def test_free_chat_limit_per_report(client, memory_db):
    rid = analyze(client)[0][1]["id"]
    for i in range(5):
        assert client.post(f"/api/reports/{rid}/chat", json={"message": f"سؤال {i}"}).status_code == 200
    r = client.post(f"/api/reports/{rid}/chat", json={"message": "سؤال إضافي"})
    assert r.status_code == 402 and r.json()["reason"] == "chat"
    with Session(memory_db) as s:
        assert len(s.exec(select(db.Message).where(db.Message.role == "user")).all()) == 5  # not saved


def test_chat_unlimited_after_upgrade(client, memory_db):
    rid = analyze(client)[0][1]["id"]
    for i in range(5):
        client.post(f"/api/reports/{rid}/chat", json={"message": f"سؤال {i}"})
    give_plan(memory_db, TEST_USER["email"], "pro")
    assert client.post(f"/api/reports/{rid}/chat", json={"message": "واحد آخر"}).status_code == 200


def test_free_cannot_regenerate(client, fake_llm):
    rid = analyze(client)[0][1]["id"]
    calls = len(fake_llm.calls)
    r = client.post(f"/api/reports/{rid}/sections/swot/regenerate", json={})
    assert r.status_code == 402 and r.json()["reason"] == "regenerate"
    assert len(fake_llm.calls) == calls


def test_regenerate_on_paid_plan_is_recorded(pro_client, memory_db):
    rid = analyze(pro_client)[0][1]["id"]
    assert pro_client.post(f"/api/reports/{rid}/sections/swot/regenerate", json={}).status_code == 200
    with Session(memory_db) as s:
        assert s.exec(select(db.UsageEvent).where(db.UsageEvent.kind == "regenerate")).one().report_id == rid


@pytest.mark.parametrize("path", ["/api/clarify", "/api/analyze"])
def test_free_cannot_use_templates(client, path):
    r = client.post(path, json={**IDEA, "industry": "saas"})
    assert r.status_code == 402 and r.json()["reason"] == "templates"


def test_free_auto_template_is_fine(client):
    assert client.post("/api/clarify", json={**IDEA, "industry": "auto", "strategy": "auto"}).status_code == 200


def test_pack_unlocks_templates_for_its_report(client, memory_db):
    analyze(client)
    analyze(client)
    buy_pack(memory_db)
    assert analyze(client, industry="saas", strategy="funding")[-1][0] == "done"


# ---- model per plan ----------------------------------------------------------------------------

class TierRecorder:
    """Analyzer whose for_tier() records the tier it was asked for."""

    def __init__(self):
        self.tiers = []
        self.llm = FakeLLM()

    def factory(self, tier):
        self.tiers.append(tier)
        return Analyzer(self.llm)


@pytest.fixture
def tiers():
    rec = TierRecorder()
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(rec.llm, tier_factory=rec.factory)
    return rec


def test_free_report_uses_lite(client, tiers):
    analyze(client)
    assert tiers.tiers == ["lite"]


def test_pro_uses_premium_everywhere(pro_client, tiers):
    pro_client.post("/api/clarify", json=IDEA)
    rid = analyze(pro_client)[0][1]["id"]
    pro_client.post(f"/api/reports/{rid}/chat", json={"message": "سؤال"})
    pro_client.post(f"/api/reports/{rid}/sections/swot/regenerate", json={})
    assert tiers.tiers == ["premium"] * 4


def test_pack_report_uses_premium(client, memory_db, tiers):
    analyze(client)
    analyze(client)
    buy_pack(memory_db)
    analyze(client)
    assert tiers.tiers == ["lite", "lite", "premium"]


def test_tier_settings_picks_model():
    from backend.config import Settings
    base = Settings(_env_file=None, llm_model="base-model", llm_model_premium="big-model")
    assert tier_settings(base, "premium").llm_model == "big-model"
    assert tier_settings(base, "lite").llm_model == "base-model"  # not set: falls back


def test_real_factory_builds_tier_models(monkeypatch):
    from backend import main
    from backend.config import Settings
    s = Settings(_env_file=None, llm_provider="github", llm_api_key="k", llm_model="m-base",
                 llm_model_lite="m-lite", llm_model_premium="m-premium")
    monkeypatch.setattr(main, "get_settings", lambda: s)
    analyzer = main.get_analyzer()
    assert analyzer.llm.settings.llm_model == "m-base"
    assert analyzer.for_tier("lite").llm.settings.llm_model == "m-lite"
    assert analyzer.for_tier("premium").llm.settings.llm_model == "m-premium"
    assert analyzer.for_tier("standard").llm.settings.llm_model == "m-base"


# ---- what a report tells the UI (P10) -------------------------------------------------------------

def test_free_report_terms(client):
    rid = analyze(client)[0][1]["id"]
    client.post(f"/api/reports/{rid}/chat", json={"message": "سؤال"})
    r = client.get(f"/api/reports/{rid}").json()
    assert r["plan_key"] == "free"
    assert r["features"]["watermark"] is True and r["features"]["regenerate"] is False
    assert r["chat"] == {"used": 1, "limit": 5}


def test_pro_report_terms(pro_client):
    rid = analyze(pro_client)[0][1]["id"]
    r = pro_client.get(f"/api/reports/{rid}").json()
    assert r["plan_key"] == "pro"
    assert r["features"]["watermark"] is False and r["features"]["regenerate"] is True
    assert r["chat"]["limit"] is None


def test_upgrade_removes_watermark_from_old_reports(client, memory_db):
    rid = analyze(client)[0][1]["id"]
    give_plan(memory_db, TEST_USER["email"], "entrepreneur")
    r = client.get(f"/api/reports/{rid}").json()
    assert r["features"]["watermark"] is False and r["chat"]["limit"] == 30


def test_plan_tells_ui_about_next_report(client, memory_db):
    plan = client.get("/api/me/plan").json()
    assert plan["next_report_features"]["templates"] is False
    analyze(client)
    analyze(client)
    buy_pack(memory_db)
    plan = client.get("/api/me/plan").json()
    assert plan["reports_left"] == 0 and plan["pack_credits"] == 1 and plan["can_start_report"] is True
    assert plan["next_report_features"]["templates"] is True  # the pack unlocks them
