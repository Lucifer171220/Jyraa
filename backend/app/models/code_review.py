from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PullRequest(Base):
    __tablename__ = "pull_requests"

    pr_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.issue_id"), nullable=False, index=True)
    github_pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    issue = relationship("Issue")
    reviews = relationship("CodeReview", back_populates="pull_request", cascade="all, delete-orphan")
    bugs = relationship("BugReport", back_populates="pull_request", cascade="all, delete-orphan")


class CodeReview(Base):
    __tablename__ = "code_reviews"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pr_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.pr_id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    pull_request = relationship("PullRequest", back_populates="reviews")


class BugReport(Base):
    __tablename__ = "bug_reports"

    bug_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pr_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.pr_id"), nullable=False, index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.issue_id"), nullable=False, index=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    pull_request = relationship("PullRequest", back_populates="bugs")
    issue = relationship("Issue")
