"""Accounts: register, login, logout, current user, session cookie and CSRF protection.

- Passwords are hashed with Argon2id.
- The session cookie is HttpOnly + SameSite=Lax (+ Secure in production); only the SHA-256 of
  its token is stored, so a leaked database cannot be used to log in.
- CSRF uses the double-submit pattern: a readable `mustashar_csrf` cookie whose value the
  frontend must echo in the `X-CSRF-Token` header on every state-changing /api request.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from backend import db
from backend.config import get_settings
from backend.i18n import request_lang, tr
from backend.mailer import Mail, Mailer, get_mailer
from backend.ratelimit import auth_limit

SESSION_COOKIE = "mustashar_session"
CSRF_COOKIE = "mustashar_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MSG_BAD_LOGIN = "البريد الإلكتروني أو كلمة المرور غير صحيحة."
MSG_EMAIL_TAKEN = "هذا البريد الإلكتروني مسجل مسبقاً. سجّل الدخول بدلاً من ذلك."
MSG_LOGIN_REQUIRED = "يرجى تسجيل الدخول أولاً."
MSG_CSRF = "انتهت صلاحية الصفحة. يرجى تحديثها ثم المحاولة مرة أخرى."
MSG_BAD_TOKEN = "الرابط غير صالح أو منتهي الصلاحية. يرجى طلب رابط جديد."

VERIFY_HOURS = 24
RESET_HOURS = 1

_hasher = PasswordHasher()
# verified against when the email is unknown, so response time doesn't reveal which emails exist
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


# ---- helpers -----------------------------------------------------------------------

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite returns naive datetimes


def normalize_email(email: str) -> str:
    return email.strip().lower()


def public_user(user: db.User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "language": user.language,
            "email_verified": user.email_verified, "is_admin": user.is_admin}


# ---- sessions ----------------------------------------------------------------------

def start_session(session: Session, response: Response, user: db.User) -> None:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    session.add(db.AuthSession(token_hash=token_hash(token), user_id=user.id,
                               expires_at=datetime.now(UTC) + timedelta(days=settings.session_days)))
    session.commit()
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_days * 86400, httponly=True,
                        samesite="lax", secure=settings.cookie_secure, path="/")


def end_session(session: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        row = session.get(db.AuthSession, token_hash(token))
        if row:
            session.delete(row)
            session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def optional_user(request: Request, session: Session = Depends(db.get_session)) -> db.User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = session.get(db.AuthSession, token_hash(token))
    if row is None:
        return None
    if _aware(row.expires_at) <= datetime.now(UTC):
        session.delete(row)
        session.commit()
        return None
    return session.get(db.User, row.user_id)


def current_user(user: db.User | None = Depends(optional_user)) -> db.User:
    if user is None:
        raise HTTPException(401, MSG_LOGIN_REQUIRED)
    return user


# ---- CSRF middleware ---------------------------------------------------------------

def csrf_exempt(path: str) -> bool:
    return not path.startswith("/api/")


async def csrf_middleware(request: Request, call_next):
    """Reject state-changing /api requests whose X-CSRF-Token header doesn't match the CSRF cookie,
    and hand out the CSRF cookie to browsers that don't have one yet."""
    cookie = request.cookies.get(CSRF_COOKIE)
    if request.method not in SAFE_METHODS and not csrf_exempt(request.url.path):
        header = request.headers.get(CSRF_HEADER, "")
        if not cookie or not hmac.compare_digest(cookie, header):
            return JSONResponse(status_code=403, content={"detail": tr(MSG_CSRF, request_lang(request))})
    response = await call_next(request)
    if not cookie:
        response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(32), max_age=365 * 86400, httponly=False,
                            samesite="lax", secure=get_settings().cookie_secure, path="/")
    return response


# ---- request bodies ----------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=100)
    language: Literal["ar", "en"] = "ar"

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = normalize_email(v)
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ForgotRequest(BaseModel):
    email: str = Field(max_length=254)


class ResetRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


# ---- email tokens --------------------------------------------------------------------

def issue_email_token(session: Session, user: db.User, purpose: str) -> str:
    """Create a one-time token (only its hash is stored); older unused tokens of the same purpose stop working."""
    now = datetime.now(UTC)
    for old in session.exec(select(db.EmailToken).where(db.EmailToken.user_id == user.id,
                                                         db.EmailToken.purpose == purpose,
                                                         db.EmailToken.used_at.is_(None))):
        old.used_at = now
        session.add(old)
    token = secrets.token_urlsafe(32)
    hours = VERIFY_HOURS if purpose == "verify" else RESET_HOURS
    session.add(db.EmailToken(token_hash=token_hash(token), user_id=user.id, purpose=purpose,
                              expires_at=now + timedelta(hours=hours)))
    session.commit()
    return token


def consume_email_token(session: Session, token: str, purpose: str) -> db.User:
    row = session.get(db.EmailToken, token_hash(token))
    if (row is None or row.purpose != purpose or row.used_at is not None
            or _aware(row.expires_at) <= datetime.now(UTC)):
        raise HTTPException(400, MSG_BAD_TOKEN)
    row.used_at = datetime.now(UTC)
    session.add(row)
    return session.get(db.User, row.user_id)


EMAILS = {
    ("verify", "ar"): ("أكّد بريدك الإلكتروني — مستشار",
                       "مرحباً {name}،\n\nلتأكيد بريدك الإلكتروني في «مستشار» افتح الرابط التالي:\n{link}\n\n"
                       "صلاحية الرابط {hours} ساعة. إذا لم تنشئ حساباً فتجاهل هذه الرسالة."),
    ("verify", "en"): ("Confirm your email — Mustashar",
                       "Hi {name},\n\nTo confirm your email for Mustashar, open this link:\n{link}\n\n"
                       "The link is valid for {hours} hours. If you didn't create an account, ignore this email."),
    ("reset", "ar"): ("إعادة تعيين كلمة المرور — مستشار",
                      "مرحباً {name}،\n\nلإعادة تعيين كلمة المرور افتح الرابط التالي:\n{link}\n\n"
                      "صلاحية الرابط ساعة واحدة. إذا لم تطلب ذلك فتجاهل هذه الرسالة، وكلمة مرورك الحالية تبقى كما هي."),
    ("reset", "en"): ("Reset your password — Mustashar",
                      "Hi {name},\n\nTo reset your password, open this link:\n{link}\n\n"
                      "The link is valid for 1 hour. If you didn't ask for this, ignore this email; "
                      "your current password stays the same."),
}


async def send_token_email(mailer: Mailer, user: db.User, purpose: str, token: str) -> None:
    lang = user.language if user.language in ("ar", "en") else "ar"
    subject, body = EMAILS[(purpose, lang)]
    route = "verify" if purpose == "verify" else "reset"
    link = f"{get_settings().public_url.rstrip('/')}/#/{route}?token={token}"
    name = user.name or ("" if lang == "ar" else "there")
    await mailer.send(Mail(to=user.email, subject=subject,
                           text=body.format(name=name, link=link, hours=VERIFY_HOURS)))


# ---- routes ------------------------------------------------------------------------

router = APIRouter(prefix="/api")


@router.post("/auth/register", status_code=201)
@auth_limit
async def register(request: Request, body: RegisterRequest, response: Response,
                   session: Session = Depends(db.get_session), mailer: Mailer = Depends(get_mailer)):
    if session.exec(select(db.User).where(db.User.email == body.email)).first():
        raise HTTPException(409, MSG_EMAIL_TAKEN)
    user = db.User(email=body.email, name=body.name.strip(), language=body.language,
                   password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    start_session(session, response, user)
    await send_token_email(mailer, user, "verify", issue_email_token(session, user, "verify"))
    return public_user(user)


@router.post("/auth/login")
@auth_limit
async def login(request: Request, body: LoginRequest, response: Response,
                session: Session = Depends(db.get_session)):
    user = session.exec(select(db.User).where(db.User.email == normalize_email(body.email))).first()
    if not verify_password(user.password_hash if user else None, body.password):
        raise HTTPException(401, MSG_BAD_LOGIN)
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        session.add(user)
    start_session(session, response, user)
    return public_user(user)


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, response: Response, session: Session = Depends(db.get_session)):
    end_session(session, request, response)


@router.get("/me")
async def me(user: db.User = Depends(current_user)):
    return public_user(user)


@router.post("/auth/verify/resend", status_code=202)
@auth_limit
async def resend_verification(request: Request, user: db.User = Depends(current_user),
                              session: Session = Depends(db.get_session), mailer: Mailer = Depends(get_mailer)):
    if not user.email_verified:
        await send_token_email(mailer, user, "verify", issue_email_token(session, user, "verify"))
    return {"sent": not user.email_verified}


@router.post("/auth/verify")
async def verify_email(body: TokenRequest, session: Session = Depends(db.get_session)):
    user = consume_email_token(session, body.token, "verify")
    user.email_verified = True
    session.add(user)
    session.commit()
    return public_user(user)


@router.post("/auth/password/forgot", status_code=202)
@auth_limit
async def forgot_password(request: Request, body: ForgotRequest, session: Session = Depends(db.get_session),
                          mailer: Mailer = Depends(get_mailer)):
    """Always answers the same way, so it can't be used to find out which emails are registered."""
    user = session.exec(select(db.User).where(db.User.email == normalize_email(body.email))).first()
    if user is not None:
        await send_token_email(mailer, user, "reset", issue_email_token(session, user, "reset"))
    return {"sent": True}


@router.post("/auth/password/reset")
@auth_limit
async def reset_password(request: Request, body: ResetRequest, response: Response,
                         session: Session = Depends(db.get_session)):
    user = consume_email_token(session, body.token, "reset")
    user.password_hash = hash_password(body.password)
    user.email_verified = True  # they proved they can read this inbox
    session.add(user)
    for old in session.exec(select(db.AuthSession).where(db.AuthSession.user_id == user.id)):
        session.delete(old)  # log out everywhere else
    session.commit()
    start_session(session, response, user)
    return public_user(user)
