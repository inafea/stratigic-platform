import pytest
from sqlmodel import Session, select

from backend import contact, db
from backend.mailer import ConsoleMailer, get_mailer
from backend.main import app

MSG = {"name": "Sara", "email": "Sara@Example.com", "subject": "Partnership", "message": "We would like to talk."}


@pytest.fixture
def mailer():
    m = ConsoleMailer()
    app.dependency_overrides[get_mailer] = lambda: m
    return m


def test_contact_saved_without_login(anon_client, memory_db, mailer):
    assert anon_client.post("/api/contact", json=MSG).status_code == 201
    with Session(memory_db) as s:
        m = s.exec(select(db.ContactMessage)).one()
    assert (m.email, m.subject, m.user_id) == ("sara@example.com", "Partnership", None)
    assert mailer.outbox == []  # no CONTACT_EMAIL configured


def test_contact_links_logged_in_user_and_emails_team(client, memory_db, mailer, monkeypatch):
    settings = contact.get_settings().model_copy(update={"contact_email": "team@mustashar.test"})
    monkeypatch.setattr(contact, "get_settings", lambda: settings)
    client.post("/api/contact", json=MSG)
    with Session(memory_db) as s:
        assert s.exec(select(db.ContactMessage)).one().user_id is not None
    (mail,) = mailer.outbox
    assert mail.to == "team@mustashar.test" and "Sara" in mail.subject and "We would like" in mail.text


@pytest.mark.parametrize("bad", [{"email": "nope"}, {"message": "short"}, {"name": ""}])
def test_contact_validation(anon_client, mailer, bad):
    assert anon_client.post("/api/contact", json={**MSG, **bad}).status_code == 422


def test_contact_needs_csrf(anon_client, mailer):
    del anon_client.headers["X-CSRF-Token"]
    assert anon_client.post("/api/contact", json=MSG).status_code == 403
