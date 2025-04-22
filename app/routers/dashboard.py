from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Category, Article, Comment, Tag, Product
from app.auth.utils import get_user_from_cookie

router = APIRouter(prefix="/dashboard")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get counts for dashboard
    users_count = db.execute(select(func.count()).select_from(User)).scalar() or 0
    categories_count = db.execute(select(func.count()).select_from(Category)).scalar() or 0
    articles_count = db.execute(select(func.count()).select_from(Article)).scalar() or 0
    comments_count = db.execute(select(func.count()).select_from(Comment)).scalar() or 0
    tags_count = db.execute(select(func.count()).select_from(Tag)).scalar() or 0
    products_count = db.execute(select(func.count()).select_from(Product)).scalar() or 0
    
    # Get recent articles and comments
    recent_articles = db.execute(
        select(Article).options(
            selectinload(Article.author),
            selectinload(Article.category)
        ).order_by(desc(Article.created_at)).limit(5)
    ).unique().scalars().all()
    
    recent_comments = db.execute(
        select(Comment).options(
            selectinload(Comment.author),
            selectinload(Comment.article).selectinload(Article.author)
        ).order_by(desc(Comment.created_at)).limit(5)
    ).unique().scalars().all()
    
    # Get recent products
    recent_products = db.execute(
        select(Product).order_by(desc(Product.created_at)).limit(8)
    ).scalars().all()
    
    # Get top 10 articles by views for the chart
    top_articles_by_views = db.execute(
        select(Article).options(
            selectinload(Article.category)
        ).order_by(desc(Article.views)).limit(10)
    ).unique().scalars().all()
    
    # Prepare data for the chart
    article_chart_data = {
        'labels': [article.title[:20] + '...' if len(article.title) > 20 else article.title for article in top_articles_by_views],
        'views': [article.views for article in top_articles_by_views],
        'categories': [article.category.name for article in top_articles_by_views],
        'ids': [str(article.id) for article in top_articles_by_views]
    }
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "users_count": users_count,
            "categories_count": categories_count,
            "articles_count": articles_count,
            "comments_count": comments_count,
            "tags_count": tags_count,
            "products_count": products_count,
            "recent_articles": recent_articles,
            "recent_comments": recent_comments,
            "recent_products": recent_products,
            "article_chart_data": article_chart_data
        }
    )

@router.get("/search", response_class=HTMLResponse)
async def admin_search(request: Request, q: str = "", db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    search_term = f"%{q}%"
    results = {}
    
    if q:
        # Search users
        users = db.execute(
            select(User).where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term)
                )
            ).limit(5)
        ).scalars().all()
        results["users"] = users
        
        # Search articles
        articles = db.execute(
            select(Article).options(
                selectinload(Article.author),
                selectinload(Article.category)
            ).where(
                or_(
                    Article.title.ilike(search_term),
                    Article.content.ilike(search_term)
                )
            ).limit(5)
        ).unique().scalars().all()
        results["articles"] = articles
        
        # Search categories
        categories = db.execute(
            select(Category).where(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term)
                )
            ).limit(5)
        ).scalars().all()
        results["categories"] = categories
        
        # Search tags
        tags = db.execute(
            select(Tag).where(
                Tag.name.ilike(search_term)
            ).limit(5)
        ).scalars().all()
        results["tags"] = tags
        
        # Search products
        products = db.execute(
            select(Product).where(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            ).limit(5)
        ).scalars().all()
        results["products"] = products
        
        # Search comments
        comments = db.execute(
            select(Comment).options(
                selectinload(Comment.author),
                selectinload(Comment.article)
            ).where(
                Comment.content.ilike(search_term)
            ).limit(5)
        ).unique().scalars().all()
        results["comments"] = comments
    
    return templates.TemplateResponse(
        "admin/search.html",
        {
            "request": request,
            "user": user,
            "query": q,
            "results": results
        }
    ) 