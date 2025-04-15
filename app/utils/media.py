import os
import uuid
from datetime import datetime
from fastapi import UploadFile
from pathlib import Path

from app.utils.storage import StorageManager

async def save_upload(upload_file: UploadFile, folder: str = "uploads") -> str:
    """
    Save an uploaded file to either local media directory or cloud storage.
    
    Args:
        upload_file (UploadFile): The uploaded file from FastAPI
        folder (str): The subfolder within media directory to save to
    
    Returns:
        str: The path to the saved file relative to the media directory
              or a full URL if using cloud storage
    """
    if not upload_file:
        return None
    
    success, path, error = await StorageManager.save_file(upload_file, folder)
    
    if not success:
        print(f"Error saving file: {error}")
        return None
    
    return path 