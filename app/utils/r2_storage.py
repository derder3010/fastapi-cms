#!/usr/bin/env python
import sys
import os
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Tuple, Optional

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.config import settings


def get_r2_client():
    """
    Creates and returns an S3 client configured for Cloudflare R2.
    
    Returns:
        boto3.client: Boto3 S3 client configured for R2
        
    Raises:
        ValueError: If R2 is not properly configured
    """
    # Check if R2 is properly configured
    if not settings.USE_CLOUD_STORAGE:
        raise ValueError("Cloud storage is not enabled in settings")

    if not all([
        settings.R2_ENDPOINT_URL,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET_NAME
    ]):
        raise ValueError("R2 storage is not properly configured")
    
    # Set up S3 client for R2
    return boto3.client(
        service_name='s3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name=settings.R2_REGION_NAME
    )


def list_all_objects() -> List[Dict[str, Any]]:
    """
    Lists all objects in the R2 bucket.
    
    Returns:
        List[Dict[str, Any]]: List of object metadata dictionaries
    """
    s3 = get_r2_client()
    
    objects = []
    paginator = s3.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME):
        if 'Contents' in page:
            for obj in page['Contents']:
                objects.append(obj)
    
    return objects


def delete_all_objects(force: bool = False) -> Tuple[bool, int, Optional[str]]:
    """
    Deletes all objects in the R2 bucket.
    
    Args:
        force: If True, skips confirmation and deletes all objects
    
    Returns:
        Tuple containing:
        - success (bool): Whether the operation was successful
        - count (int): Number of objects deleted
        - error (Optional[str]): Error message if operation failed
    """
    try:
        s3 = get_r2_client()
        
        # List all objects in the bucket
        paginator = s3.get_paginator('list_objects_v2')
        total_objects = 0
        objects_to_delete = []
        
        for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME):
            if 'Contents' not in page:
                return True, 0, None  # No objects to delete
                
            for obj in page.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})
                total_objects += 1
                
                # Delete in batches of 1000 objects (S3 API limit)
                if len(objects_to_delete) >= 1000:
                    s3.delete_objects(
                        Bucket=settings.R2_BUCKET_NAME,
                        Delete={'Objects': objects_to_delete}
                    )
                    objects_to_delete = []
        
        # Delete any remaining objects
        if objects_to_delete:
            s3.delete_objects(
                Bucket=settings.R2_BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
        
        return True, total_objects, None
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return False, 0, f"{error_code} - {error_message}"
        
    except Exception as e:
        return False, 0, str(e)


def delete_objects_by_prefix(prefix: str, force: bool = False) -> Tuple[bool, int, Optional[str]]:
    """
    Deletes all objects in the R2 bucket with the specified prefix.
    
    Args:
        prefix: Prefix to filter objects by
        force: If True, skips confirmation and deletes objects
    
    Returns:
        Tuple containing:
        - success (bool): Whether the operation was successful
        - count (int): Number of objects deleted
        - error (Optional[str]): Error message if operation failed
    """
    try:
        s3 = get_r2_client()
        
        # List objects with the given prefix
        paginator = s3.get_paginator('list_objects_v2')
        total_objects = 0
        objects_to_delete = []
        
        for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME, Prefix=prefix):
            if 'Contents' not in page:
                return True, 0, None  # No objects to delete
                
            for obj in page.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})
                total_objects += 1
                
                # Delete in batches of 1000 objects (S3 API limit)
                if len(objects_to_delete) >= 1000:
                    s3.delete_objects(
                        Bucket=settings.R2_BUCKET_NAME,
                        Delete={'Objects': objects_to_delete}
                    )
                    objects_to_delete = []
        
        # Delete any remaining objects
        if objects_to_delete:
            s3.delete_objects(
                Bucket=settings.R2_BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
        
        return True, total_objects, None
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return False, 0, f"{error_code} - {error_message}"
        
    except Exception as e:
        return False, 0, str(e)


def delete_specific_objects(keys: List[str]) -> Tuple[bool, int, Optional[str]]:
    """
    Deletes specific objects from the R2 bucket.
    
    Args:
        keys: List of object keys to delete
    
    Returns:
        Tuple containing:
        - success (bool): Whether the operation was successful
        - count (int): Number of objects deleted
        - error (Optional[str]): Error message if operation failed
    """
    if not keys:
        return True, 0, None
        
    try:
        s3 = get_r2_client()
        
        # Process keys in batches of 1000 (S3 API limit)
        for i in range(0, len(keys), 1000):
            batch = keys[i:i+1000]
            objects_to_delete = [{'Key': key} for key in batch]
            
            s3.delete_objects(
                Bucket=settings.R2_BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
        
        return True, len(keys), None
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        return False, 0, f"{error_code} - {error_message}"
        
    except Exception as e:
        return False, 0, str(e)


if __name__ == "__main__":
    # If run directly, print help
    print("This module provides utilities for managing Cloudflare R2 storage.")
    print("It is intended to be imported from other scripts, not run directly.")
    print("\nAvailable functions:")
    print("- get_r2_client()")
    print("- list_all_objects()")
    print("- delete_all_objects(force=False)")
    print("- delete_objects_by_prefix(prefix, force=False)")
    print("- delete_specific_objects(keys)")
    
    # Show example usage
    print("\nExample usage:")
    print("from scripts.utils.r2_storage import delete_all_objects")
    print("success, count, error = delete_all_objects(force=True)")
    print("if success:")
    print("    print(f'Successfully deleted {count} objects')")
    print("else:")
    print("    print(f'Error: {error}')") 