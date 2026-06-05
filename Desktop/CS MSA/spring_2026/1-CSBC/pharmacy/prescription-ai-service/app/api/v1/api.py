from fastapi import APIRouter
from .endpoints import health_router, prescriptions_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(prescriptions_router, tags=["Prescriptions"])