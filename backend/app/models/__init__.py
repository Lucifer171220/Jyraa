from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, UniqueConstraint, Table,
    Date, Float, BigInteger
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from app.database import Base
from app.models.agents import AgentAction, AgentMemory, AgentActionStatus
from app.models.assignment import IssueRequirement, UserAssignmentHistory, UserSkill
from app.models.code_review import BugReport, CodeReview, PullRequest


# Association tables
issue_labels = Table(
    'issue_labels',
    Base.metadata,
    Column('issue_id', Integer, ForeignKey('issues.issue_id', ondelete='CASCADE'), primary_key=True),
    Column('label_id', Integer, ForeignKey('labels.label_id'), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('project_roles.role_id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.permission_id'), primary_key=True)
)

issue_sprints = Table(
    'issue_sprints',
    Base.metadata,
    Column('issue_id', Integer, ForeignKey('issues.issue_id', ondelete='CASCADE'), primary_key=True),
    Column('sprint_id', Integer, ForeignKey('sprints.sprint_id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    reported_issues = relationship("Issue", foreign_keys="Issue.reporter_user_id", back_populates="reporter")
    assigned_issues = relationship("Issue", foreign_keys="Issue.assignee_user_id", back_populates="assignee")
    comments = relationship("IssueComment", back_populates="author")
    attachments = relationship("IssueAttachment", back_populates="uploader")
    worklogs = relationship("Worklog", back_populates="user")
    project_roles = relationship("ProjectRole", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    history = relationship("IssueHistory", back_populates="changed_by")
    favorites = relationship("Favorite", back_populates="user")
    skills = relationship("UserSkill", lazy="selectin")


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(primary_key=True)
    project_key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    lead_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    project_type: Mapped[str] = mapped_column(String(50), default="software")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    lead = relationship("User")
    issues = relationship("Issue", back_populates="project")
    components = relationship("Component", back_populates="project", cascade="all, delete-orphan")
    versions = relationship("Version", back_populates="project", cascade="all, delete-orphan")
    boards = relationship("Board", back_populates="project", cascade="all, delete-orphan")
    project_roles = relationship("ProjectRole", back_populates="project", cascade="all, delete-orphan")


class IssueType(Base):
    __tablename__ = "issue_types"

    issue_type_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    icon_name: Mapped[Optional[str]] = mapped_column(String(50))
    is_subtask_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    issues = relationship("Issue", back_populates="issue_type")


class IssuePriority(Base):
    __tablename__ = "issue_priorities"

    priority_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    color_hex: Mapped[Optional[str]] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    issues = relationship("Issue", back_populates="priority")


class IssueStatus(Base):
    __tablename__ = "issue_statuses"

    status_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    color_hex: Mapped[Optional[str]] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_final_status: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    issues = relationship("Issue", back_populates="status")
    board_columns = relationship("BoardColumn", back_populates="mapped_status")


class Resolution(Base):
    __tablename__ = "resolutions"

    resolution_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))

    # Relationships
    issues = relationship("Issue", back_populates="resolution")


class Component(Base):
    __tablename__ = "components"

    component_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    lead_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="components")
    lead = relationship("User")
    issues = relationship("Issue", back_populates="component")


class Version(Base):
    __tablename__ = "versions"

    version_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    is_released: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="versions")
    issues = relationship("Issue", back_populates="version")


class Label(Base):
    __tablename__ = "labels"

    label_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color_hex: Mapped[Optional[str]] = mapped_column(String(7))

    # Relationships
    issues = relationship("Issue", secondary=issue_labels, back_populates="labels")


class Issue(Base):
    __tablename__ = "issues"

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.project_id"), nullable=False)
    issue_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("issue_types.issue_type_id"), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("issue_priorities.priority_id"))
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("issue_statuses.status_id"), nullable=False)
    resolution_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("resolutions.resolution_id"))
    assignee_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    reporter_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    component_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("components.component_id", ondelete="SET NULL"))
    version_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("versions.version_id"))
    original_estimate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    remaining_estimate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    time_spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="issues")
    issue_type = relationship("IssueType", back_populates="issues")
    priority = relationship("IssuePriority", back_populates="issues")
    status = relationship("IssueStatus", back_populates="issues")
    resolution = relationship("Resolution", back_populates="issues")
    assignee = relationship("User", foreign_keys=[assignee_user_id], back_populates="assigned_issues")
    reporter = relationship("User", foreign_keys=[reporter_user_id], back_populates="reported_issues")
    component = relationship("Component", back_populates="issues")
    version = relationship("Version", back_populates="issues")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")
    attachments = relationship("IssueAttachment", back_populates="issue", cascade="all, delete-orphan")
    worklogs = relationship("Worklog", back_populates="issue", cascade="all, delete-orphan")
    labels = relationship("Label", secondary=issue_labels, back_populates="issues")
    history = relationship("IssueHistory", back_populates="issue", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="issue", cascade="all, delete-orphan")
    sprints = relationship("Sprint", secondary=issue_sprints, back_populates="issues")
    outgoing_links = relationship(
        "IssueLink",
        foreign_keys="IssueLink.issue_id_from",
        back_populates="issue_from"
    )
    incoming_links = relationship(
        "IssueLink",
        foreign_keys="IssueLink.issue_id_to",
        back_populates="issue_to"
    )
    requirements = relationship("IssueRequirement", lazy="selectin", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", lazy="selectin", cascade="all, delete-orphan")

    @property
    def project_key(self) -> str:
        return self.project.project_key if self.project else ""

    @property
    def issue_type_name(self) -> str:
        return self.issue_type.name if self.issue_type else ""

    @property
    def priority_name(self) -> Optional[str]:
        return self.priority.name if self.priority else None

    @property
    def assignee_username(self) -> Optional[str]:
        return self.assignee.username if self.assignee else None

    @property
    def component_name(self) -> Optional[str]:
        return self.component.name if self.component else None

    @property
    def version_name(self) -> Optional[str]:
        return self.version.name if self.version else None

    @property
    def label_names(self) -> List[str]:
        return [label.name for label in self.labels]

    @property
    def reporter_username(self) -> str:
        return self.reporter.username if self.reporter else ""

    @property
    def reporter_display_name(self) -> str:
        return self.reporter.display_name if self.reporter else ""

    @property
    def time_spent_hours(self) -> float:
        return float(self.time_spent or 0)

    @property
    def status_name(self) -> str:
        return self.status.name if self.status else ""

    @property
    def resolution_name(self) -> Optional[str]:
        return self.resolution.name if self.resolution else None

    @property
    def component_description(self) -> Optional[str]:
        return self.component.description if self.component else None

    @property
    def version_released(self) -> Optional[bool]:
        return self.version.is_released if self.version else None


class IssueComment(Base):
    __tablename__ = "issue_comments"

    comment_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    issue = relationship("Issue", back_populates="comments")
    author = relationship("User", back_populates="comments")

    @property
    def username(self) -> str:
        return self.author.username if self.author else ""

    @property
    def display_name(self) -> str:
        return self.author.display_name if self.author else ""


class IssueAttachment(Base):
    __tablename__ = "issue_attachments"

    attachment_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    issue = relationship("Issue", back_populates="attachments")
    uploader = relationship("User", back_populates="attachments")

    @property
    def uploaded_by(self) -> str:
        return self.uploader.display_name if self.uploader else ""


class Worklog(Base):
    __tablename__ = "worklogs"

    worklog_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    time_spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    issue = relationship("Issue", back_populates="worklogs")
    user = relationship("User", back_populates="worklogs")

    @property
    def username(self) -> str:
        return self.user.username if self.user else ""

    @property
    def display_name(self) -> str:
        return self.user.display_name if self.user else ""


class Board(Base):
    __tablename__ = "boards"

    board_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    board_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'kanban' or 'scrum'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="boards")
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="board", cascade="all, delete-orphan")

    @property
    def project_key(self) -> str:
        return self.project.project_key if self.project else ""


class BoardColumn(Base):
    __tablename__ = "board_columns"

    column_id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(Integer, ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    column_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'status' or 'custom'
    mapped_status_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("issue_statuses.status_id"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    board = relationship("Board", back_populates="columns")
    mapped_status = relationship("IssueStatus", back_populates="board_columns")

    @property
    def status_name(self) -> Optional[str]:
        return self.mapped_status.name if self.mapped_status else None

    @property
    def status_color(self) -> Optional[str]:
        return self.mapped_status.color_hex if self.mapped_status else None


class Sprint(Base):
    __tablename__ = "sprints"

    sprint_id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(Integer, ForeignKey("boards.board_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    sprint_status: Mapped[str] = mapped_column(String(50), default="future")  # future, active, closed
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    board = relationship("Board", back_populates="sprints")
    issues = relationship("Issue", secondary=issue_sprints, back_populates="sprints")


class IssueLink(Base):
    __tablename__ = "issue_links"

    link_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id_from: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    issue_id_to: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id"), nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'blocks', 'duplicates', 'relates to', etc.

    # Relationships
    issue_from = relationship("Issue", foreign_keys=[issue_id_from], back_populates="outgoing_links")
    issue_to = relationship("Issue", foreign_keys=[issue_id_to], back_populates="incoming_links")


class ProjectRole(Base):
    __tablename__ = "project_roles"

    role_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    role_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'admin', 'member', 'viewer'
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="project_roles")
    user = relationship("User", back_populates="project_roles")
    permissions = relationship("Permission", secondary=role_permissions)


class Permission(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[int] = mapped_column(primary_key=True)
    permission_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    roles = relationship("ProjectRole", secondary=role_permissions, back_populates="permissions")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'issue_assigned', etc.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_issue_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("issues.issue_id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")
    issue = relationship("Issue")


class IssueHistory(Base):
    __tablename__ = "issue_history"

    history_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    issue = relationship("Issue", back_populates="history")
    changed_by = relationship("User", back_populates="history")


class Favorite(Base):
    __tablename__ = "favorites"

    favorite_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorites")
    issue = relationship("Issue", back_populates="favorites")
