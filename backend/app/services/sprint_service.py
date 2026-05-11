from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Board, Sprint

SPRINT_DURATION_WEEKS = 2


def create_sprint_for_board(db: Session, board_id: int, name: str | None = None) -> Sprint:
    board = db.query(Board).filter(Board.board_id == board_id).first()
    if not board:
        raise ValueError("Board not found")

    last_sprint = (
        db.query(Sprint)
        .filter(Sprint.board_id == board_id)
        .order_by(Sprint.end_date.desc())
        .first()
    )
    start_date = (last_sprint.end_date + timedelta(days=1)) if last_sprint else date.today()
    end_date = start_date + timedelta(weeks=SPRINT_DURATION_WEEKS)

    sprint = Sprint(
        board_id=board_id,
        name=name or f"Sprint {start_date.isoformat()} - {end_date.isoformat()}",
        start_date=start_date,
        end_date=end_date,
        sprint_status="future",
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


def activate_current_sprint(db: Session, board_id: int) -> list[Sprint]:
    today = date.today()
    sprints = (
        db.query(Sprint)
        .filter(
            Sprint.board_id == board_id,
            Sprint.sprint_status == "future",
            Sprint.start_date <= today,
        )
        .all()
    )
    for sprint in sprints:
        sprint.sprint_status = "active"
    db.commit()
    return sprints


def close_completed_sprint(db: Session, board_id: int) -> list[Sprint]:
    today = date.today()
    sprints = (
        db.query(Sprint)
        .filter(
            Sprint.board_id == board_id,
            Sprint.sprint_status == "active",
            Sprint.end_date < today,
        )
        .all()
    )
    for sprint in sprints:
        sprint.sprint_status = "closed"
        sprint.is_completed = True
    db.commit()
    return sprints
