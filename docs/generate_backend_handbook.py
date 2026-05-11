from __future__ import annotations

import ast
import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "backend" / "app"
OUTPUT_HTML = ROOT / "docs" / "ZYRAA_Backend_Handbook.html"
OUTPUT_PDF = ROOT / "docs" / "ZYRAA_Backend_Handbook.pdf"


@dataclass
class SymbolInfo:
    kind: str
    name: str
    lineno: int


@dataclass
class FileInfo:
    path: Path
    rel_path: str
    line_count: int
    symbols: list[SymbolInfo]


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.symbols: list[SymbolInfo] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(SymbolInfo("class", node.name, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.append(SymbolInfo("function", node.name, node.lineno))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.symbols.append(SymbolInfo("async function", node.name, node.lineno))
        self.generic_visit(node)


def discover_files() -> list[FileInfo]:
    files: list[FileInfo] = []
    for path in sorted(BACKEND_APP.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix not in {".py", ".psy"}:
            continue

        text = path.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        symbols: list[SymbolInfo] = []
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            visitor = SymbolVisitor()
            visitor.visit(tree)
            symbols = visitor.symbols

        files.append(
            FileInfo(
                path=path,
                rel_path=str(path.relative_to(ROOT)).replace("\\", "/"),
                line_count=line_count,
                symbols=symbols,
            )
        )
    return files


FILE_NOTES: dict[str, dict[str, list[str] | str]] = {
    "backend/app/main.py": {
        "purpose": "Application entrypoint. Builds the FastAPI object, configures CORS, mounts the versioned router, and performs schema/bootstrap work during startup.",
        "details": [
            "The FastAPI instance is created once at import time. This is the object Uvicorn looks for when you run `uvicorn app.main:app`.",
            "CORS is narrowed to the configured frontend URL. That prevents the browser from rejecting cross-origin API calls coming from the Next.js frontend.",
            "The startup hook calls `create_database_if_not_exists()`, imports the model package so SQLAlchemy metadata is fully populated, runs `Base.metadata.create_all(bind=engine)`, and then seeds lookup rows.",
            "Because `engine` is configured with `echo=True`, SQLAlchemy logs the SQL it emits. That is why startup often prints metadata checks and `CREATE TABLE` / `SELECT` statements.",
        ],
    },
    "backend/app/database.py": {
        "purpose": "Owns the SQL Server connection string, SQLAlchemy engine, session factory, declarative base, database creation routine, and reference-data seeding.",
        "details": [
            "The module uses `mssql+pyodbc` against `localhost\\SQLEXPRESS02` with ODBC Driver 18 and Windows trusted authentication.",
            "Two URLs exist: one for the application database (`JiraDB`) and one for `master`. The `master` connection is used only for existence checks and initial `CREATE DATABASE`.",
            "The `SessionLocal` factory creates request-scoped sessions. Each API dependency calls `SessionLocal()`, yields it, and closes it afterward.",
            "The `seed_reference_data()` function ensures required lookup rows exist for issue types, priorities, statuses, and resolutions. Many higher-level endpoints assume these rows are present.",
            "A large share of the SQL logs the user sees come from this module because `echo=True` tells SQLAlchemy to log generated SQL and bound parameters for every request.",
        ],
    },
    "backend/app/config.py": {
        "purpose": "Central settings object built with `pydantic_settings.BaseSettings`.",
        "details": [
            "JWT, CORS, Ollama, and SMTP settings are all loaded through one typed configuration class.",
            "The `.env` file is the default source for overrides, but class defaults make local development work even without extra environment variables.",
            "The `database_server` field exists, but the live database module currently builds its own hard-coded SQL Server URL instead of consuming this setting directly.",
        ],
    },
    "backend/app/auth.py": {
        "purpose": "Authentication primitives: password hashing/verification and JWT creation/decoding.",
        "details": [
            "Passlib's `CryptContext` is configured with multiple schemes so older hashes remain readable if formats evolve.",
            "`verify_password()` compares plain text credentials with the stored hash from the database.",
            "`create_access_token()` puts an `exp` claim into the token and signs it with the configured secret key and algorithm.",
            "`decode_token()` returns the payload when the token is valid and `None` when validation fails; the dependency layer translates `None` into a 401.",
        ],
    },
    "backend/app/api/v1/__init__.py": {
        "purpose": "Versioned API composition point.",
        "details": [
            "Creates the `/api/v1` router and includes the auth, users, projects, issues, boards, and agents subrouters.",
            "This keeps route registration centralized so the root app only mounts one router.",
        ],
    },
    "backend/app/api/v1/dependencies.py": {
        "purpose": "Reusable authentication dependencies for protected endpoints.",
        "details": [
            "Defines `oauth2_scheme` with `/api/v1/auth/login` as the token URL so FastAPI's OpenAPI docs understand how bearer auth is acquired.",
            "`get_current_user()` decodes the token, reads the `sub` claim as a username, and looks the user up in the database.",
            "`get_current_active_user()` is a second guard that rejects inactive accounts.",
        ],
    },
    "backend/app/api/v1/auth.py": {
        "purpose": "Login and registration endpoints.",
        "details": [
            "The login route accepts both form-encoded and JSON credentials, which makes it compatible with browser form posts and Axios JSON calls.",
            "On successful login it returns a bearer token only; the frontend stores and reuses that token for later requests.",
            "Registration performs uniqueness checks on username and email, hashes the password, and writes the `User` row directly.",
        ],
    },
    "backend/app/api/v1/users.py": {
        "purpose": "User CRUD endpoints plus assignee search.",
        "details": [
            "The `/search` route is important for issue assignment UX. It performs an active-user filter plus `ILIKE` search on username, display name, and email.",
            "Update authorization is intentionally simple: a user can only update their own record.",
            "The create route still uses the CRUD layer, but it constructs a `UserCreate` object in a slightly awkward way because password hashing is handled outside the generic CRUD helper.",
        ],
    },
    "backend/app/api/v1/projects.py": {
        "purpose": "Project CRUD and project-scoped issue/stat endpoints.",
        "details": [
            "Creating a project stamps the current user as the project lead.",
            "Project issues are fetched through `crud.issue.get_by_project(...)`, so paging and filters are applied at the CRUD layer.",
            "The stats endpoint deliberately calculates totals in Python after loading issues. That is easy to understand, but it is less efficient than pushing aggregates into SQL.",
        ],
    },
    "backend/app/api/v1/boards.py": {
        "purpose": "Board and board-column management plus board issue grouping.",
        "details": [
            "Boards are linked to projects by project key at creation time, then stored with the project's numeric foreign key.",
            "Columns can map to statuses, which is how the board turns workflow states into visual lanes.",
            "The board issue endpoint loops through columns and queries issues by each mapped status. That is straightforward but can become chatty at scale because it issues one query per mapped column.",
        ],
    },
    "backend/app/api/v1/issues.py": {
        "purpose": "Largest router in the application. Handles issue create/read/update/delete, comments, worklogs, links, PR linking, auto-assignment, serialization, and Epic parenting.",
        "details": [
            "The file contains helper functions such as `generate_issue_key()`, `serialize_issue()`, and Epic-link helpers. These exist because the app returns custom response dictionaries rather than raw ORM objects.",
            "Issue creation resolves project, issue type, default status, optional assignee, optional component/version, optional priority, and labels before committing the row.",
            "When `auto_assign` is enabled, the router delegates to `recommend_issue_assignee()` and optionally rewrites the assignee after the issue is initially created.",
            "Issue listing uses `joinedload(...)` for related objects. That reduces N+1 query explosions when serializing project, priority, status, assignee, reporter, component, version, and labels.",
            "Update logic is explicit rather than generic because enum values, assignee usernames, project moves, component scoping, version scoping, and label replacement all need custom handling.",
            "The Epic endpoint treats Epic membership as a special case of `IssueLink` with `link_type='parent-child'`, but it wraps that rule in validation so the UI can treat it as a first-class feature.",
            "The PR endpoint creates a `PullRequest`, runs code analysis, updates PR health, and creates bug reports from high-severity findings.",
        ],
    },
    "backend/app/api/v1/agents.py": {
        "purpose": "Public interface for the automation subsystem.",
        "details": [
            "The status endpoint reports whether local AI, LangChain, LangGraph, and SMTP are available, which is useful for debugging hybrid deterministic/AI behavior.",
            "The automation endpoint invokes the internal state-driven workflow for assignment, sprint maintenance, PR health checks, or a full scan.",
            "The prompt execution endpoint is the natural-language project/board/issue creation interface.",
            "Approve/reject endpoints operate on persisted `AgentAction` rows, which lets the system stage agent recommendations before applying them.",
        ],
    },
    "backend/app/crud/base.py": {
        "purpose": "Generic CRUD helper used by specialized CRUD classes.",
        "details": [
            "Implements `get`, `get_multi`, `create`, `update`, and `delete` in a model-agnostic way.",
            "The helper assumes Pydantic-style objects expose `model_dump(...)`. That design caused one of the earlier bugs when a SQLAlchemy model was accidentally passed into `create()`.",
            "`get_multi` automatically adds an `ORDER BY` on the primary key when no explicit order is provided. That matters for SQL Server because OFFSET/LIMIT pagination requires ordering.",
        ],
    },
    "backend/app/crud/__init__.py": {
        "purpose": "Specialized CRUD objects for users, projects, issues, comments, worklogs, boards, sprints, labels, notifications, favorites, and board columns.",
        "details": [
            "This file is the persistence convenience layer. It keeps routine query patterns out of routers so controllers stay readable.",
            "The issue CRUD object adds project scoping, board issue lookup, and free-text search.",
            "Notification helpers centralize unread filtering and bulk mark-as-read behavior.",
            "The module exposes both named instances like `crud_user` and namespaced aliases like `crud.user`, which is why imports can use either style.",
        ],
    },
    "backend/app/models/__init__.py": {
        "purpose": "Core domain model package. Defines users, projects, issues, statuses, priorities, components, versions, labels, comments, worklogs, boards, sprints, links, permissions, notifications, history, and favorites.",
        "details": [
            "The file uses SQLAlchemy 2-style typed mappings (`Mapped[...]` and `mapped_column(...)`) together with classic `relationship(...)` declarations.",
            "Association tables such as `issue_labels`, `role_permissions`, and `issue_sprints` model many-to-many relationships.",
            "Convenience `@property` methods like `project_key`, `priority_name`, `label_names`, and `status_name` make downstream serialization more readable.",
            "The Issue model is the center of gravity: nearly every major feature relates back to it directly or indirectly.",
        ],
    },
    "backend/app/models/agents.py": {
        "purpose": "Persistence models for agent memory and agent action approvals.",
        "details": [
            "Agent memories store conversational context and workflow summaries for later inspection.",
            "Agent actions capture deferred tasks that need a human decision, such as approving an assignment recommendation.",
        ],
    },
    "backend/app/models/assignment.py": {
        "purpose": "Data structures used by assignment intelligence.",
        "details": [
            "User skills describe each person's strengths.",
            "Assignment history lets the recommender reward users who have already worked in a project's context.",
            "Issue requirements store inferred skill needs extracted from issue text.",
        ],
    },
    "backend/app/models/code_review.py": {
        "purpose": "Persistence for PR linkage, code review findings, and bug reports created from those findings.",
        "details": [
            "This is the code-quality branch of the data model.",
            "A linked PR can generate multiple code review findings and multiple bug reports.",
        ],
    },
    "backend/app/schemas/__init__.py": {
        "purpose": "Pydantic schemas and enums used for validation and response shaping.",
        "details": [
            "Enums such as `IssueTypeEnum`, `PriorityEnum`, `StatusEnum`, and `BoardTypeEnum` keep the API contract tight.",
            "Create/update/response schemas are split so incoming and outgoing payloads can evolve independently.",
            "The issue schema family now includes Epic metadata and the `IssueEpicUpdate` payload used by the dedicated parent-Epic endpoint.",
        ],
    },
    "backend/app/services/email_service.py": {
        "purpose": "SMTP integration for assignment notifications.",
        "details": [
            "It is intentionally thin: configuration check, generic `send_email`, and a domain-specific `send_issue_assignment_email` wrapper.",
            "The return values are dictionaries instead of exceptions so higher-level services can report partial success cleanly.",
        ],
    },
    "backend/app/services/ollama_service.py": {
        "purpose": "Local-LLM integration layer.",
        "details": [
            "Searches common install paths for the Ollama executable, then uses `ollama list` to discover installed models.",
            "`choose_best_model()` prefers a curated list but falls back to the first installed model.",
            "Both non-streaming and streaming chat helpers are provided. If Ollama or `httpx` is unavailable, the service degrades gracefully instead of crashing the app.",
        ],
    },
    "backend/app/services/langchain_service.py": {
        "purpose": "Natural-language prompt planner for automation.",
        "details": [
            "If LangChain and a usable Ollama model are available, the planner asks the model to return strict JSON for project, board, issues, and email actions.",
            "If AI planning is not available or JSON parsing fails, a regex-driven fallback parser extracts project names, keys, issue types, priorities, assignee hints, auto-assign requests, and email intent.",
            "The normalizer stage ensures downstream automation code always sees the same shape even if the original plan came from different paths.",
        ],
    },
    "backend/app/services/sprint_service.py": {
        "purpose": "Small service module for sprint lifecycle automation.",
        "details": [
            "Creates future sprints, activates future sprints whose start date has arrived, and closes active sprints whose end date has passed.",
            "This logic is intentionally deterministic and is reused by the automation workflow.",
        ],
    },
    "backend/app/services/code_analyzer.py": {
        "purpose": "Static-rule code analysis for linked pull requests.",
        "details": [
            "Fetches PR file contents, scans them against rule dictionaries, persists findings as `CodeReview` rows, and turns serious findings into bug reports.",
            "The rules are pattern-based rather than AST-based, so they are easy to extend but can generate false positives.",
            "The health score starts at 100 and is penalized according to finding severity.",
        ],
    },
    "backend/app/services/agent_service.py": {
        "purpose": "Main automation brain. Contains deterministic assignment logic, sprint and PR agents, executive summary synthesis, pending action gating, action execution, and prompt-based object creation.",
        "details": [
            "The assignment engine infers skill requirements from issue text, stores those requirements, looks at user skills and assignment history, and then produces ranked candidates.",
            "The workload cap (`MAX_ISSUES_PER_USER`) is enforced before ranking so overloaded users are heavily penalized.",
            "The 'agentic workflow' is not a LangGraph graph object today; it is an internal orchestration function that calls the relevant agent functions in sequence and then optionally asks Ollama for a narrative executive summary.",
            "Pending actions are persisted as database rows. Approval is decoupled from recommendation generation, which is why agent actions can survive request boundaries.",
            "Prompt automation is a second branch of the automation system. It converts natural language into a plan, creates the requested project/board/issues, links issue chains, assigns owners, creates notifications, and optionally sends email.",
            "The module blends deterministic rules with optional AI rather than depending fully on an LLM. That hybrid design explains many of the conditional capability checks throughout the file.",
        ],
    },
    "backend/app/__init__.py": {
        "purpose": "Package marker for the `app` Python package.",
        "details": [
            "This file is intentionally minimal. Its main role is making `app` importable as a package namespace.",
        ],
    },
    "backend/app/api/v1/users.psy": {
        "purpose": "Legacy or stray duplicate of the users router kept in the tree with a non-standard extension.",
        "details": [
            "It is not imported by the live router composition file, so it does not participate in the running application.",
            "Its presence is worth documenting because it can confuse readers who search for user endpoints and find two copies.",
        ],
    },
}


ARCHITECTURE_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "1. Runtime Startup Sequence",
        [
            "Uvicorn imports `app.main:app`. Import-time code builds the FastAPI instance, registers CORS, and mounts the API router tree.",
            "When FastAPI fires the startup event, the app calls `create_database_if_not_exists()` against SQL Server `master`. This checks `sys.databases` and creates `JiraDB` if needed.",
            "The startup hook then imports `app.models`, causing SQLAlchemy model classes to register themselves inside `Base.metadata`.",
            "Next, `Base.metadata.create_all(bind=engine)` asks SQLAlchemy to inspect existing tables and create any missing ones. This emits metadata queries and possibly DDL.",
            "Finally, `seed_reference_data()` inserts required rows such as `Epic`, `Story`, `Task`, `Bug`, `To Do`, `Done`, and priority rows. Without these rows, issue creation endpoints would fail validation or default lookup logic.",
        ],
    ),
    (
        "2. Why SQL Logs Appear So Frequently",
        [
            "The engine in `database.py` is created with `echo=True`. That setting logs SQL text, parameters, and transaction markers for every database interaction.",
            "SQLAlchemy starts implicit transactions for many operations. Even a read-only request may show `BEGIN (implicit)` followed by one or more `SELECT` statements.",
            "If the request finishes without an explicit commit, SQLAlchemy or the DBAPI connection may emit `ROLLBACK` when the session is cleaned up. In this app that is normal for read-only flows; it does not mean data loss occurred.",
            "Many endpoints use `joinedload(...)` to prefetch relationships. That changes SQL shape and often produces wider queries to reduce later per-row fetches.",
            "Pagination on SQL Server requires ordering. Earlier in development, missing `ORDER BY` clauses caused MSSQL compilation errors when SQLAlchemy generated OFFSET/LIMIT queries.",
        ],
    ),
    (
        "3. Request Lifecycle in This App",
        [
            "The browser sends a request with a bearer token stored in local storage by the frontend.",
            "FastAPI matches the route and resolves dependencies. Protected endpoints call `get_db()` to create a SQLAlchemy session and `get_current_user()` to decode the JWT and load the user row.",
            "The router performs validation through Pydantic schemas, then either uses raw SQLAlchemy ORM calls or delegates to the CRUD/service layers.",
            "The endpoint usually commits changes, refreshes ORM objects to hydrate DB-generated values, and returns either ORM models or custom dictionaries for JSON serialization.",
            "When the request ends, the DB session is closed. If nothing was committed in a read flow, SQLAlchemy may roll back the open transaction during cleanup.",
        ],
    ),
    (
        "4. How the Agent System Is Actually Implemented",
        [
            "There are two distinct automation families: the workflow agents in `agent_service.py` and the prompt planner/creator path driven by `langchain_service.py` plus `run_prompt_automation()`.",
            "The workflow side is deterministic first. Assignment, sprint rotation, and PR analysis all work even with no model installed.",
            "Ollama is used as an optional narrative layer for executive summaries. LangChain is used as an optional structured JSON planner for prompt automation.",
            "LangGraph is only capability-checked today. The system reports whether it is installed, but the current workflow execution is still hand-orchestrated Python, not a built `StateGraph`.",
            "Human approval is modeled explicitly with `AgentAction` rows, which allows the app to stage proposed actions and execute them later only after approval.",
        ],
    ),
]


MODEL_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Identity and access",
        [
            "`User` stores accounts and is the anchor for reported issues, assigned issues, comments, worklogs, notifications, and project roles.",
            "`ProjectRole` and `Permission` lay groundwork for authorization, although current endpoint checks are still relatively simple.",
        ],
    ),
    (
        "Issue tracking core",
        [
            "`Project` groups issues and boards under a project key.",
            "`IssueType`, `IssuePriority`, `IssueStatus`, and `Resolution` are lookup tables used by issue rows.",
            "`Issue` is the central transactional record and connects almost every other subsystem together.",
            "`Label`, `Component`, and `Version` provide issue classification and release metadata.",
        ],
    ),
    (
        "Collaboration and workflow",
        [
            "`IssueComment`, `Worklog`, `IssueAttachment`, `IssueHistory`, and `Favorite` represent user interaction around work items.",
            "`Board`, `BoardColumn`, and `Sprint` support kanban/scrum workflow organization.",
            "`IssueLink` generalizes relationships such as parent-child links used for Epic membership.",
        ],
    ),
    (
        "Automation and analytics",
        [
            "`UserSkill`, `UserAssignmentHistory`, and `IssueRequirement` feed assignment scoring.",
            "`AgentMemory` and `AgentAction` persist automation context and approval-gated tasks.",
            "`PullRequest`, `CodeReview`, and `BugReport` connect source control health checks back into issue tracking.",
        ],
    ),
]


REQUEST_WALKS: list[tuple[str, list[str]]] = [
    (
        "POST /api/v1/auth/login",
        [
            "Reads credentials from JSON or form data.",
            "Fetches the user by username.",
            "Verifies the password hash with Passlib.",
            "Rejects inactive users.",
            "Creates a JWT whose `sub` claim stores the username.",
            "Returns `{access_token, token_type}` to the frontend.",
        ],
    ),
    (
        "POST /api/v1/issues/",
        [
            "Validates the request body with `IssueCreate`.",
            "Resolves the project by key and the issue type by enum value.",
            "Loads the default `To Do` status row.",
            "Optionally resolves assignee, component, version, and priority.",
            "Creates the issue row and then attaches labels using `crud.label.get_or_create(...)`.",
            "If `auto_assign` is true and there is no manual assignee, runs the assignment recommender and updates the issue assignee.",
            "Serializes a custom issue response dictionary, optionally including recommendation metadata.",
        ],
    ),
    (
        "POST /api/v1/agents/prompt/execute",
        [
            "Accepts a natural-language prompt.",
            "Builds an automation plan via LangChain+Ollama when available, otherwise via regex fallback parsing.",
            "Optionally creates a project, a board, one or more issues, issue-chain links, assignees, notifications, and emails.",
            "Returns both the interpreted plan and the concrete objects that were created.",
        ],
    ),
]


def bullet_list(items: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_symbols(symbols: list[SymbolInfo]) -> str:
    if not symbols:
        return "<p class='muted'>No parseable classes or functions were extracted for this file.</p>"
    rows = []
    for symbol in symbols:
        rows.append(
            "<tr>"
            f"<td>{html.escape(symbol.kind)}</td>"
            f"<td><code>{html.escape(symbol.name)}</code></td>"
            f"<td>{symbol.lineno}</td>"
            "</tr>"
        )
    return (
        "<table class='symbols'><thead><tr><th>Kind</th><th>Name</th><th>Line</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_file_section(file_info: FileInfo) -> str:
    note = FILE_NOTES.get(file_info.rel_path, {})
    purpose = note.get("purpose", "This module exists in the backend tree but does not yet have a custom narrative note in the generator.")
    details = note.get("details", [])
    return (
        "<section class='file-section'>"
        f"<h3 id='{file_info.rel_path.replace('/', '-').replace('.', '-')}'>{html.escape(file_info.rel_path)}</h3>"
        f"<p><strong>Line count:</strong> {file_info.line_count}</p>"
        f"<p><strong>Purpose:</strong> {html.escape(str(purpose))}</p>"
        f"{bullet_list([str(item) for item in details]) if details else ''}"
        "<h4>Classes and Functions</h4>"
        f"{render_symbols(file_info.symbols)}"
        "</section>"
    )


def build_html(files: list[FileInfo]) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    toc_items = []
    file_sections = []
    for file_info in files:
        file_id = file_info.rel_path.replace("/", "-").replace(".", "-")
        toc_items.append(f"<li><a href='#{file_id}'>{html.escape(file_info.rel_path)}</a></li>")
        file_sections.append(render_file_section(file_info))

    architecture_html = "".join(
        f"<section><h2>{html.escape(title)}</h2>{bullet_list(items)}</section>"
        for title, items in ARCHITECTURE_SECTIONS
    )
    model_html = "".join(
        f"<section><h3>{html.escape(title)}</h3>{bullet_list(items)}</section>"
        for title, items in MODEL_GROUPS
    )
    request_html = "".join(
        f"<section><h3>{html.escape(title)}</h3>{bullet_list(items)}</section>"
        for title, items in REQUEST_WALKS
    )

    total_lines = sum(file.line_count for file in files)
    total_symbols = sum(len(file.symbols) for file in files)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>ZYRAA Backend Handbook</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm 14mm 18mm 14mm;
    }}
    body {{
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: #1f2937;
      line-height: 1.5;
      font-size: 11px;
    }}
    h1, h2, h3, h4 {{
      color: #0f172a;
      margin-bottom: 0.35rem;
    }}
    h1 {{
      font-size: 28px;
      margin-top: 0;
    }}
    h2 {{
      font-size: 20px;
      margin-top: 1.6rem;
      border-bottom: 2px solid #cbd5e1;
      padding-bottom: 0.25rem;
    }}
    h3 {{
      font-size: 15px;
      margin-top: 1.2rem;
    }}
    h4 {{
      font-size: 12px;
      margin-top: 0.9rem;
    }}
    p {{
      margin: 0.35rem 0 0.7rem;
    }}
    ul {{
      margin: 0.2rem 0 0.8rem 1.2rem;
      padding: 0;
    }}
    li {{
      margin: 0.18rem 0;
    }}
    .cover {{
      padding-top: 40px;
      page-break-after: always;
    }}
    .meta {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 10px;
      padding: 14px 16px;
      margin-top: 20px;
    }}
    .callout {{
      background: #f8fafc;
      border-left: 4px solid #2563eb;
      padding: 10px 12px;
      margin: 0.9rem 0;
    }}
    .toc {{
      columns: 2;
      column-gap: 24px;
    }}
    .toc li {{
      break-inside: avoid;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0.5rem 0 1rem;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 6px 8px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #e2e8f0;
    }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 10px;
      color: #111827;
    }}
    .muted {{
      color: #64748b;
    }}
    .file-section {{
      break-inside: avoid-page;
      page-break-inside: avoid;
      margin-bottom: 1.2rem;
      padding-bottom: 0.8rem;
      border-bottom: 1px solid #e5e7eb;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin: 1rem 0 1.2rem;
    }}
    .stat {{
      border: 1px solid #dbeafe;
      background: #f8fbff;
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .stat strong {{
      display: block;
      font-size: 18px;
      margin-top: 2px;
    }}
    .page-break {{
      page-break-before: always;
    }}
  </style>
</head>
<body>
  <section class="cover">
    <h1>ZYRAA Backend Engineering Handbook</h1>
    <p>This document is a deep code walkthrough of the FastAPI backend in this repository. It explains the startup path, SQLAlchemy behavior, authentication flow, routers, schemas, CRUD patterns, domain models, automation services, agent implementation, and the reasons behind the SQL logs visible during runtime.</p>
    <div class="meta">
      <p><strong>Repository scope:</strong> <code>backend/app</code></p>
      <p><strong>Generated:</strong> {html.escape(generated)}</p>
      <p><strong>Files covered:</strong> {len(files)} source files</p>
      <p><strong>Total source lines covered:</strong> {total_lines}</p>
      <p><strong>Classes and functions indexed:</strong> {total_symbols}</p>
    </div>
    <div class="callout">
      <strong>Important framing:</strong> the backend is not purely "AI-driven." Most behavior is deterministic FastAPI + SQLAlchemy application logic. AI is layered on top in selected places such as executive summaries and structured prompt planning when local models are available.
    </div>
  </section>

  <section>
    <h2>Table of Contents</h2>
    <ol>
      <li><a href="#system-overview">System Overview</a></li>
      <li><a href="#startup-sql">Startup, Sessions, and SQL Logs</a></li>
      <li><a href="#auth-request">Authentication and Request Flow</a></li>
      <li><a href="#data-model">Data Model Walkthrough</a></li>
      <li><a href="#agents-automation">Agents and Automation</a></li>
      <li><a href="#request-examples">End-to-End Request Examples</a></li>
      <li><a href="#file-by-file">File-by-File Reference</a></li>
    </ol>
    <h3>File Index</h3>
    <ol class="toc">
      {''.join(toc_items)}
    </ol>
  </section>

  <section id="system-overview" class="page-break">
    <h2>System Overview</h2>
    <p>The backend is a classic layered FastAPI service. Its high-level stack looks like this:</p>
    <ul>
      <li><strong>Entry and app wiring:</strong> <code>main.py</code>, <code>config.py</code>, <code>database.py</code></li>
      <li><strong>Authentication:</strong> <code>auth.py</code> plus dependency guards in <code>api/v1/dependencies.py</code></li>
      <li><strong>Request validation:</strong> Pydantic schemas in <code>schemas/__init__.py</code></li>
      <li><strong>Persistence models:</strong> SQLAlchemy models in <code>models/</code></li>
      <li><strong>Persistence helpers:</strong> CRUD classes in <code>crud/</code></li>
      <li><strong>HTTP controllers:</strong> routers in <code>api/v1/</code></li>
      <li><strong>Business services:</strong> <code>services/</code> modules for assignment, sprint rotation, local-LLM integration, code analysis, and email delivery</li>
    </ul>
    <div class="stats">
      <div class="stat">Tracked files<strong>{len(files)}</strong></div>
      <div class="stat">Tracked source lines<strong>{total_lines}</strong></div>
      <div class="stat">Indexed symbols<strong>{total_symbols}</strong></div>
    </div>
    <p>The most important backend nucleus is the combination of <code>Issue</code>, <code>Project</code>, and the routers/services that operate on them. Everything else either enriches issue management directly, or provides automation around it.</p>
  </section>

  <section id="startup-sql">
    <h2>Startup, Sessions, and SQL Logs</h2>
    {architecture_html}
  </section>

  <section id="auth-request">
    <h2>Authentication and Request Flow</h2>
    <p>Authentication is bearer-token based and intentionally lightweight. Passwords are hashed with Passlib, tokens are signed with JOSE, and protected routes depend on a current-user loader that translates token claims into a real database user.</p>
    <ul>
      <li><strong>Password storage:</strong> passwords are never stored in plain text. They are hashed before persistence.</li>
      <li><strong>Token subject:</strong> the JWT <code>sub</code> claim stores the username, not the numeric user ID.</li>
      <li><strong>Current-user resolution:</strong> every protected route resolves the token to a username and then issues a database query to fetch the user row.</li>
      <li><strong>Session scoping:</strong> each request receives a SQLAlchemy session via dependency injection. That keeps database work isolated per request.</li>
    </ul>
    <div class="callout">
      <strong>Why a read request can still show ROLLBACK:</strong> SQLAlchemy often opens an implicit transaction for consistency even when the code only reads. When the session is disposed without a commit, the driver emits a rollback to close the transaction cleanly.
    </div>
  </section>

  <section id="data-model">
    <h2>Data Model Walkthrough</h2>
    <p>The data model is broad, but it can be understood as four clusters: identity/access, issue tracking core, collaboration/workflow, and automation/analytics.</p>
    {model_html}
    <p>The <code>Issue</code> model is the system's center. It references the project, type, priority, status, assignee, reporter, component, version, labels, comments, worklogs, links, pull requests, and assignment requirements. Because of that central role, many routers use eager loading to gather related rows before serializing responses.</p>
  </section>

  <section id="agents-automation">
    <h2>Agents and Automation</h2>
    <p>The codebase contains two overlapping automation tracks:</p>
    <ul>
      <li><strong>Operational workflow agents:</strong> assignment, PR health, sprint maintenance, pending-action approval, and executive summarization inside <code>agent_service.py</code>.</li>
      <li><strong>Prompt automation:</strong> natural-language planning and object creation across projects, boards, issues, links, assignees, notifications, and emails.</li>
    </ul>
    <h3>Assignment logic</h3>
    <ul>
      <li><code>infer_issue_requirements()</code> scans issue text for skill keywords and turns them into weighted skill requirements.</li>
      <li><code>ensure_issue_requirements()</code> persists those requirements so recommendation can reuse them later.</li>
      <li><code>_score_user_for_issue()</code> combines skill fit, historical assignments in the same project, and recent workload.</li>
      <li><code>recommend_issue_assignee()</code> ranks active users and applies a fallback-to-any-active-user strategy when no strong match exists.</li>
    </ul>
    <h3>PR health logic</h3>
    <ul>
      <li>A linked PR is fetched from GitHub using repository URL + PR number.</li>
      <li>Changed files are scanned with regex rules for problems like SQL injection patterns, hardcoded passwords, eval usage, and console logging.</li>
      <li>Findings are stored as <code>CodeReview</code> rows and severe findings become <code>BugReport</code> rows.</li>
    </ul>
    <h3>Prompt automation logic</h3>
    <ul>
      <li>Prompt planning prefers LangChain+Ollama for strict JSON output.</li>
      <li>If AI planning is unavailable, fallback regex parsing extracts project intent, board intent, issue chain items, assignee hints, priority, auto-assign, and email intent.</li>
      <li>The runner then creates project, board, issue chain, parent-child links, assignee decisions, assignment history, notifications, and optional email messages.</li>
    </ul>
    <div class="callout">
      <strong>Reality check on "agentic":</strong> the current code reports LangGraph availability, but the live orchestration is still imperative Python that passes around an <code>AgentState</code> dictionary. It is better described as agent-inspired workflow orchestration than a fully graph-modeled agent framework.
    </div>
  </section>

  <section id="request-examples">
    <h2>End-to-End Request Examples</h2>
    {request_html}
  </section>

  <section id="file-by-file" class="page-break">
    <h2>File-by-File Reference</h2>
    <p>This section is the most exhaustive part of the handbook. Each file entry includes its role in the system, key implementation details, and an extracted list of top-level classes/functions with line numbers.</p>
    {''.join(file_sections)}
  </section>
</body>
</html>
"""


def escape_para(text: str) -> str:
    return html.escape(text).replace("\n", "<br/>")


def build_pdf(files: list[FileInfo]) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=8,
    )
    sub_style = ParagraphStyle(
        "SubSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "BulletBody",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=0,
        bulletIndent=0,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=body_style,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="ZYRAA Backend Engineering Handbook",
        author="OpenAI Codex",
    )

    story = []
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_lines = sum(file.line_count for file in files)
    total_symbols = sum(len(file.symbols) for file in files)

    story.append(Spacer(1, 18))
    story.append(Paragraph("ZYRAA Backend Engineering Handbook", title_style))
    story.append(Paragraph("Comprehensive backend code walkthrough and architecture reference", sub_style))
    story.append(Spacer(1, 8))
    for line in [
        f"Generated: {generated}",
        f"Files covered: {len(files)}",
        f"Total source lines covered: {total_lines}",
        f"Classes and functions indexed: {total_symbols}",
        "Scope: backend/app",
    ]:
        story.append(Paragraph(escape_para(line), body_style))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            escape_para(
                "This handbook explains the FastAPI startup path, SQLAlchemy behavior, routers, CRUD helpers, schemas, models, service layer, prompt automation, assignment intelligence, and the practical meaning of the SQL logs produced during runtime."
            ),
            body_style,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("System Overview", section_style))
    story.append(
        Paragraph(
            escape_para(
                "The backend is a layered FastAPI application. The core flow is: HTTP request -> dependency resolution -> validation -> ORM/service logic -> commit/refresh -> JSON response."
            ),
            body_style,
        )
    )
    for item in [
        "Entry and app wiring live in main.py, config.py, and database.py.",
        "Authentication lives in auth.py plus api/v1/dependencies.py.",
        "Pydantic schemas define request and response contracts.",
        "SQLAlchemy models define the persistent domain graph.",
        "CRUD helpers centralize routine query patterns.",
        "Routers translate HTTP requests into business operations.",
        "Services implement assignment, sprint, PR health, prompt planning, local LLM access, and email delivery.",
    ]:
        story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(Paragraph("Startup, Sessions, and SQL Logs", section_style))
    for title, items in ARCHITECTURE_SECTIONS:
        story.append(Paragraph(escape_para(title), sub_style))
        for item in items:
            story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(Paragraph("Authentication and Request Flow", section_style))
    for item in [
        "Passwords are hashed with Passlib before persistence.",
        "JWT tokens store the username in the sub claim.",
        "Protected routes resolve the token to a real database user through get_current_user().",
        "Each request gets its own SQLAlchemy session from get_db().",
        "Read-only requests can still show BEGIN and ROLLBACK in logs because the session opens and then cleans up an implicit transaction.",
    ]:
        story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(Paragraph("Data Model Walkthrough", section_style))
    for title, items in MODEL_GROUPS:
        story.append(Paragraph(escape_para(title), sub_style))
        for item in items:
            story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(Paragraph("Agents and Automation", section_style))
    for item in [
        "The app mixes deterministic automation with optional AI support from local Ollama models.",
        "Workflow automation in agent_service.py handles assignment recommendations, sprint maintenance, PR health analysis, executive summaries, pending approval actions, and prompt-driven object creation.",
        "LangChain is optional and is used only for structured prompt planning when available.",
        "LangGraph is only capability-checked today; the actual workflow orchestration is still imperative Python over an AgentState dictionary.",
        "Prompt automation can create projects, boards, multiple issues, parent-child links, assignees, notifications, and assignment emails from one sentence.",
    ]:
        story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(Paragraph("End-to-End Request Examples", section_style))
    for title, items in REQUEST_WALKS:
        story.append(Paragraph(escape_para(title), sub_style))
        for item in items:
            story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

    story.append(PageBreak())
    story.append(Paragraph("File-by-File Reference", section_style))
    story.append(
        Paragraph(
            escape_para(
                "Each entry below includes the module purpose, key implementation notes, and the top-level classes/functions parsed from the source."
            ),
            body_style,
        )
    )

    for file_info in files:
        note = FILE_NOTES.get(file_info.rel_path, {})
        purpose = str(note.get("purpose", "This module exists in the backend tree but does not yet have a custom narrative note in the generator."))
        details = [str(item) for item in note.get("details", [])]

        story.append(Paragraph(escape_para(file_info.rel_path), sub_style))
        story.append(Paragraph(escape_para(f"Line count: {file_info.line_count}"), small_style))
        story.append(Paragraph(escape_para(f"Purpose: {purpose}"), body_style))
        for item in details:
            story.append(Paragraph(escape_para(item), bullet_style, bulletText="-"))

        if file_info.symbols:
            table_data = [["Kind", "Name", "Line"]]
            for symbol in file_info.symbols:
                table_data.append([symbol.kind, symbol.name, str(symbol.lineno)])
            table = Table(table_data, colWidths=[32 * mm, 90 * mm, 18 * mm], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEADING", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("No parseable classes or functions were extracted for this file.", small_style))

        story.append(Spacer(1, 8))

    doc.build(story)


def main() -> None:
    files = discover_files()
    OUTPUT_HTML.write_text(build_html(files), encoding="utf-8")
    build_pdf(files)
    print(f"Wrote {OUTPUT_HTML}")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
