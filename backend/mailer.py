"""Outgoing email. `MAIL_BACKEND=console` (default) logs messages instead of sending them;
`MAIL_BACKEND=smtp` sends through the SMTP_* settings (works with Resend, SES, Zoho, Gmail...)."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

from backend.config import Settings, get_settings

log = logging.getLogger(__name__)


@dataclass
class Mail:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    async def send(self, mail: Mail) -> None: ...


class ConsoleMailer:
    """Development/tests: keeps sent mail in `outbox` and writes it to the log."""

    def __init__(self) -> None:
        self.outbox: list[Mail] = []

    async def send(self, mail: Mail) -> None:
        self.outbox.append(mail)
        log.info("EMAIL to %s | %s\n%s", mail.to, mail.subject, mail.text)


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def _send_sync(self, mail: Mail) -> None:
        msg = EmailMessage()
        msg["From"] = self.s.mail_from
        msg["To"] = mail.to
        msg["Subject"] = mail.subject
        msg.set_content(mail.text)
        if self.s.smtp_port == 465:
            server = smtplib.SMTP_SSL(self.s.smtp_host, self.s.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=20)
            server.starttls()
        with server:
            if self.s.smtp_user:
                server.login(self.s.smtp_user, self.s.smtp_password)
            server.send_message(msg)

    async def send(self, mail: Mail) -> None:
        await asyncio.to_thread(self._send_sync, mail)


@lru_cache
def get_mailer() -> Mailer:
    settings = get_settings()
    return SmtpMailer(settings) if settings.mail_backend == "smtp" else ConsoleMailer()
