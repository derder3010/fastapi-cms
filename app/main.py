import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status, Request, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from tortoise.contrib.fastapi import register_tortoise
from datetime import datetime, timedelta
from typing import Optional, List

from app.config import (
    ADMIN,
    CORS_ALLOW_ORIGINS,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    MEDIA_ROOT,
    STATIC_ROOT,
    TORTOISE_ORM,
)
from app.models import (
    Article, 
    Article_Pydantic, 
    ArticleIn_Pydantic,
    Category, 
    Category_Pydantic, 
    CategoryIn_Pydantic,
    Comment, 
    Comment_Pydantic, 
    CommentIn_Pydantic,
    User, 
    User_Pydantic, 
    UserIn_Pydantic
)

# Initialize FastAPI app
app = FastAPI(title="FastAPI CMS", description="A CMS built with FastAPI")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Set up OAuth2 with JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Register Tortoise ORM
register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

# Helper functions for authentication
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str):
    user = await User.filter(username=username).first()
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await User.filter(username=username).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Function to get user from cookie token (for web routes)
async def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = await User.filter(username=username).first()
        return user
    except:
        return None


# Root route for a nice welcome page
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>FastAPI CMS</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                .container {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 20px;
                    margin-top: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                }
                a {
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-right: 10px;
                    margin-top: 10px;
                }
                a:hover {
                    background-color: #45a049;
                }
                .api {
                    background-color: #2196F3;
                }
                .api:hover {
                    background-color: #0b7dda;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to FastAPI CMS</h1>
            <div class="container">
                <h2>A Content Management System built with FastAPI</h2>
                <p>This CMS provides an interface for managing content. You can use it to create, update, and delete articles, categories, and comments.</p>
                <h3>Getting Started:</h3>
                <p>
                    <a href="/admin/login">Admin Interface</a>
                    <a href="/docs" class="api">API Documentation</a>
                </p>
                <h3>Default Admin Credentials:</h3>
                <p>Username: <strong>admin</strong><br>Password: <strong>admin</strong></p>
                <p><small>Note: Please change these credentials in a production environment.</small></p>
            </div>
        </body>
    </html>
    """

# Admin routes
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    # Check if user is already logged in
    user = await get_user_from_cookie(request)
    if user and user.is_superuser:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": request.query_params.get("error")}
    )

@app.post("/admin/login")
async def admin_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    # Authenticate user
    user = await authenticate_user(username, password)
    
    if not user:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401
        )
    
    if not user.is_superuser:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "You do not have admin privileges"},
            status_code=403
        )
    
    # Create access token and set cookie
    access_token = create_access_token(
        data={"sub": user.username}
    )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,  # 30 minutes
        expires=1800,
    )
    
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get counts for dashboard
    users_count = await User.all().count()
    categories_count = await Category.all().count()
    articles_count = await Article.all().count()
    comments_count = await Comment.all().count()
    
    # Get recent articles and comments
    recent_articles = await Article.all().prefetch_related('author', 'category').order_by('-created_at').limit(5)
    recent_comments = await Comment.all().prefetch_related('author', 'article').order_by('-created_at').limit(5)
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "users_count": users_count,
            "categories_count": categories_count,
            "articles_count": articles_count,
            "comments_count": comments_count,
            "recent_articles": recent_articles,
            "recent_comments": recent_comments
        }
    )

@app.get("/admin/logout")
async def admin_logout(response: Response):
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

# Auth endpoints
@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# API endpoints for User
@app.post("/api/users/", response_model=User_Pydantic)
async def create_user(user: UserIn_Pydantic):
    user_obj = User(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
    )
    await user_obj.save()
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app.get("/api/users/me", response_model=User_Pydantic)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return await User_Pydantic.from_tortoise_orm(current_user)


# API endpoints for Category
@app.post("/api/categories/", response_model=Category_Pydantic)
async def create_category(
    category: CategoryIn_Pydantic, current_user: User = Depends(get_current_active_user)
):
    category_obj = await Category.create(**category.dict(exclude_unset=True))
    return await Category_Pydantic.from_tortoise_orm(category_obj)


@app.get("/api/categories/", response_model=List[Category_Pydantic])
async def get_categories():
    return await Category_Pydantic.from_queryset(Category.all())


@app.get("/api/categories/{category_id}", response_model=Category_Pydantic)
async def get_category(category_id: int):
    return await Category_Pydantic.from_queryset_single(Category.get(id=category_id))


# API endpoints for Article
@app.post("/api/articles/", response_model=Article_Pydantic)
async def create_article(
    article: ArticleIn_Pydantic, current_user: User = Depends(get_current_active_user)
):
    article_obj = Article(**article.dict(exclude_unset=True), author_id=current_user.id)
    await article_obj.save()
    return await Article_Pydantic.from_tortoise_orm(article_obj)


@app.get("/api/articles/", response_model=List[Article_Pydantic])
async def get_articles():
    return await Article_Pydantic.from_queryset(Article.all())


@app.get("/api/articles/{article_id}", response_model=Article_Pydantic)
async def get_article(article_id: int):
    return await Article_Pydantic.from_queryset_single(Article.get(id=article_id))


# API endpoints for Comment
@app.post("/api/comments/", response_model=Comment_Pydantic)
async def create_comment(
    comment: CommentIn_Pydantic, current_user: User = Depends(get_current_active_user)
):
    comment_obj = Comment(**comment.dict(exclude_unset=True), author_id=current_user.id)
    await comment_obj.save()
    return await Comment_Pydantic.from_tortoise_orm(comment_obj)


@app.get("/api/comments/", response_model=List[Comment_Pydantic])
async def get_comments():
    return await Comment_Pydantic.from_queryset(Comment.all())


@app.get("/api/comments/{comment_id}", response_model=Comment_Pydantic)
async def get_comment(comment_id: int):
    return await Comment_Pydantic.from_queryset_single(Comment.get(id=comment_id))


# Admin routes for Users
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get all users
    users = await User.all()
    
    # Render the admin users template
    return templates.TemplateResponse(
        "admin/users/list.html",
        {"request": request, "user": user, "users": users}
    )

@app.get("/admin/users/add", response_class=HTMLResponse)
async def admin_add_user_form(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Render the add user form
    return templates.TemplateResponse(
        "admin/users/add.html",
        {"request": request, "user": user}
    )

@app.post("/admin/users/add")
async def admin_add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_active: bool = Form(False),
    is_superuser: bool = Form(False),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Check if username or email already exists
    existing_user = await User.get_or_none(username=username)
    if existing_user:
        return templates.TemplateResponse(
            "admin/users/add.html",
            {
                "request": request,
                "user": user,
                "error": f"User with username {username} already exists."
            },
            status_code=400
        )
    
    existing_email = await User.get_or_none(email=email)
    if existing_email:
        return templates.TemplateResponse(
            "admin/users/add.html",
            {
                "request": request,
                "user": user,
                "error": f"User with email {email} already exists."
            },
            status_code=400
        )
    
    # Create new user
    new_user = await User.create(
        username=username,
        email=email,
        password=get_password_hash(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User created successfully",
        status_code=303
    )

@app.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user_form(request: Request, user_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to edit
    user_to_edit = await User.get_or_none(id=user_id)
    if not user_to_edit:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Render the edit user form
    return templates.TemplateResponse(
        "admin/users/edit.html",
        {"request": request, "user": user, "edit_user": user_to_edit}
    )

@app.post("/admin/users/{user_id}/edit")
async def admin_edit_user(
    request: Request,
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),
    is_active: bool = Form(False),
    is_superuser: bool = Form(False),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to edit
    user_to_edit = await User.get_or_none(id=user_id)
    if not user_to_edit:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Check if username or email already exists (excluding the current user)
    if user_to_edit.username != username:
        existing_user = await User.filter(username=username).first()
        if existing_user:
            return templates.TemplateResponse(
                "admin/users/edit.html",
                {
                    "request": request,
                    "user": user,
                    "edit_user": user_to_edit,
                    "error": f"User with username {username} already exists."
                },
                status_code=400
            )
    
    if user_to_edit.email != email:
        existing_email = await User.filter(email=email).first()
        if existing_email:
            return templates.TemplateResponse(
                "admin/users/edit.html",
                {
                    "request": request,
                    "user": user,
                    "edit_user": user_to_edit,
                    "error": f"User with email {email} already exists."
                },
                status_code=400
            )
    
    # Update user
    user_to_edit.username = username
    user_to_edit.email = email
    if password:
        user_to_edit.password = get_password_hash(password)
    user_to_edit.is_active = is_active
    user_to_edit.is_superuser = is_superuser
    
    await user_to_edit.save()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User updated successfully",
        status_code=303
    )

@app.get("/admin/users/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get the user to delete
    user_to_delete = await User.get_or_none(id=user_id)
    if not user_to_delete:
        return RedirectResponse(url="/admin/users?message=User not found", status_code=303)
    
    # Prevent deleting your own account
    if user_to_delete.id == user.id:
        return RedirectResponse(
            url="/admin/users?message=You cannot delete your own account",
            status_code=303
        )
    
    # Delete user
    await user_to_delete.delete()
    
    # Redirect to users list with success message
    return RedirectResponse(
        url="/admin/users?message=User deleted successfully",
        status_code=303
    )

# Admin routes for Categories
@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get all categories
    categories = await Category.all()
    
    # Render the admin categories template
    return templates.TemplateResponse(
        "admin/categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "message": request.query_params.get("message")
        }
    )

@app.get("/admin/categories/add", response_class=HTMLResponse)
async def admin_add_category_form(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Render the add category form
    return templates.TemplateResponse(
        "admin/categories/add.html",
        {"request": request, "user": user}
    )

@app.post("/admin/categories/add")
async def admin_add_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Check if category name already exists
        existing_category = await Category.filter(name=name).first()
        if existing_category:
            return templates.TemplateResponse(
                "admin/categories/add.html", 
                {
                    "request": request,
                    "user": user,
                    "error": f"Category with name '{name}' already exists."
                },
                status_code=400
            )
        
        # Create new category
        category = Category(
            name=name,
            description=description,
        )
        await category.save()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{name}' created successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/add.html",
            {
                "request": request,
                "user": user,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@app.get("/admin/categories/{category_id}/edit", response_class=HTMLResponse)
async def admin_edit_category_form(request: Request, category_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get the category to edit
        category = await Category.get_or_none(id=category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Render the edit category form
        return templates.TemplateResponse(
            "admin/categories/edit.html",
            {"request": request, "user": user, "category": category}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/list.html",
            {
                "request": request,
                "user": user,
                "categories": await Category.all(),
                "error": f"Error loading category: {str(e)}"
            }
        )

@app.post("/admin/categories/{category_id}/edit")
async def admin_edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    description: str = Form(""),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get category
        category = await Category.get_or_none(id=category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Check if category name already exists (excluding current category)
        if category.name != name:
            existing_category = await Category.filter(name=name).first()
            if existing_category:
                return templates.TemplateResponse(
                    "admin/categories/edit.html",
                    {
                        "request": request,
                        "user": user,
                        "category": category,
                        "error": f"Category with name '{name}' already exists."
                    },
                    status_code=400
                )
        
        # Update category
        category.name = name
        category.description = description
        
        await category.save()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{name}' updated successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/edit.html",
            {
                "request": request,
                "user": user,
                "category": category if 'category' in locals() else None,
                "error": f"Error: {str(e)}."
            },
            status_code=500
        )

@app.get("/admin/categories/{category_id}/delete")
async def admin_delete_category(request: Request, category_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get category
        category = await Category.get_or_none(id=category_id)
        if not category:
            return RedirectResponse(
                url="/admin/categories?message=Category not found",
                status_code=303
            )
        
        # Check if category has articles
        article_count = await Article.filter(category_id=category_id).count()
        if article_count > 0:
            return templates.TemplateResponse(
                "admin/categories/list.html",
                {
                    "request": request,
                    "user": user,
                    "categories": await Category.all(),
                    "error": f"Cannot delete category '{category.name}' because it has {article_count} articles. Remove the articles first."
                }
            )
        
        # Get category name before deletion for success message
        category_name = category.name
        
        # Delete category
        await category.delete()
        
        return RedirectResponse(
            url=f"/admin/categories?message=Category '{category_name}' deleted successfully",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "admin/categories/list.html",
            {
                "request": request,
                "user": user,
                "categories": await Category.all(),
                "error": f"Error: {str(e)}."
            }
        )

# Admin routes for Articles
@app.get("/admin/articles", response_class=HTMLResponse)
async def admin_articles(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all articles with their categories
    articles = await Article.all().prefetch_related("category", "author")
    
    # Sort articles by most recent first
    articles = sorted(articles, key=lambda x: x.created_at, reverse=True)
    
    # Render the admin articles template
    return templates.TemplateResponse(
        "admin/articles/index.html",
        {"request": request, "user": user, "articles": articles, "message": request.query_params.get("message")}
    )

@app.get("/admin/articles/add", response_class=HTMLResponse)
async def admin_add_article_form(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all categories for the dropdown
    categories = await Category.all()
    
    # Render the add article form
    return templates.TemplateResponse(
        "admin/articles/add.html",
        {"request": request, "user": user, "categories": categories}
    )

@app.post("/admin/articles/add")
async def admin_add_article(
    request: Request,
    title: str = Form(...),
    category_id: int = Form(...),
    content: str = Form(...),
    featured_image: str = Form(None),
    published: bool = Form(False),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Validate category exists
    category = await Category.get_or_none(id=category_id)
    if not category:
        categories = await Category.all()
        return templates.TemplateResponse(
            "admin/articles/add.html",
            {
                "request": request, 
                "user": user, 
                "categories": categories,
                "error": "Invalid category selected."
            },
            status_code=400
        )
    
    # Create the article
    article = await Article.create(
        title=title,
        content=content,
        category=category,
        author=user,
        published=published,
        featured_image=featured_image if featured_image and featured_image.strip() else None
    )
    
    # Redirect to articles list with success message
    return RedirectResponse(
        url=f"/admin/articles?message=Article '{title}' created successfully",
        status_code=303
    )

@app.get("/admin/articles/{article_id}/edit", response_class=HTMLResponse)
async def admin_edit_article_form(request: Request, article_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article
        article = await Article.get_or_none(id=article_id).prefetch_related('category')
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Get all categories for the dropdown
        categories = await Category.all()
        
        # Render the edit article template
        return templates.TemplateResponse(
            "admin/articles/edit.html",
            {
                "request": request, 
                "user": user, 
                "article": article,
                "categories": categories
            }
        )
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles'>Go back</a>")

@app.post("/admin/articles/{article_id}/edit")
async def admin_edit_article(
    request: Request,
    article_id: int,
    title: str = Form(...),
    category_id: int = Form(...),
    content: str = Form(...),
    featured_image: str = Form(None),
    published: bool = Form(False),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article
        article = await Article.get_or_none(id=article_id)
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Validate category
        category = await Category.filter(id=category_id).first()
        if not category:
            categories = await Category.all()
            return templates.TemplateResponse(
                "admin/articles/edit.html",
                {
                    "request": request, 
                    "user": user, 
                    "article": article,
                    "categories": categories,
                    "error": "Invalid category selected."
                },
                status_code=400
            )
        
        # Update article
        article.title = title
        article.content = content
        article.category_id = category_id
        article.published = published
        article.featured_image = featured_image if featured_image and featured_image.strip() else None
        
        await article.save()
        
        return RedirectResponse(url=f"/admin/articles?message=Article '{title}' updated successfully", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles/{article_id}/edit'>Try again</a>")

@app.get("/admin/articles/{article_id}/delete")
async def admin_delete_article(request: Request, article_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get article
        article = await Article.get_or_none(id=article_id)
        if not article:
            return HTMLResponse("Article not found", status_code=404)
        
        # Check if article has comments
        comment_count = await Comment.filter(article_id=article_id).count()
        if comment_count > 0:
            # Delete all comments associated with this article
            await Comment.filter(article_id=article_id).delete()
        
        # Get article title before deletion for success message
        article_title = article.title
        
        # Delete article
        await article.delete()
        
        return RedirectResponse(url=f"/admin/articles?message=Article '{article_title}' deleted successfully", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}. <a href='/admin/articles'>Try again</a>")

# Admin routes for Comments
@app.get("/admin/comments", response_class=HTMLResponse)
async def admin_comments(request: Request):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get all comments with related article and author
    comments = await Comment.all().prefetch_related("article", "author", "article__author")
    
    # Sort comments by most recent first
    comments = sorted(comments, key=lambda x: x.created_at, reverse=True)
    
    # Render the admin comments template
    return templates.TemplateResponse(
        "admin/comments/index.html",
        {"request": request, "user": user, "comments": comments, "message": request.query_params.get("message")}
    )

@app.get("/admin/comments/{comment_id}/edit", response_class=HTMLResponse)
async def admin_edit_comment_form(request: Request, comment_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get the comment to edit
    comment = await Comment.get_or_none(id=comment_id).prefetch_related("article", "author")
    if not comment:
        return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
    
    # Render the edit comment form
    return templates.TemplateResponse(
        "admin/comments/edit.html",
        {"request": request, "user": user, "comment": comment}
    )

@app.post("/admin/comments/{comment_id}/edit")
async def admin_edit_comment(
    request: Request,
    comment_id: int,
    content: str = Form(...),
):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get the comment to edit
    comment = await Comment.get_or_none(id=comment_id)
    if not comment:
        return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
    
    # Update the comment
    comment.content = content
    await comment.save()
    
    # Redirect to comments list with success message
    return RedirectResponse(
        url=f"/admin/comments?message=Comment updated successfully",
        status_code=303
    )

@app.get("/admin/comments/{comment_id}/delete")
async def admin_delete_comment(request: Request, comment_id: int):
    # Verify user is logged in and is an admin
    user = await get_user_from_cookie(request)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get the comment to delete
    comment = await Comment.get_or_none(id=comment_id)
    if not comment:
        return RedirectResponse(url="/admin/comments?message=Comment not found", status_code=303)
    
    # Delete the comment
    await comment.delete()
    
    # Redirect to comments list with success message
    return RedirectResponse(
        url="/admin/comments?message=Comment deleted successfully",
        status_code=303
    )

# Init function to create superuser and setup db
@app.on_event("startup")
async def startup_event():
    # Check if there are any users, if not create admin user
    if not await User.exists():
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password=get_password_hash("admin"),
            is_active=True,
            is_superuser=True,
        )
        await admin_user.save()
        print("Created admin user: admin / admin")


# Run the app with uvicorn
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 