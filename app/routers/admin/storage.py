from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import Session
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.models import User
from app.auth.deps import get_current_active_superuser
from app.config import settings
from app.utils.r2_storage import (
    list_all_objects, 
    delete_all_objects, 
    delete_objects_by_prefix,
    delete_specific_objects
)
from app.utils.logging import log_admin_action

router = APIRouter(prefix="/storage", tags=["admin", "storage"])


@router.get("/r2/stats", response_model=Dict[str, Any])
async def get_r2_storage_stats(
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    """
    Get statistics about the R2 storage.
    Requires superuser access.
    """
    if not settings.USE_CLOUD_STORAGE:
        raise HTTPException(status_code=400, detail="Cloud storage is not enabled")
    
    try:
        log_admin_action(
            db=db,
            user_id=current_user.id,
            action="view_r2_stats",
            resource_type="storage",
            resource_id=None,
            description="Viewed R2 storage statistics"
        )
        
        # Get all objects
        objects = list_all_objects()
        
        # Calculate statistics
        total_objects = len(objects)
        total_size = sum(obj.get('Size', 0) for obj in objects)
        
        # Categorize by file type
        file_types = {}
        for obj in objects:
            key = obj.get('Key', '')
            extension = key.split('.')[-1].lower() if '.' in key else 'unknown'
            
            if extension not in file_types:
                file_types[extension] = {
                    'count': 0,
                    'size': 0
                }
            
            file_types[extension]['count'] += 1
            file_types[extension]['size'] += obj.get('Size', 0)
        
        # Get most recent files
        most_recent = sorted(
            objects, 
            key=lambda x: x.get('LastModified', 0), 
            reverse=True
        )[:10]
        
        return {
            "total_objects": total_objects,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "most_recent_files": [
                {
                    "key": obj.get('Key'),
                    "size": obj.get('Size'),
                    "last_modified": obj.get('LastModified')
                }
                for obj in most_recent
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving R2 stats: {str(e)}")


@router.post("/r2/purge", response_model=Dict[str, Any])
async def purge_r2_storage(
    background_tasks: BackgroundTasks,
    prefix: Optional[str] = None,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete all files in the R2 storage.
    Optionally limit to a specific prefix.
    Requires superuser access.
    """
    if not settings.USE_CLOUD_STORAGE:
        raise HTTPException(status_code=400, detail="Cloud storage is not enabled")
    
    try:
        # Log the action
        log_description = "Purged all R2 storage files"
        if prefix:
            log_description = f"Purged R2 storage files with prefix '{prefix}'"
            
        log_admin_action(
            db=db,
            user_id=current_user.id,
            action="purge_r2_storage",
            resource_type="storage",
            resource_id=None,
            description=log_description
        )
        
        # Start the deletion in a background task
        def delete_files():
            if prefix:
                return delete_objects_by_prefix(prefix, force=True)
            else:
                return delete_all_objects(force=True)
        
        background_tasks.add_task(delete_files)
        
        # Return immediate success response
        return {
            "status": "started",
            "message": f"R2 storage purge {'for prefix ' + prefix if prefix else ''} has been started",
            "background": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting R2 purge: {str(e)}")


@router.delete("/r2/objects", response_model=Dict[str, Any])
async def delete_r2_objects(
    keys: List[str],
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete specific files from R2 storage by their keys.
    Requires superuser access.
    """
    if not settings.USE_CLOUD_STORAGE:
        raise HTTPException(status_code=400, detail="Cloud storage is not enabled")
    
    if not keys:
        raise HTTPException(status_code=400, detail="No file keys provided")
    
    try:
        # Log the action
        log_admin_action(
            db=db,
            user_id=current_user.id,
            action="delete_r2_objects",
            resource_type="storage",
            resource_id=None,
            description=f"Deleted {len(keys)} objects from R2 storage"
        )
        
        # Delete the objects
        success, count, error = delete_specific_objects(keys)
        
        if success:
            return {
                "status": "success",
                "deleted_count": count,
                "message": f"Successfully deleted {count} objects"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Error deleting objects: {error}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting R2 objects: {str(e)}") 