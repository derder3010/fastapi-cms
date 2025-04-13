from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_db
from app.models import User
from app.auth.utils import get_user_from_cookie, get_password_hash

router = APIRouter(prefix="/users")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get all users
    users = db.execute(select(User)).scalars().all()
    
    # Render the admin users template
    return templates.TemplateResponse(
        "admin/users/list.html",
        {"request": request, "user": user, "users": users}
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
    
    # Update user
    user_to_edit.username = username
    user_to_edit.email = email
    if password:
        user_to_edit.password = get_password_hash(password)
    user_to_edit.is_active = is_active
    user_to_edit.is_superuser = is_superuser
    
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
    
    # Delete user
    db.delete(user_to_delete)
    db.commit()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User deleted successfully",
        status_code=303
    ) 