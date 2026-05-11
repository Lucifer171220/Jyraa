from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Filter, User

router = APIRouter(prefix="/filters", tags=["filters"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_filter(
    filter_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_obj = Filter(
        user_id=current_user.user_id,
        project_id=filter_data.get("project_id"),
        name=filter_data["name"],
        jql_query=filter_data["jql_query"],
        is_favorite=filter_data.get("is_favorite", False),
        is_shared=filter_data.get("is_shared", False),
    )
    db.add(filter_obj)
    db.commit()
    db.refresh(filter_obj)
    return {
        "filter_id": filter_obj.filter_id,
        "name": filter_obj.name,
        "jql_query": filter_obj.jql_query,
        "is_favorite": filter_obj.is_favorite,
        "is_shared": filter_obj.is_shared,
    }


@router.get("/", response_model=List[dict])
def get_filters(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Filter).filter(
        (Filter.user_id == current_user.user_id) | (Filter.is_shared == True)
    )
    if project_id:
        query = query.filter(Filter.project_id == project_id)
    filters = query.all()
    return [
        {
            "filter_id": f.filter_id,
            "name": f.name,
            "jql_query": f.jql_query,
            "is_favorite": f.is_favorite,
            "is_shared": f.is_shared,
        }
        for f in filters
    ]


@router.get("/{filter_id}", response_model=dict)
def get_filter(
    filter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_obj = db.query(Filter).filter(
        (Filter.filter_id == filter_id) &
        ((Filter.user_id == current_user.user_id) | (Filter.is_shared == True))
    ).first()
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    return {
        "filter_id": filter_obj.filter_id,
        "name": filter_obj.name,
        "jql_query": filter_obj.jql_query,
        "is_favorite": filter_obj.is_favorite,
        "is_shared": filter_obj.is_shared,
    }


@router.put("/{filter_id}", response_model=dict)
def update_filter(
    filter_id: int,
    filter_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_obj = db.query(Filter).filter(
        (Filter.filter_id == filter_id) & (Filter.user_id == current_user.user_id)
    ).first()
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")

    filter_obj.name = filter_data.get("name", filter_obj.name)
    filter_obj.jql_query = filter_data.get("jql_query", filter_obj.jql_query)
    filter_obj.is_favorite = filter_data.get("is_favorite", filter_obj.is_favorite)
    filter_obj.is_shared = filter_data.get("is_shared", filter_obj.is_shared)
    db.commit()
    db.refresh(filter_obj)
    return {
        "filter_id": filter_obj.filter_id,
        "name": filter_obj.name,
        "jql_query": filter_obj.jql_query,
    }


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filter(
    filter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_obj = db.query(Filter).filter(
        (Filter.filter_id == filter_id) & (Filter.user_id == current_user.user_id)
    ).first()
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    db.delete(filter_obj)
    db.commit()
    return None