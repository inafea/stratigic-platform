"""SQLite persistence for reports and follow-up chat messages."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, select

from backend.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    idea: str
    goals: str
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
    SQLModel.metadata.create_all(get_engine())


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
