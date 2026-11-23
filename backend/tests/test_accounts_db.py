from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from backend import db


def test_new_tables_created(memory_db):
    tables = set(inspect(memory_db).get_table_names())
    assert {"user", "authsession", "emailtoken", "report", "message"} <= tables
    assert "user_id" in {c["name"] for c in inspect(memory_db).get_columns("report")}


def test_email_is_unique(memory_db):
    with Session(memory_db) as s:
        s.add(db.User(email="a@x.com"))
        s.commit()
        s.add(db.User(email="a@x.com"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_session_and_token_link_to_user(memory_db):
    soon = datetime.now(UTC) + timedelta(days=1)
    with Session(memory_db) as s:
        u = db.User(email="b@x.com", password_hash="h")
        s.add(u)
        s.commit()
        s.add(db.AuthSession(token_hash="t1", user_id=u.id, expires_at=soon))
        s.add(db.EmailToken(token_hash="e1", user_id=u.id, purpose="verify", expires_at=soon))
        s.add(db.Report(idea="i", goals="g", user_id=u.id))
        s.commit()
        assert s.get(db.AuthSession, "t1").user_id == u.id
        assert s.get(db.EmailToken, "e1").used_at is None
        assert s.exec(select(db.Report)).one().user_id == u.id


def test_fresh_db_creates_no_admin(memory_db):
    with Session(memory_db) as s:
        assert s.exec(select(db.User)).all() == []


def old_database(tmp_path):
    """A database as it was before accounts: report table without user_id, two reports."""
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE report (id INTEGER PRIMARY KEY, created_at DATETIME, idea VARCHAR, "
                          "goals VARCHAR, industry VARCHAR, strategy VARCHAR, language VARCHAR, answers JSON, "
                          "sections JSON, status VARCHAR)"))
        for i in (1, 2):
            conn.execute(text("INSERT INTO report (id, created_at, idea, goals, industry, strategy, language, "
                              "answers, sections, status) VALUES "
                              f"({i}, '2026-11-01 10:00:00', 'idea {i}', 'g', 'auto', 'auto', 'ar', '[]', '{{}}', 'done')"))
    return engine


def test_old_reports_attached_to_admin(tmp_path):
    engine = old_database(tmp_path)
    db.set_engine(engine)
    db.init_db()
    with Session(engine) as s:
        admin = s.exec(select(db.User)).one()
        assert admin.email == "admin@localhost"
        assert admin.is_admin and admin.email_verified and admin.password_hash is None
        reports = s.exec(select(db.Report).order_by(db.Report.id)).all()
        assert [r.user_id for r in reports] == [admin.id, admin.id]
        assert reports[0].idea == "idea 1"


def test_migration_is_idempotent(tmp_path):
    engine = old_database(tmp_path)
    db.set_engine(engine)
    db.init_db()
    db.init_db()
    with Session(engine) as s:
        assert len(s.exec(select(db.User)).all()) == 1


def test_existing_admin_reused(tmp_path, monkeypatch):
    engine = old_database(tmp_path)
    db.set_engine(engine)
    SQLModel = db.SQLModel
    SQLModel.metadata.create_all(engine, tables=[db.User.__table__])
    with Session(engine) as s:
        s.add(db.User(email="owner@example.com", password_hash="h"))
        s.commit()
    settings = db.get_settings().model_copy(update={"admin_email": "Owner@Example.com"})
    monkeypatch.setattr(db, "get_settings", lambda: settings)
    db.init_db()
    with Session(engine) as s:
        owner = s.exec(select(db.User)).one()
        assert owner.password_hash == "h"  # existing account kept, not replaced
        assert {r.user_id for r in s.exec(select(db.Report))} == {owner.id}
