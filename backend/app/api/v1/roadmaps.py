from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Issue, Project, Roadmap, RoadmapItem, User

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


def serialize_item(item: RoadmapItem) -> dict:
    return {
        "item_id": item.item_id,
        "roadmap_id": item.roadmap_id,
        "issue_id": item.issue_id,
        "issue_key": item.issue.issue_key if item.issue else None,
        "name": item.name,
        "description": item.description,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "status": item.status,
        "color_hex": item.color_hex,
        "sort_order": item.sort_order,
    }


def serialize_roadmap(roadmap: Roadmap, include_items: bool = False) -> dict:
    payload = {
        "roadmap_id": roadmap.roadmap_id,
        "project_id": roadmap.project_id,
        "project_key": roadmap.project.project_key if roadmap.project else "",
        "name": roadmap.name,
        "description": roadmap.description,
        "start_date": roadmap.start_date,
        "end_date": roadmap.end_date,
        "created_by": roadmap.created_by,
        "created_at": roadmap.created_at,
        "updated_at": roadmap.updated_at,
    }
    if include_items:
        payload["items"] = [serialize_item(item) for item in roadmap.items]
    return payload


@router.get("/", response_model=List[dict])
def list_roadmaps(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Roadmap)
    if project_id:
        query = query.filter(Roadmap.project_id == project_id)
    return [serialize_roadmap(roadmap) for roadmap in query.order_by(Roadmap.created_at.desc()).all()]


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_roadmap(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.project_id == payload["project_id"]).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    roadmap = Roadmap(
        project_id=project.project_id,
        name=payload["name"],
        description=payload.get("description"),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        created_by=current_user.user_id,
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return serialize_roadmap(roadmap)


@router.get("/{roadmap_id}", response_model=dict)
def get_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(Roadmap.roadmap_id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return serialize_roadmap(roadmap, include_items=True)


@router.post("/{roadmap_id}/items", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_roadmap_item(
    roadmap_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(Roadmap.roadmap_id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    issue = None
    if payload.get("issue_id"):
        issue = db.query(Issue).filter(Issue.issue_id == payload["issue_id"]).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

    item = RoadmapItem(
        roadmap_id=roadmap_id,
        issue_id=issue.issue_id if issue else None,
        name=payload.get("name") or (issue.summary if issue else "Roadmap item"),
        description=payload.get("description"),
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        status=payload.get("status", "planned"),
        color_hex=payload.get("color_hex"),
        sort_order=payload.get("sort_order", 0),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_item(item)


@router.get("/{roadmap_id}/gantt", response_model=dict)
def get_gantt(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(Roadmap.roadmap_id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    items = sorted(roadmap.items, key=lambda item: (item.start_date, item.sort_order))
    return {"roadmap": serialize_roadmap(roadmap), "items": [serialize_item(item) for item in items]}
