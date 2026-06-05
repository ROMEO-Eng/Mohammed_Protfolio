"""Dependency injection layer"""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.database import get_db
from app.repositories.prescription_repo import PrescriptionRepository
from app.repositories.cache_repo import CacheRepository, get_cache_repo
from app.core.security import (
    CurrentUser,
    CurrentStaff,
    CurrentAdmin,
    ServiceAuth,
    get_current_user,
    get_current_staff,
    get_current_admin,
    require_spring_boot_key,
)

# ── Repositories ───────────────────────────────

def get_prescription_repo(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> PrescriptionRepository:
    return PrescriptionRepository(db)


# ── Typed deps ─────────────────────────────────

DBDep = Annotated[AsyncIOMotorDatabase, Depends(get_db)]

RepoDep = Annotated[
    PrescriptionRepository,
    Depends(get_prescription_repo)
]

CacheDep = Annotated[
    CacheRepository,
    Depends(get_cache_repo)
]

__all__ = [
    "DBDep",
    "RepoDep",
    "CacheDep",
    "CurrentUser",
    "CurrentStaff",
    "CurrentAdmin",
    "ServiceAuth",
    "get_db",
    "get_prescription_repo",
    "get_cache_repo",
    "get_current_user",
    "get_current_staff",
    "get_current_admin",
    "require_spring_boot_key",
]