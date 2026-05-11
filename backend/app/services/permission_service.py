from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Project, ProjectRole, Permission


def has_permission(permission_key: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, current_user: User = None, db: Session = None, **kwargs):
            if not current_user:
                raise HTTPException(status_code=401, detail="User not authenticated")

            if has_user_permission(db, current_user.user_id, permission_key):
                return func(*args, **kwargs)
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission_key}")
        return wrapper
    return decorator


def has_user_permission(db: Session, user_id: int, permission_key: str, project_id: int = None) -> bool:
    permissions = get_user_permissions(db, user_id, project_id)
    return permission_key in permissions


def get_user_permissions(db: Session, user_id: int, project_id: int = None) -> List[str]:
    permissions = []

    if project_id:
        project_roles = db.query(ProjectRole).filter(
            ProjectRole.user_id == user_id,
            ProjectRole.project_id == project_id
        ).all()

        for role in project_roles:
            perm_list = [p.permission_key for p in role.permissions]
            permissions.extend(perm_list)

    is_admin = db.query(User).filter(User.user_id == user_id).first()

    if is_admin and has_admin_permissions(is_admin):
        global_perms = db.query(Permission).all()
        permissions.extend([p.permission_key for p in global_perms])

    return list(set(permissions))


def has_admin_permissions(user: User) -> bool:
    return user.user_id == 1


def check_project_access(db: Session, user_id: int, project_id: int) -> bool:
    project_roles = db.query(ProjectRole).filter(
        ProjectRole.user_id == user_id,
        ProjectRole.project_id == project_id
    ).count()

    if project_roles > 0:
        return True

    project = db.query(Project).filter(Project.project_id == project_id).first()
    if project and project.lead_user_id == user_id:
        return True

    return False


def get_user_project_role(db: Session, user_id: int, project_id: int) -> Optional[str]:
    role = db.query(ProjectRole).filter(
        ProjectRole.user_id == user_id,
        ProjectRole.project_id == project_id
    ).first()

    return role.role_type if role else None


def assign_project_role(db: Session, user_id: int, project_id: int, role_type: str) -> ProjectRole:
    existing = db.query(ProjectRole).filter(
        ProjectRole.user_id == user_id,
        ProjectRole.project_id == project_id
    ).first()

    if existing:
        existing.role_type = role_type
        db.commit()
        db.refresh(existing)
        return existing

    role = ProjectRole(
        user_id=user_id,
        project_id=project_id,
        role_type=role_type
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def add_role_permission(db: Session, role_id: int, permission_key: str) -> Permission:
    permission = db.query(Permission).filter(
        Permission.permission_key == permission_key
    ).first()

    if not permission:
        permission = Permission(
            permission_key=permission_key,
            description=f"Permission: {permission_key}"
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

    role = db.query(ProjectRole).filter(ProjectRole.role_id == role_id).first()
    if role and permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()

    return permission