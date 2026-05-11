from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user, get_db
from app.models import AgentAction, AgentActionStatus, User
from app.services.agent_service import (
    AgentState,
    execute_actions,
    langgraph_available,
    run_agentic_workflow,
    run_conversational_agent,
    run_prompt_automation,
)
from app.services.email_service import email_is_configured
from app.services.langchain_service import langchain_available
from app.services.ollama_service import choose_best_model, get_installed_models
from app.services.code_analyzer import review_repository_from_github

router = APIRouter(prefix="/agents", tags=["agents"])


class RunAutomationAgentRequest(BaseModel):
    intent: str = Field(default="full_scan", examples=["full_scan", "assign", "pr_health", "sprint"])
    issue_id: int | None = None
    board_id: int | None = None


class AskAgentRequest(BaseModel):
    message: str = Field(min_length=3, max_length=5000)


class PromptAutomationRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=8000)


class RepositoryReviewRequest(BaseModel):
    repository_url: str = Field(min_length=10, max_length=1000)
    branch: str | None = Field(default=None, max_length=200)
    github_token: str | None = Field(default=None, max_length=500)
    max_files: int = Field(default=120, ge=10, le=300)


@router.get("/status")
def agent_status(current_user: User = Depends(get_current_user)) -> dict:
    model = choose_best_model()
    return {
        "ollama_available": model is not None,
        "selected_model": model,
        "installed_models": get_installed_models() or [],
        "mode": "ollama-assisted" if model else "rule-based-fallback",
        "langchain_available": langchain_available(),
        "langgraph_available": langgraph_available(),
        "email_configured": email_is_configured(),
        "user": current_user.username,
    }


@router.post("/automation/run")
async def run_automation(
    payload: RunAutomationAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_agentic_workflow(
        db,
        current_user,
        issue_id=payload.issue_id,
        board_id=payload.board_id,
        intent=payload.intent,
    )


@router.post("/workflow/ask")
async def ask_agent(
    payload: AskAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_conversational_agent(db, current_user, payload.message)


@router.post("/prompt/execute")
async def execute_prompt(
    payload: PromptAutomationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_prompt_automation(db, current_user, payload.prompt)


@router.post("/repository/review")
async def review_repository(
    payload: RepositoryReviewRequest,
    current_user: User = Depends(get_current_user),
):
    result = await review_repository_from_github(
        payload.repository_url,
        branch=payload.branch,
        github_token=payload.github_token,
        max_files=payload.max_files,
    )
    result["requested_by"] = current_user.username
    return result


@router.post("/actions/{action_id}/approve")
def approve_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Action already decided")

    action.status = AgentActionStatus.APPROVED.value
    action.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(action)

    state = AgentState(db=db, current_user=current_user, action_id=action.id, output={}, pending_actions=[])
    execute_actions(state)
    return {"status": "approved", "action_id": action.id, "execution_results": state.get("execution_results", [])}


@router.post("/actions/{action_id}/reject")
def reject_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Action already decided")

    action.status = AgentActionStatus.REJECTED.value
    action.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(action)
    return {"status": "rejected", "action_id": action.id, "rejected_by": current_user.username}
