from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import Session
from datetime import timedelta

from app.config import settings
from app.database import get_db
from app.auth.utils import authenticate_user, create_access_token, get_user_from_cookie

router = APIRouter(tags=["auth"])

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, db: Session = Depends(get_db)):
    # Check if user is already logged in
    user = await get_user_from_cookie(request, db)
    if user and user.is_superuser:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": request.query_params.get("error")}
    )

@router.post("/login")
async def admin_login(
    request: Request, 
    response: Response, 
    username: str = Form(...), 
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Authenticate user
    user = await authenticate_user(db, username, password)
    
    if not user:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401
        )
    
    if not user.is_superuser:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "You do not have admin privileges"},
            status_code=403
        )
    
    # Create access token and set cookie
    access_token = create_access_token(
        data={"sub": user.username}
    )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    # Set cookie with an explicit max_age
    max_age = 60 * settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES  # Convert minutes to seconds
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=max_age,
        samesite="lax"
    )
    return response

@router.get("/logout")
async def admin_logout(response: Response):
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

@router.post("/token", response_model=dict)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"} 