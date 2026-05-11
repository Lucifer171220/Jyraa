import re
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Issue, IssuePriority, IssueStatus, IssueType, Label, Project, User


TOKEN_RE = re.compile(
    r"(?P<field>\w+)\s*(?P<operator>!=|>=|<=|=|~|>|<)\s*(?P<value>\"[^\"]+\"|'[^']+'|[^\s]+)",
    re.IGNORECASE,
)


def parse_jql(jql: str) -> list[dict[str, str]]:
    """Parse a small JQL-like subset: field op value clauses joined implicitly by AND."""
    tokens: list[dict[str, str]] = []
    for match in TOKEN_RE.finditer(jql or ""):
        value = match.group("value").strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        tokens.append(
            {
                "field": match.group("field").lower(),
                "operator": match.group("operator"),
                "value": value,
            }
        )
    return tokens


def _like(value: str) -> str:
    return f"%{value}%"


def _matches_text(column: Any, operator: str, value: str):
    if operator == "~":
        return column.ilike(_like(value))
    if operator == "=":
        return column.ilike(value)
    if operator == "!=":
        return ~column.ilike(value)
    return None


def _matches_lookup(relationship_attr: Any, lookup_model: Any, columns: list[Any], operator: str, value: str):
    if value.lower() in {"null", "empty"}:
        return relationship_attr == None if operator == "=" else relationship_attr != None

    condition = or_(*[column.ilike(_like(value)) for column in columns])
    if operator in {"=", "~"}:
        return relationship_attr.has(condition)
    if operator == "!=":
        return ~relationship_attr.has(condition)
    return None


def _parse_date(value: str):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return value


def _matches_date(column: Any, operator: str, value: str):
    parsed = _parse_date(value)
    if operator == "=":
        return column == parsed
    if operator == "!=":
        return column != parsed
    if operator == ">":
        return column > parsed
    if operator == ">=":
        return column >= parsed
    if operator == "<":
        return column < parsed
    if operator == "<=":
        return column <= parsed
    return None


def build_condition(field: str, operator: str, value: str):
    if field in {"project", "projectkey"}:
        return _matches_lookup(Issue.project, Project, [Project.project_key, Project.name], operator, value)
    if field in {"issuetype", "type"}:
        return _matches_lookup(Issue.issue_type, IssueType, [IssueType.name], operator, value)
    if field == "priority":
        return _matches_lookup(Issue.priority, IssuePriority, [IssuePriority.name], operator, value)
    if field == "status":
        return _matches_lookup(Issue.status, IssueStatus, [IssueStatus.name], operator, value)
    if field == "assignee":
        return _matches_lookup(Issue.assignee, User, [User.username, User.display_name, User.email], operator, value)
    if field == "reporter":
        return _matches_lookup(Issue.reporter, User, [User.username, User.display_name, User.email], operator, value)
    if field == "summary":
        return _matches_text(Issue.summary, operator, value)
    if field == "description":
        return _matches_text(Issue.description, operator, value)
    if field in {"key", "issuekey"}:
        return _matches_text(Issue.issue_key, operator, value)
    if field in {"label", "labels"} and operator in {"=", "~"}:
        return Issue.labels.any(Label.name.ilike(_like(value)))
    if field == "text":
        return or_(Issue.summary.ilike(_like(value)), Issue.description.ilike(_like(value)), Issue.issue_key.ilike(_like(value)))
    if field == "created":
        return _matches_date(Issue.created_at, operator, value)
    if field == "updated":
        return _matches_date(Issue.updated_at, operator, value)
    if field in {"due", "duedate"}:
        return _matches_date(Issue.due_date, operator, value)
    return None


def apply_jql_filters(query, tokens: list[dict[str, str]]):
    conditions = []
    for token in tokens:
        condition = build_condition(token["field"], token["operator"], token["value"])
        if condition is not None:
            conditions.append(condition)

    return query.filter(and_(*conditions)) if conditions else query


def search_issues(jql: str, db: Session, limit: int = 100, offset: int = 0):
    query = (
        db.query(Issue)
        .options(
            joinedload(Issue.project),
            joinedload(Issue.issue_type),
            joinedload(Issue.priority),
            joinedload(Issue.status),
            joinedload(Issue.assignee),
            joinedload(Issue.reporter),
            joinedload(Issue.component),
            joinedload(Issue.version),
            joinedload(Issue.labels),
        )
        .order_by(Issue.issue_id.asc())
    )

    query = apply_jql_filters(query, parse_jql(jql))
    total = query.count()
    return total, query.offset(offset).limit(limit).all()
