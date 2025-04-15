import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
import boto3
from botocore.exceptions import ClientError
from contextlib import asynccontextmanager

# Configure SQLAlchemy logging level
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from app.config import settings
from app.database import engine, create_db_and_tables, get_db
from app.models import User
from app.auth.utils import get_password_hash
from app.api import api_router
from app.routers import admin_router
from app.auth.routes import router as auth_router
from app.utils.storage import StorageManager

# Function to verify R2 connection
def verify_r2_connection():
    try:
        # Create S3 client for R2
        s3 = boto3.client(
            service_name='s3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION_NAME
        )
        
        # Check if bucket exists by listing its contents
        s3.head_bucket(Bucket=settings.R2_BUCKET_NAME)
        
        # If the request does not raise an exception, the connection is successful
        print(f"\n✅ Successfully connected to Cloudflare R2 bucket: {settings.R2_BUCKET_NAME}")
        
        # List a few objects to verify permissions
        response = s3.list_objects_v2(Bucket=settings.R2_BUCKET_NAME, MaxKeys=5)
        
        # If there are objects, print some information
        if response.get('Contents'):
            print(f"   Found {len(response['Contents'])} objects in the bucket")
            print("   Example objects:")
            for obj in response['Contents'][:3]:  # Show up to 3 objects
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   Bucket is empty")
            
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        
        print(f"\n❌ Failed to connect to Cloudflare R2: {error_code} - {error_message}")
        
        if error_code == "AccessDenied":
            print("   Access denied. Please check your R2 credentials and bucket permissions.")
        elif error_code == "NoSuchBucket":
            print(f"   Bucket '{settings.R2_BUCKET_NAME}' does not exist.")
        elif error_code == "InvalidAccessKeyId":
            print("   Invalid Access Key ID. Please check your R2_ACCESS_KEY_ID.")
        elif error_code == "SignatureDoesNotMatch":
            print("   Signature error. Please check your R2_SECRET_ACCESS_KEY.")
        
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error connecting to Cloudflare R2: {str(e)}")
        return False

# Define lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables, admin user, and verify R2 connection
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
    
    # Verify R2 connection if cloud storage is enabled
    if settings.USE_CLOUD_STORAGE:
        r2_connected = verify_r2_connection()
        if not r2_connected:
            print("\n⚠️ WARNING: Failed to connect to Cloudflare R2")
            print("   File uploads will fail. Please check your R2 configuration in .env file.")
        
    print("\n*********************************************")
    print("* FastAPI CMS is now running with modular   *")
    print("* architecture using SQLModel, Pydantic,    *")
    print("* and FastAPI.                             *")
    print("*********************************************\n")
    
    # Yield control back to FastAPI
    yield
    
    # Shutdown: Cleanup code can go here
    print("\nShutting down FastAPI CMS...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME, 
    description=settings.APP_DESCRIPTION,
    debug=settings.DEBUG,
    lifespan=lifespan
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

# Add the filter to Jinja2 environment
templates.env.filters["media_url"] = StorageManager.get_file_url

# Mount static files
app.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")

# Only mount media directory locally if not using cloud storage
if not settings.USE_CLOUD_STORAGE:
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