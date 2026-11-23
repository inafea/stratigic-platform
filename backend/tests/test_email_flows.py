import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend import auth, db
from backend.mailer import ConsoleMailer, get_mailer
from backend.main import app

USER = {"email": "sara@example.com", "password": "correct horse 1", "name": "Sara", "language": "en"}
NEW_PASSWORD = "a brand new pass 2"


@pytest.fixture
def mailer(client):
    m = ConsoleMailer()
    app.dependency_overrides[get_mailer] = lambda: m
    return m


def token_from(mail, route):
    m = re.search(rf"/#/{route}\?token=([\w-]+)", mail.text)
    assert m, mail.text
    return m.group(1)


def register(client, **over):
    return client.post("/api/auth/register", json={**USER, **over})


# ---- verification ----------------------------------------------------------------------

def test_register_sends_verification_email(client, mailer):
    register(client)
    (mail,) = mailer.outbox
    assert mail.to == "sara@example.com"
    assert mail.subject.startswith("Confirm your email")
    assert "http://127.0.0.1:8000/#/verify?token=" in mail.text


def test_email_in_users_language(client, mailer):
    register(client, language="ar")
    assert "أكّد" in mailer.outbox[0].subject


def test_verify_marks_email_verified(client, mailer):
    register(client)
    r = client.post("/api/auth/verify", json={"token": token_from(mailer.outbox[0], "verify")})
    assert r.status_code == 200 and r.json()["email_verified"] is True
    assert client.get("/api/me").json()["email_verified"] is True


def test_verify_token_single_use(client, mailer):
    register(client)
    token = token_from(mailer.outbox[0], "verify")
    client.post("/api/auth/verify", json={"token": token})
    r = client.post("/api/auth/verify", json={"token": token})
    assert r.status_code == 400
    assert "الرابط" in r.json()["detail"]


def test_verify_bad_token(client, mailer):
    r = client.post("/api/auth/verify", json={"token": "x" * 40}, headers={"X-Lang": "en"})
    assert r.status_code == 400 and "invalid or has expired" in r.json()["detail"]


def test_expired_verify_token(client, mailer, memory_db):
    register(client)
    with Session(memory_db) as s:
        row = s.exec(select(db.EmailToken)).one()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        s.add(row)
        s.commit()
    assert client.post("/api/auth/verify", json={"token": token_from(mailer.outbox[0], "verify")}).status_code == 400


def test_resend_invalidates_old_link(client, mailer):
    register(client)
    assert client.post("/api/auth/verify/resend").json() == {"sent": True}
    old, new = (token_from(m, "verify") for m in mailer.outbox)
    assert client.post("/api/auth/verify", json={"token": old}).status_code == 400
    assert client.post("/api/auth/verify", json={"token": new}).status_code == 200
    assert client.post("/api/auth/verify/resend").json() == {"sent": False}  # already verified
    assert len(mailer.outbox) == 2


def test_resend_needs_login(client, mailer):
    assert client.post("/api/auth/verify/resend").status_code == 401


def test_tokens_stored_hashed(client, mailer, memory_db):
    register(client)
    token = token_from(mailer.outbox[0], "verify")
    with Session(memory_db) as s:
        assert s.exec(select(db.EmailToken)).one().token_hash == auth.token_hash(token)


# ---- password reset ---------------------------------------------------------------------

def forgot(client, email=USER["email"]):
    return client.post("/api/auth/password/forgot", json={"email": email})


def test_forgot_same_answer_for_unknown_email(client, mailer):
    register(client)
    mailer.outbox.clear()
    known, unknown = forgot(client), forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [m.to for m in mailer.outbox] == ["sara@example.com"]


def test_reset_password_flow(client, mailer):
    register(client)
    client.post("/api/auth/logout")
    forgot(client)
    token = token_from(mailer.outbox[-1], "reset")
    r = client.post("/api/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})
    assert r.status_code == 200
    assert r.json()["email_verified"] is True  # inbox proven
    assert client.get("/api/me").status_code == 200  # logged in by the reset
    client.post("/api/auth/logout")
    login = lambda pw: client.post("/api/auth/login", json={"email": USER["email"], "password": pw}).status_code
    assert login(USER["password"]) == 401
    assert login(NEW_PASSWORD) == 200


def test_reset_logs_out_other_sessions(client, mailer, memory_db):
    register(client)  # session 1 (e.g. a stolen one)
    forgot(client)
    token = token_from(mailer.outbox[-1], "reset")
    old_cookie = client.cookies[auth.SESSION_COOKIE]
    client.post("/api/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})
    with Session(memory_db) as s:
        hashes = [row.token_hash for row in s.exec(select(db.AuthSession))]
    assert auth.token_hash(old_cookie) not in hashes and len(hashes) == 1


def test_reset_token_cannot_verify_and_vice_versa(client, mailer):
    register(client)
    forgot(client)
    verify_token = token_from(mailer.outbox[0], "verify")
    reset_token = token_from(mailer.outbox[1], "reset")
    assert client.post("/api/auth/verify", json={"token": reset_token}).status_code == 400
    assert client.post("/api/auth/password/reset",
                       json={"token": verify_token, "password": NEW_PASSWORD}).status_code == 400


def test_reset_token_expires_after_an_hour(client, mailer, memory_db):
    register(client)
    forgot(client)
    with Session(memory_db) as s:
        row = s.exec(select(db.EmailToken).where(db.EmailToken.purpose == "reset")).one()
        assert auth._aware(row.expires_at) - datetime.now(UTC) <= timedelta(hours=1)
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        s.add(row)
        s.commit()
    token = token_from(mailer.outbox[-1], "reset")
    assert client.post("/api/auth/password/reset",
                       json={"token": token, "password": NEW_PASSWORD}).status_code == 400


def test_admin_without_password_can_set_one(client, mailer, memory_db):
    with Session(memory_db) as s:
        s.add(db.User(email="admin@localhost", is_admin=True, email_verified=True))
        s.commit()
    forgot(client, "admin@localhost")
    token = token_from(mailer.outbox[-1], "reset")
    client.post("/api/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": "admin@localhost", "password": NEW_PASSWORD})
    assert r.status_code == 200 and r.json()["is_admin"] is True


def test_reset_password_validation(client, mailer):
    assert client.post("/api/auth/password/reset", json={"token": "x" * 40, "password": "short"}).status_code == 422
