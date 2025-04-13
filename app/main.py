import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

# Configure SQLAlchemy logging level
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from app.config import settings
from app.database import engine, create_db_and_tables, get_db
from app.models import User
from app.auth.utils import get_password_hash
from app.api import api_router
from app.routers import admin_router
from app.auth.routes import router as auth_router

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME, 
    description=settings.APP_DESCRIPTION,
    debug=settings.DEBUG
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")
app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

# Include routers
app.include_router(api_router)
app.include_router(admin_router)
# Include auth router with admin prefix
app.include_router(auth_router, prefix="/admin")

# Root route for welcome page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Init function to create superuser and setup db
@app.on_event("startup")
async def startup_event():
    # Create tables
    create_db_and_tables()
    
    # Create admin user if no users exist
    db = next(get_db())
    user_count = db.execute(select(User)).first()
    
    if not user_count:
        admin_user = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password=get_password_hash(settings.ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin_user)
        db.commit()
        print(f"Created admin user: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
        
    print("\n*********************************************")
    print("* FastAPI CMS is now running with modular   *")
    print("* architecture using SQLModel, Pydantic,    *")
    print("* and FastAPI.                             *")
    print("*********************************************\n") 