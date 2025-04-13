from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Category, CategoryCreate, CategoryRead
from app.auth.deps import get_current_active_user

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    category_obj = Category.from_orm(category)
    db.add(category_obj)
    db.commit()
    db.refresh(category_obj)
    return category_obj

@router.get("/", response_model=List[CategoryRead])
async def get_categories(db: Session = Depends(get_db)):
    categories = db.execute(select(Category)).scalars().all()
    return categories

@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category 