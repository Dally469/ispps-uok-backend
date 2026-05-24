"""Outbound email via SMTP.

Uses stdlib smtplib in a worker thread (`asyncio.to_thread`) so the
event loop is never blocked. Failures are logged and swallowed — email
delivery is best-effort and must never break a request.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import Settings, get_settings


log = logging.getLogger("ispps.email")


def _build_msg(
    settings: Settings,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_addr = settings.smtp_from_email or settings.smtp_username
    msg["From"] = f"{settings.smtp_from_name} <{from_addr}>"
    msg["To"] = to
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    return msg


def _send_sync(
    settings: Settings,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None,
) -> None:
    msg = _build_msg(settings, to, subject, body_text, body_html)
    # Gmail App Passwords are shown to users with spaces ("abcd efgh ...");
    # the SMTP auth requires the spaces removed.
    password = settings.smtp_password.replace(" ", "")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.ehlo()
        if settings.smtp_use_tls:
            server.starttls()
            server.ehlo()
        server.login(settings.smtp_username, password)
        server.send_message(msg)


async def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> bool:
    """Send a single email. Returns True on success, False if SMTP is
    disabled or delivery failed. Never raises."""
    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password:
        log.warning("SMTP not configured (set SMTP_USERNAME + SMTP_PASSWORD) — skipping email to %s", to)
        return False
    try:
        await asyncio.to_thread(_send_sync, settings, to, subject, body_text, body_html)
        log.info("Sent email to %s · %s", to, subject)
        return True
    except Exception as exc:
        log.exception("Failed to send email to %s: %s", to, exc)
        return False
