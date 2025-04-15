from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from typing import Optional
import json
import os
import shutil
from datetime import datetime, timedelta
from sqlalchemy import text

from app.database import get_db, engine
from app.models import (
    User, Category, Article, Comment, Tag, Product,
    SystemLog, SystemLogCreate, SystemSettings
)
from app.auth.utils import get_user_from_cookie, get_client_ip
from app.config import settings as app_settings

router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get system logs
    logs = db.execute(
        select(SystemLog)
        .order_by(desc(SystemLog.created_at))
        .limit(100)
    ).scalars().all()
    
    # Get system settings
    token_expiry = db.execute(
        select(SystemSettings)
        .where(SystemSettings.key == "token_expiry_minutes")
    ).scalar_one_or_none()
    
    # If token_expiry setting doesn't exist, create it with default value
    if not token_expiry:
        token_expiry = SystemSettings(
            key="token_expiry_minutes",
            value=str(app_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            description="Token expiry time in minutes"
        )
        db.add(token_expiry)
        db.commit()
        db.refresh(token_expiry)
    
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": user,
            "logs": logs,
            "token_expiry": token_expiry,
            "success_message": request.query_params.get("success"),
            "error_message": request.query_params.get("error")
        }
    )

@router.post("/settings/update_token_expiry", response_class=HTMLResponse)
async def update_token_expiry(
    request: Request,
    token_expiry_minutes: int = Form(...),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Update token expiry setting
    token_expiry = db.execute(
        select(SystemSettings)
        .where(SystemSettings.key == "token_expiry_minutes")
    ).scalar_one_or_none()
    
    if token_expiry:
        token_expiry.value = str(token_expiry_minutes)
        db.add(token_expiry)
    else:
        token_expiry = SystemSettings(
            key="token_expiry_minutes",
            value=str(token_expiry_minutes),
            description="Token expiry time in minutes"
        )
        db.add(token_expiry)
    
    # Log the action
    log_entry = SystemLogCreate(
        action="Update Token Expiry",
        details=f"Token expiry updated to {token_expiry_minutes} minutes",
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    db.add(SystemLog(**log_entry.dict()))
    
    db.commit()
    
    return RedirectResponse(
        url="/admin/settings?success=Token expiry updated successfully",
        status_code=303
    )

@router.get("/settings/confirm_clear_logs", response_class=HTMLResponse)
async def confirm_clear_logs(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count logs
    logs_count = db.execute(select(func.count()).select_from(SystemLog)).scalar() or 0
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": logs_count,
            "item_type": "logs",
            "back_url": "/admin/settings",
            "confirm_url": "/admin/settings/clear_logs"
        }
    )

@router.get("/settings/clear_logs", response_class=HTMLResponse)
async def clear_logs(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Clear all logs
    db.execute(text("DELETE FROM systemlog"))
    
    # Add a log entry for this action
    log_entry = SystemLogCreate(
        action="Clear Logs",
        details="System logs cleared",
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    db.add(SystemLog(**log_entry.dict()))
    db.commit()
    
    return RedirectResponse(
        url="/admin/settings?success=Logs cleared successfully",
        status_code=303
    )

@router.get("/settings/confirm_reset_database", response_class=HTMLResponse)
async def confirm_reset_database(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    return templates.TemplateResponse(
        "admin/confirm_reset_database.html",
        {
            "request": request,
            "user": user
        }
    )

@router.post("/settings/reset_database", response_class=HTMLResponse)
async def reset_database(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Drop all tables and recreate them
        from sqlmodel import SQLModel
        
        # Close current database session
        db.close()
        
        # Log action before dropping tables
        log_entry = SystemLogCreate(
            action="Reset Database",
            details="Full database reset",
            user_id=user.id,
            ip_address=get_client_ip(request)
        )
        db.add(SystemLog(**log_entry.dict()))
        db.commit()
        
        # Reset database by recreating all tables
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        
        # Also clear media directory if it exists
        media_dir = os.path.join(os.getcwd(), "media")
        if os.path.exists(media_dir):
            for item in os.listdir(media_dir):
                item_path = os.path.join(media_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        # Create a new admin user
        new_db = next(get_db())
        from app.auth.utils import get_password_hash
        admin = User(
            username="admin",
            email="admin@example.com",
            password=get_password_hash("admin"),
            is_superuser=True
        )
        new_db.add(admin)
        new_db.commit()
        
        return RedirectResponse(
            url="/admin/login?message=Database reset successfully. Login with username: admin, password: admin",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/settings/?error=Error resetting database: {str(e)}",
            status_code=303
        )

@router.post("/settings/log_action", response_class=HTMLResponse)
async def log_action(
    request: Request,
    action: str = Form(...),
    details: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Create log entry
    log_entry = SystemLogCreate(
        action=action,
        details=details,
        user_id=user.id,
        ip_address=get_client_ip(request)
    )
    db.add(SystemLog(**log_entry.dict()))
    db.commit()
    
    return {"success": True, "message": "Action logged successfully"} 