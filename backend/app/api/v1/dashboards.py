from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Dashboard, DashboardGadget, User

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_dashboard(
    dashboard_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = Dashboard(
        user_id=current_user.user_id,
        name=dashboard_data["name"],
        description=dashboard_data.get("description"),
        is_shared=dashboard_data.get("is_shared", False),
        layout_config=dashboard_data.get("layout_config"),
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return {
        "dashboard_id": dashboard.dashboard_id,
        "name": dashboard.name,
        "description": dashboard.description,
        "is_shared": dashboard.is_shared,
    }


@router.get("/", response_model=List[dict])
def get_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboards = db.query(Dashboard).filter(
        (Dashboard.user_id == current_user.user_id) | (Dashboard.is_shared == True)
    ).all()
    return [
        {
            "dashboard_id": d.dashboard_id,
            "name": d.name,
            "description": d.description,
            "is_shared": d.is_shared,
        }
        for d in dashboards
    ]


@router.get("/{dashboard_id}", response_model=dict)
def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = db.query(Dashboard).filter(
        (Dashboard.dashboard_id == dashboard_id) &
        ((Dashboard.user_id == current_user.user_id) | (Dashboard.is_shared == True))
    ).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    gadgets = [
        {
            "gadget_id": g.gadget_id,
            "gadget_type": g.gadget_type,
            "title": g.title,
            "config": g.config,
            "position_x": g.position_x,
            "position_y": g.position_y,
            "width": g.width,
            "height": g.height,
        }
        for g in dashboard.gadgets
    ]
    return {
        "dashboard_id": dashboard.dashboard_id,
        "name": dashboard.name,
        "description": dashboard.description,
        "is_shared": dashboard.is_shared,
        "gadgets": gadgets,
    }


@router.post("/{dashboard_id}/gadgets", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_gadget(
    dashboard_id: int,
    gadget_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = db.query(Dashboard).filter(
        (Dashboard.dashboard_id == dashboard_id) & (Dashboard.user_id == current_user.user_id)
    ).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    gadget = DashboardGadget(
        dashboard_id=dashboard_id,
        gadget_type=gadget_data["gadget_type"],
        title=gadget_data["title"],
        config=gadget_data.get("config"),
        position_x=gadget_data.get("position_x", 0),
        position_y=gadget_data.get("position_y", 0),
        width=gadget_data.get("width", 4),
        height=gadget_data.get("height", 4),
    )
    db.add(gadget)
    db.commit()
    db.refresh(gadget)
    return {
        "gadget_id": gadget.gadget_id,
        "gadget_type": gadget.gadget_type,
        "title": gadget.title,
    }


@router.delete("/{dashboard_id}/gadgets/{gadget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gadget(
    dashboard_id: int,
    gadget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = db.query(Dashboard).filter(
        (Dashboard.dashboard_id == dashboard_id) & (Dashboard.user_id == current_user.user_id)
    ).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    gadget = db.query(DashboardGadget).filter(DashboardGadget.gadget_id == gadget_id).first()
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")
    db.delete(gadget)
    db.commit()
    return None