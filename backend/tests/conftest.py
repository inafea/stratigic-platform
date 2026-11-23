import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_analyzer
from backend.services.analyzer import Analyzer
from backend.tests.fakes import FakeLLM


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def client(fake_llm):
    app.dependency_overrides[get_analyzer] = lambda: Analyzer(fake_llm)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events
