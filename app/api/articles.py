from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Article, ArticleCreate, ArticleRead, ArticleUpdate
from app.auth.deps import get_current_active_user

router = APIRouter(prefix="/articles", tags=["articles"])

@router.post("/", response_model=ArticleRead)
async def create_article(
    article: ArticleCreate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    article_obj = Article.from_orm(article)
    article_obj.author_id = current_user.id
    db.add(article_obj)
    db.commit()
    db.refresh(article_obj)
    return article_obj

@router.get("/", response_model=List[ArticleRead])
async def get_articles(db: Session = Depends(get_db)):
    articles = db.execute(select(Article)).scalars().all()
    return articles

@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.put("/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Only allow the author or superuser to update the article
    if article.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update this article")
    
    article_data = article_update.dict(exclude_unset=True)
    for key, value in article_data.items():
        setattr(article, key, value)
    
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Only allow the author or superuser to delete the article
    if article.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to delete this article")
    
    # Delete associated comments first (cascade delete)
    for comment in article.comments:
        db.delete(comment)
    
    db.delete(article)
    db.commit()
    return None 