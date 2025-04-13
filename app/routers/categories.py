from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, delete

from app.database import get_db
from app.models import Category, Article, Comment
from app.auth.utils import get_user_from_cookie

router = APIRouter(prefix="/categories")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get all categories
    categories = db.execute(select(Category)).scalars().all()
    
    # Render the admin categories template
    return templates.TemplateResponse(
        "admin/categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "message": request.query_params.get("message")
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
        category.name = name
        category.description = description
        
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
        
        # Check if category has articles
        article_count = db.execute(
            select(func.count()).select_from(Article).where(Article.category_id == category_id)
        ).scalar() or 0
        
        if article_count > 0:
            return templates.TemplateResponse(
                "admin/categories/list.html",
                {
                    "request": request,
                    "user": user,
                    "categories": db.execute(select(Category)).scalars().all(),
                    "error": f"Cannot delete category '{category.name}' because it has {article_count} articles. Remove the articles first."
                }
            )
        
        # Get category name before deletion for success message
        category_name = category.name
        
        # Delete category
        db.delete(category)
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{category_name}' deleted successfully",
            status_code=303
        )
    except Exception as e:
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
    
    # Check if any categories have articles
    categories_with_articles = db.execute(
        select(Category.id, Category.name, func.count(Article.id).label("article_count"))
        .join(Article, Category.id == Article.category_id, isouter=True)
        .group_by(Category.id)
        .having(func.count(Article.id) > 0)
    ).all()
    
    if categories_with_articles:
        # Some categories have articles, show error message
        category_list = ", ".join([f"'{cat.name}' ({cat.article_count} articles)" for cat in categories_with_articles])
        return templates.TemplateResponse(
            "admin/categories/list.html",
            {
                "request": request,
                "user": user,
                "categories": db.execute(select(Category)).scalars().all(),
                "error": f"Cannot delete all categories because some have articles: {category_list}. Delete the articles first."
            }
        )
    
    # Count categories
    category_count = db.execute(select(Category)).all()
    count = len(category_count)
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": count,
            "item_type": "categories",
            "back_url": "/admin/categories",
            "confirm_url": "/admin/categories/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_categories(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Check again if any categories have articles
        categories_with_articles = db.execute(
            select(Category.id)
            .join(Article, Category.id == Article.category_id)
            .group_by(Category.id)
        ).all()
        
        if categories_with_articles:
            return RedirectResponse(
                url="/admin/categories?message=Cannot delete all categories because some have articles. Delete the articles first.",
                status_code=303
            )
        
        # Delete all categories
        db.execute(delete(Category))
        db.commit()
        
        return RedirectResponse(
            url="/admin/categories?message=All categories have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting all categories: {str(e)}. <a href='/admin/categories'>Go back</a>", status_code=500) 