import json
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.models import AuditLog


async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    return response


def log_audit_event(
    db: Session,
    action_type: str,
    entity_type: str,
    entity_id: Optional[int],
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    audit = AuditLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    return audit