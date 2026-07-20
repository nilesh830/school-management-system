"""
Outbound email helper for bulk-registration credential delivery.

Two responsibilities:

1. ``resolve_smtp_settings`` — decide *how* to send for the current school:
   the school's own SMTP config (from the master ``school_email_configs`` table,
   so mail is genuinely FROM the school's address) when present, otherwise the
   global ``MAIL_*`` app config as a fallback. MUST be called inside an app /
   request context (it reads the DB and current_app.config).

2. ``send_emails_async`` — dispatch a batch of already-composed messages on a
   daemon thread using raw ``smtplib`` (NOT Flask-Mail, which needs an app
   context the thread won't have). Settings and messages are resolved up front
   in the request, so the thread only does plain socket I/O. Sending 30–100
   emails inline would risk an HTTP timeout; the endpoint returns immediately
   and the thread reports per-message success/failure to the logger.

If ``MAIL_SUPPRESS_SEND`` is true (dev/testing), messages are logged, not sent.
"""

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.utils import formataddr

from flask import current_app

logger = logging.getLogger(__name__)


def resolve_smtp_settings(school_slug: str | None) -> dict | None:
    """Return a plain dict of SMTP settings for this school, or None if email
    is not configured at all (neither per-school nor global).

    Keys: host, port, use_tls, username, password, from_email, from_name,
          suppress (bool).
    Safe to serialise / hand to a thread — contains no ORM objects.
    """
    cfg = current_app.config
    suppress = bool(cfg.get("MAIL_SUPPRESS_SEND", True))

    # 1) Per-school SMTP (preferred — sends FROM the school's own address).
    if school_slug:
        try:
            from app.models.master.school_email_config import SchoolEmailConfig
            from app.models.master.school import School

            row = SchoolEmailConfig.query.filter_by(
                school_slug=school_slug, is_active=True
            ).first()
            if row:
                school = School.query.filter_by(slug=school_slug).first()
                return {
                    "host": row.smtp_host,
                    "port": row.smtp_port,
                    "use_tls": row.smtp_use_tls,
                    "username": row.smtp_username,
                    "password": row.smtp_password,
                    "from_email": row.from_email,
                    "from_name": row.from_name or (school.name if school else None),
                    "suppress": suppress,
                }
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not load per-school SMTP config for %s: %s", school_slug, exc)

    # 2) Global fallback (MAIL_* config). Requires a host + sender to be usable.
    host = cfg.get("MAIL_SERVER")
    from_email = cfg.get("MAIL_DEFAULT_SENDER")
    if not host or not from_email:
        return None
    return {
        "host": host,
        "port": cfg.get("MAIL_PORT", 587),
        "use_tls": cfg.get("MAIL_USE_TLS", True),
        "username": cfg.get("MAIL_USERNAME"),
        "password": cfg.get("MAIL_PASSWORD"),
        "from_email": from_email,
        "from_name": None,
        "suppress": suppress,
    }


def _build_mime(settings: dict, to_email: str, subject: str, body: str) -> MIMEText:
    msg = MIMEText(body, "plain", "utf-8")
    from_name = settings.get("from_name")
    from_email = settings["from_email"]
    msg["From"] = formataddr((from_name, from_email)) if from_name else from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    return msg


def _send_batch(settings: dict, messages: list) -> None:
    """Blocking send of all messages over a single SMTP connection.

    Runs on a background thread. Never raises — logs each failure so a single
    bad recipient never aborts the batch.
    """
    if settings.get("suppress"):
        for m in messages:
            logger.info(
                "MAIL SUPPRESSED (dev) → to=%s subject=%s\n%s",
                m["to"], m["subject"], m["body"],
            )
        return

    sent = failed = 0
    server = None
    try:
        server = smtplib.SMTP(settings["host"], int(settings["port"]), timeout=30)
        if settings.get("use_tls"):
            server.starttls()
        if settings.get("username") and settings.get("password"):
            server.login(settings["username"], settings["password"])

        for m in messages:
            try:
                mime = _build_mime(settings, m["to"], m["subject"], m["body"])
                server.sendmail(settings["from_email"], [m["to"]], mime.as_string())
                sent += 1
            except Exception as exc:
                failed += 1
                logger.error("Credential email to %s failed: %s", m["to"], exc)
    except Exception as exc:
        failed = len(messages) - sent
        logger.error("SMTP connection/setup failed (%s:%s): %s", settings.get("host"), settings.get("port"), exc)
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
    logger.info("Credential email batch complete: %d sent, %d failed", sent, failed)


def send_emails_async(settings: dict, messages: list) -> int:
    """Fire-and-forget: send ``messages`` on a daemon thread.

    ``messages`` is a list of {"to", "subject", "body"} dicts.
    Returns the count queued (len(messages)); actual delivery is asynchronous
    and reported to the logger by the worker thread.
    """
    if not settings or not messages:
        return 0
    thread = threading.Thread(
        target=_send_batch,
        args=(settings, list(messages)),
        name="bulk-credential-email",
        daemon=True,
    )
    thread.start()
    return len(messages)
