import os
import uuid
from datetime import datetime
from fastapi import UploadFile
from pathlib import Path

async def save_upload(upload_file: UploadFile, folder: str = "uploads") -> str:
    """
    Save an uploaded file to the media directory.
    
    Args:
        upload_file (UploadFile): The uploaded file from FastAPI
        folder (str): The subfolder within media directory to save to
    
    Returns:
        str: The path to the saved file relative to the media directory
    """
    if not upload_file:
        return None
    
    # Create directory if it doesn't exist
    media_dir = Path("media")
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)
    
    target_dir = media_dir / folder
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Generate a unique filename to prevent collisions
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Get file extension from the original filename
    _, file_extension = os.path.splitext(upload_file.filename)
    
    # Sanitize filename - remove special characters and convert spaces to underscores
    sanitized_filename = ''.join(c for c in upload_file.filename if c.isalnum() or c in ['.', '_', '-']).replace(' ', '_')
    base_filename = os.path.splitext(sanitized_filename)[0]
    
    # Generate the new filename
    new_filename = f"{base_filename}_{current_time}_{unique_id}{file_extension}"
    file_path = target_dir / new_filename
    
    # Save the file
    with open(file_path, "wb") as f:
        # Read the file in chunks to handle large files
        content = await upload_file.read()
        f.write(content)
    
    # Return the path relative to the media directory
    return f"{folder}/{new_filename}" 