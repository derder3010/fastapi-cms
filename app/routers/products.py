from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, or_, delete
import os
from datetime import datetime
import shutil
import json
from typing import Optional

from app.database import get_db
from app.models import Product, Article, ProductArticleLink
from app.auth.utils import get_user_from_cookie
from app.utils.text import generate_unique_slug
from app.config import settings

router = APIRouter(prefix="/products")

# Set up templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_products(
    request: Request, 
    q: str = None, 
    page: int = 1, 
    page_size: int = 10,
    price_min: Optional[str] = None,
    price_max: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,  
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Create base query
        query = select(Product)
        
        # Track applied filters
        applied_filters = 0
        
        # Apply search filter if query parameter is provided
        if q:
            search_term = f"%{q}%"
            query = query.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )
        
        # Apply price filters
        if price_min and price_min.isdigit():
            query = query.where(Product.price >= int(price_min))
            applied_filters += 1
            
        if price_max and price_max.isdigit():
            query = query.where(Product.price <= int(price_max))
            applied_filters += 1
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.where(Product.created_at >= from_date)
                applied_filters += 1
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                # Set time to end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.where(Product.created_at <= to_date)
                applied_filters += 1
            except ValueError:
                pass
        
        # Count total records for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_records = db.execute(count_query).scalar_one()
        
        # Calculate pagination values
        total_pages = (total_records + page_size - 1) // page_size
        page = max(1, min(page, total_pages) if total_pages > 0 else 1)
        offset = (page - 1) * page_size
        
        # Add pagination
        paginated_query = query.order_by(Product.name).offset(offset).limit(page_size)
        
        # Get products
        products = db.execute(paginated_query).scalars().all()
        
        # Render the admin products template
        return templates.TemplateResponse(
            "admin/products/list.html",
            {
                "request": request,
                "user": user,
                "products": products,
                "query": q,
                "message": request.query_params.get("message"),
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_records": total_records,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                },
                # Filter variables
                "filter_price_min": price_min,
                "filter_price_max": price_max,
                "filter_date_from": date_from,
                "filter_date_to": date_to,
                "applied_filters": applied_filters
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/products/list.html",
            {
                "request": request,
                "user": user,
                "products": [],
                "error": f"Error: {str(e)}"
            }
        )

@router.get("/add", response_class=HTMLResponse)
async def admin_add_product_form(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get articles for selection
    articles = db.execute(select(Article)).scalars().all()
    
    # Render the add product form
    return templates.TemplateResponse(
        "admin/products/add.html",
        {"request": request, "user": user, "articles": articles}
    )

@router.post("/add")
async def admin_add_product(
    request: Request,
    name: str = Form(...),
    price: int = Form(0),
    slug: str = Form(None),
    description: str = Form(None),
    social_links: str = Form(None),
    featured_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Validate social_links as valid JSON if provided
        if social_links:
            try:
                json.loads(social_links)
            except json.JSONDecodeError:
                return templates.TemplateResponse(
                    "admin/products/add.html", 
                    {
                        "request": request,
                        "user": user,
                        "error": "Social links must be valid JSON."
                    },
                    status_code=400
                )
        
        # Generate slug if not provided
        if not slug:
            existing_slugs = db.execute(select(Product.slug)).scalars().all()
            slug = generate_unique_slug(name, existing_slugs)
        
        # Check if product slug already exists
        existing_product = db.execute(select(Product).where(Product.slug == slug)).scalar_one_or_none()
        if existing_product:
            return templates.TemplateResponse(
                "admin/products/add.html", 
                {
                    "request": request,
                    "user": user,
                    "error": f"Product with slug '{slug}' already exists."
                },
                status_code=400
            )
        
        # Handle featured image upload
        featured_image_path = None
        if featured_image and featured_image.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join("media", "products")
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_extension = os.path.splitext(featured_image.filename)[1]
            new_filename = f"product_{slug}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_dir, new_filename)
            
            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(featured_image.file, buffer)
            
            # Save the relative path
            featured_image_path = os.path.join("products", new_filename)
        
        # Create new product
        product = Product(
            name=name,
            price=price,
            slug=slug,
            description=description,
            featured_image=featured_image_path,
            social_links=social_links
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        return RedirectResponse(
            url=f"/admin/products?message=Product '{name}' created successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/products/add.html",
            {
                "request": request,
                "user": user,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{product_id}/edit", response_class=HTMLResponse)
async def admin_edit_product_form(request: Request, product_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get the product to edit
        product = db.get(Product, product_id)
        if not product:
            return RedirectResponse(
                url="/admin/products?message=Product not found",
                status_code=303
            )
        
        # Get all articles
        articles = db.execute(select(Article)).scalars().all()
        
        # Get the articles associated with this product
        associated_article_ids = [article.id for article in product.articles]
        
        # Render the edit product form
        return templates.TemplateResponse(
            "admin/products/edit.html",
            {
                "request": request, 
                "user": user, 
                "product": product,
                "articles": articles,
                "associated_article_ids": associated_article_ids
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/products/list.html",
            {
                "request": request,
                "user": user,
                "products": db.execute(select(Product)).scalars().all(),
                "error": f"Error loading product: {str(e)}"
            }
        )

@router.post("/{product_id}/edit")
async def admin_edit_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    price: int = Form(0),
    slug: str = Form(None),
    description: str = Form(None),
    social_links: str = Form(None),
    featured_image: UploadFile = File(None),
    article_ids: list[int] = Form([]),
    db: Session = Depends(get_db)
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get product
        product = db.get(Product, product_id)
        if not product:
            return RedirectResponse(
                url="/admin/products?message=Product not found",
                status_code=303
            )
        
        # Validate social_links as valid JSON if provided
        if social_links:
            try:
                json.loads(social_links)
            except json.JSONDecodeError:
                return templates.TemplateResponse(
                    "admin/products/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "product": product,
                        "error": "Social links must be valid JSON."
                    },
                    status_code=400
                )
        
        # Generate slug if not provided
        if not slug:
            existing_slugs = db.execute(select(Product.slug).where(Product.id != product_id)).scalars().all()
            slug = generate_unique_slug(name, existing_slugs)
        
        # Check if product slug already exists (excluding current product)
        if product.slug != slug:
            existing_product = db.execute(select(Product).where(Product.slug == slug)).scalar_one_or_none()
            if existing_product:
                return templates.TemplateResponse(
                    "admin/products/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "product": product,
                        "error": f"Product with slug '{slug}' already exists."
                    },
                    status_code=400
                )
        
        # Handle featured image upload
        featured_image_path = product.featured_image
        if featured_image and featured_image.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join("media", "products")
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_extension = os.path.splitext(featured_image.filename)[1]
            new_filename = f"product_{slug}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_dir, new_filename)
            
            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(featured_image.file, buffer)
            
            # Remove old image if it exists
            if product.featured_image:
                old_file_path = os.path.join("media", product.featured_image)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            # Update featured image path
            featured_image_path = os.path.join("products", new_filename)
        
        # Update product fields
        product.name = name
        product.price = price
        product.slug = slug
        product.description = description
        product.featured_image = featured_image_path
        product.social_links = social_links
        
        # Update product
        db.add(product)
        db.commit()
        
        # Update article associations
        current_article_ids = [article.id for article in product.articles]
        
        # Remove associations that are not in the new list
        for article_id in current_article_ids:
            if article_id not in article_ids:
                link = db.execute(
                    select(ProductArticleLink).where(
                        (ProductArticleLink.product_id == product_id) & 
                        (ProductArticleLink.article_id == article_id)
                    )
                ).scalar_one_or_none()
                if link:
                    db.delete(link)
        
        # Add new associations
        for article_id in article_ids:
            if article_id not in current_article_ids:
                # Check if article exists
                article = db.get(Article, article_id)
                if article:
                    link = ProductArticleLink(product_id=product_id, article_id=article_id)
                    db.add(link)
        
        db.commit()
        db.refresh(product)
        
        return RedirectResponse(
            url=f"/admin/products?message=Product '{name}' updated successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/products/edit.html",
            {
                "request": request,
                "user": user,
                "product": product,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@router.get("/{product_id}/delete")
async def admin_delete_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get product
        product = db.get(Product, product_id)
        if not product:
            return HTMLResponse("Product not found", status_code=404)
        
        # Delete product-article links first
        db.execute(delete(ProductArticleLink).where(ProductArticleLink.product_id == product_id))
        db.commit()
        
        # Get product name before deletion for success message
        product_name = product.name
        
        # Delete product
        db.delete(product)
        db.commit()
        
        return RedirectResponse(url=f"/admin/products?message=Product '{product_name}' deleted successfully", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/products'>Try again</a>")

@router.get("/delete-all", response_class=HTMLResponse)
async def admin_delete_all_products_confirm(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Count products
    product_count = db.execute(select(Product)).all()
    count = len(product_count)
    
    # Render confirmation page
    return templates.TemplateResponse(
        "admin/confirm_delete_all.html",
        {
            "request": request,
            "user": user,
            "count": count,
            "item_type": "products",
            "back_url": "/admin/products",
            "confirm_url": "/admin/products/delete-all-confirm"
        }
    )

@router.get("/delete-all-confirm")
async def admin_delete_all_products(request: Request, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Delete all product-article links first
        db.execute(delete(ProductArticleLink))
        db.commit()
        
        # Delete all products
        db.execute(delete(Product))
        db.commit()
        
        return RedirectResponse(
            url="/admin/products?message=All products have been deleted successfully",
            status_code=303
        )
    except Exception as e:
        return HTMLResponse(f"Error deleting all products: {str(e)}. <a href='/admin/products'>Go back</a>", status_code=500)

@router.get("/{product_id}/articles", response_class=HTMLResponse)
async def admin_product_articles(request: Request, product_id: int, db: Session = Depends(get_db)):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get product
        product = db.get(Product, product_id)
        if not product:
            return RedirectResponse(
                url="/admin/products?message=Product not found",
                status_code=303
            )
        
        # Get all articles
        all_articles = db.execute(select(Article)).scalars().all()
        
        # Get associated articles
        associated_articles = product.articles
        
        return templates.TemplateResponse(
            "admin/products/articles.html",
            {
                "request": request,
                "user": user,
                "product": product,
                "associated_articles": associated_articles,
                "all_articles": all_articles
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/products/list.html",
            {
                "request": request,
                "user": user,
                "products": db.execute(select(Product)).scalars().all(),
                "error": f"Error: {str(e)}"
            }
        ) 