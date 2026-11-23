"""Sign in with Google (OpenID Connect authorization-code flow with PKCE).

/api/auth/google/start     → redirects to Google; state, nonce and PKCE verifier go in a short-lived
                             HttpOnly cookie.
/api/auth/google/callback  → checks state, exchanges the code for an ID token (server to server over
                             HTTPS, so per Google's docs checking iss/aud/exp/nonce is sufficient),
                             then finds, links or creates the user and starts a session.

Linking: an existing account with the same email is linked only when Google says the email is verified.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from backend import db
from backend.auth import start_session
from backend.config import get_settings

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
FLOW_COOKIE = "mustashar_google"
FLOW_SECONDS = 600

router = APIRouter(prefix="/api/auth/google")


def google_http() -> httpx.AsyncClient:
    """HTTP client for Google's token endpoint (overridden in tests)."""
    return httpx.AsyncClient(timeout=15)


def _redirect_uri() -> str:
    return get_settings().public_url.rstrip("/") + "/api/auth/google/callback"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _fail(reason: str) -> RedirectResponse:
    log.warning("google sign-in failed: %s", reason)
    resp = RedirectResponse("/#/login?error=google", status_code=303)
    resp.delete_cookie(FLOW_COOKIE, path="/api/auth/google")
    return resp


def decode_id_token(id_token: str) -> dict:
    payload = id_token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


@router.get("/start")
async def start(lang: Literal["ar", "en"] = "ar"):
    settings = get_settings()
    if not settings.google_client_id:
        return _fail("GOOGLE_CLIENT_ID not configured")
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{AUTH_URL}?{urlencode(params)}", status_code=303)
    flow = json.dumps({"state": state, "nonce": nonce, "verifier": verifier, "lang": lang})
    resp.set_cookie(FLOW_COOKIE, flow, max_age=FLOW_SECONDS, httponly=True, samesite="lax",
                    secure=settings.cookie_secure, path="/api/auth/google")
    return resp


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = "",
                   session: Session = Depends(db.get_session), http: httpx.AsyncClient = Depends(google_http)):
    settings = get_settings()
    try:
        flow = json.loads(request.cookies.get(FLOW_COOKIE, ""))
    except ValueError:
        return _fail("missing or bad flow cookie")
    if error or not code:
        return _fail(f"google returned error={error!r}")
    if not hmac.compare_digest(flow.get("state", ""), state):
        return _fail("state mismatch")

    try:
        async with http:
            r = await http.post(TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": flow["verifier"],
            })
        if r.status_code != 200:
            return _fail(f"token endpoint HTTP {r.status_code}: {r.text[:200]}")
        claims = decode_id_token(r.json()["id_token"])
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as e:
        return _fail(f"token exchange failed: {e!r}")

    if (claims.get("iss") not in ISSUERS or claims.get("aud") != settings.google_client_id
            or claims.get("exp", 0) <= time.time() or claims.get("nonce") != flow["nonce"]
            or not claims.get("sub") or not claims.get("email")):
        return _fail("invalid id token claims")

    sub, email = claims["sub"], claims["email"].strip().lower()
    google_verified = claims.get("email_verified") is True
    user = session.exec(select(db.User).where(db.User.google_sub == sub)).first()
    is_new = False
    if user is None:
        user = session.exec(select(db.User).where(db.User.email == email)).first()
        if user is not None:
            if not google_verified:
                return _fail("email exists but Google did not verify it; not linking")
            user.google_sub = sub
            user.email_verified = True
        else:
            is_new = True
            user = db.User(email=email, google_sub=sub, name=claims.get("name", ""),
                           language=flow.get("lang", "ar"), email_verified=google_verified)
        session.add(user)
        session.commit()
        session.refresh(user)

    resp = RedirectResponse("/#/welcome" if is_new else "/#/", status_code=303)
    resp.delete_cookie(FLOW_COOKIE, path="/api/auth/google")
    start_session(session, resp, user)
    return resp
