from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.images import router as images_router
from app.api.v1.jobs import router as jobs_router


api_router = APIRouter()

api_router.include_router(images_router)
api_router.include_router(jobs_router)
api_router.include_router(analytics_router)
