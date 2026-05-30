from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, User
from app.services.permission_service import check_project_access, has_admin_permissions, has_user_permission


def require_project_access(db: Session, current_user: User, project_id: int) -> None:
    if has_admin_permissions(current_user) or check_project_access(db, current_user.user_id, project_id):
        return
    raise HTTPException(status_code=403, detail="Project access required")


def require_project_permission(db: Session, current_user: User, project_id: int, permission_key: str) -> None:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if has_admin_permissions(current_user) or project.lead_user_id == current_user.user_id:
        return
    if has_user_permission(db, current_user.user_id, permission_key, project_id=project_id):
        return
    raise HTTPException(status_code=403, detail=f"Missing permission: {permission_key}")


def require_action_owner(action, current_user: User) -> None:
    if action.user_id == current_user.user_id or has_admin_permissions(current_user):
        return
    raise HTTPException(status_code=403, detail="Action does not belong to current user")
