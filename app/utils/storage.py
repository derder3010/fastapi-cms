import os
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from typing import Optional, Tuple

from app.config import settings


class StorageManager:
    """
    Storage manager for handling file uploads to either local filesystem
    or Cloudflare R2 cloud storage based on configuration.
    """
    
    @staticmethod
    async def save_file(
        file: UploadFile, 
        folder: str = "uploads",
        public: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Save a file to either local filesystem or R2 based on configuration.
        
        Args:
            file: The FastAPI UploadFile object
            folder: The subfolder to save the file in
            public: Whether the file should be publicly accessible
            
        Returns:
            Tuple containing:
            - success (bool): Whether the operation was successful
            - path (str): The path or URL to the saved file
            - error_message (Optional[str]): Error message if operation failed
        """
        if not file:
            return False, "", "No file provided"
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            file_ext = os.path.splitext(file.filename)[1].lower()
            sanitized_name = ''.join(c for c in os.path.splitext(file.filename)[0] 
                                     if c.isalnum() or c in ['.', '_', '-']).replace(' ', '_')
            
            new_filename = f"{sanitized_name}_{timestamp}_{unique_id}{file_ext}"
            relative_path = f"{folder}/{new_filename}"
            
            # Read file content
            file_content = await file.read()
            
            # Determine if we should use cloud storage
            if settings.USE_CLOUD_STORAGE:
                return StorageManager._save_to_r2(
                    file_content=file_content,
                    relative_path=relative_path,
                    content_type=file.content_type,
                    public=public
                )
            else:
                return StorageManager._save_to_local(
                    file_content=file_content,
                    relative_path=relative_path
                )
                
        except Exception as e:
            return False, "", f"Error saving file: {str(e)}"
    
    @staticmethod
    def _save_to_local(file_content: bytes, relative_path: str) -> Tuple[bool, str, Optional[str]]:
        """Save file to local filesystem"""
        try:
            media_dir = settings.MEDIA_ROOT
            target_path = os.path.join(media_dir, relative_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Write file
            with open(target_path, "wb") as f:
                f.write(file_content)
                
            return True, relative_path, None
            
        except Exception as e:
            return False, "", f"Error saving to local storage: {str(e)}"
    
    @staticmethod
    def _save_to_r2(
        file_content: bytes, 
        relative_path: str, 
        content_type: str = "application/octet-stream",
        public: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """Save file to Cloudflare R2"""
        try:
            # Set up S3 client for R2
            s3 = boto3.client(
                service_name='s3',
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name=settings.R2_REGION_NAME
            )
            
            # Build extra args based on whether file should be public
            extra_args = {
                'ContentType': content_type,
            }
            
            if public:
                extra_args['ACL'] = 'public-read'
            
            # Upload file to R2
            s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=relative_path,
                Body=file_content,
                **extra_args
            )
            
            # Return the public URL if we have one configured, otherwise return the relative path
            if settings.R2_PUBLIC_URL:
                url = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{relative_path}"
                return True, url, None
            else:
                url = f"{settings.R2_ENDPOINT_URL.rstrip('/')}/{settings.R2_BUCKET_NAME}/{relative_path}"
                return True, url, None
                
        except ClientError as e:
            return False, "", f"Error saving to R2: {str(e)}"
        except Exception as e:
            return False, "", f"Unexpected error saving to R2: {str(e)}"
    
    @staticmethod
    def get_file_url(path: str) -> str:
        """
        Get the URL for a file path, handling both local and R2 storage.
        
        Args:
            path: The relative path to the file
            
        Returns:
            str: The full URL to access the file
        """
        if not path:
            return ""
            
        # If it's already a full URL (starts with http/https), return as is
        if path.startswith(("http://", "https://")):
            return path
            
        # If using cloud storage and we have a public URL configured
        if settings.USE_CLOUD_STORAGE:
            if settings.R2_PUBLIC_URL:
                return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{path}"
            else:
                return f"{settings.R2_ENDPOINT_URL.rstrip('/')}/{settings.R2_BUCKET_NAME}/{path}"
            
        # Otherwise, it's a local file
        return f"/media/{path}" 