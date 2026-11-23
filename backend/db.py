"""SQLite persistence: users and auth, reports, and follow-up chat messages."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, select

from backend.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


# ---- accounts --------------------------------------------------------------------

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)  # stored lower-case
    name: str = ""
    password_hash: str | None = None  # None: Google-only account, or admin created by migration
    google_sub: str | None = Field(default=None, index=True, unique=True)
    language: str = "ar"
    email_verified: bool = False
    is_admin: bool = False
    created_at: datetime = Field(default_factory=_now)


class AuthSession(SQLModel, table=True):
    """A logged-in browser session. Only the SHA-256 of the cookie token is stored."""
    token_hash: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime


class EmailToken(SQLModel, table=True):
    """One-time token sent by email (verify address / reset password). Only the hash is stored."""
    token_hash: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    purpose: str  # verify | reset
    expires_at: datetime
    used_at: datetime | None = None


# ---- reports ---------------------------------------------------------------------

class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=_now)
    idea: str
    goals: str
    industry: str = "auto"
    strategy: str = "auto"
    language: str = "ar"
    answers: list = Field(default_factory=list, sa_column=Column(JSON))
    sections: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "running"  # running | done | error


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", index=True)
    role: str  # user | assistant
    content: str
    created_at: datetime = Field(default_factory=_now)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=args)
    return _engine


def set_engine(engine: Engine) -> None:
    """Swap the engine (used by tests)."""
    global _engine
    _engine = engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)
    _attach_orphan_reports(engine)


def _add_missing_columns(engine: Engine) -> None:
    """Add columns introduced after a database was created (no migration tool for SQLite here)."""
    existing = {c["name"] for c in inspect(engine).get_columns("report")}
    with engine.begin() as conn:
        for name, default in (("industry", "auto"), ("strategy", "auto"), ("language", "ar")):
            if name not in existing:
                conn.execute(text(f"ALTER TABLE report ADD COLUMN {name} VARCHAR NOT NULL DEFAULT '{default}'"))
        if "user_id" not in existing:
            conn.execute(text("ALTER TABLE report ADD COLUMN user_id INTEGER REFERENCES user(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_report_user_id ON report (user_id)"))


def _attach_orphan_reports(engine: Engine) -> None:
    """Reports made before accounts existed belong to the admin user (created if needed, no password:
    set one through password reset)."""
    with Session(engine) as s:
        orphans = list(s.exec(select(Report).where(Report.user_id.is_(None))))
        if not orphans:
            return
        email = get_settings().admin_email.strip().lower()
        admin = s.exec(select(User).where(User.email == email)).first()
        if admin is None:
            admin = User(email=email, name="Admin", is_admin=True, email_verified=True)
            s.add(admin)
            s.flush()
        for r in orphans:
            r.user_id = admin.id
            s.add(r)
        s.commit()


def get_session():
    with Session(get_engine()) as session:
        yield session


def save_section(report_id: int, key: str, data: dict) -> None:
    with Session(get_engine()) as s:
        report = s.get(Report, report_id)
        if report is None:
            return
        report.sections = {**report.sections, key: data}  # reassign so JSON change is tracked
        s.add(report)
        s.commit()


def set_status(report_id: int, status: str) -> None:
    with Session(get_engine()) as s:
        report = s.get(Report, report_id)
        if report is not None:
            report.status = status
            s.add(report)
            s.commit()


def list_messages(session: Session, report_id: int) -> list[Message]:
    return list(session.exec(select(Message).where(Message.report_id == report_id).order_by(Message.id)))
