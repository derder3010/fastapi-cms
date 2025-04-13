from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Category, CategoryCreate, CategoryRead, CategoryUpdate
from app.auth.deps import get_current_active_user, get_current_active_superuser

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate, 
    current_user = Depends(get_current_active_superuser),
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

@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category_data = category_update.dict(exclude_unset=True)
    for key, value in category_data.items():
        setattr(category, key, value)
    
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if the category has any articles
    if category.articles:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete category with associated articles. Remove or reassign articles first."
        )
    
    db.delete(category)
    db.commit()
    return None 