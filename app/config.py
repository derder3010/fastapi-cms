import os
from typing import List
from pathlib import Path
import json
from pydantic_settings import BaseSettings

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "FastAPI CMS"
    APP_DESCRIPTION: str = "A Content Management System built with FastAPI"
    DEBUG: bool = True
    ENV: str = "development"
    
    # Security settings
    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    CORS_ALLOW_ORIGINS_STR: str = '["http://localhost", "http://localhost:8000", "http://127.0.0.1", "http://127.0.0.1:8000"]'
    
    @property
    def CORS_ALLOW_ORIGINS(self) -> List[str]:
        try:
            return json.loads(self.CORS_ALLOW_ORIGINS_STR)
        except (json.JSONDecodeError, TypeError):
            return ["*"]
    
    # Database settings
    DATABASE_URL: str = "sqlite:///db.sqlite3"
    
    # Paths
    STATIC_ROOT: str = "static"
    MEDIA_ROOT: str = "media"
    
    # Admin user
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin"
    
    # Admin settings
    ADMIN_SITE_TITLE: str = "FastAPI CMS"
    ADMIN_SITE_HEADER: str = "FastAPI CMS Admin"
    ADMIN_SITE_URL: str = "/"
    ADMIN_INDEX_TITLE: str = "Dashboard"
    ADMIN_FOOTER_HTML: str = "FastAPI Admin CMS - Powered by FastAPI"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Make sure paths are absolute
if not os.path.isabs(settings.STATIC_ROOT):
    settings.STATIC_ROOT = os.path.join(BASE_DIR, settings.STATIC_ROOT)

if not os.path.isabs(settings.MEDIA_ROOT):
    settings.MEDIA_ROOT = os.path.join(BASE_DIR, settings.MEDIA_ROOT)

# Ensure directories exist
os.makedirs(settings.STATIC_ROOT, exist_ok=True)
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

# FastAPI Admin configuration
ADMIN_SECRET = "admin-secret-key-change-in-production"

# Password hashing
PASSWORD_HASHING_ALGORITHM = "bcrypt"

# Admin settings
ADMIN = {
    "site_title": "FastAPI CMS",
    "site_header": "FastAPI CMS Admin",
    "site_url": "/",
    "index_title": "Dashboard",
    "footer_html": "FastAPI Admin CMS - Powered by FastAPI Admin",
} 