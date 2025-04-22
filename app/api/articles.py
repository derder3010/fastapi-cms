from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from sqlmodel import Session, select, delete, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Generic, TypeVar
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models import (
    Article, 
    ArticleCreate, 
    ArticleRead, 
    ArticleUpdate,
    Category,
    ArticleTagLink,
    Product,
    ProductRead
)
from app.auth.deps import get_current_active_user, get_current_active_superuser
from app.utils.text import generate_unique_slug
from app.utils.media import save_upload

router = APIRouter(prefix="/articles", tags=["articles"])

class PaginatedResponse(BaseModel):
    items: List[ArticleRead]
    total: int
    page: int
    per_page: int
    total_pages: int

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
    category_id: str = Form(...),
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

@router.get("/", response_model=PaginatedResponse)
async def get_articles(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    tag_id: Optional[str] = Query(None, description="Filter by tag ID"),
    author_id: Optional[str] = Query(None, description="Filter by author ID"),
    published: Optional[bool] = Query(None, description="Filter by published status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    sort_by: Optional[str] = Query("created_at", description="Sort by field (created_at, updated_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    page: Optional[int] = Query(1, ge=1, description="Page number"),
    per_page: Optional[int] = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    # Build base query
    query = select(Article).distinct().options(
        selectinload(Article.category),
        selectinload(Article.author),
        selectinload(Article.tags)
    )
    
    # Check if category exists
    if category_id is not None:
        category = db.get(Category, category_id)
        logging.info(f"Filtering by category_id {category_id}, category exists: {category is not None}")
        if category is None:
            return PaginatedResponse(
                items=[],
                total=0,
                page=page,
                per_page=per_page,
                total_pages=0
            )
        query = query.where(Article.category_id == category_id)
    
    if tag_id is not None:
        # Use subquery to avoid duplicates
        articles_with_tag = (
            select(ArticleTagLink.article_id)
            .where(ArticleTagLink.tag_id == tag_id)
            .subquery()
        )
        query = query.join(articles_with_tag, Article.id == articles_with_tag.c.article_id)
    
    if author_id is not None:
        query = query.where(Article.author_id == author_id)
    
    if published is not None:
        query = query.where(Article.published == published)
    
    if search:
        search = f"%{search}%"
        query = query.where(
            or_(
                Article.title.ilike(search),
                Article.content.ilike(search)
            )
        )
    
    # Apply sorting
    if sort_by in ["created_at", "updated_at"]:
        if sort_order == "desc":
            query = query.order_by(getattr(Article, sort_by).desc())
        else:
            query = query.order_by(getattr(Article, sort_by).asc())
    
    # Get total count
    base_count_query = select(func.count(Article.id.distinct())).select_from(Article)
    
    # Apply the same conditions as the main query
    if category_id is not None:
        base_count_query = base_count_query.where(Article.category_id == category_id)
    
    if tag_id is not None:
        articles_with_tag = (
            select(ArticleTagLink.article_id)
            .where(ArticleTagLink.tag_id == tag_id)
            .subquery()
        )
        base_count_query = base_count_query.join(
            articles_with_tag, 
            Article.id == articles_with_tag.c.article_id
        )
    
    if author_id is not None:
        base_count_query = base_count_query.where(Article.author_id == author_id)
    
    if published is not None:
        base_count_query = base_count_query.where(Article.published == published)
    
    if search:
        base_count_query = base_count_query.where(
            or_(
                Article.title.ilike(search),
                Article.content.ilike(search)
            )
        )
    
    total = db.execute(base_count_query).scalar() or 0
    logging.info(f"Total articles found: {total}")
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    articles = db.execute(query).unique().scalars().all()
    
    return PaginatedResponse(
        items=articles,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(article_id: str, db: Session = Depends(get_db)):
    article = db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(
            selectinload(Article.category),
            selectinload(Article.author),
            selectinload(Article.tags),
            selectinload(Article.products)
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
            selectinload(Article.tags),
            selectinload(Article.products)
        )
    ).scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article

@router.put("/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: str,
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
    article_id: str,
    title: str = Form(...),
    content: str = Form(...),
    category_id: str = Form(...),
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
    article_id: str,
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