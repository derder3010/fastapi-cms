from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import json

from app.database import get_db
from app.models import Product, ProductCreate, ProductRead, ProductUpdate, ProductReadWithParsedLinks
from app.auth.deps import get_current_active_user
from app.utils.text import generate_unique_slug

router = APIRouter(prefix="/products", tags=["products"])

def _parse_product_for_response(product: Product) -> ProductReadWithParsedLinks:
    """Convert a Product instance to ProductReadWithParsedLinks with parsed social_links."""
    product_dict = product.dict()
    social_links_str = product_dict.pop("social_links", None)
    
    # Create a new dictionary with the parsed social_links
    product_data = ProductReadWithParsedLinks(
        **product_dict,
        social_links=json.loads(social_links_str) if social_links_str else None
    )
    return product_data

@router.post("/", response_model=ProductReadWithParsedLinks)
async def create_product(
    product: ProductCreate, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow superusers to create products
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to create products")
    
    # Validate social_links as valid JSON if provided
    if product.social_links:
        try:
            json.loads(product.social_links)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="social_links must be a valid JSON string")
    
    product_obj = Product.from_orm(product)
    
    # Generate slug from name if not provided
    if not product_obj.slug:
        # Get existing slugs to ensure uniqueness
        existing_slugs = db.execute(select(Product.slug)).scalars().all()
        product_obj.slug = generate_unique_slug(product_obj.name, existing_slugs)
    
    db.add(product_obj)
    db.commit()
    db.refresh(product_obj)
    
    # Convert to response model with parsed social_links
    return _parse_product_for_response(product_obj)

@router.get("/", response_model=List[ProductReadWithParsedLinks])
async def get_products(db: Session = Depends(get_db)):
    products = db.execute(select(Product)).scalars().all()
    return [_parse_product_for_response(product) for product in products]

@router.get("/{product_id}", response_model=ProductReadWithParsedLinks)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _parse_product_for_response(product)

@router.get("/by-slug/{slug}", response_model=ProductReadWithParsedLinks)
async def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    product = db.execute(select(Product).where(Product.slug == slug)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _parse_product_for_response(product)

@router.put("/{product_id}", response_model=ProductReadWithParsedLinks)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow superusers to update products
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update products")
    
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = product_update.dict(exclude_unset=True)
    
    # Validate social_links as valid JSON if provided
    if "social_links" in product_data and product_data["social_links"]:
        try:
            json.loads(product_data["social_links"])
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="social_links must be a valid JSON string")
    
    # If name is updated but slug is not provided, regenerate slug
    if "name" in product_data and "slug" not in product_data:
        # Get existing slugs excluding current product's slug
        existing_slugs = db.execute(select(Product.slug).where(Product.id != product_id)).scalars().all()
        product_data["slug"] = generate_unique_slug(product_data["name"], existing_slugs)
    
    for key, value in product_data.items():
        setattr(product, key, value)
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Convert to response model with parsed social_links
    return _parse_product_for_response(product)

@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow superusers to delete products
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to delete products")
    
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return None

@router.post("/{product_id}/add-to-article/{article_id}", status_code=200)
async def add_product_to_article(
    product_id: int,
    article_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow superusers to associate products with articles
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to associate products with articles")
    
    from app.models import Article, ProductArticleLink
    
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check if association already exists
    existing_link = db.execute(
        select(ProductArticleLink).where(
            (ProductArticleLink.product_id == product_id) & 
            (ProductArticleLink.article_id == article_id)
        )
    ).scalar_one_or_none()
    
    if existing_link:
        return {"message": "Product already associated with article"}
    
    # Create association
    product_article_link = ProductArticleLink(product_id=product_id, article_id=article_id)
    db.add(product_article_link)
    db.commit()
    
    return {"message": "Product added to article successfully"}

@router.delete("/{product_id}/remove-from-article/{article_id}", status_code=200)
async def remove_product_from_article(
    product_id: int,
    article_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow superusers to disassociate products from articles
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to disassociate products from articles")
    
    from app.models import ProductArticleLink
    
    link = db.execute(
        select(ProductArticleLink).where(
            (ProductArticleLink.product_id == product_id) & 
            (ProductArticleLink.article_id == article_id)
        )
    ).scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Association not found")
    
    db.delete(link)
    db.commit()
    
    return {"message": "Product removed from article successfully"}

@router.get("/{product_id}/articles", response_model=List[int])
async def get_product_articles(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get article IDs associated with the product
    article_ids = [article.id for article in product.articles]
    
    return article_ids 