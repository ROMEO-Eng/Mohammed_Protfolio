"""Database connection configuration and management"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MongoDatabase:
    """MongoDB connection manager"""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Create MongoDB connection"""
        try:
            logger.info(f"Connecting to MongoDB at {settings.mongodb_url}")

            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=settings.mongodb_timeout,
                retryWrites=True,
            )

            # test connection
            await cls.client.admin.command("ping")

            cls.db = cls.client[settings.mongodb_db_name]

            logger.info(f"Connected to database: {settings.mongodb_db_name}")

            await cls._create_indexes()

        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Close connection"""
        if cls.client is not None:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create DB indexes"""

        # ✅ FIX IMPORTANT: NEVER use "if not cls.db"
        if cls.db is None:
            return

        try:
            await cls.db.prescription_analysis.create_index(
                "prescriptionId",
                unique=True
            )
            await cls.db.prescription_analysis.create_index("userId")
            await cls.db.prescription_analysis.create_index("processingStatus")
            await cls.db.prescription_analysis.create_index("createdAt")

            await cls.db.processing_logs.create_index("prescriptionId")
            await cls.db.processing_logs.create_index("stage")
            await cls.db.processing_logs.create_index("createdAt")

            logger.info("Indexes created successfully")

        except Exception as e:
            logger.error(f"Index creation failed: {e}")


# ─────────────────────────────────────────────
# FastAPI dependency
# ─────────────────────────────────────────────

async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency"""
    if MongoDatabase.db is None:
        raise RuntimeError("Database not connected")
    return MongoDatabase.db


# instance
db = MongoDatabase()