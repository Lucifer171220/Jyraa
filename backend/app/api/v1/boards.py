from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app import crud, schemas
from app.api.v1.dependencies import get_current_user
from app.database import get_db
from app.models import Board, BoardColumn, Issue, IssueStatus, User

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("/", response_model=schemas.BoardResponse, status_code=status.HTTP_201_CREATED)
def create_board(
    board: schemas.BoardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.project.get_by_key(db, project_key=board.project_key)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_board = Board(
        project_id=project.project_id,
        name=board.name,
        description=board.description,
        board_type=board.board_type.value if hasattr(board.board_type, "value") else board.board_type,
    )
    db.add(db_board)
    db.commit()
    db.refresh(db_board)
    return db_board


@router.get("/project/{project_id}", response_model=List[schemas.BoardResponse])
def read_project_boards(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.board.get_by_project(db, project_id=project_id, skip=skip, limit=limit)


@router.get("/{board_id}", response_model=schemas.BoardResponse)
def read_board(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_board = crud.board.get(db, board_id)
    if db_board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return db_board


@router.put("/{board_id}", response_model=schemas.BoardResponse)
def update_board(
    board_id: int,
    board_update: schemas.BoardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_board = crud.board.get(db, board_id)
    if db_board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return crud.board.update(db, db_obj=db_board, obj_in=board_update)


@router.post("/{board_id}/columns", response_model=schemas.BoardColumnResponse)
def create_board_column(
    board_id: int,
    column: schemas.BoardColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_board = crud.board.get(db, board_id)
    if not db_board:
        raise HTTPException(status_code=404, detail="Board not found")

    mapped_status = None
    if column.mapped_status_name:
        mapped_status = db.query(IssueStatus).filter(IssueStatus.name == column.mapped_status_name).first()
        if not mapped_status:
            raise HTTPException(status_code=400, detail=f"Status '{column.mapped_status_name}' not found")

    db_column = BoardColumn(
        board_id=board_id,
        name=column.name,
        column_type=column.column_type,
        mapped_status_id=mapped_status.status_id if mapped_status else None,
        sort_order=column.sort_order,
        is_editable=column.is_editable,
    )
    db.add(db_column)
    db.commit()
    db.refresh(db_column)
    return db_column


@router.get("/{board_id}/columns", response_model=List[schemas.BoardColumnResponse])
def read_board_columns(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_board = crud.board.get(db, board_id)
    if not db_board:
        raise HTTPException(status_code=404, detail="Board not found")
    return (
        db.query(BoardColumn)
        .options(joinedload(BoardColumn.mapped_status))
        .filter(BoardColumn.board_id == board_id)
        .order_by(BoardColumn.sort_order.asc())
        .all()
    )


@router.get("/{board_id}/issues")
def read_board_issues(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_board = crud.board.get(db, board_id)
    if not db_board:
        raise HTTPException(status_code=404, detail="Board not found")

    columns = (
        db.query(BoardColumn)
        .filter(BoardColumn.board_id == board_id)
        .order_by(BoardColumn.sort_order.asc())
        .all()
    )

    result = []
    for column in columns:
        issues = []
        if column.mapped_status_id:
            issues = (
                db.query(Issue)
                .filter(Issue.status_id == column.mapped_status_id, Issue.project_id == db_board.project_id)
                .all()
            )
        result.append(
            {
                "column_id": column.column_id,
                "name": column.name,
                "sort_order": column.sort_order,
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "issue_key": issue.issue_key,
                        "summary": issue.summary,
                        "priority": issue.priority.name if issue.priority else None,
                        "assignee": issue.assignee.display_name if issue.assignee else None,
                    }
                    for issue in issues
                ],
            }
        )
    return result
