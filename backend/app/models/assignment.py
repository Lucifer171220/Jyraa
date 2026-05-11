from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSkill(Base):
    __tablename__ = "user_skills"

    skill_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    proficiency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user = relationship("User")


class UserAssignmentHistory(Base):
    __tablename__ = "user_assignment_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.issue_id"), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user = relationship("User")
    issue = relationship("Issue")


class IssueRequirement(Base):
    __tablename__ = "issue_requirements"

    requirement_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.issue_id"), nullable=False, index=True)
    required_skill: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    issue = relationship("Issue")
