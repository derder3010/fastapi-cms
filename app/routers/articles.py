from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc, delete, func
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.database import get_db
from app.models import Article, Category, Comment, Tag, ArticleTagLink
from app.auth.utils import get_user_from_cookie
from app.utils.text import generate_unique_slug

router = APIRouter(prefix="/articles")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_articles(
    request: Request, 
    q: str = None, 
    page: int = 1, 
    page_size: int = 10,
    category_id: Optional[str] = None,
    author_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Create base query
    query = select(Article).options(
        selectinload(Article.category),
        selectinload(Article.author),
        selectinload(Article.tags)
    )
    
    # Track applied filters
    applied_filters = 0
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(
            Article.title.ilike(search_term) | 
            Article.content.ilike(search_term)
        )
    
    # Apply category filter
    if category_id and category_id.isdigit():
        query = query.where(Article.category_id == int(category_id))
        applied_filters += 1
    
    # Apply author filter
    if author_id and author_id.isdigit():
        query = query.where(Article.author_id == int(author_id))
        applied_filters += 1
    
    # Apply tag filter
    if tag_id and tag_id.isdigit():
        tag_id_int = int(tag_id)
        query = query.join(ArticleTagLink).where(ArticleTagLink.tag_id == tag_id_int)
        applied_filters += 1
    
    # Apply status filter
    if status:
        if status == 'published':
            query = query.where(Article.published == True)
            applied_filters += 1
        elif status == 'draft':
            query = query.where(Article.published == False)
            applied_filters += 1
    
    # Apply date range filters
    from datetime import datetime
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.where(Article.created_at >= from_date)
            applied_filters += 1
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            # Set time to end of day
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.where(Article.created_at <= to_date)
            applied_filters += 1
        except ValueError:
            pass
    
    # Count total records for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_records = db.execute(count_query).scalar_one()
    
    # Calculate pagination values
    total_pages = (total_records + page_size - 1) // page_size
    page = max(1, min(page, total_pages) if total_pages > 0 else 1)
    offset = (page - 1) * page_size
    
    # Add pagination
    paginated_query = query.order_by(desc(Article.created_at)).offset(offset).limit(page_size)
    
    # Get paginated articles with their categories, authors, and tags
    articles = db.execute(
        paginated_query
    ).unique().scalars().all()
    
    # Get all categories for the filter dropdown
    categories = db.execute(select(Category)).scalars().all()
    
    # Get all authors for the filter dropdown
    from app.models import User
    authors = db.execute(select(User)).scalars().all()
    
    # Get all tags for the filter dropdown
    tags = db.execute(select(Tag)).scalars().all()
    
    # Render the admin articles template
    return templates.TemplateResponse(
        "admin/articles/index.html",
        {
            "request": request, 
            "user": user, 
            "articles": articles,
            "query": q,
            "message": request.query_params.get("message"),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
                "has_prev": page > 1,
                "has_next": page < total_pages
            },
            # Filter variables
            "categories": categories,
            "authors": authors,
            "tags": tags,
            "filter_category_id": category_id,
            "filter_author_id": author_id,
            "filter_tag_id": tag_id,
            "filter_status": status,
            "filter_date_from": date_from,
            "filter_date_to": date_to,
            "applied_filters": applied_filters
        }
    )

@router.get("/add", response_class=HTMLResponse)
async def admin_add_article_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get categories for the form
    categories = db.execute(select(Category)).scalars().all()
    
    # Get tags for the form
    tags = db.execute(select(Tag)).scalars().all()
    
    # Render the add article form
    return templates.TemplateResponse(
        "admin/articles/add.html",
        {"request": request, "user": user, "categories": categories, "tags": tags}
    )

@router.post("/add")
async def admin_add_article(
    request: Request,
    title: str = Form(...),
    category_id: int = Form(...),
    content: str = Form(...),
    featured_image: str = Form(None),
    slug: Optional[str] = Form(None),
    published: bool = Form(False),
    tag_ids: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        # Validate category
        category = db.get(Category, category_id)
        if not category:
            categories = db.execute(select(Category)).scalars().all()
            tags = db.execute(select(Tag)).scalars().all()
            return templates.TemplateResponse(
                "admin/articles/add.html",
                {
                    "request": request, 
                    "user": user, 
                    "categories": categories, 
                    "tags": tags,
                    "error": "Invalid category selected."
                },
                status_code=400
            )
        
        # Generate slug from title if not provided
        if not slug or not slug.strip():
            existing_slugs = db.execute(select(Article.slug)).scalars().all()
            slug = generate_unique_slug(title, existing_slugs)
        
        # Create new article
        article = Article(
            title=title,
            content=content,
            category_id=category_id,
            author_id=user.id,
            published=published,
            featured_image=featured_image if featured_image and featured_image.strip() else None,
            slug=slug
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        
        # Add tags to article
        if tag_ids:
            for tag_id in tag_ids:
                tag = db.get(Tag, tag_id)
                if tag:
                    article_tag_link = ArticleTagLink(article_id=article.id, tag_id=tag_id)
                    db.add(article_tag_link)
            db.commit()
        
        return RedirectResponse(url=f"/admin/articles?message=Article '{title}' created successfully", status_code=303)
    except Exception as e:
        categories = db.execute(select(Category)).scalars().all()
        tags = db.execute(select(Tag)).scalars().all()
        return templates.TemplateResponse(
            "admin/articles/add.html",
            {
                "request": request, 
                "user": user, 
                "categories": categories, 
                "tags": tags,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{article_id}/edit", response_class=HTMLResponse)
async def admin_edit_article_form(request: Request, article_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article with relationships
        article = db.get(Article, article_id)
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Get categories for the form
        categories = db.execute(select(Category)).scalars().all()
        
        # Get tags for the form
        tags = db.execute(select(Tag)).scalars().all()
        
        # Render the edit article template
        return templates.TemplateResponse(
            "admin/articles/edit.html",
            {
                "request": request, 
                "user": user, 
                "article": article,
                "categories": categories,
                "tags": tags
            }
        )
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles'>Go back</a>")

@router.post("/{article_id}/edit")
async def admin_edit_article(
    request: Request,
    article_id: int,
    title: str = Form(...),
    category_id: int = Form(...),
    content: str = Form(...),
    featured_image: str = Form(None),
    slug: Optional[str] = Form(None),
    published: bool = Form(False),
    tag_ids: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article
        article = db.get(Article, article_id)
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Validate category
        category = db.get(Category, category_id)
        if not category:
            categories = db.execute(select(Category)).scalars().all()
            tags = db.execute(select(Tag)).scalars().all()
            return templates.TemplateResponse(
                "admin/articles/edit.html",
                {
                    "request": request, 
                    "user": user, 
                    "article": article,
                    "categories": categories,
                    "tags": tags,
                    "error": "Invalid category selected."
                },
                status_code=400
            )
        
        # Generate slug from title if not provided
        if not slug or not slug.strip():
            existing_slugs = db.execute(select(Article.slug).where(Article.id != article_id)).scalars().all()
            slug = generate_unique_slug(title, existing_slugs)
        
        # Update article
        article.title = title
        article.content = content
        article.category_id = category_id
        article.published = published
        article.featured_image = featured_image if featured_image and featured_image.strip() else None
        article.slug = slug
        
        db.add(article)
        db.commit()
        
        # Update tags for article
        # First, delete all existing article-tag relationships
        db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id == article_id))
        db.commit()
        
        # Then, add the new tag relationships
        if tag_ids:
            for tag_id in tag_ids:
                tag = db.get(Tag, tag_id)
                if tag:
                    article_tag_link = ArticleTagLink(article_id=article.id, tag_id=tag_id)
                    db.add(article_tag_link)
            db.commit()
        
        return RedirectResponse(url=f"/admin/articles?message=Article '{title}' updated successfully", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles/{article_id}/edit'>Try again</a>")

@router.get("/{article_id}/delete")
async def admin_delete_article(request: Request, article_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article
        article = db.get(Article, article_id)
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Delete all comments for this article first
        db.execute(delete(Comment).where(Comment.article_id == article_id))
        db.commit()
        
        # Get article title before deletion for success message
        article_title = article.title
        
        # Delete article
        db.delete(article)
        db.commit()
        
        return RedirectResponse(url=f"/admin/articles?message=Article '{article_title}' deleted successfully", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles'>Try again</a>")

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_articles_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count articles
    article_count = db.execute(select(Article)).all()
    count = len(article_count)
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": count,
            "item_type": "articles",
            "back_url": "/admin/articles",
            "confirm_url": "/admin/articles/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_articles(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Delete all comments first (they depend on articles)
        db.execute(delete(Comment))
        db.commit()
        
        # Delete all articles
        db.execute(delete(Article))
        db.commit()
        
        return RedirectResponse(
            url="/admin/articles?message=All articles and their comments have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting all articles: {str(e)}. <a href='/admin/articles'>Go back</a>", status_code=500) 