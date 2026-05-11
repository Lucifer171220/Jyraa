from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app import crud
from app.models import Issue, IssueStatus, User

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/issues/status", response_model=dict)
def bulk_update_status(
    operation: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue_ids = operation.get("issue_ids", [])
    status_name = operation.get("status")

    if not issue_ids or not status_name:
        raise HTTPException(status_code=400, detail="issue_ids and status are required")

    status_obj = db.query(IssueStatus).filter(IssueStatus.name == status_name).first()
    if not status_obj:
        raise HTTPException(status_code=404, detail="Status not found")

    updated_count = 0
    for issue_id in issue_ids:
        issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
        if issue:
            issue.status_id = status_obj.status_id
            updated_count += 1

    db.commit()
    return {"updated_count": updated_count, "message": f"Updated {updated_count} issues"}


@router.post("/issues/assignee", response_model=dict)
def bulk_update_assignee(
    operation: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue_ids = operation.get("issue_ids", [])
    assignee_username = operation.get("assignee_username")

    if not issue_ids:
        raise HTTPException(status_code=400, detail="issue_ids is required")

    assignee = None
    if assignee_username:
        assignee = crud.user.get_by_username(db, username=assignee_username)
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")

    updated_count = 0
    for issue_id in issue_ids:
        issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
        if issue:
            issue.assignee_user_id = assignee.user_id if assignee else None
            updated_count += 1

    db.commit()
    return {"updated_count": updated_count, "message": f"Updated {updated_count} issues"}


@router.post("/issues/delete", response_model=dict)
def bulk_delete_issues(
    operation: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue_ids = operation.get("issue_ids", [])

    if not issue_ids:
        raise HTTPException(status_code=400, detail="issue_ids is required")

    deleted_count = 0
    for issue_id in issue_ids:
        issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
        if issue:
            db.delete(issue)
            deleted_count += 1

    db.commit()
    return {"deleted_count": deleted_count, "message": f"Deleted {deleted_count} issues"}


@router.post("/issues/labels", response_model=dict)
def bulk_add_labels(
    operation: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue_ids = operation.get("issue_ids", [])
    labels = operation.get("labels", [])

    if not issue_ids or not labels:
        raise HTTPException(status_code=400, detail="issue_ids and labels are required")

    updated_count = 0
    for issue_id in issue_ids:
        issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
        if issue:
            for label_name in labels:
                label = crud.label.get_or_create(db, name=label_name)
                if label not in issue.labels:
                    issue.labels.append(label)
            updated_count += 1

    db.commit()
    return {"updated_count": updated_count, "message": f"Updated {updated_count} issues"}
