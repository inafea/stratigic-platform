"""What a user may do right now: plan, monthly quota, pack credits, model tier and features.

Monthly windows:
- Free users: the calendar month (UTC).
- Subscribers: monthly windows counted from the subscription's period start, so a yearly plan
  gets its quota every month and a monthly plan's window matches its billing period.

A report uses the monthly quota first, then the pack credit that expires soonest. The plan or pack
used is saved on the report (Report.plan_key); later chat and regeneration on that report get the
more generous of the report's terms and the user's current plan.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlmodel import Session, func, select

from backend import db
from backend.billing.plans import Features, Pack, Plan, get_catalog

TIER_RANK = {"lite": 0, "standard": 1, "premium": 2}
ACTIVE_STATUSES = ("active", "past_due")  # past_due keeps the plan until the renewal job downgrades it


# ---- errors ----------------------------------------------------------------------------

MSG_NO_REPORTS = "لقد استخدمت كل تقارير باقتك لهذا الشهر. قم بالترقية أو اشترِ باقة تقارير للمتابعة."
MSG_NO_CHAT = "وصلت إلى الحد الأقصى لأسئلة المتابعة لهذا التقرير في باقتك. قم بالترقية لطرح المزيد."
MSG_NO_REGENERATE = "إعادة توليد الأقسام غير متاحة في باقتك الحالية. قم بالترقية لاستخدامها."
MSG_NO_TEMPLATES = "قوالب القطاعات وأنواع الاستراتيجية متاحة في الباقات المدفوعة. اختر «تحديد تلقائي» أو قم بالترقية."


class QuotaError(Exception):
    """Raised when the plan doesn't allow the action; answered with HTTP 402 and an upgrade hint."""

    def __init__(self, reason: str, user_message: str):
        super().__init__(reason)
        self.reason = reason  # reports | chat | regenerate | templates
        self.user_message = user_message


# ---- time helpers --------------------------------------------------------------------------

def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def add_months(dt: datetime, months: int) -> datetime:
    """Same day next month(s), clamped to the month's last day (Jan 31 + 1 month = Feb 28/29)."""
    total = dt.month - 1 + months
    year, month = dt.year + total // 12, total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def monthly_window(anchor: datetime, now: datetime) -> tuple[datetime, datetime]:
    """The [start, end) monthly window that contains `now`, counting months from `anchor`."""
    anchor, now = _aware(anchor), _aware(now)
    months = (now.year - anchor.year) * 12 + (now.month - anchor.month)
    start = add_months(anchor, months)
    if start > now:
        months -= 1
        start = add_months(anchor, months)
    return start, add_months(anchor, months + 1)


def calendar_month(now: datetime) -> tuple[datetime, datetime]:
    start = _aware(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, add_months(start, 1)


# ---- entitlements ----------------------------------------------------------------------------

@dataclass
class Entitlements:
    plan: Plan
    subscription: db.Subscription | None
    window_start: datetime
    window_end: datetime
    reports_used: int
    pack_credits: int
    next_pack: db.CreditPack | None = field(default=None, repr=False)

    @property
    def reports_limit(self) -> int | None:
        return self.plan.limits.reports_per_month

    @property
    def reports_left(self) -> int | None:
        """Left in this month's plan quota (None = unlimited); pack credits not included."""
        return None if self.reports_limit is None else max(0, self.reports_limit - self.reports_used)

    @property
    def next_report_source(self) -> str | None:
        """Where the next report's credit comes from: plan, pack, or None (no quota left)."""
        if self.reports_left is None or self.reports_left > 0:
            return "plan"
        return "pack" if self.pack_credits > 0 else None

    @property
    def next_report_terms(self) -> Plan | Pack:
        if self.next_report_source == "pack":
            return get_catalog().packs[self.next_pack.pack_key]
        return self.plan

    def to_public(self) -> dict:
        s = self.subscription
        return {
            "plan": self.plan.key,
            "plan_name": {"ar": self.plan.name_ar, "en": self.plan.name_en},
            "period": s.period if s else None,
            "renews_at": _aware(s.current_period_end).isoformat() if s else None,
            "cancel_at_period_end": s.cancel_at_period_end if s else False,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "reports_used": self.reports_used,
            "reports_limit": self.reports_limit,
            "reports_left": self.reports_left,
            "pack_credits": self.pack_credits,
            "can_start_report": self.next_report_source is not None,
            "model_tier": self.plan.model_tier,
            "limits": self.plan.limits.model_dump(),
            "features": self.plan.features.model_dump(),
            # features for the next report (a pack credit may unlock more than the plan)
            "next_report_features": self.next_report_terms.features.model_dump(),
        }


def active_subscription(session: Session, user: db.User, now: datetime) -> db.Subscription | None:
    subs = session.exec(select(db.Subscription).where(db.Subscription.user_id == user.id,
                                                      db.Subscription.status.in_(ACTIVE_STATUSES))
                        .order_by(db.Subscription.id.desc())).all()
    catalog = get_catalog()
    for sub in subs:
        if _aware(sub.current_period_start) <= now < _aware(sub.current_period_end) and sub.plan_key in catalog.plans:
            return sub
    return None


def get_entitlements(session: Session, user: db.User, now: datetime | None = None) -> Entitlements:
    now = _aware(now or datetime.now(UTC))
    catalog = get_catalog()
    sub = active_subscription(session, user, now)
    if sub:
        plan = catalog.plans[sub.plan_key]
        start, end = monthly_window(sub.current_period_start, now)
    else:
        plan = catalog.free
        start, end = calendar_month(now)

    used = session.exec(select(func.count()).select_from(db.UsageEvent).where(
        db.UsageEvent.user_id == user.id, db.UsageEvent.kind == "report", db.UsageEvent.source == "plan",
        db.UsageEvent.at >= start, db.UsageEvent.at < end)).one()

    packs = [p for p in session.exec(select(db.CreditPack).where(
        db.CreditPack.user_id == user.id, db.CreditPack.credits_left > 0)).all()
        if _aware(p.expires_at) > now and p.pack_key in catalog.packs]
    packs.sort(key=lambda p: _aware(p.expires_at))
    return Entitlements(plan=plan, subscription=sub, window_start=start, window_end=end, reports_used=used,
                        pack_credits=sum(p.credits_left for p in packs), next_pack=packs[0] if packs else None)


# ---- using and refunding a report credit -----------------------------------------------------------

def consume_report(session: Session, user: db.User, report: db.Report, ent: Entitlements) -> None:
    """Charge one report to the plan quota or a pack and record which terms the report gets.
    Raises QuotaError when nothing is left. The caller commits."""
    source = ent.next_report_source
    if source is None:
        raise QuotaError("reports", MSG_NO_REPORTS)
    event = db.UsageEvent(user_id=user.id, kind="report", report_id=report.id, source=source)
    if source == "pack":
        pack = ent.next_pack
        pack.credits_left -= 1
        event.pack_id = pack.id
        report.plan_key = pack.pack_key
        session.add(pack)
    else:
        report.plan_key = ent.plan.key
    session.add(event)
    session.add(report)


def refund_report(session: Session, report_id: int) -> None:
    """Give back the credit of a report that produced nothing (e.g. the AI service failed)."""
    for event in session.exec(select(db.UsageEvent).where(db.UsageEvent.report_id == report_id,
                                                          db.UsageEvent.kind == "report")).all():
        if event.pack_id:
            pack = session.get(db.CreditPack, event.pack_id)
            if pack:
                pack.credits_left += 1
                session.add(pack)
        session.delete(event)
    session.commit()


# ---- per-report rules ------------------------------------------------------------------------------

def report_terms(report: db.Report) -> Plan | Pack:
    catalog = get_catalog()
    return catalog.plans.get(report.plan_key) or catalog.packs.get(report.plan_key) or catalog.free


def _more_generous_limit(a: int | None, b: int | None) -> int | None:
    return None if a is None or b is None else max(a, b)


def chat_limit(report: db.Report, ent: Entitlements) -> int | None:
    return _more_generous_limit(report_terms(report).limits.chat_per_report, ent.plan.limits.chat_per_report)


def report_features(report: db.Report, ent: Entitlements) -> Features:
    a, b = report_terms(report).features, ent.plan.features
    return Features(templates=a.templates or b.templates, regenerate=a.regenerate or b.regenerate,
                    watermark=a.watermark and b.watermark, branded_pdf=a.branded_pdf or b.branded_pdf,
                    seats=max(a.seats, b.seats))


def report_tier(report: db.Report, ent: Entitlements) -> str:
    return max(report_terms(report).model_tier, ent.plan.model_tier, key=TIER_RANK.__getitem__)


def check_chat(session: Session, report: db.Report, ent: Entitlements) -> None:
    limit = chat_limit(report, ent)
    if limit is None:
        return
    asked = session.exec(select(func.count()).select_from(db.Message).where(
        db.Message.report_id == report.id, db.Message.role == "user")).one()
    if asked >= limit:
        raise QuotaError("chat", MSG_NO_CHAT)


def check_regenerate(report: db.Report, ent: Entitlements) -> None:
    if not report_features(report, ent).regenerate:
        raise QuotaError("regenerate", MSG_NO_REGENERATE)


def check_templates(industry: str, strategy: str, ent: Entitlements) -> None:
    if (industry != "auto" or strategy != "auto") and not ent.next_report_terms.features.templates:
        raise QuotaError("templates", MSG_NO_TEMPLATES)
