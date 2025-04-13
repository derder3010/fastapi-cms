# Routers package 
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from app.database import get_db
from app.auth.utils import get_user_from_cookie

from app.routers.dashboard import router as dashboard_router
from app.routers.users import router as users_router
from app.routers.categories import router as categories_router
from app.routers.articles import router as articles_router
from app.routers.comments import router as comments_router

admin_router = APIRouter(prefix="/admin")

# Root admin route redirect to dashboard or login
@admin_router.get("/", include_in_schema=False)
async def admin_root(request: Request, db=Depends(get_db)):
    # Check if user is logged in
    user = await get_user_from_cookie(request, db)
    if user and user.is_superuser:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    else:
        return RedirectResponse(url="/admin/login", status_code=303)

admin_router.include_router(dashboard_router)
admin_router.include_router(users_router)
admin_router.include_router(categories_router)
admin_router.include_router(articles_router)
admin_router.include_router(comments_router) 