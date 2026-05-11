import smtplib
from email.message import EmailMessage

from app.config import settings


def email_is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_port and settings.smtp_sender_email and settings.smtp_username and settings.smtp_password)


def send_email(subject: str, body: str, recipients: list[str]) -> dict:
    if not recipients:
        return {"sent": False, "reason": "no_recipients"}
    if not email_is_configured():
        return {"sent": False, "reason": "smtp_not_configured"}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_sender_email
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    return {"sent": True, "recipients": recipients}


def send_issue_assignment_email(*, recipient_email: str, recipient_name: str, issue_key: str, summary: str, project_name: str) -> dict:
    subject = f"[ZYRAA] Issue Assigned: {issue_key}"
    body = (
        f"Hello {recipient_name},\n\n"
        f"You have been assigned a new issue in ZYRAA.\n\n"
        f"Project: {project_name}\n"
        f"Issue: {issue_key}\n"
        f"Summary: {summary}\n\n"
        f"Please sign in to ZYRAA to review and begin work.\n\n"
        f"Regards,\nZYRAA Automation"
    )
    return send_email(subject, body, [recipient_email])
