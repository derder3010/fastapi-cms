from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import User, UserCreate, UserRead
from app.auth.deps import get_current_active_user
from app.auth.utils import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    user_obj = User(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
        is_active=user.is_active,
        is_superuser=user.is_superuser
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user 