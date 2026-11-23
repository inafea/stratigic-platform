import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from backend import db

from backend.main import app, get_analyzer
from backend.ratelimit import limiter
from backend.services.analyzer import Analyzer
from backend.llm.fake import FakeLLM


@pytest.fixture(autouse=True)
def memory_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db.set_engine(engine)
    db.init_db()
    yield engine
    db.set_engine(None)


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    limiter.reset()
    yield


TEST_USER = {"email": "tester@example.com", "password": "tester-password-1", "name": "Tester"}


@pytest.fixture
def anon_client(fake_llm):
    """A browser with a CSRF token but nobody logged in."""
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(fake_llm)
    with TestClient(app) as c:
        with_csrf(c)
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client):
    """A browser logged in as TEST_USER."""
    return login_new_user(anon_client)


@pytest.fixture
def pro_client(client, memory_db):
    """A browser logged in as TEST_USER on the Pro plan."""
    give_plan(memory_db, TEST_USER["email"], "pro")
    return client


def give_plan(engine, email: str, plan: str, months: int = 1) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlmodel import Session, select
    with Session(engine) as s:
        user = s.exec(select(db.User).where(db.User.email == email)).one()
        now = datetime.now(UTC)
        s.add(db.Subscription(user_id=user.id, plan_key=plan, current_period_start=now - timedelta(days=1),
                              current_period_end=now + timedelta(days=30 * months)))
        s.commit()


def login_new_user(c: TestClient, **user) -> TestClient:
    r = c.post("/api/auth/register", json={**TEST_USER, **user})
    assert r.status_code == 201, r.text
    return c


def with_csrf(c: TestClient) -> TestClient:
    """Act like the browser: get the CSRF cookie and echo it in the header on every request."""
    c.get("/api/health")
    c.headers["X-CSRF-Token"] = c.cookies["mustashar_csrf"]
    return c


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events
