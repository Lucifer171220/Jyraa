import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Webhook, Project, User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_webhook(
    webhook_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.project_id == webhook_data["project_id"]).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    webhook = Webhook(
        project_id=webhook_data["project_id"],
        name=webhook_data["name"],
        url=webhook_data["url"],
        events=json.dumps(webhook_data.get("events", [])),
        secret=webhook_data.get("secret"),
        created_by=current_user.user_id,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return {
        "webhook_id": webhook.webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "events": json.loads(webhook.events),
        "is_active": webhook.is_active,
    }


@router.get("/", response_model=List[dict])
def get_webhooks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhooks = db.query(Webhook).filter(Webhook.project_id == project_id).all()
    return [
        {
            "webhook_id": w.webhook_id,
            "name": w.name,
            "url": w.url,
            "events": json.loads(w.events),
            "is_active": w.is_active,
        }
        for w in webhooks
    ]


@router.put("/{webhook_id}", response_model=dict)
def update_webhook(
    webhook_id: int,
    webhook_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = db.query(Webhook).filter(Webhook.webhook_id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook.name = webhook_data.get("name", webhook.name)
    webhook.url = webhook_data.get("url", webhook.url)
    webhook.events = json.dumps(webhook_data.get("events", json.loads(webhook.events)))
    webhook.is_active = webhook_data.get("is_active", webhook.is_active)
    db.commit()
    db.refresh(webhook)
    return {
        "webhook_id": webhook.webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "events": json.loads(webhook.events),
        "is_active": webhook.is_active,
    }


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = db.query(Webhook).filter(Webhook.webhook_id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(webhook)
    db.commit()
    return None


@router.post("/{webhook_id}/test", response_model=dict)
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = db.query(Webhook).filter(Webhook.webhook_id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook.url,
                json={
                    "event": "webhook.test",
                    "source": "ZYRAA",
                    "webhook_id": webhook.webhook_id,
                    "project_id": webhook.project_id,
                },
                headers={"X-ZYRAA-Event": "webhook.test"},
            )
        return {"ok": response.status_code < 400, "status_code": response.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
