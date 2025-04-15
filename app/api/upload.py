from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
import os
from datetime import datetime
import shutil
import uuid

from app.database import get_db
from app.auth.deps import get_current_active_user
from app.auth.utils import get_user_from_cookie
from app.models import User
from app.config import settings
from app.utils.storage import StorageManager

# Set up OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")
router = APIRouter(prefix="/upload")

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload an image with token authentication and return its URL."""
    # Check if user is authenticated (will raise exception if not)
    if not current_user or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
    
    # Process the upload
    return await process_image_upload(file)

@router.post("/image/web")
async def upload_image_web(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an image using cookie authentication and return its URL."""
    # Check if user is authenticated via cookie
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
    
    # Process the upload
    return await process_image_upload(file)

async def process_image_upload(file: UploadFile):
    """Process image upload and return the file URL."""
    # Validate file type
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Supported types: {', '.join(valid_extensions)}"
        )
    
    try:
        success, path, error = await StorageManager.save_file(
            file=file, 
            folder="uploads/images",
            public=True
        )
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail=f"Upload failed: {error}"
            )
        
        # If path is already a full URL (cloud storage case)
        if path.startswith(("http://", "https://")):
            file_url = path
        else:
            # Otherwise, it's a local file path
            file_url = f"/media/{path}"
        
        return {"url": file_url, "success": True}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") 