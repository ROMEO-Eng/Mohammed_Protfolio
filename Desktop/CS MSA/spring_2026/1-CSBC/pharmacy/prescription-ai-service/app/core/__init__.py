"""Core module — security, exceptions, middleware"""

from .exceptions import (
    CustomException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    NotFoundError,
    DatabaseError,
    OCRError,
    LLMError,
    FileUploadError,
)

from .security import (
    create_access_token,
    decode_token,
    get_current_user,
    get_current_staff,
    get_current_admin,
    require_spring_boot_key,
    CurrentUser,
    CurrentStaff,
    CurrentAdmin,
    ServiceAuth,
    ROLE_CUSTOMER,
    ROLE_PHARMACIST,
    ROLE_ADMIN,
)

__all__ = [
    # Exceptions
    "CustomException",
    "AuthenticationException",
    "AuthorizationException",
    "ValidationException",
    "NotFoundError",
    "DatabaseError",
    "OCRError",
    "LLMError",
    "FileUploadError",
    # Security
    "create_access_token",
    "decode_token",
    "get_current_user",
    "get_current_staff",
    "get_current_admin",
    "require_spring_boot_key",
    "CurrentUser",
    "CurrentStaff",
    "CurrentAdmin",
    "ServiceAuth",
    "ROLE_CUSTOMER",
    "ROLE_PHARMACIST",
    "ROLE_ADMIN",
]
