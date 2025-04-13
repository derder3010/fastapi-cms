# API package 
from fastapi import APIRouter
from app.api.users import router as users_router
from app.api.categories import router as categories_router
from app.api.articles import router as articles_router
from app.api.comments import router as comments_router
from app.api.tags import router as tags_router
from app.api.products import router as products_router
from app.api.upload import router as upload_router

api_router = APIRouter(prefix="/api")

api_router.include_router(users_router)
api_router.include_router(categories_router)
api_router.include_router(articles_router)
api_router.include_router(comments_router)
api_router.include_router(tags_router)
api_router.include_router(products_router)
api_router.include_router(upload_router) 