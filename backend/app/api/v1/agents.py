import asyncio
import json
import time
from datetime import datetime
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.access_control import require_action_owner
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
from app.services.nim_service import choose_best_model, get_available_models, nim_is_configured
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


def _stream_line(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


async def _stream_operation(
    label: str,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    *,
    progress_messages: list[str],
) -> StreamingResponse:
    async def events():
        started = time.monotonic()
        yield _stream_line("status", message=f"{label} started", elapsed_seconds=0)
        task = asyncio.create_task(operation())
        message_index = 0

        while True:
            done, _ = await asyncio.wait({task}, timeout=2)
            if task in done:
                break
            elapsed = round(time.monotonic() - started, 1)
            message = progress_messages[min(message_index, len(progress_messages) - 1)]
            message_index += 1
            yield _stream_line("status", message=message, elapsed_seconds=elapsed)

        try:
            result = await task
        except Exception as exc:
            yield _stream_line(
                "error",
                message=f"{label} failed",
                detail=str(exc),
                elapsed_seconds=round(time.monotonic() - started, 1),
            )
            return

        yield _stream_line(
            "result",
            message=f"{label} completed",
            data=result,
            elapsed_seconds=round(time.monotonic() - started, 1),
        )

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/status")
def agent_status(current_user: User = Depends(get_current_user)) -> dict:
    model = choose_best_model()
    return {
        "nim_available": nim_is_configured(),
        "selected_model": model,
        "available_models": get_available_models() or [],
        "mode": "nim-assisted" if model else "rule-based-fallback",
        "langchain_available": langchain_available(),
        "ai_planner_available": langchain_available(),
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


@router.post("/automation/run/stream")
async def run_automation_stream(
    payload: RunAutomationAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _stream_operation(
        "Automation workflow",
        lambda: run_agentic_workflow(
            db,
            current_user,
            issue_id=payload.issue_id,
            board_id=payload.board_id,
            intent=payload.intent,
        ),
        progress_messages=[
            "Inspecting sprint, issue, and PR context",
            "Running deterministic agents",
            "Generating executive summary",
            "Preparing structured workflow output",
        ],
    )


@router.post("/workflow/ask")
async def ask_agent(
    payload: AskAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_conversational_agent(db, current_user, payload.message)


@router.post("/workflow/ask/stream")
async def ask_agent_stream(
    payload: AskAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _stream_operation(
        "Agent answer",
        lambda: run_conversational_agent(db, current_user, payload.message),
        progress_messages=[
            "Routing your question to the right agent",
            "Reading current project data",
            "Synthesizing the answer",
            "Formatting the response",
        ],
    )


@router.post("/prompt/execute")
async def execute_prompt(
    payload: PromptAutomationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_prompt_automation(db, current_user, payload.prompt)


@router.post("/prompt/execute/stream")
async def execute_prompt_stream(
    payload: PromptAutomationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _stream_operation(
        "Prompt automation",
        lambda: run_prompt_automation(db, current_user, payload.prompt),
        progress_messages=[
            "Planning the requested workflow",
            "Creating or resolving project structure",
            "Creating issues and links",
            "Assigning owners and preparing notifications",
        ],
    )


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


@router.post("/repository/review/stream")
async def review_repository_stream(
    payload: RepositoryReviewRequest,
    current_user: User = Depends(get_current_user),
):
    async def run_review() -> dict[str, Any]:
        result = await asyncio.to_thread(
            lambda: asyncio.run(
                review_repository_from_github(
                    payload.repository_url,
                    branch=payload.branch,
                    github_token=payload.github_token,
                    max_files=payload.max_files,
                )
            )
        )
        result["requested_by"] = current_user.username
        return result

    return await _stream_operation(
        "Repository review",
        run_review,
        progress_messages=[
            "Fetching repository metadata and file tree",
            "Downloading prioritized source files",
            "Running strict SAST and project-structure checks",
            "Checking dependency manifests against OSV",
            "Generating the security summary",
            "Assembling the final report",
        ],
    )


@router.post("/actions/{action_id}/approve")
def approve_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    require_action_owner(action, current_user)
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
    require_action_owner(action, current_user)
    if action.status != AgentActionStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Action already decided")

    action.status = AgentActionStatus.REJECTED.value
    action.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(action)
    return {"status": "rejected", "action_id": action.id, "rejected_by": current_user.username}
