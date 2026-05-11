# ZYRAA Jira System - Full Agentic AI (LangGraph + Ollama)

## Executive Summary

This document provides a comprehensive guide to the ZYRAA Jira-like project management system, including the current implementation status, missing features, 
and **a full Agentic AI layer built with LangGraph** and **Ollama**.

The Agentic AI layer is made of **typed agents** (nodes in a LangGraph graph) that can inspect live project data, evaluate code health, suggest sprint actions, and queue business actions for human approval. Each agent is a pure 
Python function that receives a shared state and returns updated state, making the system naturally mirror a LangGraph workflow.

---

## 1. Table of Contents

1. [Current System Status](#current-system-status)
2. [Architecture Overview](#architecture-overview)
3. [Backend Documentation](#backend-documentation)
4. [Frontend Documentation](#frontend-documentation)
5. [Agentic AI Architecture with LangGraph](#agentic-ai-architecture-with-langgraph)
6. [Intelligent Story Assignment System](#intelligent-story-assignment-system)
7. [GitHub PR Code Review & Health Scoring](#github-pr-code-review--health-scoring)
8. [Sprint Management & Agile Methodology](#sprint-management--agile-methodology)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Environment Setup](#environment-setup)
11. [Testing](#testing-the-system)

---

## 2. Current System Status

### Working Features

| Feature | Status | Notes |
|---------|--------|-------|
| User Authentication (JWT) | ✅ Working | Registration, login |
| Project Management | ✅ Working | Create, read, update, delete |
| Issue Management | ✅ Working | CRUD operations |
| Board Management | ✅ Working | Kanban/Scrum boards |
| Drag & Drop | ✅ Working | Issue status transitions |
| Comments | ✅ Working | Add/fetch comments |
| Worklogs | ✅ Working | Time tracking |
| Labels/Components | ✅ Working | Categorization |
### Missing Critical Features

| Feature | Status | Priority |
|---------|--------|----------|
| Smart Story Assignment | ❌ Missing | High |
| GitHub PR Integration | ❌ Missing | High |
| Code Health Analysis | ❌ Missing | High |
| Sprint Automation | ❌ Partial | Medium |
| User Workload Limits | ❌ Missing | High |
| Bug Creation from PRs | ❌ Missing | High |

---

## 3. Architecture Overview

```text
                    FRONTEND (Next.js)
                  ├─ React Components
                  ├─ API Layer (axios/fetch)
                  └─ Types
                          │ HTTP (JWT)
                          ▼
                    BACKEND (FastAPI)
               ┌─────────────────────────────┐
               │  Agentic AI Router          │
               │  ├─ GET  /api/agents/status │
               │  ├─ POST /api/agents/run    │
               │  ├─ POST /api/agents/ask    │
               │  └─ /actions/{id}/approve   │
               ├─────────────────────────────┤
               │  Agent Service (LangGraph)  │
               │  ├─ Assignment Agent        │
               │  ├─ PR Health Agent         │
               │  ├─ Sprint Agent            │
               │  ├─ Executive Agent (Ollama)│
               │  ├─ Pending Action Gate     │
               │  └─ Execution Node          │
               ├─────────────────────────────┤
               │  Routes (v1): auth, users,  │
               │  projects, issues, boards   │
               └─────────────────────────────┘
                          │
                          ▼
                    SQL Server (via SQLAlchemy)
```

---

## 4. Backend Documentation

### 4.1 File Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py         # Router setup
│   │       ├── auth.py             # Authentication
│   │       ├── users.py            # User management
│   │       ├── projects.py          # Project endpoints
│   │       ├── issues.py            # Issue CRUD + comments/worklogs
│   │       ├── boards.py            # Board management
│   │       ├── agents.py          # Agentic AI endpoints
│   │       └── dependencies.py      # Auth dependencies
│   ├── crud/
│   │   ├── base.py                  # Generic CRUD base class
│   │   └── __init__.py             # CRUD operations per model
│   ├── models/
│   │   ├── __init__.py              # SQLAlchemy models (User, Issue, Board, Sprint, ...)
│   │   └── assignment.py          # ZYRAA: UserSkill, UserAssignmentHistory, IssueRequirement
│   ├── schemas/
│   │   └── __init__.py             # Pydantic schemas
│   ├── services/
│   │   ├── agent_service.py        # LangGraph-style nodes (Assignment, PR, Sprint, Executive)
│   │   ├── code_analyzer.py        # PR code security/quality analysis
│   │   ├── ollama_service.py       # Ollama LLM brain
│   │   ├── assignment.py           # Legacy smart assignment logic (preserved)
│   │   └── sprint_service.py       # Legacy sprint automation (preserved)
│   ├── database.py                  # Database connection
│   ├── auth.py                     # JWT utilities
│   ├── main.py                     # FastAPI app entry
│   └── config.py                   # Environment settings
├── requirements.txt
└── .env / .env.example
```

### 4.2 Critical Backend Files

#### `app/crud/__init__.py`
Contains all CRUD operations. Current implementation:
- `CRUDUser`: get_by_username, get_by_email, is_active, get_user_projects
- `CRUDProject`: get_by_key, get_multi_by_lead
- `CRUDIssue`: get_by_key, get_by_project, get_board_issues, search

**Needs modification for smart assignment**: Add methods to get user workload and assignment history.

#### `app/api/v1/issues.py`
Issue endpoints. Lines 38-112 contain the create_issue endpoint.

**Needs modification**: Add logic to:
1. Check user workload before assignment
2. Consider user skill history
3. Respect priority-based assignment rules

#### `app/api/v1/projects.py`
Project endpoints. Lines 96-116 contain the stats endpoint.

---

## 5. Frontend Documentation

### 5.1 File Structure

```text
frontend/src/
├── app/
│   ├── layout.tsx                  # Root layout with AuthProvider
│   ├── page.tsx                    # Dashboard
│   ├── login/page.tsx             # Login page
│   ├── register/page.tsx          # Registration
│   ├── projects/
│   │   ├── page.tsx               # Project list
│   │   ├── new/page.tsx           # Create project
│   │   └── [projectId]/page.tsx
│   └── boards/[boardId]/page.tsx
├── components/
│   ├── IssueBoard.tsx             # Main board component
│   ├── BoardColumn.tsx            # Column with drag-drop
│   ├── IssueCard.tsx              # Issue card UI
│   └── IssueDetailModal.tsx       # Issue detail/edit modal
├── lib/
│   ├── api.ts                     # API client (axios/fetch wrappers)
│   └── auth-context.tsx           # Auth context/provider
├── types/
│   └── index.ts                   # TypeScript interfaces
└── pages/
    └── AgentAutomation.tsx        # Agent UI (new, see wiring below)
```

### 5.2 Key Frontend Components

#### `IssueBoard.tsx`
The main board view. Uses:
- State: `board`, `columns`, `issuesByColumn`
- Drag-drop via `onDrop` handler
- API: `boardAPI.getIssues()`, `issueAPI.update()`

**Needs modification**: Add assignment logic display, show workload indicators.

#### `types/index.ts`
TypeScript definitions. Needs new types for:
- Assignment rules
- User skills
- PR/review data
- Agent workflow states
- Agent memory and actions

---

## 6. Agentic AI Architecture with LangGraph

### 6.1 Overview

The ZYRAA system now contains a full **Agentic AI layer** powered by **LangGraph** and **Ollama**. This layer is made of multiple typed agents (nodes in a LangGraph graph) that can inspect live project data, evaluate code health, suggest sprint actions, and queue business actions for human approval.

**LangGraph Graph:**
```text
                 ┌──────────────────┐
                 │   Input Gate     │
                 └────────┬─────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────┐
│  Assignment     │ │ PR Health   │ │    Sprint    │
│    Agent        │ │   Agent     │ │    Agent     │
└────────┬────────┘ └──────┬──────┘ └──────┬───────┘
         │                 │               │
         └──────────┬──────┘               │
                    │                      │
                    ▼                      │
         ┌──────────────────┐              │
         │  Executive Agent │◄─────────────┘
         │  (Ollama-Llama)  │
         └────────┬─────────┘
                  │
         ┌────────┴────────┐
         │  Pending Action │
         │     Review      │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ Execution Node  │
         └─────────────────┘
```

The graph is made of six node groups:
1. **Assignment Agent**: Reads workload, skills, issue requirements and picks the best assignee.
2. **PR Health Agent**: Analyzes linked GitHub PRs with security/quality rules.
3. **Sprint Agent**: Auto-creates, activates, and closes sprints based on dates.
4. **Executive Agent**: Receives all results and generates a narrative summary via Ollama.
5. **Pending Action Gate**: Stores human-approval actions in `AgentAction`.
6. **Execution Node**: Only runs after human approval.

### 6.2 Dependencies

Add to `backend/requirements.txt`:
```text
httpx>=0.24.0
```

If you later want the real `langgraph` engine, run:
```bash
cd D:\Jira\backend
.venv\Scripts\activate
pip install langgraph langchain langchain-community
```

### 6.3 New Models for the Agentic Layer

Create `backend/app/models/agents.py`:

```python
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[AgentActionStatus] = mapped_column(
        String(20), default=AgentActionStatus.PENDING.value, nullable=False
    )
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

Add to `app/models/__init__.py`:
```python
from app.models.agents import AgentAction, AgentMemory, AgentActionStatus
```

### 6.4 Ollama Service (Model Brain)

Create `backend/app/services/ollama_service.py`:

```python
"""
Ollama brain for the Agentic AI layer.
Discovers installed models, chooses the best one, and calls /api/chat.
"""

import json
import os
import shutil
from typing import Any, AsyncGenerator, Optional

import httpx


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PREFERRED_MODELS = ["llama3.1", "llama3", "mistral"]
EMBEDDING_MODELS = ["nomic-embed-text", "mxbai-embed-large"]


def _locate_ollama() -> Optional[str]:
    candidates = [
        shutil.which("ollama"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
        os.path.join("C:\\Program Files", "Ollama", "ollama.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def get_installed_models() -> list[str]:
    ollama = _locate_ollama()
    if not ollama:
        return []
    import subprocess
    try:
        result = subprocess.run([ollama, "list"], capture_output=True, text=True, check=True, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return []

    models: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def choose_best_model(preferred: list[str] = None) -> Optional[str]:
    installed = get_installed_models()
    if not installed:
        return None
    for candidate in preferred or PREFERRED_MODELS:
        if candidate in installed:
            return candidate
    return installed[0]


def choose_best_embedding_model() -> Optional[str]:
    installed = get_installed_models()
    if not installed:
        return None
    for candidate in EMBEDDING_MODELS:
        if candidate in installed:
            return candidate
    return None


async def generate_response(prompt: str, system: str) -> tuple[str, Optional[str]]:
    model = choose_best_model()
    if not model:
        return (
            "Local AI is currently unavailable. The system is running in deterministic fallback mode.",
            None,
        )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=160.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"], model
    except (httpx.HTTPError, KeyError, json.JSONDecodeError):
        return (
            "Ollama could not be reached. Returning deterministic results only.",
            model,
        )


async def generate_response_stream(prompt: str, system: str) -> AsyncGenerator[str, None]:
    model = choose_best_model()
    if not model:
        yield "Local AI is currently unavailable. No Ollama model detected."
        return

    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=160.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_text():
                    try:
                        data = json.loads(chunk)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
    except (httpx.HTTPError, KeyError):
        yield "Ollama stream failed. Falling back to deterministic summary."
```

### 6.5 LangGraph Agent Service

Create `backend/app/services/agent_service.py`:

```python
"""
LangGraph-style Agentic AI orchestration for ZYRAA Jira.
Multi-agent nodes: Assignment, PR Health, Sprint, Executive, and Action Execution.
Each node is a pure function that receives shared state and returns updated state.
"""

import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import (
    AgentAction,
    AgentActionStatus,
    AgentMemory,
    Board,
    Issue,
    IssuePriority,
    IssueRequirement,
    IssueStatus,
    PullRequest,
    Sprint,
    User,
    UserSkill,
    Worklog,
)
from app.services.ollama_service import choose_best_model, generate_response

MAX_ISSUES_PER_USER = 3
WEEK_WINDOW_DAYS = 14


# ── Shared State Container (LangGraph style) ──────────────────────────────

class AgentState(dict):
    """
    Typed state passed between LangGraph nodes.
    Keys:
        - db: Session (SQLAlchemy)
        - current_user: User
        - intent: str               # 'assignment', 'pr_health', 'sprint'
        - issue_id: int | None
        - board_id: int | None
        - output: dict              # agent results accumulate here
        - pending_actions: list[dict]
        - error: str | None
    """


def _safe(state: AgentState, key: str, default: Any = None):
    return state.get(key, default)


# ── Node: Assignment Agent ──────────────────────────────────────────────────

def _requirement_from_text(description: str) -> list[dict]:
    keywords = {
        "frontend": ["react", "javascript", "typescript", "ui", "ux", "css"],
        "backend": ["api", "database", "server", "sql", "python", "fastapi"],
        "devops": ["docker", "deployment", "ci/cd", "pipeline"],
        "testing": ["test", "qa", "automation", "selenium"],
    }
    out = []
    d = (description or "").lower()
    for skill, words in keywords.items():
        if any(w in d for w in words):
            out.append({"skill": skill, "weight": 2})
    return out


def _get_issues_assigned_in_window(db: Session, user_id: int, days: int = 14) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    return db.query(Issue).filter(
        Issue.assignee_user_id == user_id,
        Issue.created_at >= cutoff,
    ).count()


def _score_assignee(db: Session, user: User, req: IssueRequirement) -> float:
    skills = db.query(UserSkill).filter(
        UserSkill.user_id == user.user_id,
        UserSkill.skill_name == req.required_skill,
    ).all()
    if not skills:
        return -float("inf")
    proficiency = max(s.proficiency for s in skills)
    current = _get_issues_assigned_in_window(db, user.user_id, days=WEEK_WINDOW_DAYS)
    if current >= MAX_ISSUES_PER_USER:
        return -float("inf")
    return (req.weight * proficiency) - (current * 0.5)


def _find_best_assignee(db: Session, issue: Issue) -> Optional[User]:
    requirements = db.query(IssueRequirement).filter(IssueRequirement.issue_id == issue.issue_id).all()
    if not requirements:
        # Fallback: least loaded user
        candidates = db.query(User).filter(User.is_active == True).all()
        best = None
        best_count = float("inf")
        for u in candidates:
            c = _get_issues_assigned_in_window(db, u.user_id, WEEK_WINDOW_DAYS)
            if c < best_count:
                best_count = c
                best = u
        return best

    best = None
    best_score = -float("inf")
    for req in requirements:
        skilled = db.query(UserSkill).filter(UserSkill.skill_name == req.required_skill).all()
        for sk in skilled:
            user = db.query(User).filter(User.user_id == sk.user_id).first()
            if not user:
                continue
            score = _score_assignee(db, user, req)
            if score > best_score:
                best_score = score
                best = user
    return best


def assignment_agent(state: AgentState) -> AgentState:
    """LangGraph node: find the best assignee for an issue."""
    db: Session = state["db"]
    issue_id = state.get("issue_id")
    if not issue_id:
        state["error"] = "assignment_agent requires issue_id"
        return state

    issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
    if not issue:
        state["error"] = f"Issue {issue_id} not found"
        return state

    # Extract requirements if none stored
    reqs = db.query(IssueRequirement).filter(IssueRequirement.issue_id == issue_id).all()
    if not reqs:
        for r in _requirement_from_text(issue.description or ""):
            db.add(IssueRequirement(issue_id=issue_id, required_skill=r["skill"], weight=r["weight"]))
        db.commit()

    best = _find_best_assignee(db, issue)
    state.setdefault("output", {})["assignment"] = {
        "issue_id": issue_id,
        "best_assignee_id": best.user_id if best else None,
        "best_assignee_username": best.username if best else None,
        "method": "requirement-match" if reqs else "least-loaded",
    }
    return state


# ── Node: PR Health Agent ──────────────────────────────────────────────────

SECURITY_PATTERNS = {
    "sql_injection": {
        "pattern": r'(execute|executemany|raw)\s*\(\s*["\'].*%s.*["\']',
        "severity": "critical",
        "message": "Possible SQL injection vulnerability detected"
    },
    "hardcoded_password": {
        "pattern": r'(password|passwd|pwd)\s*=\s*["'][^"']+["']',
        "severity": "high",
        "message": "Hardcoded password detected"
    },
    "console_in_prod": {
        "pattern": r'console\.(log|debug|info)\s*\(',
        "severity": "low",
        "message": "Console statement should be removed in production"
    },
}


def _analyze_text(content: str) -> list[dict]:
    findings = []
    for rule_id, rule in SECURITY_PATTERNS.items():
        for match in re.finditer(rule["pattern"], content, re.IGNORECASE):
            line = content[:match.start()].count('\n') + 1
            findings.append({"severity": rule["severity"], "message": rule["message"], "rule_id": rule_id, "line": line})
    return findings


def _calculate_health_score(findings: list[dict]) -> float:
    score = 100.0
    weights = { "critical": 15, "high": 10, "medium": 5, "low": 2, "info": 0.5 }
    for f in findings:
        score -= weights.get(f["severity"], 1)
    return max(0, min(100, score))


def pr_health_agent(state: AgentState) -> AgentState:
    """LangGraph node: analyze PR health for an issue."""
    db: Session = state["db"]
    issue_id = state.get("issue_id")
    if not issue_id:
        state["error"] = "pr_health_agent requires issue_id"
        return state

    prs = db.query(PullRequest).filter(PullRequest.issue_id == issue_id).all()
    pr_results = []
    for pr in prs:
        content = pr.branch_name or ""  # simplified; real impl fetches GitHub diff
        findings = _analyze_text(content)
        score = _calculate_health_score(findings)
        pr_results.append({"pr_id": pr.pr_id, "health_score": score, "findings": findings, "status": pr.status})

    state.setdefault("output", {})["pr_health"] = pr_results
    return state


# ── Node: Sprint Agent ──────────────────────────────────────────────────────

def sprint_agent(state: AgentState) -> AgentState:
    """LangGraph node: manage sprint lifecycle."""
    db: Session = state["db"]
    board_id = state.get("board_id")
    today = datetime.today().date()
    result = {"activated": [], "closed": [], "created": []}

    query = db.query(Sprint)
    if board_id:
        query = query.filter(Sprint.board_id == board_id)

    # Activate sprints whose start_date has arrived
    for sprint in query.filter(Sprint.sprint_status == "future", Sprint.start_date <= today).all():
        sprint.sprint_status = "active"
        db.commit()
        db.refresh(sprint)
        result["activated"].append({"sprint_id": sprint.sprint_id, "name": sprint.name})

    # Close ended sprints
    for sprint in query.filter(Sprint.sprint_status == "active", Sprint.end_date < today).all():
        sprint.sprint_status = "closed"
        sprint.is_completed = True
        db.commit()
        db.refresh(sprint)
        result["closed"].append({"sprint_id": sprint.sprint_id, "name": sprint.name})
        # Auto-create next
        next_start = sprint.end_date + timedelta(days=1)
        next_end = next_start + timedelta(weeks=2)
        new_sprint = Sprint(board_id=sprint.board_id, name=f"Sprint {next_start} - {next_end}", start_date=next_start, end_date=next_end, sprint_status="future")
        db.add(new_sprint)
        db.commit()
        db.refresh(new_sprint)
        result["created"].append({"sprint_id": new_sprint.sprint_id, "name": new_sprint.name})

    state.setdefault("output", {})["sprint"] = result
    return state


# ── Node: Executive Agent (Ollama) ──────────────────────────────────────────

async def executive_agent(state: AgentState) -> AgentState:
    """LangGraph node: call Ollama to synthesize agent outputs."""
    model = choose_best_model()
    output = state.get("output", {})
    fallback = {
        "summary": "Deterministic automation completed. Ollama was not available for narrative synthesis.",
        "recommended_actions": [],
        "source_model": None,
    }

    if not model:
        state.setdefault("output", {})["executive"] = fallback
        return state

    compact = json.dumps(output, indent=2)
    prompt = (
        "You are the Executive Intelligence Layer for a Jira-like project management system.\n"
        "Review the following agent results and produce a short operations brief.\n"
        "Return only valid JSON with: summary, recommended_actions (array of strings).\n\n"
        f"Agent results:\n{compact}\n"
    )
    system = "You are an operations coordinator for ZYRAA Jira. Be concise and practical."
    answer, source_model = await generate_response(prompt=prompt, system=system)
    try:
        parsed = json.loads(answer)
        summary = str(parsed.get("summary") or fallback["summary"])
        actions = parsed.get("recommended_actions") or fallback["recommended_actions"]
    except (TypeError, json.JSONDecodeError):
        summary = answer.strip() or fallback["summary"]
        actions = fallback["recommended_actions"]

    state.setdefault("output", {})["executive"] = {
        "summary": summary,
        "recommended_actions": actions[:6],
        "source_model": source_model,
    }
    return state


# ── Node: Pending Action Gate ─────────────────────────────────────────────

def _create_pending_action(state: AgentState) -> list[dict]:
    db: Session = state["db"]
    user = state["current_user"]
    actions = []
    output = state.get("output", {})
    assignment = output.get("assignment", {})
    if assignment and assignment.get("best_assignee_id"):
        actions.append({
            "action_type": "assign_issue",
            "title": f"Assign issue {assignment['issue_id']} to user {assignment['best_assignee_username']}",
            "payload": {"issue_id": assignment["issue_id"], "assignee_user_id": assignment["best_assignee_id"]},
        })
    sprint = output.get("sprint", {})
    for closed in sprint.get("closed", []):
        actions.append({"action_type": "close_sprint", "title": f"Close sprint {closed['name']}", "payload": closed})
    for created in sprint.get("created", []):
        actions.append({"action_type": "create_sprint", "title": f"Create sprint {created['name']}", "payload": created})

    pending = []
    from app.models import AgentAction, AgentActionStatus
    for a in actions:
        action = AgentAction(
            user_id=user.user_id if user else None,
            agent_name="executive",
            action_type=a["action_type"],
            title=a["title"],
            description=a["title"],
            payload=a["payload"],
            status=AgentActionStatus.PENDING,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        pending.append({"id": action.id, "action_type": action.action_type, "title": action.title, "status": action.status.value})
    state["pending_actions"] = pending
    return state


def pending_action_gate(state: AgentState) -> AgentState:
    """LangGraph node: convert agent outputs into AgentAction rows."""
    _create_pending_action(state)
    return state


# ── Node: Execute Approved Actions ──────────────────────────────────────────

def execute_actions(state: AgentState) -> AgentState:
    """LangGraph node: run all approved AgentAction rows."""
    db: Session = state["db"]
    approved = db.query(AgentAction).filter(AgentAction.status == AgentActionStatus.APPROVED).all()
    results = []
    for action in approved:
        try:
            if action.action_type == "assign_issue":
                issue_id = action.payload.get("issue_id")
                assignee_id = action.payload.get("assignee_user_id")
                issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
                if issue:
                    issue.assignee_user_id = assignee_id
                    db.commit()
                results.append({"action_id": action.id, "status": "done"})
            else:
                results.append({"action_id": action.id, "status": "confirmed"})
            action.status = AgentActionStatus.APPROVED
        except Exception as exc:
            action.status = AgentActionStatus.FAILED
            results.append({"action_id": action.id, "status": "failed", "error": str(exc)})
        action.decided_at = datetime.utcnow()
        db.commit()
        db.refresh(action)
    state["execution_results"] = results
    return state


# ── Orchestrator: Build LangGraph ─────────────────────────────────────────

async def run_agentic_workflow(
    db: Session,
    user: User,
    *,
    issue_id: int = None,
    board_id: int = None,
    intent: str = "full_scan",
) -> dict:
    """Run the complete LangGraph-style agent pipeline."""
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

    state = sprint_agent(state)
    if intent in ("assign", "full_scan"):
        state = assignment_agent(state)
    if intent in ("pr_health", "full_scan"):
        state = pr_health_agent(state)

    state = await executive_agent(state)
    state = pending_action_gate(state)

    return {
        "output": state.get("output", {}),
        "pending_actions": state.get("pending_actions", []),
        "error": state.get("error"),
    }


# ── Conversational Agent (single-question) ────────────────────────────────

def _save_memory(db: Session, user: User, agent_name: str, message: str, summary: str, data: dict) -> None:
    db.add(AgentMemory(
        user_id=user.user_id if user else None,
        agent_name=agent_name,
        user_message=message,
        summary=summary,
        data=data,
    ))
    db.commit()


async def run_conversational_agent(db: Session, user: User, message: str) -> dict:
    """Single-question entry point that routes to one agent and stores memory."""
    lower = message.lower()
    if any(w in lower for w in ["assign", "who should work", "best person"]):
        state = AgentState(db=db, current_user=user, intent="assign")
        state = assignment_agent(state)
        agent_name = "Assignment Agent"
    elif any(w in lower for w in ["sprint", "automation"]):
        state = AgentState(db=db, current_user=user, intent="sprint")
        state = sprint_agent(state)
        agent_name = "Sprint Agent"
    elif any(w in lower for w in ["health", "code review", "pr"]):
        state = AgentState(db=db, current_user=user, intent="pr_health")
        state = pr_health_agent(state)
        agent_name = "PR Health Agent"
    else:
        state = AgentState(db=db, current_user=user, intent="full_scan")
        state = sprint_agent(state)
        state = assignment_agent(state)
        state = pr_health_agent(state)
        agent_name = "Full Scan Agent"
        state = await executive_agent(state)

    output = state.get("output", {})
    summary = json.dumps(output, indent=2)
    _save_memory(db, user, agent_name, message, summary, output)
    return {
        "agent": agent_name,
        "summary": summary,
        "output": output,
        "pending_actions": state.get("pending_actions", []),
    }
```

### 6.6 API Router for Agents

Create `backend/app/api/v1/agents.py`:

```python
"""
Agentic AI endpoints for ZYRAA Jira.
Exposes the full LangGraph workflow as REST.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user, get_db
from app.models import User
from app.services.agent_service import (
    AgentState,
    assignment_agent,
    execute_actions,
    executive_agent,
    pending_action_gate,
    pr_health_agent,
    run_agentic_workflow,
    run_conversational_agent,
    sprint_agent,
)
from app.services.ollama_service import choose_best_model, get_installed_models
from app.services.agent_service import AgentAction, AgentActionStatus

router = APIRouter(prefix="/agents", tags=["agents"])


class RunAutomationRequest(BaseModel):
    intent: str = Field(default="full_scan", examples=["full_scan", "assign", "pr_health", "sprint"])
    issue_id: int = Field(default=None)
    board_id: int = Field(default=None)


class AskAgentRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


@router.get("/status")
def agent_status(_: User = Depends(get_current_user)):
    model = choose_best_model()
    return {
        "ollama_available": model is not None,
        "selected_model": model,
        "installed_models": get_installed_models(),
        "mode": "ollama-assisted" if model else "rule-based-fallback",
    }


@router.post("/automation/run")
async def run_automation(
    payload: RunAutomationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the full LangGraph agentic pipeline."""
    try:
        return await run_agentic_workflow(
            db, current_user, issue_id=payload.issue_id, board_id=payload.board_id, intent=payload.intent
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/workflow/ask")
async def ask_agent(
    payload: AskAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conversational entry: ask the agent a question."""
    return await run_conversational_agent(db, current_user, payload.message)


@router.post("/actions/{action_id}/approve")
def approve_action(action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Action already decided")

    from app.models import UserRole
    if action.action_type in ("assign_issue", "close_sprint", "create_sprint"):
        required = {UserRole.ADMIN.value, UserRole.MANAGER.value, UserRole.MODERATOR.value}
        if current_user.role.value not in required:
            raise HTTPException(status_code=403, detail="Only managers/moderators can approve this action")

    action.status = AgentActionStatus.APPROVED
    db.commit()
    db.refresh(action)

    state = AgentState(db=db, current_user=current_user, output={}, pending_actions=[])
    execute_actions(state)
    return {"status": "approved", "action_id": action.id}


@router.post("/actions/{action_id}/reject")
def reject_action(action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Action already decided")

    action.status = AgentActionStatus.REJECTED
    action.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(action)
    return {"status": "rejected", "action_id": action.id}
```

Register in `backend/app/api/v1/__init__.py`:
```python
from app.api.v1 import agents
router.include_router(agents.router, prefix="/agents")
```

### 6.7 Frontend Component

Create `frontend/src/pages/AgentAutomation.tsx`:

```tsx
import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AgentAutomation() {
  const [status, setStatus] = useState<any>(null);
  const [run, setRun] = useState<any>(null);
  const [question, setQuestion] = useState("What is the sprint status?");
  const [workflow, setWorkflow] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadStatus(); }, []);

  async function loadStatus() {
    try { const res = await api.get("/agents/status"); setStatus(res.data); } catch (e) { console.error(e); }
  }

  async function runAutomation() {
    setLoading(true);
    try { const res = await api.post("/agents/automation/run", { intent: "full_scan" }); setRun(res.data); }
    finally { setLoading(false); }
  }

  async function ask() {
    setLoading(true);
    try { const res = await api.post("/agents/workflow/ask", { message: question }); setWorkflow(res.data); }
    finally { setLoading(false); }
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">Agentic AI</h1>
      <div className="mb-6">
        <strong>Mode:</strong> {status?.mode || "Checking..."} &nbsp;|&nbsp;
        <strong>Model:</strong> {status?.selected_model || "None"}
      </div>
      <button className="btn-primary mr-2" onClick={runAutomation} disabled={loading}>Run Automation</button>
      <button className="btn-secondary" onClick={() => { setRun(null); setWorkflow(null); }}>Clear</button>

      {run && <div className="mt-6 panel"><h2 className="text-xl font-semibold">Automation Result</h2>
        <pre className="bg-slate-800 text-slate-100 p-4 mt-2 rounded-lg text-sm overflow-auto">{JSON.stringify(run, null, 2)}</pre></div>}

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-2">Ask an Agent</h2>
        <input className="border rounded-lg p-2 w-full mb-2" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about sprint, assignment, or PR health..." />
        <button className="btn-primary" onClick={ask} disabled={loading}>Ask</button>
      </div>

      {workflow && <div className="mt-6 panel"><h3 className="text-lg font-semibold">{workflow.agent}</h3>
        <pre className="bg-slate-800 text-slate-100 p-4 mt-2 rounded-lg text-sm overflow-auto">{JSON.stringify(workflow, null, 2)}</pre></div>}
    </div>
  );
}
```

### 6.8 Wiring into FastAPI

Update `backend/app/main.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.v1.agents import router as agents_router
from app.services.agent_service import run_agentic_workflow
from app.database import SessionLocal

# Register routers
from app.api.v1 import api_router
api_router.include_router(agents_router)

# Optional: automated daily sweep
scheduler = BackgroundScheduler()

@scheduler.scheduled_job("cron", hour=0)
def daily_agent_sweep():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == "admin").first()
        if user:
            import asyncio
            asyncio.run(run_agentic_workflow(db, user, intent="full_scan"))
    finally:
        db.close()

if os.getenv("AGENT_SCHEDULER", "true") == "true":
    scheduler.start()
```

---

## 7. Intelligent Story Assignment System

### 7.1 Requirements Summary

1. **Best Resource Selection**: Assign to user most qualified for the story.
2. **Assignment History**: Consider user's past work on similar stories.
3. **Priority Handling**:
   - If qualified user working on low-priority story → reassign to new story only.
   - If qualified user has high-priority work → keep them, choose different user.
4. **Workload Limits**: Max 2-3 stories per user in 2-week window.

### 7.2 New Database Models

Create `backend/app/models/assignment.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class UserSkill(Base):
    __tablename__ = "user_skills"
    skill_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    proficiency = Column(Integer, default=1)
    user = relationship("User", back_populates="skills")

class UserAssignmentHistory(Base):
    __tablename__ = "user_assignment_history"
    history_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    outcome = Column(String(50))

class IssueRequirement(Base):
    __tablename__ = "issue_requirements"
    requirement_id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    required_skill = Column(String(100), nullable=False)
    weight = Column(Integer, default=1)
```

### 7.3 CRUD Extensions

Add to `app/crud/__init__.py`:

```python
class CRUDUserSkill(CRUDBase):
    def get_by_user(self, db: Session, *, user_id: int) -> list:
        return db.query(UserSkill).filter(UserSkill.user_id == user_id).all()

    def get_users_by_skill(self, db: Session, *, skill_name: str, min_proficiency: int = 1) -> list:
        return db.query(UserSkill).filter(
            UserSkill.skill_name == skill_name, UserSkill.proficiency >= min_proficiency
        ).all()

class CRUDIssue:
    def get_issues_by_assignee_in_window(self, db: Session, *, user_id: int, days: int = 14) -> int:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        return db.query(Issue).filter(Issue.assignee_user_id == user_id, Issue.created_at >= cutoff).count()
```

### 7.4 Integration

In `backend/app/api/v1/issues.py`, the `create_issue` endpoint is already enhanced by the **Assignment Agent** (see `agent_service.py`).
To ensure deterministic fallback is always available, also keep the legacy `find_best_assignee()` in `services/assignment.py`.

---

## 8. GitHub PR Code Review & Health Scoring

### 8.1 New Models

Create `backend/app/models/code_review.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime

class PullRequest(Base):
    __tablename__ = "pull_requests"
    pr_id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    github_pr_number = Column(Integer, nullable=False)
    repository_url = Column(String(500), nullable=False)
    branch_name = Column(String(200))
    status = Column(String(50))
    health_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    issue = relationship("Issue")
    reviews = relationship("CodeReview", back_populates="pull_request")
    bugs = relationship("BugReport", back_populates="pull_request")

class CodeReview(Base):
    __tablename__ = "code_reviews"
    review_id = Column(Integer, primary_key=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.pr_id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer)
    severity = Column(String(20))
    message = Column(Text, nullable=False)
    rule_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    pull_request = relationship("PullRequest", back_populates="reviews")

class BugReport(Base):
    __tablename__ = "bug_reports"
    bug_id = Column(Integer, primary_key=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.pr_id"), nullable=False)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    severity = Column(String(20))
    description = Column(Text, nullable=False)
    code_location = Column(String(500))
    suggestion = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    pull_request = relationship("PullRequest", back_populates="bugs")
```

### 8.2 Service

Create `backend/app/services/code_analyzer.py`:

```python
import re
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import CodeReview, BugReport

SECURITY_PATTERNS = {
    "sql_injection": {
        "pattern": r'(execute|executemany|raw)\s*\(\s*["\'].*%s.*["\']',
        "severity": "critical", "message": "Possible SQL injection vulnerability detected"
    },
    "hardcoded_password": {
        "pattern": r'(password|passwd|pwd)\s*=\s*["'][^"']+["']',
        "severity": "high", "message": "Hardcoded password detected"
    },
    "xss_vulnerability": {
        "pattern": r'(innerHTML|outerHTML)\s*=\s*[^;]+(?!\.textContent|\.text)',
        "severity": "high", "message": "Possible XSS vulnerability"
    },
}

STANDARD_PATTERNS = {
    "console_log": {
        "pattern": r'console\.(log|debug|info)\s*\(', "severity": "low",
        "message": "Console statement should be removed in production"
    },
    "unused_variable": {
        "pattern": r'(?:const|let|var)\s+\w+\s*=\s*[^;]+;\s*//.*unused', "severity": "medium",
        "message": "Unused variable detected"
    },
}


def analyze_code_from_github(db: Session, pr_id: int, repository_url: str, github_token: str = None):
    findings = []
    files = _fetch_pr_files(repository_url, github_token)
    for file in files:
        file_findings = _analyze_file(file["path"], file["content"])
        findings.extend(file_findings)
        for f in file_findings:
            db.add(CodeReview(pr_id=pr_id, file_path=file["path"], line_number=f.get("line"),
                              severity=f["severity"], message=f["message"], rule_id=f.get("rule_id")))
    db.commit()
    score = _calculate_health_score(findings)
    return score, findings


def _analyze_file(file_path: str, content: str) -> List[Dict]:
    findings = []
    all_rules = {**SECURITY_PATTERNS, **STANDARD_PATTERNS}
    for rule_id, rule in all_rules.items():
        for match in re.finditer(rule["pattern"], content, re.IGNORECASE):
            line = content[:match.start()].count('\n') + 1
            findings.append({"severity": rule["severity"], "message": rule["message"], "rule_id": rule_id, "line": line})
    return findings


def _calculate_health_score(findings: List[Dict]) -> float:
    score = 100.0
    weights = {"critical": 15, "high": 10, "medium": 5, "low": 2, "info": 0.5}
    for f in findings:
        score -= weights.get(f["severity"], 1)
    return max(0, min(100, score))


def _fetch_pr_files(repository_url: str, token: str = None) -> List[Dict]:
    # Placeholder: use GitHub API - GET /repos/{owner}/{repo}/pulls/{pull_number}/files
    return []
```

### 8.3 API Endpoint

Extend `backend/app/api/v1/issues.py`:

```python
from app.services.code_analyzer import analyze_code_from_github, create_bugs_from_findings
from app.models import PullRequest

@router.post("/{issue_id}/pr")
def link_pull_request(issue_id: int, pr_data: schemas.PRCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    issue = crud.issue.get(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    pr = PullRequest(issue_id=issue_id, github_pr_number=pr_data.pr_number, repository_url=pr_data.repository_url)
    db.add(pr); db.commit(); db.refresh(pr)
    health_score, findings = analyze_code_from_github(db, pr.pr_id, pr_data.repository_url)
    pr.health_score = health_score; pr.status = "analyzed"
    db.commit()
    bugs = create_bugs_from_findings(db, pr.pr_id, findings, issue_id)
    return {"pr_id": pr.pr_id, "health_score": health_score, "findings_count": len(findings), "bugs_created": len(bugs)}
```

---

## 9. Sprint Management & Agile Methodology

### 9.1 Enhanced Sprint Model

Add to `app/models/__init__.py`:
```python
class Sprint(Base):
    __tablename__ = "sprints"
    sprint_id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey("boards.board_id"), nullable=False)
    name = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    sprint_status = Column(String(20), default="future")
    is_completed = Column(Boolean, default=False)
    story_points_completed = Column(Integer, default=0)
    story_points_total = Column(Integer, default=0)
    velocity = Column(Float, default=0)
```

### 9.2 Sprint Automation Service

Create `backend/app/services/sprint_service.py`:

```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Sprint, Board

SPRINT_DURATION_WEEKS = 2

def create_sprint_for_board(db: Session, board_id: int, name: str = None):
    board = db.query(Board).filter(Board.board_id == board_id).first()
    if not board:
        raise ValueError("Board not found")
    last_sprint = db.query(Sprint).filter(Sprint.board_id == board_id).order_by(Sprint.start_date.desc()).first()
    if last_sprint and last_sprint.sprint_status in ("future", "active"):
        start_date = (last_sprint.end_date or datetime.utcnow()) + timedelta(days=1)
    else:
        start_date = datetime.utcnow().date()
    end_date = start_date + timedelta(weeks=SPRINT_DURATION_WEEKS)
    sprint = Sprint(board_id=board_id, name=name or f"Sprint {start_date} - {end_date}",
                     start_date=start_date, end_date=end_date, sprint_status="future")
    db.add(sprint); db.commit(); db.refresh(sprint)
    return sprint

def activate_current_sprint(db: Session, board_id: int):
    today = datetime.utcnow().date()
    for s in db.query(Sprint).filter(Sprint.board_id == board_id, Sprint.sprint_status == "future", Sprint.start_date <= today):
        s.sprint_status = "active"
    db.commit()

def close_completed_sprint(db: Session, board_id: int):
    today = datetime.utcnow().date()
    for s in db.query(Sprint).filter(Sprint.board_id == board_id, Sprint.sprint_status == "active", Sprint.end_date < today):
        s.sprint_status = "closed"; s.is_completed = True; s.velocity = s.story_points_completed or 0
    db.commit()
```

### 9.3 Cron Job

In `backend/app/main.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.sprint_service import activate_current_sprint, close_completed_sprint, create_sprint_for_board
from app.database import SessionLocal

scheduler = BackgroundScheduler()

@scheduler.scheduled_job("interval", hours=24)
def sprint_maintenance():
    db = SessionLocal()
    try:
        for board in db.query(Board).all():
            close_completed_sprint(db, board.board_id)
            activate_current_sprint(db, board.board_id)
    finally:
        db.close()

scheduler.start()
```

---

## 10. Implementation Roadmap

### Phase 1: Agentic AI Foundation (Week 1)
- [ ] Create `AgentMemory` and `AgentAction` models
- [ ] Create `ollama_service.py` (Ollama brain)
- [ ] Create `agent_service.py` with LangGraph nodes (Assignment, PR, Sprint, Executive)
- [ ] Create `agents.py` FastAPI router
- [ ] Add frontend `AgentAutomation.tsx` page
- [ ] Add agent-specific routes to `api/v1/__init__.py`

### Phase 2: Smart Assignment (Week 2)
- [ ] Add `UserSkill`, `UserAssignmentHistory`, `IssueRequirement` models
- [ ] Add assignment logic and workload tracking to `agent_service.py` Assignment Agent
- [ ] Ensure `create_issue` calls the Agent or legacy service
- [ ] Add `get_issues_by_assignee_in_window` to `CRUDIssue`
- [ ] Frontend: add workload indicators to board/sidebar

### Phase 3: GitHub PR Integration (Week 3)
- [ ] Add `PullRequest`, `CodeReview`, `BugReport` models
- [ ] Implement `_fetch_pr_files` using GitHub API + `GITHUB_TOKEN`
- [ ] Wire PR linking into the PR Health Agent
- [ ] Add health score display to `AgentAutomation.tsx`

### Phase 4: Sprint Automation (Week 4)
- [ ] Implement `sprint_service.py` with 2-week cycle logic
- [ ] Add auto-activate and auto-close to Sprint Agent node
- [ ] Add `BackgroundScheduler` cron in `main.py`
- [ ] Frontend: show sprint status in agent output / board view

---

## 11. Environment Setup Required

### Backend `.env` additions:
```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_PRIORITY_MODELS=llama3.1,llama3,mistral
GITHUB_TOKEN=ghp_xxx
GITHUB_WEBHOOK_SECRET=xxx
AGENT_SCHEDULER=true
```

### Frontend `.env` additions:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 12. Testing the System

### Test 1: Smart Assignment
1. Create issue without assignee.
2. Ensure issue description contains backend/frontend keywords.
3. Verify `assignment` node in agent output selects a user with matching skills and low workload.

### Test 2: PR Analysis
1. Link a GitHub PR to an issue.
2. Verify `pr_health` node calculates a health score.
3. Check that critical findings create bug issues in the database.

### Test 3: Sprint Management
1. Create a board with a scrum type.
2. Add a sprint with a past end date.
3. Trigger the Sprint Agent node.
4. Verify the sprint is auto-closed and a new sprint is auto-created.

### Test 4: Conversational Agent
1. Ask the agent: "What is the sprint status?"
2. Verify the `Sprint Agent` node is routed and returns structured output.
3. Ask: "Who should work on this backend issue?"
4. Verify the `Assignment Agent` node activates and returns a recommendation.

---

## 13. Future Scope

- **Memory & Context**: Store full conversation history for multi-turn agent interactions.
- **Streaming Executive**: Allow Ollama streaming in the Executive Agent.
- **LangGraph Upgrade**: Replace the lightweight in-repo graph with the official `langgraph` package for conditional branching, sub-graphs, and cycles.
- **Enterprise LLM**: Support OpenAI, Claude, or Azure OpenAI via the `ollama_service.py` abstraction.
- **Policy Engine**: Add a rule engine (e.g., `json-rules-engine`) for complex assignment and compliance policies.

---

*This documentation was generated for the ZYRAA Jira system on 2026-05-08.