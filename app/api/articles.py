from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlmodel import Session, select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json

from app.database import get_db
from app.models import (
    Article, 
    ArticleCreate, 
    ArticleRead, 
    ArticleUpdate,
    TagRead,
    CategoryRead,
    UserRead
)
from app.auth.deps import get_current_active_user, get_current_active_superuser
from app.utils.text import generate_unique_slug
from app.utils.media import save_upload

router = APIRouter(prefix="/articles", tags=["articles"])

@router.post("/", response_model=ArticleRead)
async def create_article(
    article: ArticleCreate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    article_obj = Article.from_orm(article)
    article_obj.author_id = current_user.id
    
    # Generate slug from title if not provided
    if not article_obj.slug:
        # Get existing slugs to ensure uniqueness
        existing_slugs = db.execute(select(Article.slug)).scalars().all()
        article_obj.slug = generate_unique_slug(article_obj.title, existing_slugs)
    
    db.add(article_obj)
    db.commit()
    db.refresh(article_obj)
    return article_obj

@router.post("/upload", response_model=ArticleRead)
async def create_article_with_file(
    title: str = Form(...),
    content: str = Form(...),
    category_id: int = Form(...),
    featured_image: Optional[UploadFile] = File(None),
    excerpt: Optional[str] = Form(None),
    footer_content: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    published: bool = Form(False),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Handle file upload
    featured_image_path = None
    if featured_image:
        featured_image_path = await save_upload(featured_image, folder="articles")
    
    # Generate slug from title if not provided
    if not slug or not slug.strip():
        existing_slugs = db.execute(select(Article.slug)).scalars().all()
        slug = generate_unique_slug(title, existing_slugs)
    
    # Create article
    article = Article(
        title=title,
        content=content,
        category_id=category_id,
        author_id=current_user.id,
        featured_image=featured_image_path,
        slug=slug,
        excerpt=excerpt if excerpt and excerpt.strip() else None,
        footer_content=footer_content if footer_content and footer_content.strip() else None,
        published=published
    )
    
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

@router.get("/", response_model=List[ArticleRead])
async def get_articles(db: Session = Depends(get_db)):
    articles = db.execute(
        select(Article).options(
            selectinload(Article.category),
            selectinload(Article.author),
            selectinload(Article.tags)
        )
    ).scalars().all()
    return articles

@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(
            selectinload(Article.category),
            selectinload(Article.author),
            selectinload(Article.tags)
        )
    ).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.get("/by-slug/{slug}", response_model=ArticleRead)
async def get_article_by_slug(slug: str, db: Session = Depends(get_db)):
    article = db.execute(
        select(Article)
        .where(Article.slug == slug)
        .options(
            selectinload(Article.category),
            selectinload(Article.author),
            selectinload(Article.tags)
        )
    ).scalar_one_or_none()
    
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
    
    # If title is updated but slug is not provided, regenerate slug
    if "title" in article_data and "slug" not in article_data:
        # Get existing slugs excluding current article's slug
        existing_slugs = db.execute(select(Article.slug).where(Article.id != article_id)).scalars().all()
        article_data["slug"] = generate_unique_slug(article_data["title"], existing_slugs)
    
    for key, value in article_data.items():
        setattr(article, key, value)
    
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

@router.put("/{article_id}/upload", response_model=ArticleRead)
async def update_article_with_file(
    article_id: int,
    title: str = Form(...),
    content: str = Form(...),
    category_id: int = Form(...),
    featured_image: Optional[UploadFile] = File(None),
    excerpt: Optional[str] = Form(None),
    footer_content: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    published: bool = Form(False),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Only allow the author or superuser to update the article
    if article.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update this article")
    
    # Handle file upload
    if featured_image:
        article.featured_image = await save_upload(featured_image, folder="articles")
    
    # Generate slug from title if not provided
    if not slug or not slug.strip():
        existing_slugs = db.execute(select(Article.slug).where(Article.id != article_id)).scalars().all()
        slug = generate_unique_slug(title, existing_slugs)
    
    # Update article fields
    article.title = title
    article.content = content
    article.category_id = category_id
    article.slug = slug
    article.excerpt = excerpt if excerpt and excerpt.strip() else None
    article.footer_content = footer_content if footer_content and footer_content.strip() else None
    article.published = published
    
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
    try:
        article = db.get(Article, article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Only allow the author or superuser to delete the article
        if article.author_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to delete this article")
        
        # Import these models here to avoid circular imports
        from app.models import Comment, ArticleTagLink, ProductArticleLink
        
        # Delete article-tag links for this article
        db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id == article_id))
        
        # Delete article-product links for this article
        db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id == article_id))
        
        # Delete all comments on this article
        db.execute(delete(Comment).where(Comment.article_id == article_id))
        
        # Delete the article
        db.delete(article)
        db.commit()
        
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting article: {str(e)}")

@router.delete("/", status_code=204)
async def delete_all_articles(
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    try:
        # Import these models here to avoid circular imports
        from app.models import Comment, ArticleTagLink, ProductArticleLink
        
        # Get all article IDs
        article_ids = [row[0] for row in db.execute(select(Article.id)).all()]
        
        if article_ids:
            # Delete all article-tag links
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete all article-product links
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete all comments on all articles
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete all articles
        db.execute(delete(Article))
        
        db.commit()
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all articles: {str(e)}") 