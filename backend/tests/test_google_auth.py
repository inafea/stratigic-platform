import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlmodel import Session, select

from backend import auth, db, google_auth
from backend.main import app

CLIENT_ID = "test-client.apps.googleusercontent.com"


@pytest.fixture
def google(client, monkeypatch):
    """Configure Google sign-in and fake Google's token endpoint. Returns a dict to tweak the ID token."""
    settings = google_auth.get_settings().model_copy(
        update={"google_client_id": CLIENT_ID, "google_client_secret": "secret"})
    monkeypatch.setattr(google_auth, "get_settings", lambda: settings)
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    fake = {"claims": {}, "status": 200, "seen": None}

    def handler(req: httpx.Request):
        fake["seen"] = parse_qs(req.content.decode())
        if fake["status"] != 200:
            return httpx.Response(fake["status"], json={"error": "invalid_grant"})
        claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "exp": time.time() + 300,
                  "sub": "g-123", "email": "sara@gmail.com", "email_verified": True, "name": "Sara G",
                  "nonce": fake["nonce"], **fake["claims"]}
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        return httpx.Response(200, json={"id_token": f"h.{payload}.sig", "access_token": "a"})

    app.dependency_overrides[google_auth.google_http] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handler))
    return fake


def sign_in(client, google, state=None, lang="en"):
    start = client.get(f"/api/auth/google/start?lang={lang}", follow_redirects=False)
    assert start.status_code == 303
    params = parse_qs(urlparse(start.headers["location"]).query)
    google["nonce"] = params["nonce"][0]
    google["start_params"] = params
    return client.get("/api/auth/google/callback",
                      params={"code": "auth-code", "state": state or params["state"][0]}, follow_redirects=False)


def test_start_redirects_to_google_with_pkce(client, google):
    sign_in(client, google)
    p = google["start_params"]
    assert p["client_id"] == [CLIENT_ID]
    assert p["redirect_uri"] == ["http://127.0.0.1:8000/api/auth/google/callback"]
    assert p["scope"] == ["openid email profile"]
    assert p["code_challenge_method"] == ["S256"]
    # the verifier sent to the token endpoint matches the challenge
    import hashlib
    verifier = google["seen"]["code_verifier"][0]
    assert google_auth._b64url(hashlib.sha256(verifier.encode()).digest()) == p["code_challenge"][0]


def test_new_user_created_and_logged_in(client, google, memory_db):
    r = sign_in(client, google)
    assert r.status_code == 303 and r.headers["location"] == "/#/welcome"
    me = client.get("/api/me").json()
    assert me["email"] == "sara@gmail.com" and me["name"] == "Sara G"
    assert me["email_verified"] is True and me["language"] == "en"
    with Session(memory_db) as s:
        user = s.exec(select(db.User)).one()
    assert user.google_sub == "g-123" and user.password_hash is None


def test_returning_user_goes_home(client, google, memory_db):
    sign_in(client, google)
    client.post("/api/auth/logout")
    r = sign_in(client, google)
    assert r.headers["location"] == "/#/"
    with Session(memory_db) as s:
        assert len(s.exec(select(db.User)).all()) == 1


def test_links_existing_password_account(client, google, memory_db):
    client.post("/api/auth/register", json={"email": "sara@gmail.com", "password": "password123"})
    client.post("/api/auth/logout")
    r = sign_in(client, google)
    assert r.headers["location"] == "/#/"
    with Session(memory_db) as s:
        user = s.exec(select(db.User)).one()
    assert user.google_sub == "g-123" and user.email_verified and user.password_hash  # password kept


def test_does_not_link_when_google_email_unverified(client, google, memory_db):
    client.post("/api/auth/register", json={"email": "sara@gmail.com", "password": "password123"})
    client.post("/api/auth/logout")
    google["claims"] = {"email_verified": False}
    r = sign_in(client, google)
    assert r.headers["location"] == "/#/login?error=google"
    assert client.get("/api/me").status_code == 401
    with Session(memory_db) as s:
        assert s.exec(select(db.User)).one().google_sub is None


@pytest.mark.parametrize("claims", [
    {"aud": "someone-else"},
    {"iss": "https://evil.example"},
    {"exp": time.time() - 10},
    {"nonce": "replayed"},
])
def test_bad_id_token_rejected(client, google, claims):
    google["claims"] = claims
    r = sign_in(client, google)
    assert r.headers["location"] == "/#/login?error=google"
    assert client.get("/api/me").status_code == 401


def test_state_mismatch_rejected(client, google):
    r = sign_in(client, google, state="forged")
    assert r.headers["location"] == "/#/login?error=google"
    assert google["seen"] is None  # never reached Google


def test_callback_without_flow_cookie_rejected(client, google):
    r = client.get("/api/auth/google/callback", params={"code": "c", "state": "s"}, follow_redirects=False)
    assert r.headers["location"] == "/#/login?error=google"


def test_token_endpoint_error(client, google):
    google["status"] = 400
    assert sign_in(client, google).headers["location"] == "/#/login?error=google"


def test_user_cancelled_at_google(client, google):
    client.get("/api/auth/google/start", follow_redirects=False)
    r = client.get("/api/auth/google/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert r.headers["location"] == "/#/login?error=google"


def test_disabled_without_client_id(client):
    r = client.get("/api/auth/google/start", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#/login?error=google"


def test_flow_cookie_is_httponly_and_scoped(client, google):
    r = client.get("/api/auth/google/start", follow_redirects=False)
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Path=/api/auth/google" in cookie and "Max-Age=600" in cookie
