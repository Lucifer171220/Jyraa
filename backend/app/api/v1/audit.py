import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


def _loads(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


@router.get("/", response_model=List[dict])
def list_audit_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)

    events = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "audit_id": event.audit_id,
            "user_id": event.user_id,
            "username": event.user.username if event.user else "",
            "action_type": event.action_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "old_values": _loads(event.old_values),
            "new_values": _loads(event.new_values),
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": event.created_at,
        }
        for event in events
    ]
