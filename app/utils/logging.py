from fastapi import Request
from sqlmodel import Session
from app.models import SystemLog, SystemLogCreate
from app.auth.utils import get_client_ip

def log_admin_action(
    db: Session, 
    user_id: int, 
    action: str, 
    details: str, 
    request: Request = None
):
    """
    Utility function to log admin actions
    
    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Short description of the action
        details: Detailed description of what was done
        request: Request object for getting IP address (optional)
    """
    ip_address = None
    if request:
        ip_address = get_client_ip(request)
    
    log_entry = SystemLogCreate(
        action=action,
        details=details,
        user_id=user_id,
        ip_address=ip_address
    )
    
    db.add(SystemLog(**log_entry.dict()))
    # Note: This doesn't commit the transaction
    # You should call db.commit() after this function 