"""Custom exception classes"""

from typing import Any, Optional


class CustomException(Exception):
    """Base custom exception"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_SERVER_ERROR"
        self.details = details
        super().__init__(self.message)


class AuthenticationException(CustomException):
    """Authentication failed exception"""

    def __init__(
        self, message: str = "Authentication failed", details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationException(CustomException):
    """Authorization failed exception"""

    def __init__(
        self, message: str = "Insufficient permissions", details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class ValidationException(CustomException):
    """Validation failed exception"""

    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class NotFoundError(CustomException):
    """Resource not found exception"""

    def __init__(
        self, resource: str = "Resource", details: Optional[Any] = None
    ):
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class DatabaseError(CustomException):
    """Database operation error"""

    def __init__(self, message: str = "Database error", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )


class OCRError(CustomException):
    """OCR processing error"""

    def __init__(self, message: str = "OCR processing failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="OCR_ERROR",
            details=details,
        )


class LLMError(CustomException):
    """LLM processing error"""

    def __init__(self, message: str = "LLM processing failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="LLM_ERROR",
            details=details,
        )


class FileUploadError(CustomException):
    """File upload error"""

    def __init__(self, message: str = "File upload failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="FILE_UPLOAD_ERROR",
            details=details,
        )
