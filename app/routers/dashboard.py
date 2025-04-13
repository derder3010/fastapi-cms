from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Category, Article, Comment, Tag
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
            "recent_articles": recent_articles,
            "recent_comments": recent_comments
        }
    ) 