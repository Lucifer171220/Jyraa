import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import (
    AgentAction,
    AgentActionStatus,
    AgentMemory,
    Board,
    BoardColumn,
    Issue,
    IssueStatus,
    IssueType,
    IssuePriority,
    IssueRequirement,
    IssueLink,
    Notification,
    Project,
    ProjectRole,
    PullRequest,
    Sprint,
    User,
    UserAssignmentHistory,
    UserSkill,
)
from app.services.email_service import email_is_configured, send_issue_assignment_email
from app.services.langchain_service import build_automation_plan_with_nim
from app.services.code_analyzer import analyze_code_from_github, create_bugs_from_findings
from app.services.nim_service import choose_best_model, generate_response
from app.services.sprint_service import activate_current_sprint, close_completed_sprint, create_sprint_for_board

MAX_ISSUES_PER_USER = 3
WINDOW_DAYS = 14


class AgentState(dict):
    pass


def langgraph_available() -> bool:
    try:
        from langgraph.graph import StateGraph  # noqa: F401

        return True
    except ImportError:
        return False


def infer_issue_requirements(summary: str | None, description: str | None) -> list[dict[str, Any]]:
    text = f"{summary or ''} {description or ''}".lower()
    skills = {
        "frontend": ["react", "javascript", "typescript", "ui", "ux", "css", "tailwind", "next.js"],
        "backend": ["backend", "api", "database", "server", "python", "fastapi", "sql", "auth"],
        "devops": ["deployment", "ci/cd", "docker", "kubernetes", "aws", "azure"],
        "testing": ["test", "testing", "qa", "selenium", "playwright", "pytest", "jest"],
    }
    requirements: list[dict[str, Any]] = []
    for skill, words in skills.items():
        matches = sum(1 for word in words if word in text)
        if matches:
            requirements.append({"skill": skill, "weight": min(3, matches)})
    if not requirements:
        requirements.append({"skill": "general", "weight": 1})
    return requirements


def ensure_issue_requirements(db: Session, issue: Issue) -> list[IssueRequirement]:
    existing = db.query(IssueRequirement).filter(IssueRequirement.issue_id == issue.issue_id).all()
    if existing:
        return existing
    for requirement in infer_issue_requirements(issue.summary, issue.description):
        db.add(
            IssueRequirement(
                issue_id=issue.issue_id,
                required_skill=requirement["skill"],
                weight=requirement["weight"],
            )
        )
    db.commit()
    return db.query(IssueRequirement).filter(IssueRequirement.issue_id == issue.issue_id).all()


def get_user_workload(db: Session, user_id: int, days: int = WINDOW_DAYS) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Issue)
        .filter(
            Issue.assignee_user_id == user_id,
            Issue.created_at >= cutoff,
        )
        .count()
    )


def _priority_rank(db: Session, issue: Issue | None) -> int:
    if not issue or not issue.priority_id:
        return 0
    priority = db.query(IssuePriority).filter(IssuePriority.priority_id == issue.priority_id).first()
    return priority.sort_order if priority else 0


def _score_user_for_issue(db: Session, user: User, issue: Issue, requirements: list[IssueRequirement]) -> dict[str, Any]:
    workload = get_user_workload(db, user.user_id)
    if workload >= MAX_ISSUES_PER_USER:
        return {"score": -999.0, "workload": workload, "skill_score": 0, "history_score": 0}

    user_skills = db.query(UserSkill).filter(UserSkill.user_id == user.user_id).all()
    skill_map = {skill.skill_name.lower(): skill.proficiency for skill in user_skills}

    skill_score = 0.0
    matched_skills: list[str] = []
    for requirement in requirements:
        proficiency = skill_map.get(requirement.required_skill.lower(), 0)
        if proficiency:
            matched_skills.append(requirement.required_skill)
        skill_score += proficiency * requirement.weight

    history_score = (
        db.query(func.count(UserAssignmentHistory.history_id))
        .join(Issue, Issue.issue_id == UserAssignmentHistory.issue_id)
        .filter(
            UserAssignmentHistory.user_id == user.user_id,
            Issue.project_id == issue.project_id,
        )
        .scalar()
        or 0
    )

    return {
        "score": skill_score + (history_score * 0.4) - (workload * 1.2),
        "workload": workload,
        "skill_score": skill_score,
        "history_score": history_score,
        "matched_skills": matched_skills,
    }


def recommend_issue_assignee(db: Session, issue: Issue) -> dict[str, Any]:
    requirements = ensure_issue_requirements(db, issue)
    active_users = db.query(User).filter(User.is_active == True).all()
    if not active_users:
        return {"best_assignee": None, "requirements": [], "candidates": []}

    ranked = []
    for user in active_users:
        metrics = _score_user_for_issue(db, user, issue, requirements)
        ranked.append({"user": user, **metrics})

    ranked.sort(key=lambda item: item["score"], reverse=True)
    best = ranked[0] if ranked else None
    fallback = None
    if ranked:
        fallback = min(
            ranked,
            key=lambda item: (
                item["workload"],
                -item["score"],
                item["user"].user_id,
            ),
        )
    best_assignee = best["user"] if best and best["score"] > -999 else (fallback["user"] if fallback else None)
    selection_mode = "scored" if best and best["score"] > -999 else ("fallback-any-active-user" if fallback else "none")

    return {
        "best_assignee": best_assignee,
        "selection_mode": selection_mode,
        "requirements": [
            {"skill": req.required_skill, "weight": req.weight}
            for req in requirements
        ],
        "candidates": [
            {
                "user_id": entry["user"].user_id,
                "username": entry["user"].username,
                "display_name": entry["user"].display_name,
                "score": round(entry["score"], 2),
                "workload": entry["workload"],
                "skill_score": round(entry["skill_score"], 2),
                "history_score": round(entry["history_score"], 2),
                "matched_skills": entry["matched_skills"],
            }
            for entry in ranked[:5]
        ],
    }


def assignment_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    issue_id = state.get("issue_id")
    if not issue_id:
        state["error"] = "assignment_agent requires issue_id"
        return state

    issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
    if not issue:
        state["error"] = f"Issue {issue_id} not found"
        return state

    recommendation = recommend_issue_assignee(db, issue)
    best = recommendation["best_assignee"]
    state.setdefault("output", {})["assignment"] = {
        "issue_id": issue.issue_id,
        "issue_key": issue.issue_key,
        "requirements": recommendation["requirements"],
        "best_assignee_id": best.user_id if best else None,
        "best_assignee_username": best.username if best else None,
        "best_assignee_display_name": best.display_name if best else None,
        "candidate_scores": recommendation["candidates"],
        "method": "skill-history-workload",
    }
    return state


def pr_health_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    issue_id = state.get("issue_id")
    if not issue_id:
        state.setdefault("output", {})["pr_health"] = []
        return state

    prs = db.query(PullRequest).filter(PullRequest.issue_id == issue_id).all()
    pr_results = []
    for pr in prs:
        score, findings = analyze_code_from_github(
            db,
            pr.pr_id,
            pr.repository_url,
            pr.github_pr_number,
        )
        pr.health_score = score
        pr.status = "analyzed"
        db.commit()
        created_bugs = create_bugs_from_findings(db, pr.pr_id, findings, issue_id)
        pr_results.append(
            {
                "pr_id": pr.pr_id,
                "github_pr_number": pr.github_pr_number,
                "health_score": score,
                "findings": findings,
                "bugs_created": len(created_bugs),
                "status": pr.status,
            }
        )

    state.setdefault("output", {})["pr_health"] = pr_results
    return state


def sprint_agent(state: AgentState) -> AgentState:
    db: Session = state["db"]
    board_id = state.get("board_id")
    boards = (
        db.query(Board).filter(Board.board_id == board_id).all()
        if board_id
        else db.query(Board).all()
    )
    result = {"activated": [], "closed": [], "created": []}

    for board in boards:
        activated = activate_current_sprint(db, board.board_id)
        closed = close_completed_sprint(db, board.board_id)
        for sprint in activated:
            result["activated"].append({"sprint_id": sprint.sprint_id, "name": sprint.name, "board_id": board.board_id})
        for sprint in closed:
            result["closed"].append({"sprint_id": sprint.sprint_id, "name": sprint.name, "board_id": board.board_id})
            has_future = (
                db.query(Sprint)
                .filter(Sprint.board_id == board.board_id, Sprint.sprint_status == "future")
                .first()
            )
            if not has_future and board.board_type == "scrum":
                created = create_sprint_for_board(db, board.board_id)
                result["created"].append({"sprint_id": created.sprint_id, "name": created.name, "board_id": board.board_id})

    state.setdefault("output", {})["sprint"] = result
    return state


async def executive_agent(state: AgentState) -> AgentState:
    output = state.get("output", {})
    fallback = {
        "summary": "Deterministic automation completed. NIM was not available for narrative synthesis.",
        "recommended_actions": [],
        "source_model": None,
    }
    model = choose_best_model()
    if not model:
        state.setdefault("output", {})["executive"] = fallback
        return state

    prompt = (
        "You are the Executive Intelligence Layer for ZYRAA.\n"
        "Review the structured agent output below and return valid JSON with keys "
        "`summary` and `recommended_actions`.\n\n"
        f"{json.dumps(output, indent=2, default=str)}"
    )
    system = "Be concise, operational, and practical."
    answer, source_model = await generate_response(prompt=prompt, system=system)
    try:
        parsed = json.loads(answer)
        summary = str(parsed.get("summary") or fallback["summary"])
        actions = parsed.get("recommended_actions") or []
    except (json.JSONDecodeError, TypeError):
        summary = answer.strip() or fallback["summary"]
        actions = []

    state.setdefault("output", {})["executive"] = {
        "summary": summary,
        "recommended_actions": actions[:6],
        "source_model": source_model,
    }
    return state


def pending_action_gate(state: AgentState) -> AgentState:
    db: Session = state["db"]
    current_user: User | None = state.get("current_user")
    pending_actions = []

    assignment = state.get("output", {}).get("assignment")
    if assignment and assignment.get("best_assignee_id"):
        action = AgentAction(
            user_id=current_user.user_id if current_user else None,
            agent_name="assignment_agent",
            action_type="assign_issue",
            title=f"Assign {assignment['issue_key']} to {assignment['best_assignee_username']}",
            description="Apply the assignee recommendation from the assignment agent.",
            payload={
                "issue_id": assignment["issue_id"],
                "assignee_user_id": assignment["best_assignee_id"],
            },
            status=AgentActionStatus.PENDING.value,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        pending_actions.append(action)

    state["pending_actions"] = [
        {
            "id": action.id,
            "action_type": action.action_type,
            "title": action.title,
            "status": action.status,
        }
        for action in pending_actions
    ]
    return state


def execute_actions(state: AgentState) -> AgentState:
    db: Session = state["db"]
    action_id = state.get("action_id")
    query = db.query(AgentAction).filter(AgentAction.status == AgentActionStatus.APPROVED.value)
    if action_id:
        query = query.filter(AgentAction.id == action_id)
    actions = query.all()

    results = []
    for action in actions:
        try:
            if action.action_type == "assign_issue":
                issue = db.query(Issue).filter(Issue.issue_id == action.payload["issue_id"]).first()
                if issue:
                    issue.assignee_user_id = action.payload["assignee_user_id"]
                    if not db.query(UserAssignmentHistory).filter(
                        UserAssignmentHistory.issue_id == issue.issue_id,
                        UserAssignmentHistory.user_id == issue.assignee_user_id,
                    ).first():
                        db.add(
                            UserAssignmentHistory(
                                user_id=issue.assignee_user_id,
                                issue_id=issue.issue_id,
                                assigned_at=datetime.utcnow(),
                                outcome="assigned_by_agent",
                            )
                        )
            action.result = {"status": "done"}
            action.decided_at = datetime.utcnow()
            db.commit()
            results.append({"action_id": action.id, "status": "done"})
        except Exception as exc:
            db.rollback()
            action.status = AgentActionStatus.FAILED.value
            action.result = {"error": str(exc)}
            action.decided_at = datetime.utcnow()
            db.commit()
            results.append({"action_id": action.id, "status": "failed", "error": str(exc)})

    state["execution_results"] = results
    return state


def _save_memory(db: Session, user: User | None, agent_name: str, message: str, summary: str, data: dict) -> None:
    db.add(
        AgentMemory(
            user_id=user.user_id if user else None,
            agent_name=agent_name,
            user_message=message,
            summary=summary,
            data=data,
        )
    )
    db.commit()


async def run_agentic_workflow(
    db: Session,
    user: User,
    *,
    issue_id: int | None = None,
    board_id: int | None = None,
    intent: str = "full_scan",
) -> dict[str, Any]:
    state: AgentState = AgentState(
        db=db,
        current_user=user,
        intent=intent,
        issue_id=issue_id,
        board_id=board_id,
        output={},
        pending_actions=[],
        error=None,
    )

    if intent in {"sprint", "full_scan"}:
        sprint_agent(state)
    if intent in {"assign", "full_scan"} and issue_id:
        assignment_agent(state)
    if intent in {"pr_health", "full_scan"} and issue_id:
        pr_health_agent(state)

    await executive_agent(state)
    pending_action_gate(state)
    return {
        "output": state.get("output", {}),
        "pending_actions": state.get("pending_actions", []),
        "error": state.get("error"),
    }


async def run_conversational_agent(db: Session, user: User, message: str) -> dict[str, Any]:
    lower = message.lower()
    issue = db.query(Issue).order_by(Issue.created_at.desc()).first()
    board = db.query(Board).order_by(Board.created_at.desc()).first()

    if any(token in lower for token in ["assign", "who should work", "best person"]):
        result = await run_agentic_workflow(db, user, issue_id=issue.issue_id if issue else None, intent="assign")
        agent_name = "Assignment Agent"
    elif "sprint" in lower:
        result = await run_agentic_workflow(db, user, board_id=board.board_id if board else None, intent="sprint")
        agent_name = "Sprint Agent"
    elif any(token in lower for token in ["pr", "code review", "health"]):
        result = await run_agentic_workflow(db, user, issue_id=issue.issue_id if issue else None, intent="pr_health")
        agent_name = "PR Health Agent"
    else:
        result = await run_agentic_workflow(
            db,
            user,
            issue_id=issue.issue_id if issue else None,
            board_id=board.board_id if board else None,
            intent="full_scan",
        )
        agent_name = "Executive Agent"

    summary = json.dumps(result["output"], indent=2, default=str)
    _save_memory(db, user, agent_name, message, summary, result["output"])
    return {
        "agent": agent_name,
        "summary": summary,
        **result,
    }


def _default_board_columns(db: Session, board_id: int) -> None:
    status_names = ["To Do", "In Progress", "In Review", "Done"]
    statuses = db.query(IssueStatus).filter(IssueStatus.name.in_(status_names)).all()
    status_map = {status.name: status for status in statuses}
    names = ["To Do", "In Progress", "In Review", "Done"]
    for index, name in enumerate(names, start=1):
        status = status_map.get(name)
        db.add(
            BoardColumn(
                board_id=board_id,
                name=name,
                column_type="status",
                mapped_status_id=status.status_id if status else None,
                sort_order=index,
                is_editable=False,
            )
        )
    db.commit()


def _create_project_from_plan(db: Session, current_user: User, project_plan: dict[str, Any]) -> Project | None:
    if not project_plan.get("create"):
        return None
    project_key = project_plan.get("project_key")
    project_name = project_plan.get("name")
    if not project_key or not project_name:
        return None

    existing = db.query(Project).filter(Project.project_key == project_key).first()
    if existing:
        return existing

    project = Project(
        project_key=project_key,
        name=project_name,
        description=project_plan.get("description"),
        lead_user_id=current_user.user_id,
        project_type="software",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    db.add(ProjectRole(project_id=project.project_id, user_id=current_user.user_id, role_type="admin"))
    db.commit()
    return project


def _create_board_from_plan(db: Session, project: Project | None, board_plan: dict[str, Any]) -> Board | None:
    if not project or not board_plan.get("create"):
        return None
    existing = db.query(Board).filter(Board.project_id == project.project_id).first()
    if existing:
        return existing

    board = Board(
        project_id=project.project_id,
        name=board_plan.get("name") or f"{project.name} Board",
        description=f"Automation board for {project.name}",
        board_type=board_plan.get("board_type") or "kanban",
        is_active=True,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    _default_board_columns(db, board.board_id)
    return board


def _create_issue_from_plan(db: Session, current_user: User, project: Project | None, issue_plan: dict[str, Any]) -> Issue | None:
    if not project or not issue_plan.get("create"):
        return None
    issue_type_name = issue_plan.get("issue_type") or "Story"
    issue_type = db.query(IssueType).filter(IssueType.name == issue_type_name).first()
    status = db.query(IssueStatus).filter(IssueStatus.name == "To Do").first()
    priority = None
    if issue_plan.get("priority"):
        priority = db.query(IssuePriority).filter(IssuePriority.name == issue_plan["priority"]).first()
    if not issue_type or not status or not issue_plan.get("summary"):
        return None

    last_issue = (
        db.query(Issue)
        .filter(Issue.project_id == project.project_id)
        .order_by(Issue.issue_id.desc())
        .first()
    )
    next_number = 1
    if last_issue and "-" in last_issue.issue_key:
        try:
            next_number = int(last_issue.issue_key.rsplit("-", 1)[1]) + 1
        except ValueError:
            next_number = 1

    issue = Issue(
        issue_key=f"{project.project_key}-{next_number}",
        project_id=project.project_id,
        issue_type_id=issue_type.issue_type_id,
        summary=issue_plan["summary"],
        description=issue_plan.get("description"),
        priority_id=priority.priority_id if priority else None,
        status_id=status.status_id,
        reporter_user_id=current_user.user_id,
        assignee_user_id=None,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def _resolve_user_from_hint(db: Session, hint: str | None) -> User | None:
    if not hint:
        return None

    normalized = hint.strip()
    if not normalized:
        return None

    exact = (
        db.query(User)
        .filter(
            User.is_active == True,
            or_(
                func.lower(User.username) == normalized.lower(),
                func.lower(User.email) == normalized.lower(),
            ),
        )
        .first()
    )
    if exact:
        return exact

    like = f"%{normalized}%"
    return (
        db.query(User)
        .filter(
            User.is_active == True,
            or_(
                User.username.ilike(like),
                User.display_name.ilike(like),
                User.email.ilike(like),
            ),
        )
        .order_by(User.display_name.asc(), User.username.asc())
        .first()
    )


def _assign_issue_and_notify(db: Session, issue: Issue | None, issue_plan: dict[str, Any], email_plan: dict[str, Any]) -> dict[str, Any]:
    if not issue:
        return {"assigned": False}

    requested_hint = issue_plan.get("assignee_username")
    auto_assign = bool(issue_plan.get("auto_assign"))
    requested_user = _resolve_user_from_hint(db, requested_hint)
    recommendation = None

    if requested_user:
        best = requested_user
        assignment_method = "prompt-selected-user"
        assignment_outcome = "assigned_by_prompt_selection"
    else:
        if requested_hint and not auto_assign:
            return {
                "assigned": False,
                "reason": "requested_assignee_not_found",
                "requested_assignee": requested_hint,
            }
        if not auto_assign:
            return {"assigned": False, "reason": "assignment_not_requested"}

        recommendation = recommend_issue_assignee(db, issue)
        best = recommendation["best_assignee"]
        if not best:
            return {"assigned": False, "reason": "no_assignee_found", "recommendation": recommendation}
        assignment_method = "skill-history-workload"
        assignment_outcome = "assigned_by_prompt_automation"

    issue.assignee_user_id = best.user_id
    db.add(
        UserAssignmentHistory(
            user_id=best.user_id,
            issue_id=issue.issue_id,
            assigned_at=datetime.utcnow(),
            outcome=assignment_outcome,
        )
    )
    db.add(
        Notification(
            user_id=best.user_id,
            type="issue_assigned",
            title="Issue Assigned",
            message=f"{issue.issue_key}: {issue.summary} has been assigned to you",
            related_issue_id=issue.issue_id,
        )
    )
    db.commit()
    db.refresh(issue)

    email_result = {"sent": False, "reason": "not_requested"}
    if email_plan.get("send_assignment_email"):
        email_result = send_issue_assignment_email(
            recipient_email=best.email,
            recipient_name=best.display_name,
            issue_key=issue.issue_key,
            summary=issue.summary,
            project_name=issue.project.name if issue.project else "ZYRAA Project",
        )

    return {
        "assigned": True,
        "assignment_method": assignment_method,
        "assignee_user_id": best.user_id,
        "assignee_username": best.username,
        "assignee_display_name": best.display_name,
        "assignee_email": best.email,
        "recommendation": recommendation,
        "email": email_result,
    }


def _create_issues_from_plan(db: Session, current_user: User, project: Project | None, plan: dict[str, Any]) -> list[Issue]:
    issues_plan = plan.get("issues") or []
    if not issues_plan:
        issues_plan = [plan.get("issue", {})]

    created: list[Issue] = []
    for issue_plan in issues_plan:
        issue = _create_issue_from_plan(db, current_user, project, issue_plan)
        if issue:
            created.append(issue)
    return created


def _link_issue_chain(db: Session, issues: list[Issue]) -> None:
    if len(issues) < 2:
        return

    for parent, child in zip(issues, issues[1:]):
        existing = (
            db.query(IssueLink)
            .filter(
                IssueLink.issue_id_from == parent.issue_id,
                IssueLink.issue_id_to == child.issue_id,
                IssueLink.link_type == "parent-child",
            )
            .first()
        )
        if not existing:
            db.add(IssueLink(issue_id_from=parent.issue_id, issue_id_to=child.issue_id, link_type="parent-child"))
    db.commit()


async def run_prompt_automation(db: Session, user: User, prompt: str) -> dict[str, Any]:
    plan = await build_automation_plan_with_nim(prompt)
    project = _create_project_from_plan(db, user, plan.get("project", {}))
    board = _create_board_from_plan(db, project, plan.get("board", {}))
    created_issues = _create_issues_from_plan(db, user, project, plan)
    _link_issue_chain(db, created_issues)
    assignments = [
        _assign_issue_and_notify(db, issue, issue_plan, plan.get("email", {}))
        for issue, issue_plan in zip(created_issues, plan.get("issues", []))
    ]
    primary_issue = created_issues[0] if created_issues else None
    primary_assignment = assignments[0] if assignments else {"assigned": False}

    return {
        "mode": "nim-assisted" if choose_best_model() else "fallback",
        "workflow_engine": "langgraph" if langgraph_available() else "internal-state-graph",
        "email_configured": email_is_configured(),
        "plan": plan,
        "result": {
            "project": {
                "project_id": project.project_id,
                "project_key": project.project_key,
                "name": project.name,
            } if project else None,
            "board": {
                "board_id": board.board_id,
                "name": board.name,
                "board_type": board.board_type,
            } if board else None,
            "issue": {
                "issue_id": primary_issue.issue_id,
                "issue_key": primary_issue.issue_key,
                "summary": primary_issue.summary,
            } if primary_issue else None,
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "issue_key": issue.issue_key,
                    "summary": issue.summary,
                    "issue_type": issue.issue_type.name if issue.issue_type else None,
                }
                for issue in created_issues
            ],
            "assignment": primary_assignment,
            "assignments": assignments,
        },
    }
