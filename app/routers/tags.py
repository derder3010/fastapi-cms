from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, delete

from app.database import get_db
from app.models import Tag, Article
from app.auth.utils import get_user_from_cookie

router = APIRouter(prefix="/tags")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_tags(request: Request, q: str = None, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Create base query
    query = select(Tag)
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(Tag.name.ilike(search_term))
    
    # Get tags
    tags = db.execute(query).scalars().all()
    
    # Render the admin tags template
    return templates.TemplateResponse(
        "admin/tags/list.html",
        {
            "request": request,
            "user": user,
            "tags": tags,
            "query": q,
            "message": request.query_params.get("message")
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
        
        # Create new tag
        tag = Tag(name=name)
        db.add(tag)
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
async def admin_edit_tag_form(request: Request, tag_id: int, db: Session = Depends(get_db)):
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
    tag_id: int,
    name: str = Form(...),
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
        
        # Update tag
        tag.name = name
        
        db.add(tag)
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
                "tag": tag if 'tag' in locals() else None,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{tag_id}/delete")
async def admin_delete_tag(request: Request, tag_id: int, db: Session = Depends(get_db)):
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
        
        # Delete tag
        db.delete(tag)
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
        "admin/confirm_delete.html",
        {
            "request": request,
            "user": user,
            "count": tags_count,
            "item_type": "tags",
            "cancel_url": "/admin/tags",
            "confirm_url": "/admin/tags/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_tags(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Delete all tags
        db.execute(delete(Tag))
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