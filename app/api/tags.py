from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
from typing import List

from app.database import get_db
from app.models import Tag, TagCreate, TagRead, TagUpdate
from app.auth.deps import get_current_active_user, get_current_active_superuser

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=TagRead)
async def create_tag(
    tag: TagCreate, 
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    tag_obj = Tag.from_orm(tag)
    db.add(tag_obj)
    db.commit()
    db.refresh(tag_obj)
    return tag_obj

@router.get("/", response_model=List[TagRead])
async def get_tags(db: Session = Depends(get_db)):
    tags = db.execute(select(Tag)).scalars().all()
    return tags

@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag

@router.put("/{tag_id}", response_model=TagRead)
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    tag_data = tag_update.dict(exclude_unset=True)
    for key, value in tag_data.items():
        setattr(tag, key, value)
    
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    try:
        tag = db.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Import these models here to avoid circular imports
        from app.models import ArticleTagLink
        
        # Delete all article-tag links for this tag
        db.execute(delete(ArticleTagLink).where(ArticleTagLink.tag_id == tag_id))
        
        # Delete the tag
        db.delete(tag)
        db.commit()
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting tag: {str(e)}")

@router.delete("/", status_code=204)
async def delete_all_tags(
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    try:
        # Import these models here to avoid circular imports
        from app.models import ArticleTagLink
        
        # First delete all article-tag links
        db.execute(delete(ArticleTagLink))
        
        # Then delete all tags
        db.execute(delete(Tag))
        
        db.commit()
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all tags: {str(e)}") 