from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def serialize_notification(notification: Notification) -> dict:
    return {
        "notification_id": notification.notification_id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "related_issue_id": notification.related_issue_id,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


@router.get("/", response_model=List[dict])
def list_notifications(
    unread_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = crud.notification.get_by_user(
        db,
        user_id=current_user.user_id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )
    return [serialize_notification(notification) for notification in notifications]


@router.put("/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return serialize_notification(notification)


@router.put("/read-all", response_model=dict)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = crud.notification.mark_all_as_read(db, user_id=current_user.user_id)
    return {"updated_count": count}
