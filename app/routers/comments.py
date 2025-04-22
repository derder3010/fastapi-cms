from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc, delete, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Comment, Article, User
from app.auth.utils import get_user_from_cookie
from app.utils.logging import log_admin_action

router = APIRouter(prefix="/comments")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_comments(
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
    
    # Create base query with relationships
    query = select(Comment).options(
        selectinload(Comment.article),
        selectinload(Comment.author)
    )
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(
            Comment.content.ilike(search_term)
        )
    
    # Count total records for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_records = db.execute(count_query).scalar_one()
    
    # Calculate pagination values
    total_pages = (total_records + page_size - 1) // page_size
    page = max(1, min(page, total_pages) if total_pages > 0 else 1)
    offset = (page - 1) * page_size
    
    # Add pagination
    paginated_query = query.order_by(desc(Comment.created_at)).offset(offset).limit(page_size)
    
    # Get comments
    comments = db.execute(paginated_query).unique().scalars().all()
    
    # Render the admin comments template
    return templates.TemplateResponse(
        "admin/comments/list.html",
        {
            "request": request,
            "user": user,
            "comments": comments,
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

@router.get("/{comment_id}/edit", response_class=HTMLResponse)
async def admin_edit_comment_form(request: Request, comment_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get the comment to edit
    comment = db.execute(
        select(Comment).where(Comment.id == comment_id).options(
            selectinload(Comment.article),
            selectinload(Comment.author)
        )
    ).unique().scalar_one_or_none()

    if not comment:
        return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
    
    # Render the edit comment form
    return templates.TemplateResponse(
        "admin/comments/edit.html",
        {"request": request, "user": user, "comment": comment}
    )

@router.post("/{comment_id}/edit")
async def admin_edit_comment(
    request: Request,
    comment_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get the comment to edit
    comment = db.get(Comment, comment_id)
    if not comment:
        return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
    
    # Lưu nội dung cũ để so sánh
    old_content = comment.content
    
    # Update the comment
    comment.content = content
    db.add(comment)
    
    # Log the action
    log_admin_action(
        db=db,
        user_id=user.id,
        action="Edit Comment",
        details=f"Edited comment ID: {comment_id}, from article: {comment.article.title if comment.article else 'Unknown'}",
        request=request
    )
    
    db.commit()
    
    # Redirect to comments list with success message
    return RedirectResponse(
        url="/admin/comments?message=Comment updated successfully",
        status_code=303
    )

@router.get("/{comment_id}/delete")
async def admin_delete_comment(request: Request, comment_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        # Get the comment to delete
        comment = db.get(Comment, comment_id)
        if not comment:
            return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
        
        # Store comment information for logging
        comment_id_val = comment.id
        article_title = comment.article.title if comment.article else "Unknown"
        comment_author = comment.author.username if comment.author else "Unknown"
        
        # Delete the comment
        db.delete(comment)
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete Comment",
            details=f"Deleted comment ID: {comment_id_val}, from article: {article_title}, by: {comment_author}",
            request=request
        )
        
        db.commit()
        
        # Redirect to comments list with success message
        return RedirectResponse(
            url="/admin/comments?message=Comment deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting comment: {str(e)}. <a href='/admin/comments'>Go back</a>", status_code=500)

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_comments_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count comments
    comment_count = db.execute(select(Comment)).all()
    count = len(comment_count)
    
    if count == 0:
        return templates.TemplateResponse(
            "admin/comments/list.html",
            {
                "request": request,
                "user": user,
                "comments": [],
                "error": "There are no comments to delete."
            }
        )
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": count,
            "item_type": "comments",
            "back_url": "/admin/comments",
            "confirm_url": "/admin/comments/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_comments(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Count comments before deleting
        comment_count = db.execute(select(func.count()).select_from(Comment)).scalar_one_or_none() or 0
        
        # Delete all comments
        db.execute(delete(Comment))
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete All Comments",
            details=f"Deleted all comments ({comment_count} total)",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url="/admin/comments?message=All comments have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting all comments: {str(e)}. <a href='/admin/comments'>Go back</a>", status_code=500) 