"""
Prescription Repository — all MongoDB CRUD operations.
No business logic here. Pure data access only.
"""

import logging
from typing import Optional, List
from datetime import datetime

import motor.motor_asyncio
from pymongo import DESCENDING

from app.models.database import (
    PrescriptionDocument,
    ProcessingLogDocument,
    ProcessingStatus,
    ProcessingStage,
    ExtractedDataDoc,
    OCRResultsDoc,
    LLMAnalysisDoc,
    ProductMatchDoc,
)
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

COLLECTION = "prescription_analysis"
LOGS_COLLECTION = "processing_logs"


class PrescriptionRepository:
    """
    Repository for all prescription analysis database operations.
    Requires a Motor async database instance.
    """

    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[COLLECTION]
        self.logs = db[LOGS_COLLECTION]

    # ─────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────

    async def create(self, doc: PrescriptionDocument) -> str:
        """
        Insert a new prescription document.
        Returns the prescription_id on success.
        """
        try:
            result = await self.collection.insert_one(doc.to_mongo())
            logger.info(f"Created prescription {doc.prescription_id}")
            return doc.prescription_id
        except Exception as e:
            logger.error(f"Failed to create prescription: {e}")
            raise DatabaseError(f"Failed to create prescription: {str(e)}")

    # ─────────────────────────────────────────────
    # READ
    # ─────────────────────────────────────────────

    async def get_by_id(self, prescription_id: str) -> PrescriptionDocument:
        """Fetch a single prescription by prescriptionId. Raises NotFoundError if missing."""
        try:
            data = await self.collection.find_one({"prescriptionId": prescription_id})
            if not data:
                raise NotFoundError("Prescription")
            return PrescriptionDocument.from_mongo(data)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get prescription {prescription_id}: {e}")
            raise DatabaseError(f"Failed to retrieve prescription: {str(e)}")

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
    ) -> List[PrescriptionDocument]:
        """Return all prescriptions for a user, newest first."""
        try:
            cursor = (
                self.collection
                .find({"userId": user_id})
                .sort("createdAt", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            docs = await cursor.to_list(length=limit)
            return [PrescriptionDocument.from_mongo(d) for d in docs]
        except Exception as e:
            logger.error(f"Failed to list prescriptions for user {user_id}: {e}")
            raise DatabaseError(f"Failed to list prescriptions: {str(e)}")

    async def exists(self, prescription_id: str) -> bool:
        """Return True if prescription exists."""
        count = await self.collection.count_documents(
            {"prescriptionId": prescription_id}, limit=1
        )
        return count > 0

    # ─────────────────────────────────────────────
    # UPDATE — granular stage updates
    # ─────────────────────────────────────────────

    async def update_status(
        self,
        prescription_id: str,
        status: ProcessingStatus,
    ) -> None:
        """Update only the processing status + updatedAt."""
        update: dict = {
            "$set": {
                "processingStatus": status.value,
                "updatedAt": datetime.utcnow(),
            }
        }
        if status == ProcessingStatus.COMPLETED:
            update["$set"]["completedAt"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"prescriptionId": prescription_id}, update
        )
        if result.matched_count == 0:
            raise NotFoundError("Prescription")
        logger.debug(f"Updated status of {prescription_id} → {status}")

    async def save_ocr_results(
        self,
        prescription_id: str,
        ocr: OCRResultsDoc,
    ) -> None:
        """Persist OCR extraction results."""
        await self.collection.update_one(
            {"prescriptionId": prescription_id},
            {
                "$set": {
                    "ocrResults": ocr.model_dump(),
                    "processingStatus": ProcessingStatus.PROCESSING.value,
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    async def save_llm_analysis(
        self,
        prescription_id: str,
        llm: LLMAnalysisDoc,
    ) -> None:
        """Persist LLM raw analysis."""
        await self.collection.update_one(
            {"prescriptionId": prescription_id},
            {
                "$set": {
                    "llmAnalysis": llm.model_dump(),
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    async def save_extracted_data(
        self,
        prescription_id: str,
        extracted: ExtractedDataDoc,
    ) -> None:
        """Persist extracted medications."""
        await self.collection.update_one(
            {"prescriptionId": prescription_id},
            {
                "$set": {
                    "extractedData": extracted.model_dump(),
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    async def save_product_matches(
        self,
        prescription_id: str,
        matches: List[ProductMatchDoc],
        overall_confidence: float,
        total_processing_time_ms: int,
    ) -> None:
        """Persist product matching results and finalize the document."""
        await self.collection.update_one(
            {"prescriptionId": prescription_id},
            {
                "$set": {
                    "productMatching": [m.model_dump() for m in matches],
                    "overallConfidence": overall_confidence,
                    "totalProcessingTimeMs": total_processing_time_ms,
                    "processingStatus": ProcessingStatus.COMPLETED.value,
                    "completedAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    async def add_error(self, prescription_id: str, error_message: str) -> None:
        """Append an error message and mark as failed."""
        await self.collection.update_one(
            {"prescriptionId": prescription_id},
            {
                "$push": {"processingErrors": error_message},
                "$set": {
                    "processingStatus": ProcessingStatus.FAILED.value,
                    "updatedAt": datetime.utcnow(),
                },
            },
        )

    # ─────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────

    async def delete(self, prescription_id: str) -> None:
        """Delete prescription and its logs."""
        result = await self.collection.delete_one(
            {"prescriptionId": prescription_id}
        )
        if result.deleted_count == 0:
            raise NotFoundError("Prescription")

        # also remove processing logs
        await self.logs.delete_many({"prescriptionId": prescription_id})
        logger.info(f"Deleted prescription {prescription_id}")

    # ─────────────────────────────────────────────
    # PROCESSING LOGS
    # ─────────────────────────────────────────────

    async def log_stage_start(
        self, prescription_id: str, stage: ProcessingStage
    ) -> None:
        """Record the start of a processing stage."""
        log_doc = ProcessingLogDocument(
            prescriptionId=prescription_id,
            stage=stage,
            status="started",
        )
        await self.logs.insert_one(log_doc.to_mongo())

    async def log_stage_complete(
        self,
        prescription_id: str,
        stage: ProcessingStage,
        duration_ms: int,
        metadata: dict | None = None,
    ) -> None:
        """Record the successful completion of a processing stage."""
        now = datetime.utcnow()
        await self.logs.update_one(
            {"prescriptionId": prescription_id, "stage": stage.value, "status": "started"},
            {
                "$set": {
                    "status": "completed",
                    "endTime": now,
                    "durationMs": duration_ms,
                    "metadata": metadata or {},
                }
            },
            upsert=True,
        )

    async def log_stage_failed(
        self,
        prescription_id: str,
        stage: ProcessingStage,
        error_message: str,
    ) -> None:
        """Record a processing stage failure."""
        now = datetime.utcnow()
        await self.logs.update_one(
            {"prescriptionId": prescription_id, "stage": stage.value, "status": "started"},
            {
                "$set": {
                    "status": "failed",
                    "endTime": now,
                    "errorMessage": error_message,
                }
            },
            upsert=True,
        )

    async def get_logs(self, prescription_id: str) -> List[ProcessingLogDocument]:
        """Return all processing logs for a prescription."""
        cursor = self.logs.find({"prescriptionId": prescription_id})
        docs = await cursor.to_list(length=50)
        return [ProcessingLogDocument.from_mongo(d) for d in docs]
