"""Optional SMTP notify — owner match emails + staff invite/reset."""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST)


def send_email(*, to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns False if SMTP unset or send fails."""
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured — skipping email to %s", to)
        return False
    if not to:
        return False

    sender = settings.SMTP_FROM or settings.SMTP_USER or "noreply@pawfriend.in"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Email sent to %s (%s)", to, subject)
        return True
    except Exception as e:
        logger.warning("Email failed to %s: %s", to, e)
        return False


def notify_owner_confirmed_match(owner_email: str | None, dog_name: str | None) -> bool:
    """
    Email the owner that PawFriend staff confirmed a possible reunion.
    Returns False if SMTP is not configured or send fails — never raises.
    """
    name = dog_name or "your dog"
    return send_email(
        to=owner_email or "",
        subject="PawFriend: a staff member confirmed a possible match",
        body=(
            f"Hello,\n\n"
            f"PawFriend staff confirmed a possible match for {name}. "
            f"Please contact PawFriend to arrange reunion. "
            f"Do not reply to this automated message.\n\n"
            f"— PawFriend.in\n"
        ),
    )


def notify_staff_invite(email: str, accept_url: str, role: str) -> bool:
    return send_email(
        to=email,
        subject="PawFriend staff invite",
        body=(
            f"You have been invited to PawFriend staff as {role}.\n\n"
            f"Open this link to set your password (expires soon):\n{accept_url}\n\n"
            f"If you did not expect this, ignore this email.\n\n— PawFriend.in\n"
        ),
    )


def notify_staff_password_reset(email: str, reset_url: str) -> bool:
    return send_email(
        to=email,
        subject="PawFriend staff password reset",
        body=(
            f"A password reset was requested for your PawFriend staff account.\n\n"
            f"Open this link to choose a new password (expires soon):\n{reset_url}\n\n"
            f"If you did not request this, ignore this email.\n\n— PawFriend.in\n"
        ),
    )
