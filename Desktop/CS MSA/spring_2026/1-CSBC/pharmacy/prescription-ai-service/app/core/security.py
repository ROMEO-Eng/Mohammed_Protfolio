"""
Security & authentication utilities (FastAPI AI service)

Compatible with Spring Boot JWT structure:

{
  "sub": "userId",
  "role": "customer | pharmacist | admin",
  "exp": 1234567890,
  "iat": 1234567890
}
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, Dict, Any

from jose import JWTError, ExpiredSignatureError, jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.core.exceptions import AuthenticationException

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Bearer auth scheme
# ─────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

# ─────────────────────────────────────────────
# Roles
# ─────────────────────────────────────────────
ROLE_CUSTOMER   = "customer"
ROLE_PHARMACIST = "pharmacist"
ROLE_ADMIN      = "admin"

STAFF_ROLES = {ROLE_PHARMACIST, ROLE_ADMIN}
ALL_ROLES   = {ROLE_CUSTOMER, ROLE_PHARMACIST, ROLE_ADMIN}

# ─────────────────────────────────────────────
# Create token (DEV ONLY - not used in production)
# ─────────────────────────────────────────────
def create_access_token(
    user_id: str,
    role: str = ROLE_CUSTOMER,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)

    expire = now + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": user_id,
        "role": role.lower(),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

# ─────────────────────────────────────────────
# Decode + validate JWT
# ─────────────────────────────────────────────
def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

    except ExpiredSignatureError:
        raise AuthenticationException("Token expired")
    except JWTError as exc:
        logger.debug(f"JWT error: {exc}")
        raise AuthenticationException("Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Missing user id (sub)")

    role = (payload.get("role") or ROLE_CUSTOMER).lower()

    if role not in ALL_ROLES:
        logger.warning(f"Unknown role: {role}, defaulting to customer")
        role = ROLE_CUSTOMER

    return {
        "sub": user_id,
        "role": role,
        "iat": payload.get("iat"),
        "exp": payload.get("exp"),
    }

# ─────────────────────────────────────────────
# Current user dependency
# ─────────────────────────────────────────────
async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> Dict[str, Any]:

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except AuthenticationException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": payload["sub"],
        "role": payload["role"],
        "token_data": payload,
    }

# ─────────────────────────────────────────────
# Staff only (pharmacist/admin)
# ─────────────────────────────────────────────
async def get_current_staff(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
) -> Dict[str, Any]:

    if current_user["role"] not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )

    return current_user

# ─────────────────────────────────────────────
# Admin only
# ─────────────────────────────────────────────
async def get_current_admin(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
) -> Dict[str, Any]:

    if current_user["role"] != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user

# ─────────────────────────────────────────────
# Service-to-service auth (Spring Boot → FastAPI)
# ─────────────────────────────────────────────
async def require_spring_boot_key(
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> None:

    if not settings.spring_boot_api_key:
        return  # disabled in dev

    if x_api_key != settings.spring_boot_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key",
        )

# ─────────────────────────────────────────────
# Typed aliases for endpoints
# ─────────────────────────────────────────────
CurrentUser  = Annotated[Dict[str, Any], Depends(get_current_user)]
CurrentStaff = Annotated[Dict[str, Any], Depends(get_current_staff)]
CurrentAdmin = Annotated[Dict[str, Any], Depends(get_current_admin)]
ServiceAuth  = Annotated[None, Depends(require_spring_boot_key)]