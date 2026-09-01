from fastapi import APIRouter

from app.api.v1.auditor import router as auditor_router
from app.api.v1.converter import router as converter_router
from app.api.v1.maker import router as maker_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(maker_router)
api_v1_router.include_router(converter_router)
api_v1_router.include_router(auditor_router)
