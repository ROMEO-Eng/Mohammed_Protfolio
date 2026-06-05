"""
Prescription analysis endpoints.

Routes
------
POST   /api/v1/prescriptions/analyze             — upload image, start analysis
GET    /api/v1/prescriptions/my/history          — list current user's prescriptions
GET    /api/v1/prescriptions/{id}/status         — poll processing status
GET    /api/v1/prescriptions/{id}/results        — get final analysis results
DELETE /api/v1/prescriptions/{id}                — delete a prescription
GET    /api/v1/prescriptions/admin/all           — admin: list all prescriptions
"""

import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.api.deps import RepoDep, CacheDep, CurrentUser, CurrentAdmin
from app.core.exceptions import NotFoundError, DatabaseError
from app.models.prescription import (
    PrescriptionAnalysisResponse,
    AnalysisStatusResponse,
)
from app.models.analysis import APIResponse
from app.models.database import (
    PrescriptionDocument,
    OriginalImageDoc,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


# ─────────────────────────────────────────────────────────
# POST /analyze
# ─────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=APIResponse,
    summary="Upload a prescription image for AI analysis",
    responses={
        200: {"description": "Prescription queued"},
        400: {"description": "Invalid file type or size"},
        401: {"description": "Not authenticated"},
    },
)
async def analyze_prescription(
    repo: RepoDep,
    cache: CacheDep,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="JPEG or PNG prescription image"),
) -> APIResponse:
    """
    Upload a prescription image and start AI analysis.

    The image is saved, then passed through:
    1. PaddleOCR  → extract raw text
    2. Qwen3 8B   → extract medications, dosages, frequencies
    3. Product matcher → link drugs to pharmacy inventory

    Returns immediately with a `prescription_id`.
    Poll `/status` until `status == completed`, then fetch `/results`.
    """
    # ── File validation ───────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        return APIResponse(
            success=False,
            message=f"Unsupported file type '{file.content_type}'. Use JPEG or PNG.",
            error={"code": "INVALID_FILE_TYPE"},
        )

    content = await file.read()
    if len(content) > MAX_BYTES:
        return APIResponse(
            success=False,
            message="File exceeds the 50 MB limit.",
            error={"code": "FILE_TOO_LARGE", "size_bytes": len(content)},
        )

    # ── Build and persist document ────────────────────────
    prescription_id = str(uuid.uuid4())
    user_id = current_user["user_id"]

    doc = PrescriptionDocument(
        prescriptionId=prescription_id,
        userId=user_id,
        processingStatus=ProcessingStatus.PENDING,
        originalImage=OriginalImageDoc(
            filename=file.filename or "prescription.jpg",
            filepath=f"uploads/{prescription_id}/{file.filename}",
            file_size=len(content),
            mime_type=file.content_type or "image/jpeg",
        ),
    )

    try:
        await repo.create(doc)
        await cache.set_status(prescription_id, ProcessingStatus.PENDING.value)
    except DatabaseError as exc:
        logger.error(f"DB error saving prescription: {exc.message}")
        return APIResponse(
            success=False,
            message="Failed to save prescription. Please try again.",
            error={"detail": exc.message},
        )

    logger.info(f"Prescription {prescription_id} created — user={user_id} size={len(content)}")

    # TODO Phase 2 — enqueue OCR task:
    #   from app.tasks.prescription_tasks import run_analysis
    #   run_analysis.delay(prescription_id)

    return APIResponse(
        success=True,
        message="Prescription uploaded successfully",
        data=PrescriptionAnalysisResponse(
            prescription_id=prescription_id,
            status="pending",
            estimated_processing_time=30,
            message="Prescription queued for AI analysis. Poll /status for updates.",
        ).model_dump(),
    )


# ─────────────────────────────────────────────────────────
# GET /my/history
# ─────────────────────────────────────────────────────────

@router.get(
    "/my/history",
    response_model=APIResponse,
    summary="List the current user's prescription history",
)
async def get_my_prescriptions(
    repo: RepoDep,
    current_user: CurrentUser,
    limit: int = 10,
    skip: int = 0,
) -> APIResponse:
    """Return all prescriptions uploaded by the authenticated user (newest first)."""
    docs = await repo.get_by_user(current_user["user_id"], limit=limit, skip=skip)

    return APIResponse(
        success=True,
        message=f"Found {len(docs)} prescriptions",
        data=[_summary(d) for d in docs],
    )


# ─────────────────────────────────────────────────────────
# GET /{id}/status
# ─────────────────────────────────────────────────────────

@router.get(
    "/{prescription_id}/status",
    response_model=APIResponse,
    summary="Poll the analysis status",
)
async def get_analysis_status(
    prescription_id: str,
    repo: RepoDep,
    cache: CacheDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Returns current processing status and progress percentage.

    Recommended polling interval: **every 3 seconds** until `status == completed`.
    """
    # Fast path — completed status cached in Redis
    cached_status = await cache.get_status(prescription_id)
    if cached_status == ProcessingStatus.COMPLETED.value:
        return _status_response(prescription_id, "completed", 100, 0, "completed")

    try:
        doc = await repo.get_by_id(prescription_id)
    except NotFoundError:
        return _not_found()

    _assert_owner(doc, current_user)

    return _status_response(
        prescription_id,
        doc.processing_status,
        _progress(doc.processing_status),
        _eta(doc.processing_status),
        _stage(doc),
    )


# ─────────────────────────────────────────────────────────
# GET /{id}/results
# ─────────────────────────────────────────────────────────

@router.get(
    "/{prescription_id}/results",
    response_model=APIResponse,
    summary="Retrieve final analysis results",
)
async def get_analysis_results(
    prescription_id: str,
    repo: RepoDep,
    cache: CacheDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Returns the complete extraction result including:
    - Medications (drug name, dosage, frequency, duration)
    - Matched pharmacy products (product_id, price, availability)
    - Overall confidence score

    Only available when `status == completed`.
    """
    # Cache hit — skip DB
    cached = await cache.get_prescription_results(prescription_id)
    if cached:
        return APIResponse(success=True, message="Results retrieved", data=cached)

    try:
        doc = await repo.get_by_id(prescription_id)
    except NotFoundError:
        return _not_found()

    _assert_owner(doc, current_user)

    if doc.processing_status != ProcessingStatus.COMPLETED:
        return APIResponse(
            success=False,
            message=f"Analysis not yet complete — current status: {doc.processing_status}",
            error={"status": doc.processing_status, "code": "ANALYSIS_PENDING"},
        )

    results = _build_results(doc)
    await cache.cache_prescription_results(prescription_id, results)

    return APIResponse(success=True, message="Results retrieved", data=results)


# ─────────────────────────────────────────────────────────
# DELETE /{id}
# ─────────────────────────────────────────────────────────

@router.delete(
    "/{prescription_id}",
    response_model=APIResponse,
    summary="Delete a prescription",
)
async def delete_prescription(
    prescription_id: str,
    repo: RepoDep,
    cache: CacheDep,
    current_user: CurrentUser,
) -> APIResponse:
    """Delete a prescription and all its associated data (logs, cached results)."""
    try:
        doc = await repo.get_by_id(prescription_id)
    except NotFoundError:
        return _not_found()

    _assert_owner(doc, current_user)

    await repo.delete(prescription_id)
    await cache.delete(f"prescription:{prescription_id}")
    await cache.delete(f"status:{prescription_id}")

    logger.info(f"Prescription {prescription_id} deleted by user {current_user['user_id']}")
    return APIResponse(success=True, message="Prescription deleted successfully")


# ─────────────────────────────────────────────────────────
# Admin endpoints
# ─────────────────────────────────────────────────────────

@router.get(
    "/admin/all",
    response_model=APIResponse,
    summary="[Admin] List all prescriptions",
    tags=["Admin"],
)
async def admin_list_all(
    repo: RepoDep,
    current_admin: CurrentAdmin,   # 403 if not admin
    user_id: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> APIResponse:
    """
    Admin endpoint — list all prescriptions or filter by user_id.
    Requires admin role.
    """
    if user_id:
        docs = await repo.get_by_user(user_id, limit=limit, skip=skip)
    else:
        docs = await repo.get_by_user("", limit=limit, skip=skip)

    return APIResponse(
        success=True,
        message=f"Found {len(docs)} prescriptions",
        data=[_summary(d) for d in docs],
    )


# ─────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────

def _assert_owner(doc: PrescriptionDocument, current_user: dict) -> None:
    """Raise 403 if the authenticated user doesn't own the prescription."""
    if doc.user_id != current_user["user_id"] and current_user["role"] not in ("admin", "pharmacist"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _not_found() -> APIResponse:
    return APIResponse(
        success=False,
        message="Prescription not found",
        error={"code": "NOT_FOUND"},
    )


def _summary(doc: PrescriptionDocument) -> dict:
    """Compact representation for list endpoints."""
    return {
        "prescription_id": doc.prescription_id,
        "status": doc.processing_status,
        "uploaded_at": doc.upload_timestamp.isoformat(),
        "confidence": doc.overall_confidence,
        "medication_count": (
            len(doc.extracted_data.medications) if doc.extracted_data else 0
        ),
        "filename": doc.original_image.filename if doc.original_image else None,
    }


def _build_results(doc: PrescriptionDocument) -> dict:
    return {
        "prescription_id": doc.prescription_id,
        "status": "completed",
        "confidence": doc.overall_confidence,
        "processing_time_ms": doc.total_processing_time_ms,
        "medications": (
            [m.model_dump() for m in doc.extracted_data.medications]
            if doc.extracted_data else []
        ),
        "product_matches": [m.model_dump() for m in doc.product_matching],
        "warnings": doc.processing_errors,
        "raw_ocr_text": doc.ocr_results.raw_text if doc.ocr_results else None,
    }


def _status_response(
    prescription_id: str, s: str, progress: int, eta: int, stage: str
) -> APIResponse:
    return APIResponse(
        success=True,
        message="Status retrieved",
        data=AnalysisStatusResponse(
            prescription_id=prescription_id,
            status=s,
            progress=progress,
            estimated_time_remaining=eta,
            current_stage=stage,
        ).model_dump(),
    )


def _progress(s: str) -> int:
    return {"pending": 10, "processing": 55, "completed": 100, "failed": 0}.get(s, 0)


def _eta(s: str) -> int:
    return {"pending": 30, "processing": 10, "completed": 0, "failed": 0}.get(s, 0)


def _stage(doc: PrescriptionDocument) -> str:
    if doc.product_matching:  return "completed"
    if doc.extracted_data:    return "product_matching"
    if doc.llm_analysis:      return "entity_extraction"
    if doc.ocr_results:       return "llm_analysis"
    return "ocr_processing"
