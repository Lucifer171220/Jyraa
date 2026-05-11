from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app import schemas
from app import crud
from app.database import get_db
from app.auth import get_password_hash
from app.api.v1.dependencies import get_current_user
from app.models import User, Issue, Project

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user_username = crud.user.get_by_username(db, username=user.username)
    if db_user_username:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user_email = crud.user.get_by_email(db, email=user.email)
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        password_hash=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Retrieve all users"""
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/search", response_model=List[schemas.UserResponse])
def search_users(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search active users by username, display name, or email."""
    query = db.query(User).filter(User.is_active == True)
    search = q.strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(like),
                User.display_name.ilike(like),
                User.email.ilike(like),
            )
        )

    return query.order_by(User.display_name.asc(), User.username.asc()).limit(limit).all()


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_current_user(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's profile."""
    return crud.user.update(db, db_obj=current_user, obj_in=user_update)


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get user by ID"""
    db_user = crud.user.get(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user"""
    db_user = crud.user.get(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure users can only update their own profile unless admin (simplified - allow self update)
    if db_user.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    return crud.user.update(db, db_obj=db_user, obj_in=user_update)
