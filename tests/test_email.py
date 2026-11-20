from __future__ import annotations

import pytest

from ews.email_delivery import EmailDeliveryError, send_digest


def test_send_digest_requires_smtp_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    with pytest.raises(EmailDeliveryError, match="SMTP_HOST"):
        send_digest(subject="HF EWS", body="hello")


def test_send_digest_uses_default_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
            captured["host"] = host
            captured["port"] = port

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def ehlo(self) -> None:
            return None

        def starttls(self) -> None:
            captured["starttls"] = True

        def login(self, username: str, password: str) -> None:
            captured["username"] = username
            captured["password"] = password

        def send_message(self, message: object) -> None:
            captured["message"] = message

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "ews@navi.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.delenv("EWS_EMAIL_TO", raising=False)
    monkeypatch.delenv("EWS_EMAIL_FROM", raising=False)
    monkeypatch.setattr("ews.email_delivery.smtplib.SMTP", FakeSMTP)

    recipient = send_digest(subject="HF EWS — weekly digest", body="flags")
    message = captured["message"]
    assert recipient == "samvid.uday@navi.com"
    assert captured["host"] == "smtp.example.com"
    assert captured["starttls"] is True
    assert message["To"] == "samvid.uday@navi.com"
    assert message["From"] == "ews@navi.com"
    assert message["Subject"] == "HF EWS — weekly digest"
