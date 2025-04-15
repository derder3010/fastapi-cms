from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, delete, or_

from app.database import get_db
from app.models import Category, Article, Comment
from app.auth.utils import get_user_from_cookie
from app.utils.logging import log_admin_action

router = APIRouter(prefix="/categories")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_categories(
    request: Request, 
    q: str = None, 
    page: int = 1, 
    page_size: int = 10, 
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Create base query
    query = select(Category)
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(
            or_(
                Category.name.ilike(search_term),
                Category.description.ilike(search_term)
            )
        )
    
    # Count total records for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_records = db.execute(count_query).scalar_one()
    
    # Calculate pagination values
    total_pages = (total_records + page_size - 1) // page_size
    page = max(1, min(page, total_pages) if total_pages > 0 else 1)
    offset = (page - 1) * page_size
    
    # Add pagination
    paginated_query = query.order_by(Category.name).offset(offset).limit(page_size)
    
    # Get paginated categories
    categories = db.execute(paginated_query).scalars().all()
    
    # Render the admin categories template
    return templates.TemplateResponse(
        "admin/categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "query": q,
            "message": request.query_params.get("message"),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
                "has_prev": page > 1,
                "has_next": page < total_pages
            }
        }
    )

@router.get("/add", response_class=HTMLResponse)
async def admin_add_category_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Render the add category form
    return templates.TemplateResponse(
        "admin/categories/add.html",
        {"request": request, "user": user}
    )

@router.post("/add")
async def admin_add_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Check if category name already exists
        existing_category = db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
        if existing_category:
            return templates.TemplateResponse(
                "admin/categories/add.html", 
                {
                    "request": request,
                    "user": user,
                    "error": f"Category with name '{name}' already exists."
                },
                status_code=400
            )
        
        # Create new category
        category = Category(
            name=name,
            description=description,
        )
        db.add(category)
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Create Category",
            details=f"Created category: {name}",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{name}' created successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/add.html",
            {
                "request": request,
                "user": user,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{category_id}/edit", response_class=HTMLResponse)
async def admin_edit_category_form(request: Request, category_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get the category to edit
        category = db.get(Category, category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Render the edit category form
        return templates.TemplateResponse(
            "admin/categories/edit.html",
            {"request": request, "user": user, "category": category}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/list.html",
            {
                "request": request,
                "user": user,
                "categories": db.execute(select(Category)).scalars().all(),
                "error": f"Error loading category: {str(e)}"
            }
        )

@router.post("/{category_id}/edit")
async def admin_edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get category
        category = db.get(Category, category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Check if category name already exists (excluding current category)
        if category.name != name:
            existing_category = db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
            if existing_category:
                return templates.TemplateResponse(
                    "admin/categories/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "category": category,
                        "error": f"Category with name '{name}' already exists."
                    },
                    status_code=400
                )
        
        # Update category
        old_name = category.name
        category.name = name
        category.description = description
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Update Category",
            details=f"Updated category: {old_name} → {name}",
            request=request
        )
        
        db.add(category)
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{name}' updated successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/edit.html",
            {
                "request": request,
                "user": user,
                "category": category if 'category' in locals() else None,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{category_id}/delete")
async def admin_delete_category(request: Request, category_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get category
        category = db.get(Category, category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Get category name for logging
        category_name = category.name
        
        # Find all articles in this category
        article_query = select(Article.id).where(Article.category_id == category_id)
        article_ids = [row[0] for row in db.execute(article_query).all()]
        
        # If there are articles, delete related data
        if article_ids:
            # Import these models here to avoid circular imports
            from app.models import ArticleTagLink, ProductArticleLink, SystemLog
            
            # Delete article-tag links for these articles
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for these articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete comments on these articles
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
            
            # Delete all articles in this category
            db.execute(delete(Article).where(Article.category_id == category_id))
        
        # Delete category
        db.delete(category)
        
        # Log the action
        article_count = len(article_ids)
        log_details = f"Deleted category: {category_name}"
        if article_count > 0:
            log_details += f" and {article_count} related articles with all their data"
            
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete Category",
            details=log_details,
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{category_name}' and all related data deleted successfully",
            status_code=303
        )
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        print(f"Error deleting category: {str(e)}")
        
        return templates.TemplateResponse(
            "admin/categories/list.html",
            {
                "request": request,
                "user": user,
                "categories": db.execute(select(Category)).scalars().all(),
                "error": f"Error: {str(e)}."
            }
        )

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_categories_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get category count and article count for display
    category_count = db.execute(select(func.count()).select_from(Category)).scalar() or 0
    article_count = db.execute(select(func.count()).select_from(Article)).scalar() or 0
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": category_count,
            "item_type": "categories",
            "back_url": "/admin/categories",
            "confirm_url": "/admin/categories/delete-all-confirm",
            "additional_info": f"This will also delete {article_count} articles and all their related data."
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_categories(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Count categories before deletion
        categories_count = db.execute(select(func.count()).select_from(Category)).scalar() or 0
        
        # Find all articles to be deleted
        article_ids = [row[0] for row in db.execute(select(Article.id)).all()]
        articles_count = len(article_ids)
        
        # Import models to avoid circular imports
        from app.models import ArticleTagLink, ProductArticleLink, SystemLog
        
        # If articles exist, delete all related data first
        if article_ids:
            # Delete article-tag links
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete all comments on these articles
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete all articles
        db.execute(delete(Article))
        
        # Delete all categories
        db.execute(delete(Category))
        
        # Log the action
        log_details = f"Deleted all categories (total: {categories_count})"
        if articles_count > 0:
            log_details += f" and all related articles (total: {articles_count}) with their data"
            
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete All Categories",
            details=log_details,
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url="/admin/categories?message=All categories and related data have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        print(f"Error deleting all categories: {str(e)}")
        
        return RedirectResponse(
            url=f"/admin/categories?message=Error deleting all categories: {str(e)}",
            status_code=303
        ) 