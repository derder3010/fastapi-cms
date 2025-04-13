from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc, delete
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Comment, Article
from app.auth.utils import get_user_from_cookie

router = APIRouter(prefix="/comments")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_comments(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all comments with related article and author
    comments = db.execute(
        select(Comment).options(
            selectinload(Comment.article).selectinload(Article.author),
            selectinload(Comment.author)
        ).order_by(desc(Comment.created_at))
    ).unique().scalars().all()
    
    # Render the admin comments template
    return templates.TemplateResponse(
        "admin/comments/index.html",
        {"request": request, "user": user, "comments": comments, "message": request.query_params.get("message")}
    )

@router.get("/{comment_id}/edit", response_class=HTMLResponse)
async def admin_edit_comment_form(request: Request, comment_id: int, db: Session = Depends(get_db)):
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
    comment_id: int,
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
    
    # Update the comment
    comment.content = content
    db.add(comment)
    db.commit()
    
    # Redirect to comments list with success message
    return RedirectResponse(
        url="/admin/comments?message=Comment updated successfully",
        status_code=303
    )

@router.get("/{comment_id}/delete")
async def admin_delete_comment(request: Request, comment_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        # Get the comment to delete
        comment = db.get(Comment, comment_id)
        if not comment:
            return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
        
        # Delete the comment
        db.delete(comment)
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
            "admin/comments/index.html",
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
        # Delete all comments
        db.execute(delete(Comment))
        db.commit()
        
        return RedirectResponse(
            url="/admin/comments?message=All comments have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting all comments: {str(e)}. <a href='/admin/comments'>Go back</a>", status_code=500) 