from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, delete, or_

from app.database import get_db
from app.models import Tag, Article, ArticleTagLink
from app.auth.utils import get_user_from_cookie
from app.utils.logging import log_admin_action
from app.utils.text import slugify

router = APIRouter(prefix="/tags")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_tags(
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
    query = select(Tag)
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(
            Tag.name.ilike(search_term)
        )
    
    # Count total records for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_records = db.execute(count_query).scalar_one()
    
    # Calculate pagination values
    total_pages = (total_records + page_size - 1) // page_size
    page = max(1, min(page, total_pages) if total_pages > 0 else 1)
    offset = (page - 1) * page_size
    
    # Add pagination
    paginated_query = query.order_by(Tag.name).offset(offset).limit(page_size)
    
    # Get paginated tags
    tags = db.execute(paginated_query).scalars().all()
    
    # Render the admin tags template
    return templates.TemplateResponse(
        "admin/tags/list.html",
        {
            "request": request,
            "user": user,
            "tags": tags,
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
async def admin_add_tag_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Render the add tag form
    return templates.TemplateResponse(
        "admin/tags/add.html",
        {"request": request, "user": user}
    )

@router.post("/add")
async def admin_add_tag(
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Check if tag name already exists
        existing_tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if existing_tag:
            return templates.TemplateResponse(
                "admin/tags/add.html", 
                {
                    "request": request,
                    "user": user,
                    "error": f"Tag with name '{name}' already exists."
                },
                status_code=400
            )
        
        # Generate slug if empty
        if not slug:
            slug = slugify(name)
        
        # Check if slug already exists
        existing_slug = db.execute(select(Tag).where(Tag.slug == slug)).scalar_one_or_none()
        if existing_slug:
            return templates.TemplateResponse(
                "admin/tags/add.html", 
                {
                    "request": request,
                    "user": user,
                    "error": f"Tag with slug '{slug}' already exists."
                },
                status_code=400
            )
        
        # Create new tag
        tag = Tag(
            name=name,
            slug=slug
        )
        db.add(tag)
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Create Tag",
            details=f"Created tag: {name}",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/tags?message=Tag '{name}' created successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/tags/add.html",
            {
                "request": request,
                "user": user,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{tag_id}/edit", response_class=HTMLResponse)
async def admin_edit_tag_form(request: Request, tag_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get the tag to edit
        tag = db.get(Tag, tag_id)
        if not tag:
            return RedirectResponse(
                url="/admin/tags?message=Tag not found",
                status_code=303
            )
        
        # Render the edit tag form
        return templates.TemplateResponse(
            "admin/tags/edit.html",
            {"request": request, "user": user, "tag": tag}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/tags/list.html",
            {
                "request": request,
                "user": user,
                "tags": db.execute(select(Tag)).scalars().all(),
                "error": f"Error loading tag: {str(e)}"
            }
        )

@router.post("/{tag_id}/edit")
async def admin_edit_tag(
    request: Request,
    tag_id: str,
    name: str = Form(...),
    slug: str = Form(""),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get tag
        tag = db.get(Tag, tag_id)
        if not tag:
            return RedirectResponse(
                url="/admin/tags?message=Tag not found",
                status_code=303
            )
        
        # Check if tag name already exists (excluding current tag)
        if tag.name != name:
            existing_tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
            if existing_tag:
                return templates.TemplateResponse(
                    "admin/tags/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "tag": tag,
                        "error": f"Tag with name '{name}' already exists."
                    },
                    status_code=400
                )
        
        # Generate slug if empty
        if not slug:
            slug = slugify(name)
        
        # Check if slug already exists (excluding current tag)
        if slug != tag.slug:
            existing_slug = db.execute(select(Tag).where(Tag.slug == slug)).scalar_one_or_none()
            if existing_slug:
                return templates.TemplateResponse(
                    "admin/tags/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "tag": tag,
                        "error": f"Tag with slug '{slug}' already exists."
                    },
                    status_code=400
                )
        
        # Update tag
        tag.name = name
        tag.slug = slug
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Update Tag",
            details=f"Updated tag: {name}",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/tags?message=Tag '{name}' updated successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/tags/edit.html",
            {
                "request": request,
                "user": user,
                "tag": tag,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{tag_id}/delete")
async def admin_delete_tag(request: Request, tag_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get tag
        tag = db.get(Tag, tag_id)
        if not tag:
            return RedirectResponse(
                url="/admin/tags?message=Tag not found",
                status_code=303
            )
        
        # Delete the tag
        tag_name = tag.name
        db.delete(tag)
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete Tag",
            details=f"Deleted tag: {tag_name}",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/tags?message=Tag deleted successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/tags/list.html",
            {
                "request": request,
                "user": user,
                "tags": db.execute(select(Tag)).scalars().all(),
                "error": f"Error deleting tag: {str(e)}"
            }
        )

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_tags_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count tags
    tags_count = db.execute(select(func.count()).select_from(Tag)).scalar() or 0
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": tags_count,
            "item_type": "tags",
            "back_url": "/admin/tags",
            "confirm_url": "/admin/tags/delete-all-confirm",
            "additional_info": "This will also delete all tag associations with articles."
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_tags(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Count tags before deletion
        tags_count = db.execute(select(func.count()).select_from(Tag)).scalar() or 0
        
        # Delete all tags
        db.execute(delete(ArticleTagLink))
        db.execute(delete(Tag))
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete All Tags",
            details=f"Deleted all tags (total: {tags_count})",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url="/admin/tags?message=All tags have been deleted",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/tags/list.html",
            {
                "request": request,
                "user": user,
                "tags": db.execute(select(Tag)).scalars().all(),
                "error": f"Error deleting all tags: {str(e)}"
            }
        ) 