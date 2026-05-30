import json
import re
from typing import Any

from app.services.nim_service import choose_best_model, generate_response, langchain_nvidia_available


def langchain_available() -> bool:
    return langchain_nvidia_available() and choose_best_model() is not None


def build_automation_plan(prompt: str) -> dict[str, Any]:
    return _fallback_plan(prompt)


async def build_automation_plan_with_nim(prompt: str) -> dict[str, Any]:
    plan = await _build_plan_with_nim(prompt)
    return plan or _fallback_plan(prompt)


async def _build_plan_with_nim(prompt: str) -> dict[str, Any] | None:
    try:
        structured_prompt = (
            "You are a workflow planner for ZYRAA. Convert the user request into valid JSON only.\n"
            "Return keys: project, board, issues, email.\n"
            "project: {create:boolean, project_key:string|null, name:string|null, description:string|null}\n"
            "board: {create:boolean, name:string|null, board_type:string|null}\n"
            "issues: list of {create:boolean, issue_type:string|null, summary:string|null, description:string|null, priority:string|null, assignee_username:string|null, auto_assign:boolean, due_date:string|null, label_names:list}\n"
            "email: {send_assignment_email:boolean, recipients:list}\n"
            "Use null when unknown. Use board_type kanban or scrum. Use issue_type Epic/Story/Task/Bug. "
            "If the user names an assignee, put that value in issue.assignee_username. "
            "Set issue.auto_assign true only when the user asks for automatic assignment. "
            "If the prompt asks for an Epic, Story, and Task chain, return three separate items in issues in the requested order.\n\n"
            f"User request:\n{prompt}"
        )
        content, _ = await generate_response(
            prompt=structured_prompt,
            system="Return only valid JSON. Do not wrap the response in markdown.",
        )
        plan = json.loads(content)
        return _normalize_plan(plan)
    except Exception:
        return None


def _fallback_plan(prompt: str) -> dict[str, Any]:
    text = prompt.strip()
    lower = text.lower()

    project_name = None
    project_match = re.search(r"(?:create|make|start)\s+(?:a\s+)?project\s+(?:called|named)?\s*['\"]?([^,'\"\n]+)", text, re.IGNORECASE)
    if project_match:
        project_name = project_match.group(1).strip()

    key_match = re.search(r"\bkey\s+([A-Z][A-Z0-9]{1,9})\b", text)
    project_key = key_match.group(1) if key_match else (_derive_project_key(project_name) if project_name else None)

    priority = None
    for candidate in ["Highest", "High", "Medium", "Low", "Lowest"]:
        if candidate.lower() in lower:
            priority = candidate
            break

    assignee_username = None
    assignee_match = re.search(
        r"(?:assign(?:\s+it|\s+this|\s+the\s+issue)?\s+to|assignee(?:\s+should\s+be)?|owner(?:\s+should\s+be)?)\s+@?([A-Za-z0-9._-]{2,80})\b",
        text,
        re.IGNORECASE,
    )
    if assignee_match:
        assignee_username = assignee_match.group(1).strip().rstrip(".!,")
    auto_assign = any(
        phrase in lower
        for phrase in [
            "auto assign",
            "auto-assign",
            "automatically assign",
            "assign automatically",
            "best assignee",
        ]
    )
    extracted_issues = _extract_issue_items(text, priority, assignee_username, auto_assign)
    primary_issue = extracted_issues[0] if extracted_issues else {
        "create": False,
        "issue_type": "Story",
        "summary": None,
        "description": None,
        "priority": priority,
        "assignee_username": assignee_username,
        "auto_assign": auto_assign,
        "due_date": None,
        "label_names": [],
    }

    return _normalize_plan({
        "project": {
            "create": bool(project_name),
            "project_key": project_key,
            "name": project_name,
            "description": text if project_name else None,
        },
        "board": {
            "create": "board" in lower or bool(project_name),
            "name": f"{project_name} Board" if project_name else None,
            "board_type": "scrum" if "scrum" in lower else "kanban",
        },
        "issue": primary_issue,
        "issues": extracted_issues,
        "email": {
            "send_assignment_email": "mail" in lower or "email" in lower or "notify" in lower,
            "recipients": [],
        },
    })


def _extract_issue_items(
    text: str,
    priority: str | None,
    assignee_username: str | None,
    auto_assign: bool,
) -> list[dict[str, Any]]:
    lower = text.lower()
    shared_labels = [label for label in ["frontend", "backend", "ui", "database", "security", "performance"] if label in lower]
    pattern = re.compile(
        r"(?:create|add|make)?\s*(?:an?|the)?\s*(Epic|Story|Task|Bug)\s+(?:called|named|for)?\s*['\"]?(.+?)(?=(?:,\s*(?:create|add|make)\b)|(?:\s+and\s+(?:create|add|make)\b)|$)",
        re.IGNORECASE,
    )
    issues: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        issue_type = match.group(1).title()
        summary = match.group(2).strip().strip("'\"").rstrip(" ,.")
        if not summary:
            continue
        issues.append({
            "create": True,
            "issue_type": issue_type,
            "summary": summary,
            "description": text,
            "priority": priority,
            "assignee_username": assignee_username,
            "auto_assign": auto_assign,
            "due_date": None,
            "label_names": shared_labels,
        })

    if issues:
        return issues

    issue_match = re.search(r"(?:issue|story|task|bug)\s+(?:for|called|named)?\s*['\"]?([^.'\"\n]+)", text, re.IGNORECASE)
    if not issue_match:
        return []

    issue_type = "Story"
    padded = f" {lower} "
    if " bug " in padded:
        issue_type = "Bug"
    elif " task " in padded:
        issue_type = "Task"
    elif " epic " in padded:
        issue_type = "Epic"

    return [{
        "create": True,
        "issue_type": issue_type,
        "summary": issue_match.group(1).strip(),
        "description": text,
        "priority": priority,
        "assignee_username": assignee_username,
        "auto_assign": auto_assign,
        "due_date": None,
        "label_names": shared_labels,
    }]


def _normalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    issues = plan.get("issues")
    single_issue = plan.get("issue")

    if not issues and single_issue:
        issues = [single_issue]
    elif issues is None:
        issues = []

    normalized_issues = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        normalized_issues.append({
            "create": bool(issue.get("create", True)),
            "issue_type": issue.get("issue_type") or "Story",
            "summary": issue.get("summary"),
            "description": issue.get("description"),
            "priority": issue.get("priority"),
            "assignee_username": issue.get("assignee_username"),
            "auto_assign": bool(issue.get("auto_assign", False)),
            "due_date": issue.get("due_date"),
            "label_names": issue.get("label_names") or [],
        })

    primary_issue = normalized_issues[0] if normalized_issues else {
        "create": False,
        "issue_type": "Story",
        "summary": None,
        "description": None,
        "priority": None,
        "assignee_username": None,
        "auto_assign": False,
        "due_date": None,
        "label_names": [],
    }

    plan["issues"] = normalized_issues
    plan["issue"] = primary_issue
    return plan


def _derive_project_key(project_name: str | None) -> str | None:
    if not project_name:
        return None
    letters = re.sub(r"[^A-Za-z0-9 ]+", "", project_name).strip().split()
    if not letters:
        return None
    if len(letters) == 1:
        return letters[0][:4].upper()
    return "".join(word[0] for word in letters[:5]).upper()
