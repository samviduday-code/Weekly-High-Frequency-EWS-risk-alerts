"""SMTP delivery for the weekly HF EWS digest."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from ews.config import digest_recipient


class EmailDeliveryError(RuntimeError):
    pass


def _env_flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() not in {"0", "false", "no"}


def send_digest(*, subject: str, body: str, to_addr: str | None = None) -> str:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        raise EmailDeliveryError(
            "SMTP_HOST is required for --post-email "
            f"(digest recipient is {digest_recipient()})"
        )
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as exc:
        raise EmailDeliveryError("SMTP_PORT must be an integer") from exc

    username = (
        os.environ.get("SMTP_USERNAME") or os.environ.get("SMTP_USER") or ""
    ).strip()
    password = os.environ.get("SMTP_PASSWORD") or ""
    from_addr = (
        os.environ.get("EWS_EMAIL_FROM") or os.environ.get("SMTP_FROM") or username
    ).strip()
    if not from_addr:
        raise EmailDeliveryError(
            "EWS_EMAIL_FROM or SMTP_USERNAME is required for --post-email"
        )
    recipient = (to_addr or digest_recipient()).strip()
    if not recipient:
        raise EmailDeliveryError("EWS_EMAIL_TO is empty")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = recipient
    message.set_content(body)

    use_ssl = _env_flag("SMTP_SSL", "0") or port == 465
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.ehlo()
                if _env_flag("SMTP_STARTTLS", "1"):
                    smtp.starttls()
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(f"email delivery failed: {exc}") from exc
    return recipient
