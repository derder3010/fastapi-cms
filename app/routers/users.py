from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, delete, or_, func, desc

from app.database import get_db
from app.models import User, Article, Comment
from app.auth.utils import get_user_from_cookie, get_password_hash

router = APIRouter(prefix="/users")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_users(
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
    query = select(User)
    
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
            }
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
    db.commit()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User created successfully",
        status_code=303
    )

@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user_form(request: Request, user_id: int, db: Session = Depends(get_db)):
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
    user_id: int,
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
    
    db.add(user_to_edit)
    db.commit()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User updated successfully",
        status_code=303
    )

@router.get("/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to delete
    user_to_delete = db.get(User, user_id)
    if not user_to_delete:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Prevent deleting your own account
    if user_to_delete.id == user.id:
        return RedirectResponse(
            url="/admin/users?message=You cannot delete your own account",
            status_code=303
        )
    
    # Delete articles and comments authored by this user first
    try:
        # Delete comments by this user
        db.execute(delete(Comment).where(Comment.author_id == user_id))
        db.commit()
        
        # Get articles by this user
        articles_by_user = db.execute(select(Article.id).where(Article.author_id == user_id)).scalars().all()
        
        # Delete comments on articles by this user
        for article_id in articles_by_user:
            db.execute(delete(Comment).where(Comment.article_id == article_id))
        db.commit()
        
        # Delete articles by this user
        db.execute(delete(Article).where(Article.author_id == user_id))
        db.commit()
        
        # Delete user
        db.delete(user_to_delete)
        db.commit()
        
        return RedirectResponse(
            url="/admin/users?message=User deleted successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/users/list.html",
            {
                "request": request,
                "user": user,
                "users": db.execute(select(User)).scalars().all(),
                "error": f"Error deleting user: {str(e)}"
            },
            status_code=500
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
                "error": "There are no other users to delete."
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
        # Get IDs of users to delete (all except current user)
        users_to_delete = db.execute(select(User.id).where(User.id != user.id)).scalars().all()
        
        # Delete all content related to these users
        for user_id in users_to_delete:
            # Delete comments by this user
            db.execute(delete(Comment).where(Comment.author_id == user_id))
            
            # Get articles by this user
            articles_by_user = db.execute(select(Article.id).where(Article.author_id == user_id)).scalars().all()
            
            # Delete comments on articles by this user
            for article_id in articles_by_user:
                db.execute(delete(Comment).where(Comment.article_id == article_id))
            
            # Delete articles by this user
            db.execute(delete(Article).where(Article.author_id == user_id))
        
        db.commit()
        
        # Delete all users except current user
        db.execute(delete(User).where(User.id != user.id))
        db.commit()
        
        return RedirectResponse(
            url="/admin/users?message=All users (except your account) have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting users: {str(e)}. <a href='/admin/users'>Go back</a>", status_code=500) 