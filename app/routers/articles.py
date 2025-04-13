from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc, delete
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.models import Article, Category, Comment
from app.auth.utils import get_user_from_cookie
from app.utils.text import generate_unique_slug

router = APIRouter(prefix="/articles")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_articles(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all articles with their categories and authors
    articles = db.execute(
        select(Article).options(
            selectinload(Article.category),
            selectinload(Article.author)
        ).order_by(desc(Article.created_at))
    ).unique().scalars().all()
    
    # Render the admin articles template
    return templates.TemplateResponse(
        "admin/articles/index.html",
        {"request": request, "user": user, "articles": articles, "message": request.query_params.get("message")}
    )

@router.get("/add", response_class=HTMLResponse)
async def admin_add_article_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all categories for the dropdown
    categories = db.execute(select(Category)).scalars().all()
    
    # Render the add article form
    return templates.TemplateResponse(
        "admin/articles/add.html",
        {"request": request, "user": user, "categories": categories}
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
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Validate category exists
    category = db.get(Category, category_id)
    if not category:
        categories = db.execute(select(Category)).all()
        return templates.TemplateResponse(
            "admin/articles/add.html",
            {
                "request": request, 
                "user": user, 
                "categories": categories,
                "error": "Invalid category selected."
            },
            status_code=400
        )
    
    # Generate slug from title if not provided
    if not slug or not slug.strip():
        existing_slugs = db.execute(select(Article.slug)).scalars().all()
        slug = generate_unique_slug(title, existing_slugs)
    
    # Create the article
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
    
    # Redirect to articles list with success message
    return RedirectResponse(
        url=f"/admin/articles?message=Article '{title}' created successfully",
        status_code=303
    )

@router.get("/{article_id}/edit", response_class=HTMLResponse)
async def admin_edit_article_form(request: Request, article_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article with its category
        article = db.execute(
            select(Article).where(Article.id == article_id).options(
                selectinload(Article.category)
            )
        ).unique().scalar_one_or_none()
        
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Get all categories for the dropdown
        categories = db.execute(select(Category)).scalars().all()
        
        # Render the edit article template
        return templates.TemplateResponse(
            "admin/articles/edit.html",
            {
                "request": request, 
                "user": user, 
                "article": article,
                "categories": categories
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
            categories = db.execute(select(Category)).all()
            return templates.TemplateResponse(
                "admin/articles/edit.html",
                {
                    "request": request, 
                    "user": user, 
                    "article": article,
                    "categories": categories,
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