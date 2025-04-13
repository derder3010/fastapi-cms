from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Comment, CommentCreate, CommentRead
from app.auth.deps import get_current_active_user

router = APIRouter(prefix="/comments", tags=["comments"])

@router.post("/", response_model=CommentRead)
async def create_comment(
    comment: CommentCreate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    comment_obj = Comment.from_orm(comment)
    comment_obj.author_id = current_user.id
    db.add(comment_obj)
    db.commit()
    db.refresh(comment_obj)
    return comment_obj

@router.get("/", response_model=List[CommentRead])
async def get_comments(db: Session = Depends(get_db)):
    comments = db.execute(select(Comment)).scalars().all()
    return comments

@router.get("/{comment_id}", response_model=CommentRead)
async def get_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment 