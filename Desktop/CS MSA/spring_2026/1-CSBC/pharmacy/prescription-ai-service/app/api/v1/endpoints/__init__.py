from .health import health_router
from .prescriptions import router as prescriptions_router

__all__ = [
    "health_router",
    "prescriptions_router",
]