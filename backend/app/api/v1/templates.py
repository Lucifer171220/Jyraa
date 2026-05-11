from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import IssueTemplate, Project, User, IssueType, IssuePriority

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue_type = db.query(IssueType).filter(IssueType.issue_type_id == template_data["issue_type_id"]).first()
    if not issue_type:
        raise HTTPException(status_code=404, detail="Issue type not found")

    template = IssueTemplate(
        project_id=template_data.get("project_id"),
        name=template_data["name"],
        issue_type_id=template_data["issue_type_id"],
        summary_template=template_data.get("summary_template"),
        description_template=template_data.get("description_template"),
        priority_id=template_data.get("priority_id"),
        default_assignee=template_data.get("default_assignee"),
        is_global=template_data.get("is_global", False),
        created_by=current_user.user_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "template_id": template.template_id,
        "name": template.name,
        "issue_type": issue_type.name,
        "summary_template": template.summary_template,
        "description_template": template.description_template,
    }


@router.get("/", response_model=List[dict])
def get_templates(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(IssueTemplate)
    if project_id:
        query = query.filter(IssueTemplate.project_id == project_id)
    else:
        query = query.filter(IssueTemplate.is_global == True)

    templates = query.all()
    return [
        {
            "template_id": t.template_id,
            "name": t.name,
            "issue_type_id": t.issue_type_id,
            "summary_template": t.summary_template,
            "description_template": t.description_template,
        }
        for t in templates
    ]


@router.get("/{template_id}", response_model=dict)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(IssueTemplate).filter(IssueTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_id": template.template_id,
        "name": template.name,
        "issue_type_id": template.issue_type_id,
        "summary_template": template.summary_template,
        "description_template": template.description_template,
        "priority_id": template.priority_id,
        "default_assignee": template.default_assignee,
        "is_global": template.is_global,
    }


@router.put("/{template_id}", response_model=dict)
def update_template(
    template_id: int,
    template_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(IssueTemplate).filter(IssueTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.name = template_data.get("name", template.name)
    template.summary_template = template_data.get("summary_template", template.summary_template)
    template.description_template = template_data.get("description_template", template.description_template)
    template.priority_id = template_data.get("priority_id", template.priority_id)
    template.default_assignee = template_data.get("default_assignee", template.default_assignee)
    db.commit()
    db.refresh(template)
    return {
        "template_id": template.template_id,
        "name": template.name,
        "issue_type_id": template.issue_type_id,
        "summary_template": template.summary_template,
        "description_template": template.description_template,
    }


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(IssueTemplate).filter(IssueTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return None