import os
from typing import List

# Database configuration
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {"file_path": "db.sqlite3"}
        }
    },
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
}

# FastAPI Admin configuration
ADMIN_SECRET = "admin-secret-key-change-in-production"

# JWT settings
JWT_SECRET_KEY = "jwt-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Admin settings
ADMIN = {
    "site_title": "FastAPI CMS",
    "site_header": "FastAPI CMS Admin",
    "site_url": "/",
    "index_title": "Dashboard",
    "footer_html": "FastAPI Admin CMS - Powered by FastAPI Admin",
}

# Password hashing
PASSWORD_HASHING_ALGORITHM = "bcrypt"

# Media settings
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upload")
STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# CORS settings
CORS_ALLOW_ORIGINS: List[str] = ["*"] 