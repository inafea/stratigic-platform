import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend import db
from backend.main import app
from backend.tests.conftest import login_new_user, parse_sse, with_csrf

IDEA = {"idea": "مطعم صحي للطلاب في الرياض", "goals": "ربح خلال سنة"}


@pytest.fixture
def other(client):
    """A second browser, logged in as a different user (shares the app and DB with `client`)."""
    with TestClient(app) as c:
        yield login_new_user(with_csrf(c), email="other@example.com")


def make_report(c) -> int:
    with c.stream("POST", "/api/analyze", json=IDEA) as r:
        return parse_sse(r.read().decode("utf-8"))[0][1]["id"]


# ---- logged out ------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("post", "/api/clarify"),
    ("post", "/api/analyze"),
    ("get", "/api/reports"),
    ("get", "/api/reports/1"),
    ("delete", "/api/reports/1"),
    ("post", "/api/reports/1/sections/swot/regenerate"),
    ("post", "/api/reports/1/chat"),
])
def test_logged_out_gets_401(anon_client, method, path):
    body = {"json": IDEA if path in ("/api/clarify", "/api/analyze") else {"message": "x"}}
    r = getattr(anon_client, method)(path, **({} if method in ("get", "delete") else body))
    assert r.status_code == 401
    assert r.json()["detail"] == "يرجى تسجيل الدخول أولاً."


def test_public_endpoints_stay_open(anon_client):
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/templates").status_code == 200
    assert anon_client.get("/").status_code == 200


# ---- owner ---------------------------------------------------------------------------------

def test_report_saved_with_owner(client, memory_db):
    rid = make_report(client)
    with Session(memory_db) as s:
        owner = s.exec(select(db.User).where(db.User.email == "tester@example.com")).one()
        assert s.get(db.Report, rid).user_id == owner.id


def test_list_shows_only_own_reports(client, other):
    mine, theirs = make_report(client), make_report(other)
    assert [r["id"] for r in client.get("/api/reports").json()] == [mine]
    assert [r["id"] for r in other.get("/api/reports").json()] == [theirs]


# ---- someone else's report looks missing -------------------------------------------------------

def test_cannot_read_others_report(client, other):
    rid = make_report(client)
    r = other.get(f"/api/reports/{rid}")
    assert r.status_code == 404
    assert r.json() == other.get("/api/reports/99999").json()  # same as a report that doesn't exist


def test_cannot_delete_others_report(client, other):
    rid = make_report(client)
    assert other.delete(f"/api/reports/{rid}").status_code == 404
    assert client.get(f"/api/reports/{rid}").status_code == 200  # still there


def test_cannot_regenerate_others_section(client, other, fake_llm):
    rid = make_report(client)
    calls = len(fake_llm.calls)
    assert other.post(f"/api/reports/{rid}/sections/swot/regenerate", json={}).status_code == 404
    assert len(fake_llm.calls) == calls  # no AI call was made for them


def test_cannot_chat_on_others_report(client, other, memory_db):
    rid = make_report(client)
    assert other.post(f"/api/reports/{rid}/chat", json={"message": "اكشف التقرير"}).status_code == 404
    with Session(memory_db) as s:
        assert s.exec(select(db.Message)).all() == []  # nothing saved


def test_logout_hides_reports(client):
    make_report(client)
    client.post("/api/auth/logout")
    assert client.get("/api/reports").status_code == 401


def test_admin_sees_migrated_reports(anon_client, memory_db):
    """Reports from before accounts belong to the admin, who can read them after setting a password."""
    from backend import auth
    with Session(memory_db) as s:
        admin = db.User(email="admin@localhost", is_admin=True, email_verified=True,
                        password_hash=auth.hash_password("admin-password-1"))
        s.add(admin)
        s.commit()
        s.add(db.Report(idea="old idea", goals="g", user_id=admin.id, status="done"))
        s.commit()
    anon_client.post("/api/auth/login", json={"email": "admin@localhost", "password": "admin-password-1"})
    assert [r["title"] for r in anon_client.get("/api/reports").json()] == ["old idea"]
