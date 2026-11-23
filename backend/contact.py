"""Contact us: save the message and, if CONTACT_EMAIL is set, email it to the team."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from backend import db
from backend.auth import EMAIL_RE, normalize_email, optional_user
from backend.config import get_settings
from backend.mailer import Mail, Mailer, get_mailer
from backend.ratelimit import auth_limit

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254)
    subject: str = Field(default="", max_length=150)
    message: str = Field(min_length=10, max_length=4000)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = normalize_email(v)
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


@router.post("/contact", status_code=201)
@auth_limit
async def contact(request: Request, body: ContactRequest, session: Session = Depends(db.get_session),
                  user: db.User | None = Depends(optional_user), mailer: Mailer = Depends(get_mailer)):
    msg = db.ContactMessage(name=body.name.strip(), email=body.email, subject=body.subject.strip(),
                            message=body.message.strip(), user_id=user.id if user else None)
    session.add(msg)
    session.commit()
    to = get_settings().contact_email
    if to:
        try:
            await mailer.send(Mail(to=to, subject=f"[Mustashar] {msg.subject or 'Contact form'} — {msg.name}",
                                   text=f"From: {msg.name} <{msg.email}>\n\n{msg.message}"))
        except Exception:  # the message is saved; a mail failure shouldn't lose it or fail the request
            log.exception("could not email contact message %s", msg.id)
    return {"ok": True}
