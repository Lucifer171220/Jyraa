from sqlalchemy.orm import Session
from typing import Optional, List
from app import schemas
from app import models
from app.crud.base import CRUDBase
from datetime import datetime


class CRUDUser(CRUDBase[models.User, schemas.UserCreate, schemas.UserUpdate]):
    def get_by_username(self, db: Session, *, username: str) -> Optional[models.User]:
        return db.query(models.User).filter(models.User.username == username).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[models.User]:
        return db.query(models.User).filter(models.User.email == email).first()

    def is_active(self, user: models.User) -> bool:
        return user.is_active

    def get_user_projects(self, db: Session, *, user_id: int) -> List[models.Project]:
        user_roles = db.query(models.ProjectRole).filter(models.ProjectRole.user_id == user_id).all()
        project_ids = [ur.project_id for ur in user_roles]
        return db.query(models.Project).filter(models.Project.project_id.in_(project_ids)).all()


class CRUDProject(CRUDBase[models.Project, schemas.ProjectCreate, schemas.ProjectUpdate]):
    def get_by_key(self, db: Session, *, project_key: str) -> Optional[models.Project]:
        return db.query(models.Project).filter(models.Project.project_key == project_key).first()

    def get_multi_by_lead(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Project]:
        return (
            db.query(models.Project)
            .filter(models.Project.lead_user_id == user_id)
            .order_by(models.Project.project_id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDIssue(CRUDBase[models.Issue, schemas.IssueCreate, schemas.IssueUpdate]):
    def get_by_key(self, db: Session, *, issue_key: str) -> Optional[models.Issue]:
        return db.query(models.Issue).filter(models.Issue.issue_key == issue_key).first()

    def get_by_project(
        self,
        db: Session,
        *,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
        assignee_id: Optional[int] = None,
        status_id: Optional[int] = None,
        priority_id: Optional[int] = None
    ) -> List[models.Issue]:
        query = db.query(models.Issue).filter(models.Issue.project_id == project_id)

        if assignee_id is not None:
            query = query.filter(models.Issue.assignee_user_id == assignee_id)
        if status_id is not None:
            query = query.filter(models.Issue.status_id == status_id)
        if priority_id is not None:
            query = query.filter(models.Issue.priority_id == priority_id)

        return query.order_by(models.Issue.issue_id.asc()).offset(skip).limit(limit).all()

    def get_board_issues(
        self,
        db: Session,
        *,
        board_id: int,
        column_id: Optional[int] = None
    ) -> List[models.Issue]:
        board = db.query(models.Board).filter(models.Board.board_id == board_id).first()
        if not board:
            return []

        # Get the column statuses
        columns = db.query(models.BoardColumn).filter(models.BoardColumn.board_id == board_id).all()
        status_ids = [col.mapped_status_id for col in columns if col.mapped_status_id]

        if not status_ids:
            return []

        query = db.query(models.Issue).filter(
            models.Issue.project_id == board.project_id,
            models.Issue.status_id.in_(status_ids)
        )

        if column_id:
            column = db.query(models.BoardColumn).filter(models.BoardColumn.column_id == column_id).first()
            if column and column.mapped_status_id:
                query = query.filter(models.Issue.status_id == column.mapped_status_id)

        return query.all()

    def search(
        self,
        db: Session,
        *,
        query: str,
        project_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[models.Issue]:
        search_query = db.query(models.Issue).filter(
            (models.Issue.summary.ilike(f"%{query}%")) |
            (models.Issue.issue_key.ilike(f"%{query}%")) |
            (models.Issue.description.ilike(f"%{query}%"))
        )

        if project_id:
            search_query = search_query.filter(models.Issue.project_id == project_id)

        return search_query.order_by(models.Issue.issue_id.asc()).offset(skip).limit(limit).all()


class CRUDComment(CRUDBase[models.IssueComment, schemas.CommentCreate, schemas.CommentUpdate]):
    def get_by_issue(
        self, db: Session, *, issue_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.IssueComment]:
        return (
            db.query(models.IssueComment)
            .filter(models.IssueComment.issue_id == issue_id)
            .order_by(models.IssueComment.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDWorklog(CRUDBase[models.Worklog, schemas.WorklogCreate, schemas.WorklogUpdate]):
    def get_by_issue(
        self, db: Session, *, issue_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Worklog]:
        return (
            db.query(models.Worklog)
            .filter(models.Worklog.issue_id == issue_id)
            .order_by(models.Worklog.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Worklog]:
        return (
            db.query(models.Worklog)
            .filter(models.Worklog.user_id == user_id)
            .order_by(models.Worklog.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDBoard(CRUDBase[models.Board, schemas.BoardCreate, schemas.BoardUpdate]):
    def get_by_project(
        self, db: Session, *, project_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Board]:
        return (
            db.query(models.Board)
            .filter(models.Board.project_id == project_id)
            .order_by(models.Board.board_id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDSprint(CRUDBase[models.Sprint, schemas.SprintCreate, schemas.SprintUpdate]):
    def get_by_board(
        self, db: Session, *, board_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Sprint]:
        return (
            db.query(models.Sprint)
            .filter(models.Sprint.board_id == board_id)
            .order_by(models.Sprint.start_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_sprints(self, db: Session, *, board_id: int) -> List[models.Sprint]:
        return (
            db.query(models.Sprint)
            .filter(
                models.Sprint.board_id == board_id,
                models.Sprint.sprint_status == "active"
            )
            .all()
        )


class CRUDLabel(CRUDBase[models.Label, schemas.LabelCreate, schemas.LabelUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[models.Label]:
        return db.query(models.Label).filter(models.Label.name == name).first()

    def get_or_create(self, db: Session, *, name: str, color_hex: Optional[str] = None) -> models.Label:
        label = self.get_by_name(db, name=name)
        if not label:
            label = self.create(db, obj_in=schemas.LabelCreate(name=name, color_hex=color_hex))
        return label


class CRUDNotification(CRUDBase[models.Notification, None, None]):
    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100, unread_only: bool = False
    ) -> List[models.Notification]:
        query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
        if unread_only:
            query = query.filter(models.Notification.is_read == False)
        return query.order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()

    def mark_as_read(self, db: Session, *, notification_id: int) -> Optional[models.Notification]:
        notification = self.get(db, notification_id)
        if notification:
            notification.is_read = True
            db.add(notification)
            db.commit()
            db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, user_id: int) -> int:
        result = (
            db.query(models.Notification)
            .filter(models.Notification.user_id == user_id, models.Notification.is_read == False)
            .update({"is_read": True})
        )
        db.commit()
        return result


class CRUDFavorite(CRUDBase[models.Favorite, None, None]):
    def get_user_favorites(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Favorite]:
        return (
            db.query(models.Favorite)
            .filter(models.Favorite.user_id == user_id)
            .order_by(models.Favorite.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def is_favorite(self, db: Session, *, user_id: int, issue_id: int) -> bool:
        favorite = (
            db.query(models.Favorite)
            .filter(models.Favorite.user_id == user_id, models.Favorite.issue_id == issue_id)
            .first()
        )
        return favorite is not None


class CRUDBoardColumn(CRUDBase[models.BoardColumn, schemas.BoardColumnCreate, schemas.BoardUpdate]):
    def get_by_board(
        self, db: Session, *, board_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.BoardColumn]:
        return (
            db.query(models.BoardColumn)
            .filter(models.BoardColumn.board_id == board_id)
            .order_by(models.BoardColumn.sort_order.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )


# Initialize crud instances
crud_user = CRUDUser(models.User)
crud_project = CRUDProject(models.Project)
crud_issue = CRUDIssue(models.Issue)
crud_comment = CRUDComment(models.IssueComment)
crud_worklog = CRUDWorklog(models.Worklog)
crud_board = CRUDBoard(models.Board)
crud_board_column = CRUDBoardColumn(models.BoardColumn)
crud_sprint = CRUDSprint(models.Sprint)
crud_label = CRUDLabel(models.Label)
crud_notification = CRUDNotification(models.Notification)
crud_favorite = CRUDFavorite(models.Favorite)

# Expose namespaced attributes so `from app import crud` works as `crud.user`, `crud.project`, etc.
user = crud_user
project = crud_project
issue = crud_issue
comment = crud_comment
worklog = crud_worklog
board = crud_board
board_column = crud_board_column
sprint = crud_sprint
label = crud_label
notification = crud_notification
favorite = crud_favorite
