from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
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
        is_superuser=user.is_superuser,
        first_name=user.first_name,
        last_name=user.last_name
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
    current_user: User = Depends(get_current_active_superuser)
):
    try:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cannot delete yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")
        
        # Import related models here to avoid circular imports
        from app.models import Article, Comment, SystemLog, ArticleTagLink, ProductArticleLink
        
        # First get the IDs of all articles by this user
        article_query = select(Article.id).where(Article.author_id == user_id)
        article_ids = [row[0] for row in db.execute(article_query).all()]
        
        # If there are articles, delete related data
        if article_ids:
            # Delete article-tag links for this user's articles
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for this user's articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete ALL comments on the user's articles (regardless of commenter)
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete system logs for this user
        db.execute(delete(SystemLog).where(SystemLog.user_id == user_id))
        
        # Delete all comments made by the user on any article
        db.execute(delete(Comment).where(Comment.author_id == user_id))
        
        # Delete all articles by the user
        db.execute(delete(Article).where(Article.author_id == user_id))
        
        # Now delete the user
        db.delete(user)
        db.commit()
        
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@router.delete("/", status_code=204)
async def delete_all_users(
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    try:
        # Import related models here to avoid circular imports
        from app.models import Article, Comment, SystemLog, ArticleTagLink, ProductArticleLink
        
        # First get the IDs of all articles by users other than the current admin
        article_ids_query = select(Article.id).join(User).where(User.id != current_user.id)
        article_ids = [row[0] for row in db.execute(article_ids_query).all()]
        
        # If there are articles, delete related data
        if article_ids:
            # Delete article-tag links for other users' articles
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for other users' articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete ALL comments on these articles (regardless of commenter)
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete system logs for all users except current
        db.execute(delete(SystemLog).where(SystemLog.user_id != current_user.id))
        
        # Delete remaining comments by users other than the current admin
        db.execute(delete(Comment).where(Comment.author_id != current_user.id))
        
        # Delete articles by users other than the current admin
        db.execute(delete(Article).where(Article.author_id != current_user.id))
        
        # Finally delete all users except the current one
        db.execute(delete(User).where(User.id != current_user.id))
        
        db.commit()
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all users: {str(e)}") 