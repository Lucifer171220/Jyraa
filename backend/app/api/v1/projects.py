from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Issue, Project, User

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_project = crud.project.get_by_key(db, project_key=project.project_key)
    if db_project:
        raise HTTPException(status_code=400, detail="Project key already exists")

    db_project = Project(
        project_key=project.project_key,
        name=project.name,
        description=project.description,
        lead_user_id=current_user.user_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    from app.services.permission_service import add_role_permission, assign_project_role

    role = assign_project_role(db, user_id=current_user.user_id, project_id=db_project.project_id, role_type="admin")
    for permission_key in (
        "project.admin",
        "project.read",
        "issue.create",
        "issue.update",
        "issue.delete",
        "sprint.manage",
        "roadmap.manage",
        "webhook.manage",
        "template.manage",
        "dashboard.manage",
    ):
        add_role_permission(db, role.role_id, permission_key)
    return db_project


@router.get("/", response_model=List[schemas.ProjectResponse])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.project.get_multi(db, skip=skip, limit=limit)


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def read_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = crud.project.get(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project


@router.put("/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: int,
    project_update: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_project = crud.project.get(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.project.update(db, db_obj=db_project, obj_in=project_update)


@router.get("/{project_id}/issues", response_model=List[schemas.IssueResponse])
def read_project_issues(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    assignee_id: int | None = None,
    status_id: int | None = None,
    priority_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_project = crud.project.get(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    from app.api.v1.issues import serialize_issue

    issues = crud.issue.get_by_project(
        db,
        project_id=project_id,
        skip=skip,
        limit=limit,
        assignee_id=assignee_id,
        status_id=status_id,
        priority_id=priority_id,
    )
    return [serialize_issue(issue) for issue in issues]


@router.get("/{project_id}/stats")
def read_project_stats(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = crud.project.get(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    issues = db.query(Issue).filter(Issue.project_id == project_id).all()
    total_issues = len(issues)
    completed_issues = sum(1 for issue in issues if issue.status and issue.status.is_final_status)
    return {
        "total_issues": total_issues,
        "completed_issues": completed_issues,
        "open_issues": total_issues - completed_issues,
        "total_estimate": float(sum(float(issue.original_estimate or 0) for issue in issues)),
        "total_time_spent": float(sum(float(issue.time_spent or 0) for issue in issues)),
    }
