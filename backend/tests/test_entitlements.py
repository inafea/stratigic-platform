from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend import db
from backend.billing import entitlements as E

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def dt(*a):
    return datetime(*a, tzinfo=UTC)


@pytest.fixture
def s(memory_db):
    with Session(memory_db) as session:
        yield session


@pytest.fixture
def user(s):
    u = db.User(email="u@example.com")
    s.add(u)
    s.commit()
    s.refresh(u)
    return u


def subscribe(s, user, plan="pro", start=dt(2026, 11, 10), months=1, status="active"):
    sub = db.Subscription(user_id=user.id, plan_key=plan, status=status, current_period_start=start,
                          current_period_end=E.add_months(start, months), period="yearly" if months == 12 else "monthly")
    s.add(sub)
    s.commit()
    return sub


def use_reports(s, user, n, at=NOW, source="plan", pack_id=None):
    for _ in range(n):
        s.add(db.UsageEvent(user_id=user.id, kind="report", source=source, pack_id=pack_id, at=at))
    s.commit()


def buy_pack(s, user, key="pack_5", credits=5, expires=NOW + timedelta(days=300)):
    p = db.CreditPack(user_id=user.id, pack_key=key, credits_total=credits, credits_left=credits, expires_at=expires)
    s.add(p)
    s.commit()
    return p


def new_report(s, user):
    r = db.Report(idea="i", goals="g", user_id=user.id)
    s.add(r)
    s.commit()
    s.refresh(r)
    return r


# ---- month arithmetic ---------------------------------------------------------------------

@pytest.mark.parametrize("start,months,expected", [
    (dt(2026, 1, 31), 1, dt(2026, 2, 28)),
    (dt(2028, 1, 31), 1, dt(2028, 2, 29)),   # leap year
    (dt(2026, 12, 15), 1, dt(2027, 1, 15)),
    (dt(2026, 3, 31), 12, dt(2027, 3, 31)),
])
def test_add_months(start, months, expected):
    assert E.add_months(start, months) == expected


def test_monthly_window_from_anchor():
    assert E.monthly_window(dt(2026, 11, 10), NOW) == (dt(2026, 11, 10), dt(2026, 12, 10))
    assert E.monthly_window(dt(2026, 10, 25), NOW) == (dt(2026, 10, 25), dt(2026, 11, 25))  # before day 25
    assert E.monthly_window(dt(2026, 1, 31), dt(2026, 3, 1)) == (dt(2026, 2, 28), dt(2026, 3, 31))


def test_window_boundaries_are_start_inclusive():
    start, end = E.monthly_window(dt(2026, 11, 10), dt(2026, 12, 10))
    assert start == dt(2026, 12, 10)


def test_calendar_month():
    assert E.calendar_month(NOW) == (dt(2026, 11, 1), dt(2026, 12, 1))


# ---- free plan ----------------------------------------------------------------------------

def test_new_user_is_on_free(s, user):
    ent = E.get_entitlements(s, user, NOW)
    assert ent.plan.key == "free" and ent.subscription is None
    assert (ent.reports_used, ent.reports_limit, ent.reports_left) == (0, 2, 2)
    assert ent.next_report_source == "plan"


def test_free_quota_used_up(s, user):
    use_reports(s, user, 2)
    ent = E.get_entitlements(s, user, NOW)
    assert ent.reports_left == 0 and ent.next_report_source is None
    with pytest.raises(E.QuotaError) as e:
        E.consume_report(s, user, new_report(s, user), ent)
    assert e.value.reason == "reports"


def test_free_quota_resets_next_month(s, user):
    use_reports(s, user, 2, at=dt(2026, 10, 30))
    assert E.get_entitlements(s, user, NOW).reports_left == 2


def test_other_users_usage_not_counted(s, user):
    other = db.User(email="o@example.com")
    s.add(other)
    s.commit()
    use_reports(s, other, 2)
    assert E.get_entitlements(s, user, NOW).reports_left == 2


# ---- subscriptions ---------------------------------------------------------------------------

def test_active_subscription_gives_plan(s, user):
    subscribe(s, user, "pro")
    ent = E.get_entitlements(s, user, NOW)
    assert ent.plan.key == "pro" and ent.reports_limit == 40 and ent.plan.model_tier == "premium"
    assert (ent.window_start, ent.window_end) == (dt(2026, 11, 10), dt(2026, 12, 10))


def test_usage_before_subscription_window_not_counted(s, user):
    use_reports(s, user, 2, at=dt(2026, 11, 5))  # free reports earlier this month
    subscribe(s, user, "entrepreneur", start=dt(2026, 11, 10))
    assert E.get_entitlements(s, user, NOW).reports_left == 10


def test_expired_subscription_falls_back_to_free(s, user):
    subscribe(s, user, "pro", start=dt(2026, 9, 1))  # ended Oct 1
    assert E.get_entitlements(s, user, NOW).plan.key == "free"


@pytest.mark.parametrize("status,plan", [("canceled", "free"), ("past_due", "pro")])
def test_subscription_status(s, user, status, plan):
    subscribe(s, user, "pro", status=status)
    assert E.get_entitlements(s, user, NOW).plan.key == plan


def test_yearly_plan_quota_is_monthly(s, user):
    subscribe(s, user, "entrepreneur", start=dt(2026, 3, 5), months=12)
    use_reports(s, user, 10, at=dt(2026, 10, 20))  # previous monthly window (Oct 5 - Nov 5)
    use_reports(s, user, 3, at=dt(2026, 11, 20))
    ent = E.get_entitlements(s, user, NOW)
    assert (ent.window_start, ent.window_end) == (dt(2026, 11, 5), dt(2026, 12, 5))
    assert ent.reports_left == 7


def test_unknown_plan_key_ignored(s, user):
    subscribe(s, user, "platinum")
    assert E.get_entitlements(s, user, NOW).plan.key == "free"


# ---- packs -----------------------------------------------------------------------------------

def test_pack_used_after_quota(s, user):
    use_reports(s, user, 2)
    pack = buy_pack(s, user)
    ent = E.get_entitlements(s, user, NOW)
    assert ent.pack_credits == 5 and ent.next_report_source == "pack"
    assert ent.next_report_terms.key == "pack_5" and ent.next_report_terms.model_tier == "premium"
    report = new_report(s, user)
    E.consume_report(s, user, report, ent)
    s.commit()
    s.refresh(pack)
    assert pack.credits_left == 4 and report.plan_key == "pack_5"
    # pack reports don't count against the monthly plan quota
    assert E.get_entitlements(s, user, NOW).reports_used == 2


def test_plan_quota_used_before_pack(s, user):
    pack = buy_pack(s, user)
    report = new_report(s, user)
    E.consume_report(s, user, report, E.get_entitlements(s, user, NOW))
    s.commit()
    s.refresh(pack)
    assert pack.credits_left == 5 and report.plan_key == "free"


def test_soonest_expiring_pack_first(s, user):
    use_reports(s, user, 2)
    later = buy_pack(s, user, expires=NOW + timedelta(days=200))
    sooner = buy_pack(s, user, key="pack_1", credits=1, expires=NOW + timedelta(days=10))
    E.consume_report(s, user, new_report(s, user), E.get_entitlements(s, user, NOW))
    s.commit()
    s.refresh(sooner)
    s.refresh(later)
    assert (sooner.credits_left, later.credits_left) == (0, 5)


def test_expired_pack_ignored(s, user):
    use_reports(s, user, 2)
    buy_pack(s, user, expires=NOW - timedelta(days=1))
    assert E.get_entitlements(s, user, NOW).next_report_source is None


def test_refund_restores_plan_quota_and_pack(s, user):
    use_reports(s, user, 1)
    r1 = new_report(s, user)
    E.consume_report(s, user, r1, E.get_entitlements(s, user, NOW))
    s.commit()
    pack = buy_pack(s, user)
    r2 = new_report(s, user)
    E.consume_report(s, user, r2, E.get_entitlements(s, user, NOW))
    s.commit()
    E.refund_report(s, r2.id)
    E.refund_report(s, r1.id)
    s.refresh(pack)
    assert pack.credits_left == 5
    assert E.get_entitlements(s, user, NOW).reports_left == 1


# ---- per-report rules -------------------------------------------------------------------------

def test_chat_limit_is_the_more_generous(s, user):
    report = new_report(s, user)  # made on free: 5
    assert E.chat_limit(report, E.get_entitlements(s, user, NOW)) == 5
    subscribe(s, user, "pro")    # now pro: unlimited
    assert E.chat_limit(report, E.get_entitlements(s, user, NOW)) is None
    report.plan_key = "pack_1"   # pack: 30, user back on free: 5
    s.exec(select(db.Subscription)).one().status = "canceled"
    s.commit()
    assert E.chat_limit(report, E.get_entitlements(s, user, NOW)) == 30


def test_check_chat(s, user):
    report = new_report(s, user)
    for i in range(5):
        s.add(db.Message(report_id=report.id, role="user", content=str(i)))
        s.add(db.Message(report_id=report.id, role="assistant", content="ok"))
    s.commit()
    with pytest.raises(E.QuotaError) as e:
        E.check_chat(s, report, E.get_entitlements(s, user, NOW))
    assert e.value.reason == "chat"


def test_regenerate_and_templates_follow_features(s, user):
    report = new_report(s, user)
    ent = E.get_entitlements(s, user, NOW)
    with pytest.raises(E.QuotaError):
        E.check_regenerate(report, ent)
    with pytest.raises(E.QuotaError):
        E.check_templates("saas", "auto", ent)
    E.check_templates("auto", "auto", ent)  # auto is always fine
    report.plan_key = "pack_1"
    E.check_regenerate(report, ent)  # the pack allows it


def test_templates_allowed_when_next_report_uses_pack(s, user):
    use_reports(s, user, 2)
    buy_pack(s, user)
    E.check_templates("saas", "funding", E.get_entitlements(s, user, NOW))


def test_report_tier(s, user):
    report = new_report(s, user)
    assert E.report_tier(report, E.get_entitlements(s, user, NOW)) == "lite"
    subscribe(s, user, "entrepreneur")
    assert E.report_tier(report, E.get_entitlements(s, user, NOW)) == "standard"
    report.plan_key = "pack_5"
    assert E.report_tier(report, E.get_entitlements(s, user, NOW)) == "premium"


def test_public_view(s, user):
    subscribe(s, user, "pro")
    view = E.get_entitlements(s, user, NOW).to_public()
    assert view["plan"] == "pro" and view["plan_name"]["en"] == "Pro"
    assert view["reports_left"] == 40 and view["can_start_report"] is True
    assert view["renews_at"].startswith("2026-12-10")
