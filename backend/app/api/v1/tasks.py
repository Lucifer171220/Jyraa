import json
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import BackgroundTask, EmailQueue, User
from app.services.task_processor import process_pending_tasks

router = APIRouter(prefix="/tasks", tags=["background tasks"])


def serialize_task(task: BackgroundTask) -> dict:
    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "payload": json.loads(task.payload) if task.payload else None,
        "result": json.loads(task.result) if task.result else None,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


@router.get("/", response_model=List[dict])
def list_tasks(
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(BackgroundTask)
    if status:
        query = query.filter(BackgroundTask.status == status)
    return [
        serialize_task(task)
        for task in query.order_by(BackgroundTask.created_at.desc()).offset(skip).limit(limit).all()
    ]


@router.post("/process", response_model=dict)
def process_tasks(current_user: User = Depends(get_current_user)):
    process_pending_tasks()
    return {"message": "Processed pending background tasks"}


@router.get("/emails", response_model=List[dict])
def list_email_queue(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(EmailQueue)
    if status:
        query = query.filter(EmailQueue.status == status)
    emails = query.order_by(EmailQueue.created_at.desc()).limit(100).all()
    return [
        {
            "email_id": email.email_id,
            "recipient_email": email.recipient_email,
            "subject": email.subject,
            "template_name": email.template_name,
            "status": email.status,
            "error_message": email.error_message,
            "created_at": email.created_at,
            "sent_at": email.sent_at,
        }
        for email in emails
    ]
