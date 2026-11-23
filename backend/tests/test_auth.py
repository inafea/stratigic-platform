from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend import auth, db
from backend.main import app

USER = {"email": "Sara@Example.com", "password": "correct horse 1", "name": "سارة"}


def register(client, **over):
    return client.post("/api/auth/register", json={**USER, **over})


# ---- register / login / me / logout --------------------------------------------------

def test_register_logs_in_and_me(client):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["email"] == "sara@example.com"  # normalized
    assert "password_hash" not in r.json()
    me = client.get("/api/me").json()
    assert me["name"] == "سارة" and me["email_verified"] is False


def test_password_is_hashed_with_argon2(client, memory_db):
    register(client)
    with Session(memory_db) as s:
        user = s.exec(select(db.User)).one()
    assert user.password_hash.startswith("$argon2id$")
    assert USER["password"] not in user.password_hash


def test_duplicate_email_rejected(client):
    register(client)
    r = register(client, email="SARA@example.com ")
    assert r.status_code == 409


def test_register_validation(client):
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, password="short").status_code == 422


def test_logout_then_me_is_401(client):
    register(client)
    assert client.post("/api/auth/logout").status_code == 204
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "يرجى تسجيل الدخول أولاً."


def test_login(client):
    register(client)
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": " sara@EXAMPLE.com", "password": USER["password"]})
    assert r.status_code == 200
    assert client.get("/api/me").json()["email"] == "sara@example.com"


def test_wrong_password_and_unknown_email_look_the_same(client):
    register(client)
    client.post("/api/auth/logout")
    bad = client.post("/api/auth/login", json={"email": USER["email"], "password": "wrong password"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()


def test_login_error_in_english(client):
    r = client.post("/api/auth/login", json={"email": "x@y.com", "password": "nope1234"}, headers={"X-Lang": "en"})
    assert r.json()["detail"] == "Incorrect email or password."


def test_passwordless_account_cannot_log_in(client, memory_db):
    with Session(memory_db) as s:
        s.add(db.User(email="admin@localhost", is_admin=True))
        s.commit()
    r = client.post("/api/auth/login", json={"email": "admin@localhost", "password": "anything1"})
    assert r.status_code == 401


# ---- session cookie ----------------------------------------------------------------

def test_session_cookie_flags_and_hashed_storage(client, memory_db):
    r = register(client)
    cookie = r.headers["set-cookie"]
    assert auth.SESSION_COOKIE in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    token = client.cookies[auth.SESSION_COOKIE]
    with Session(memory_db) as s:
        row = s.exec(select(db.AuthSession)).one()
    assert row.token_hash == auth.token_hash(token) != token


def test_secure_cookie_in_production(client, monkeypatch):
    settings = auth.get_settings().model_copy(update={"cookie_secure": True})
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    assert "Secure" in register(client).headers["set-cookie"]


def test_expired_session_rejected_and_removed(client, memory_db):
    register(client)
    with Session(memory_db) as s:
        row = s.exec(select(db.AuthSession)).one()
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        s.add(row)
        s.commit()
    assert client.get("/api/me").status_code == 401
    with Session(memory_db) as s:
        assert s.exec(select(db.AuthSession)).all() == []


def test_forged_session_cookie_rejected(client):
    client.cookies.set(auth.SESSION_COOKIE, "forged-token")
    assert client.get("/api/me").status_code == 401


# ---- CSRF ----------------------------------------------------------------------------

def test_csrf_cookie_handed_out(client):
    assert client.cookies.get(auth.CSRF_COOKIE)


def test_post_without_csrf_header_rejected(client):
    del client.headers["X-CSRF-Token"]
    r = client.post("/api/auth/register", json=USER)
    assert r.status_code == 403
    assert "تحديثها" in r.json()["detail"]


def test_post_with_wrong_csrf_header_rejected(client):
    client.headers["X-CSRF-Token"] = "wrong"
    assert client.post("/api/auth/login", json=USER).status_code == 403


def test_new_browser_without_cookie_rejected():
    with TestClient(app) as fresh:
        assert fresh.post("/api/auth/register", json=USER).status_code == 403


def test_get_requests_need_no_csrf(client):
    del client.headers["X-CSRF-Token"]
    assert client.get("/api/health").status_code == 200


def test_login_is_rate_limited(client, monkeypatch):
    from backend import ratelimit
    settings = ratelimit.get_settings().model_copy(update={"auth_rate_limit": "3/minute"})
    monkeypatch.setattr(ratelimit, "get_settings", lambda: settings)
    codes = [client.post("/api/auth/login", json={"email": "a@b.co", "password": "x" * 8}).status_code
             for _ in range(4)]
    assert codes == [401, 401, 401, 429]
