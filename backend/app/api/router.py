from fastapi import APIRouter

from backend.app.api.routes import health, images, pdf


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(pdf.router, prefix="/pdf", tags=["pdf"])
