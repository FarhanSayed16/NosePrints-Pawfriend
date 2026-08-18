"""Optional SMTP notify — used after staff confirms a match."""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def notify_owner_confirmed_match(owner_email: str | None, dog_name: str | None) -> bool:
    """
    Email the owner that PawFriend staff confirmed a possible reunion.
    Returns False if SMTP is not configured or send fails — never raises.
    """
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured — skipping owner email")
        return False
    if not owner_email:
        logger.info("Owner has no email — skipping notify")
        return False

    name = dog_name or "your dog"
    sender = settings.SMTP_FROM or settings.SMTP_USER or "noreply@pawfriend.in"
    msg = EmailMessage()
    msg["Subject"] = "PawFriend: a staff member confirmed a possible match"
    msg["From"] = sender
    msg["To"] = owner_email
    msg.set_content(
        f"Hello,\n\n"
        f"PawFriend staff confirmed a possible match for {name}. "
        f"Please contact PawFriend to arrange reunion. "
        f"Do not reply to this automated message.\n\n"
        f"— PawFriend.in\n"
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Owner match email sent to %s", owner_email)
        return True
    except Exception as e:
        logger.warning("Owner match email failed: %s", e)
        return False
