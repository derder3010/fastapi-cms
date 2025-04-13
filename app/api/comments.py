from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Comment, CommentCreate, CommentRead, CommentUpdate
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

@router.put("/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: int, 
    comment_update: CommentUpdate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    comment_data = comment_update.dict(exclude_unset=True)
    for key, value in comment_data.items():
        setattr(comment, key, value)
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    db.delete(comment)
    db.commit()
    return None 