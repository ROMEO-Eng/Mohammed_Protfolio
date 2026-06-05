"""
check_db.py  — quick connectivity and schema smoke-test.

Run from the project root:
    python scripts/check_db.py
"""

import asyncio
import uuid
import sys
from datetime import datetime

# ── allow imports from project root ────────────────────────────────────────
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config.settings import settings
from app.config.database import MongoDatabase
from app.repositories.cache_repo import get_redis, close_redis
from app.repositories.prescription_repo import PrescriptionRepository
from app.models.database import PrescriptionDocument, ProcessingStatus, OriginalImageDoc


async def check_mongodb() -> bool:
    """Connect to MongoDB, write a test document, read it back, delete it."""
    print("\n── MongoDB ─────────────────────────────────────────")
    print(f"  URL : {settings.mongodb_url[:40]}...")
    print(f"  DB  : {settings.mongodb_db_name}")

    try:
        await MongoDatabase.connect()
        print("  ✅ Connection: OK")
    except Exception as e:
        print(f"  ❌ Connection FAILED: {e}")
        return False

    db = MongoDatabase.db
    repo = PrescriptionRepository(db)

    # Write test document
    test_id = f"test-{uuid.uuid4()}"
    doc = PrescriptionDocument(
        prescriptionId=test_id,
        userId="test-user",
        processingStatus=ProcessingStatus.PENDING,
        originalImage=OriginalImageDoc(
            filename="test.jpg",
            filepath=f"uploads/{test_id}/test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
        ),
    )

    try:
        await repo.create(doc)
        print("  ✅ Write:       OK")
    except Exception as e:
        print(f"  ❌ Write FAILED: {e}")
        return False

    # Read back
    try:
        fetched = await repo.get_by_id(test_id)
        assert fetched.prescription_id == test_id
        print("  ✅ Read:        OK")
    except Exception as e:
        print(f"  ❌ Read FAILED: {e}")
        return False

    # Delete
    try:
        await repo.delete(test_id)
        print("  ✅ Delete:      OK")
    except Exception as e:
        print(f"  ❌ Delete FAILED: {e}")
        return False

    # Log operations
    try:
        from app.models.database import ProcessingStage
        await repo.log_stage_start(test_id, ProcessingStage.UPLOAD)
        print("  ✅ Log write:   OK")
    except Exception as e:
        # Log on already-deleted doc is fine to warn
        print(f"  ⚠️  Log write (non-critical): {e}")

    await MongoDatabase.disconnect()
    return True


async def check_redis() -> bool:
    """Connect to Redis and run ping + set/get round-trip."""
    print("\n── Redis ───────────────────────────────────────────")
    print(f"  URL : {settings.redis_url}")

    try:
        redis = await get_redis()
        await redis.ping()
        print("  ✅ Connection: OK")
    except Exception as e:
        print(f"  ❌ Connection FAILED: {e}")
        return False

    # Set / Get round-trip
    test_key = f"check:{uuid.uuid4()}"
    try:
        redis = await get_redis()
        await redis.setex(test_key, 10, "hello")
        val = await redis.get(test_key)
        assert val == b"hello"
        await redis.delete(test_key)
        print("  ✅ Set/Get/Del: OK")
    except Exception as e:
        print(f"  ❌ Set/Get FAILED: {e}")
        return False

    await close_redis()
    return True


async def main():
    print("=" * 52)
    print("  Prescription AI Service — DB Connectivity Check")
    print("=" * 52)

    mongo_ok = await check_mongodb()
    redis_ok = await check_redis()

    print("\n── Summary ─────────────────────────────────────────")
    print(f"  MongoDB : {'✅ OK' if mongo_ok else '❌ FAILED'}")
    print(f"  Redis   : {'✅ OK' if redis_ok else '❌ FAILED'}")
    print()

    if mongo_ok and redis_ok:
        print("  🎉 All connections healthy — ready to start the service!")
        sys.exit(0)
    else:
        print("  ⚠️  One or more connections failed. Check your .env settings.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
