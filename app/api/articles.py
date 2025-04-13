from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Article, ArticleCreate, ArticleRead
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