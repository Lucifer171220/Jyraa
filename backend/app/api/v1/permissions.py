from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Permission, Project, ProjectRole, User
from app.services.permission_service import add_role_permission, assign_project_role, check_project_access, has_admin_permissions

router = APIRouter(prefix="/permissions", tags=["permissions"])


def serialize_role(role: ProjectRole) -> dict:
    return {
        "role_id": role.role_id,
        "project_id": role.project_id,
        "user_id": role.user_id,
        "username": role.user.username if role.user else "",
        "display_name": role.user.display_name if role.user else "",
        "role_type": role.role_type,
        "permissions": [permission.permission_key for permission in role.permissions],
        "created_at": role.created_at,
    }


def ensure_project_admin(db: Session, current_user: User, project_id: int) -> None:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if has_admin_permissions(current_user) or project.lead_user_id == current_user.user_id:
        return
    role = (
        db.query(ProjectRole)
        .filter(ProjectRole.project_id == project_id, ProjectRole.user_id == current_user.user_id)
        .first()
    )
    if not role or role.role_type != "admin":
        raise HTTPException(status_code=403, detail="Project admin permission required")


@router.get("/", response_model=List[dict])
def list_permissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [
        {"permission_id": item.permission_id, "permission_key": item.permission_key, "description": item.description}
        for item in db.query(Permission).order_by(Permission.permission_key.asc()).all()
    ]


@router.get("/projects/{project_id}/roles", response_model=List[dict])
def list_project_roles(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_project_access(db, current_user.user_id, project_id) and not has_admin_permissions(current_user):
        raise HTTPException(status_code=403, detail="Project access required")
    roles = db.query(ProjectRole).filter(ProjectRole.project_id == project_id).all()
    return [serialize_role(role) for role in roles]


@router.post("/projects/{project_id}/roles", response_model=dict, status_code=status.HTTP_201_CREATED)
def upsert_project_role(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_project_admin(db, current_user, project_id)
    user_id = payload.get("user_id")
    role_type = payload.get("role_type", "member")
    permission_keys = payload.get("permissions", [])
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = assign_project_role(db, user_id=user.user_id, project_id=project_id, role_type=role_type)
    role.permissions.clear()
    db.commit()
    for permission_key in permission_keys:
        add_role_permission(db, role.role_id, permission_key)
    db.refresh(role)
    return serialize_role(role)
