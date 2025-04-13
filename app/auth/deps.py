from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_db
from app.models import User
from app.auth.utils import get_current_user

# Set up OAuth2 with JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_active_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    current_user = await get_current_user(token, db)
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user 