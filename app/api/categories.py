from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
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
    try:
        category = db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Get category name for logging
        category_name = category.name
        
        # Get all articles in this category
        from app.models import Article, Comment

        # Find all articles in this category
        article_query = select(Article.id).where(Article.category_id == category_id)
        article_ids = [row[0] for row in db.execute(article_query).all()]
        
        # If there are articles, delete related data
        if article_ids:
            # Import these models here to avoid circular imports
            from app.models import ArticleTagLink, ProductArticleLink
            
            # Delete article-tag links for these articles
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links for these articles
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete comments on these articles
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
            
            # Delete all articles in this category
            db.execute(delete(Article).where(Article.category_id == category_id))
        
        # Delete category
        db.delete(category)
        db.commit()
        
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting category: {str(e)}")

@router.delete("/", status_code=204)
async def delete_all_categories(
    current_user = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    try:
        # Find all articles to be deleted
        from app.models import Article, Comment
        article_ids = [row[0] for row in db.execute(select(Article.id)).all()]
        
        # If articles exist, delete all related data first
        if article_ids:
            # Import these models here to avoid circular imports
            from app.models import ArticleTagLink, ProductArticleLink
            
            # Delete article-tag links
            db.execute(delete(ArticleTagLink).where(ArticleTagLink.article_id.in_(article_ids)))
            
            # Delete article-product links
            db.execute(delete(ProductArticleLink).where(ProductArticleLink.article_id.in_(article_ids)))
            
            # Delete all comments on these articles
            db.execute(delete(Comment).where(Comment.article_id.in_(article_ids)))
        
        # Delete all articles
        db.execute(delete(Article))
        
        # Delete all categories
        db.execute(delete(Category))
        
        db.commit()
        return None
    except Exception as e:
        # Roll back transaction on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all categories: {str(e)}") 