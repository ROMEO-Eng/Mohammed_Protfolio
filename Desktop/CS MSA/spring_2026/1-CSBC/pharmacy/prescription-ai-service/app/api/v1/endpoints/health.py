"""Health check endpoints"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config.database import MongoDatabase
from app.repositories.cache_repo import get_cache_repo, CacheRepository
from app.models.analysis import APIResponse, HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=APIResponse)
async def health_check():
    db_ok = await _check_mongo()
    redis_ok = await _check_redis()

    status = "healthy" if db_ok and redis_ok else "degraded"

    return APIResponse(
        success=True,
        message=f"Service is {status}",
        data=HealthCheckResponse(
            status=status,
            version="0.1.0",
            database_connected=db_ok,
            redis_connected=redis_ok,
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    )


@router.get("/detailed", response_model=APIResponse)
async def detailed_health():
    db_ok = await _check_mongo()
    redis_ok = await _check_redis()

    return APIResponse(
        success=True,
        message="Detailed health check",
        data={
            "database": db_ok,
            "cache": redis_ok,
            "ai": {
                "ocr": "not_initialized",
                "llm": "not_initialized",
                "matcher": "not_initialized",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def _check_mongo() -> bool:
    try:
        if MongoDatabase.client is None:
            return False
        await MongoDatabase.client.admin.command("ping")
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        cache: CacheRepository = await get_cache_repo()
        return await cache.ping()
    except Exception:
        return False


health_router = router