from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, delete, or_, func, desc
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import User, Article, Comment
from app.auth.utils import get_user_from_cookie, get_password_hash
from app.utils.logging import log_admin_action

router = APIRouter(prefix="/users")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    q: str = None, 
    page: int = 1, 
    page_size: int = 10,
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
    query = select(User)
    
    # Track applied filters
    applied_filters = 0
    
    # Apply search filter if query parameter is provided
    if q:
        search_term = f"%{q}%"
        query = query.where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    # Apply status filter
    if status:
        if status == 'published':  # We'll use 'published' for active users to be consistent with article status
            query = query.where(User.is_active == True)
            applied_filters += 1
        elif status == 'draft':    # We'll use 'draft' for inactive users
            query = query.where(User.is_active == False)
            applied_filters += 1
    
    # Apply date range filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.where(User.created_at >= from_date)
            applied_filters += 1
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            # Set time to end of day
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.where(User.created_at <= to_date)
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
    paginated_query = query.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    
    # Get users
    users = db.execute(paginated_query).scalars().all()
    
    # Render the admin users template
    return templates.TemplateResponse(
        "admin/users/list.html",
        {
            "request": request,
            "user": user,
            "users": users,
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
            "filter_status": status,
            "filter_date_from": date_from,
            "filter_date_to": date_to,
            "applied_filters": applied_filters
        }
    )

@router.get("/add", response_class=HTMLResponse)
async def admin_add_user_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Render the add user form
    return templates.TemplateResponse(
        "admin/users/add.html",
        {"request": request, "user": user}
    )

@router.post("/add")
async def admin_add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    is_active: bool = Form(False),
    is_superuser: bool = Form(False),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Check if username or email already exists
    existing_user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing_user:
        return templates.TemplateResponse(
            "admin/users/add.html",
            {
                "request": request,
                "user": user,
                "error": f"User with username {username} already exists."
            },
            status_code=400
        )
    
    existing_email = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing_email:
        return templates.TemplateResponse(
            "admin/users/add.html",
            {
                "request": request,
                "user": user,
                "error": f"User with email {email} already exists."
            },
            status_code=400
        )
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    db.add(new_user)
    
    # Log the action
    role_text = "Admin" if is_superuser else "Regular user"
    status_text = "Active" if is_active else "Inactive"
    log_admin_action(
        db=db,
        user_id=user.id,
        action="Create User",
        details=f"Created user: {username} (Email: {email}, Role: {role_text}, Status: {status_text})",
        request=request
    )
    
    db.commit()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User created successfully",
        status_code=303
    )

@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user_form(request: Request, user_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to edit
    user_to_edit = db.get(User, user_id)
    if not user_to_edit:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Render the edit user form
    return templates.TemplateResponse(
        "admin/users/edit.html",
        {"request": request, "user": user, "edit_user": user_to_edit}
    )

@router.post("/{user_id}/edit")
async def admin_edit_user(
    request: Request,
    user_id: str,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    is_active: bool = Form(False),
    is_superuser: bool = Form(False),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to edit
    user_to_edit = db.get(User, user_id)
    if not user_to_edit:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Check if username or email already exists (excluding the current user)
    if user_to_edit.username != username:
        existing_user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing_user:
            return templates.TemplateResponse(
                "admin/users/edit.html",
                {
                    "request": request,
                    "user": user,
                    "edit_user": user_to_edit,
                    "error": f"User with username {username} already exists."
                },
                status_code=400
            )
    
    if user_to_edit.email != email:
        existing_email = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing_email:
            return templates.TemplateResponse(
                "admin/users/edit.html",
                {
                    "request": request,
                    "user": user,
                    "edit_user": user_to_edit,
                    "error": f"User with email {email} already exists."
                },
                status_code=400
            )
    
    # Save original values for logging
    old_username = user_to_edit.username
    old_email = user_to_edit.email
    old_is_active = user_to_edit.is_active
    old_is_superuser = user_to_edit.is_superuser
    
    # Update user fields
    user_to_edit.username = username
    user_to_edit.email = email
    user_to_edit.first_name = first_name
    user_to_edit.last_name = last_name
    user_to_edit.is_active = is_active
    user_to_edit.is_superuser = is_superuser
    
    # Update password if provided
    if password:
        user_to_edit.password = get_password_hash(password)
    
    # Log the action
    changes = []
    if old_username != username:
        changes.append(f"username: {old_username} → {username}")
    if old_email != email:
        changes.append(f"email: {old_email} → {email}")
    if old_is_active != is_active:
        changes.append(f"status: {'Active' if old_is_active else 'Inactive'} → {'Active' if is_active else 'Inactive'}")
    if old_is_superuser != is_superuser:
        changes.append(f"role: {'Admin' if old_is_superuser else 'Regular user'} → {'Admin' if is_superuser else 'Regular user'}")
    if password:
        changes.append("password: updated")
    
    log_admin_action(
        db=db,
        user_id=user.id,
        action="Update User",
        details=f"Updated user: {username} (ID: {user_id}). Changes: {', '.join(changes) if changes else 'minor updates'}",
        request=request
    )
    
    db.add(user_to_edit)
    db.commit()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User updated successfully",
        status_code=303
    )

@router.get("/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get the user to delete
        user_to_delete = db.get(User, user_id)
        if not user_to_delete:
            return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
        
        # Cannot delete yourself
        if user_to_delete.id == user.id:
            return RedirectResponse(url="/admin/users?message=You cannot delete your own account", status_code=303)
        
        # Store info for logging
        username = user_to_delete.username
        
        # First get the IDs of all articles by this user
        article_ids_query = select(Article.id).where(Article.author_id == user_id)
        article_ids = [row[0] for row in db.execute(article_ids_query).all()]
        
        # Import relationship models to avoid circular imports
        from app.models import SystemLog, ArticleTagLink, ProductArticleLink
        
        # Delete article-tag links for this user's articles
        if article_ids:
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for this user's articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete ALL comments on the user's articles (regardless of commenter)
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete system logs for this user
        db.execute(delete(SystemLog).where(SystemLog.user_id == user_id))
        
        # Delete all comments made by the user on any article
        db.execute(delete(Comment).where(Comment.author_id == user_id))
        
        # Delete all articles by the user
        db.execute(delete(Article).where(Article.author_id == user_id))
        
        # Now delete the user
        db.delete(user_to_delete)
        
        # Log the action for the admin (not the deleted user)
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete User",
            details=f"Deleted user: {username}",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url="/admin/users?message=User deleted successfully",
            status_code=303
        )
    except Exception as e:
        # Roll back the transaction on error
        db.rollback()
        print(f"Error deleting user: {str(e)}")  # Log the error for debugging
        
        return RedirectResponse(
            url=f"/admin/users?message=Error deleting user: {str(e)}",
            status_code=303
        )

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_users_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count users
    user_count = db.execute(select(User).where(User.id != user.id)).all()
    count = len(user_count)
    
    if count == 0:
        return templates.TemplateResponse(
            "admin/users/list.html",
            {
                "request": request,
                "user": user,
                "users": db.execute(select(User)).scalars().all(),
                "error": "There are no other users to delete.",
                "applied_filters": 0,  # Add the missing parameter
                "pagination": {  # Add pagination data
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 1,
                    "total_records": count,
                    "has_prev": False,
                    "has_next": False
                }
            }
        )
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": count,
            "item_type": "users (except your account)",
            "back_url": "/admin/users",
            "confirm_url": "/admin/users/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_users(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Count users before deletion
        users_count = db.execute(select(func.count()).select_from(User).where(User.id != user.id)).scalar() or 0
        
        # First get the IDs of all articles by users other than the current admin
        article_ids_query = select(Article.id).join(User).where(User.id != user.id)
        article_ids = [row[0] for row in db.execute(article_ids_query).all()]
        
        # Import relationship models to avoid circular imports
        from app.models import SystemLog, ArticleTagLink, ProductArticleLink
        
        # Delete article-tag links for other users' articles
        if article_ids:
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for other users' articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete ALL comments on these articles (regardless of commenter)
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete system logs for all users except current
        db.execute(delete(SystemLog).where(SystemLog.user_id != user.id))
        
        # Delete remaining comments by users other than the current admin
        db.execute(delete(Comment).where(Comment.author_id != user.id))
        
        # Delete articles by users other than the current admin
        db.execute(delete(Article).where(Article.author_id != user.id))
        
        # Finally delete all users except the current one
        db.execute(delete(User).where(User.id != user.id))
        
        # Log the action
        log_admin_action(
            db=db,
            user_id=user.id,
            action="Delete All Users",
            details=f"Deleted all users except current admin (total deleted: {users_count})",
            request=request
        )
        
        db.commit()
        
        return RedirectResponse(
            url="/admin/users?message=All users (except you) have been deleted",
            status_code=303
        )
    except Exception as e:
        # Roll back the transaction on error
        db.rollback()
        print(f"Error deleting all users: {str(e)}")  # Log the error for debugging
        
        return RedirectResponse(
            url=f"/admin/users?message=Error deleting all users: {str(e)}",
            status_code=303
        ) 