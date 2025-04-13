from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import User, UserCreate, UserRead, UserUpdate
from app.auth.deps import get_current_active_user, get_current_active_superuser
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

@router.get("/", response_model=List[UserRead])
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    users = db.execute(select(User)).scalars().all()
    return users

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Only allow superusers to update other users
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user_update.dict(exclude_unset=True)
    
    # Hash the password if it's being updated
    if "password" in user_data:
        user_data["password"] = get_password_hash(user_data["password"])
    
    for key, value in user_data.items():
        setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Only allow superusers to delete other users
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return None 