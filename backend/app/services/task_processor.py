import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import BackgroundTask, EmailQueue
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


def process_pending_tasks():
    db: Session = SessionLocal()
    try:
        pending_tasks = db.query(BackgroundTask).filter(
            BackgroundTask.status == "pending"
        ).order_by(BackgroundTask.priority.desc(), BackgroundTask.created_at).limit(10).all()

        for task in pending_tasks:
            task.status = "processing"
            task.started_at = datetime.utcnow()
            db.commit()

            try:
                if task.task_type == "email":
                    result = process_email_task(db, task)
                elif task.task_type == "notification":
                    result = process_notification_task(db, task)
                else:
                    result = {"error": f"Unknown task type: {task.task_type}"}

                task.status = "completed"
                task.result = json.dumps(result)
                task.completed_at = datetime.utcnow()
                logger.info(f"Task {task.task_id} completed successfully")

            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                logger.error(f"Task {task.task_id} failed: {e}")

            db.commit()

    finally:
        db.close()


def process_email_task(db: Session, task: BackgroundTask) -> dict:
    payload = json.loads(task.payload) if task.payload else {}
    email_id = payload.get("email_id")

    if not email_id:
        raise ValueError("No email_id in task payload")

    email = db.query(EmailQueue).filter(EmailQueue.email_id == email_id).first()
    if not email:
        raise ValueError(f"Email {email_id} not found")

    result = send_email(
        subject=email.subject,
        body=email.body_text or "",
        recipients=[email.recipient_email]
    )

    if result.get("sent"):
        email.status = "sent"
        email.sent_at = datetime.utcnow()
    else:
        email.status = "failed"
        email.error_message = result.get("reason", "Unknown error")

    db.commit()
    return result


def process_notification_task(db: Session, task: BackgroundTask) -> dict:
    from app.models import Notification, User

    payload = json.loads(task.payload) if task.payload else {}
    user_id = payload.get("user_id")
    notification_type = payload.get("type")
    title = payload.get("title")
    message = payload.get("message")
    issue_id = payload.get("issue_id")

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_issue_id=issue_id
    )
    db.add(notification)
    db.commit()

    return {"notification_id": notification.notification_id}


def enqueue_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: str = None,
    recipient_name: str = None,
    template_name: str = None,
    template_data: dict = None
) -> int:
    db: Session = SessionLocal()
    try:
        email = EmailQueue(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            template_name=template_name,
            template_data=json.dumps(template_data) if template_data else None
        )
        db.add(email)
        db.commit()
        db.refresh(email)

        task = BackgroundTask(
            task_type="email",
            priority=0,
            payload=json.dumps({"email_id": email.email_id})
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return task.task_id
    finally:
        db.close()


def enqueue_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    issue_id: int = None
) -> int:
    db: Session = SessionLocal()
    try:
        task = BackgroundTask(
            task_type="notification",
            priority=1,
            payload=json.dumps({
                "user_id": user_id,
                "type": notification_type,
                "title": title,
                "message": message,
                "issue_id": issue_id
            })
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.task_id
    finally:
        db.close()