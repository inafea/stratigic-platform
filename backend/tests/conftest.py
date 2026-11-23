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


@pytest.fixture
def client(fake_llm):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(fake_llm)
    with TestClient(app) as c:
        with_csrf(c)
        yield c
    app.dependency_overrides.clear()


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
