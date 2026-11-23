import os

import pytest
from sqlmodel import Session, SQLModel, select

from backend import db


@pytest.mark.parametrize("given,expected", [
    ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
    ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///./mustashar.db", "sqlite:///./mustashar.db"),
])
def test_normalize_url(given, expected):
    assert db.normalize_url(given) == expected


def test_postgres_engine_options():
    engine = db.make_engine("postgresql://u:p@localhost/x")
    assert engine.dialect.name == "postgresql" and engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True and engine.pool._recycle == 300


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to an EMPTY throwaway PostgreSQL db")
def test_schema_on_real_postgres():
    engine = db.make_engine(os.environ["TEST_DATABASE_URL"])
    SQLModel.metadata.create_all(engine)
    db._add_missing_columns(engine)
    try:
        with Session(engine) as s:
            user = db.User(email="pg-test@example.com")
            s.add(user)
            s.commit()
            s.add(db.Report(user_id=user.id, idea="i", goals="g", sections={"swot": {"strengths": ["x"]}}))
            s.commit()
            assert s.exec(select(db.Report)).one().sections["swot"]["strengths"] == ["x"]
    finally:
        SQLModel.metadata.drop_all(engine)
