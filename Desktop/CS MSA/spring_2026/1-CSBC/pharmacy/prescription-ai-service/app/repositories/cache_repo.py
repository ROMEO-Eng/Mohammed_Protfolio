"""
Cache Repository — Redis wrapper for fast result lookups.
Used to avoid re-running expensive OCR/LLM on already-processed prescriptions.
"""

import json
import logging
from typing import Optional, Any

import redis.asyncio as aioredis

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Cache key prefixes
PREFIX_PRESCRIPTION = "prescription:"     # prescription results
PREFIX_PRODUCTS = "products:catalog"      # pharmacy product catalog
PREFIX_STATUS = "status:"                 # prescription status


class CacheRepository:
    """
    Thin async Redis wrapper.
    All values are JSON-serialised so any Pydantic model can be cached.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    # ─────────────────────────────────────────────
    # PRESCRIPTION RESULTS
    # ─────────────────────────────────────────────

    async def cache_prescription_results(
        self,
        prescription_id: str,
        results: dict,
        ttl: int | None = None,
    ) -> None:
        """Cache the final analysis results for a prescription."""
        key = f"{PREFIX_PRESCRIPTION}{prescription_id}"
        ttl = ttl or settings.redis_cache_ttl
        try:
            await self.redis.setex(key, ttl, json.dumps(results, default=str))
            logger.debug(f"Cached results for prescription {prescription_id}")
        except Exception as e:
            logger.warning(f"Failed to cache prescription {prescription_id}: {e}")

    async def get_prescription_results(
        self, prescription_id: str
    ) -> Optional[dict]:
        """Return cached results, or None if not found / expired."""
        key = f"{PREFIX_PRESCRIPTION}{prescription_id}"
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Cache HIT for prescription {prescription_id}")
                return json.loads(data)
            logger.debug(f"Cache MISS for prescription {prescription_id}")
            return None
        except Exception as e:
            logger.warning(f"Cache read failed for {prescription_id}: {e}")
            return None

    # ─────────────────────────────────────────────
    # PROCESSING STATUS
    # ─────────────────────────────────────────────

    async def set_status(
        self, prescription_id: str, status: str, ttl: int = 3600
    ) -> None:
        """Store quick-access processing status (avoids DB lookup for polls)."""
        key = f"{PREFIX_STATUS}{prescription_id}"
        try:
            await self.redis.setex(key, ttl, status)
        except Exception as e:
            logger.warning(f"Failed to set status cache for {prescription_id}: {e}")

    async def get_status(self, prescription_id: str) -> Optional[str]:
        """Return cached status string."""
        key = f"{PREFIX_STATUS}{prescription_id}"
        try:
            val = await self.redis.get(key)
            return val.decode() if val else None
        except Exception as e:
            logger.warning(f"Failed to get status cache for {prescription_id}: {e}")
            return None

    # ─────────────────────────────────────────────
    # PRODUCT CATALOG
    # ─────────────────────────────────────────────

    async def cache_product_catalog(
        self,
        products: list,
        ttl: int = 300,   # 5 minutes — catalog changes infrequently
    ) -> None:
        """Cache the full product list from Spring Boot."""
        try:
            await self.redis.setex(
                PREFIX_PRODUCTS, ttl, json.dumps(products, default=str)
            )
            logger.debug(f"Cached {len(products)} products")
        except Exception as e:
            logger.warning(f"Failed to cache product catalog: {e}")

    async def get_product_catalog(self) -> Optional[list]:
        """Return cached product list."""
        try:
            data = await self.redis.get(PREFIX_PRODUCTS)
            if data:
                logger.debug("Product catalog cache HIT")
                return json.loads(data)
            logger.debug("Product catalog cache MISS")
            return None
        except Exception as e:
            logger.warning(f"Failed to get product catalog from cache: {e}")
            return None

    # ─────────────────────────────────────────────
    # GENERIC HELPERS
    # ─────────────────────────────────────────────

    async def delete(self, key: str) -> None:
        """Delete a single cache key."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Failed to delete cache key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Return True if a key exists in cache."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.warning(f"Failed to check cache existence for {key}: {e}")
            return False

    async def ping(self) -> bool:
        """Health check — return True if Redis is reachable."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────
# Connection factory
# ─────────────────────────────────────────────

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return the shared async Redis client (created on first call)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
    return _redis_client


async def get_cache_repo() -> CacheRepository:
    """FastAPI dependency — returns a ready CacheRepository."""
    client = await get_redis()
    return CacheRepository(client)


async def close_redis() -> None:
    """Call on app shutdown to cleanly close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
