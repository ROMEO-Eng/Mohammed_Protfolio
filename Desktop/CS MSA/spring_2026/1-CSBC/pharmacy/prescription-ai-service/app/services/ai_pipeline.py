import logging
from app.config.database import MongoDatabase
from app.models.database import ProcessingStatus

logger = logging.getLogger(__name__)


class AIPipeline:
    """
    OCR → LLM → Matching pipeline
    """

    @staticmethod
    async def run(prescription_id: str):
        db = MongoDatabase.db
        if not db:
            raise RuntimeError("DB not connected")

        doc = await db.prescription_analysis.find_one(
            {"prescriptionId": prescription_id}
        )

        if not doc:
            logger.error("Prescription not found")
            return

        try:
            # 1) OCR stage
            await AIPipeline._update_status(db, prescription_id, "processing_ocr")

            ocr_text = await AIPipeline._ocr(doc)

            # 2) LLM stage
            await AIPipeline._update_status(db, prescription_id, "processing_llm")

            structured = await AIPipeline._llm_extract(ocr_text)

            # 3) Matching stage
            await AIPipeline._update_status(db, prescription_id, "processing_matching")

            matches = await AIPipeline._match_products(structured)

            # 4) Save final result
            await db.prescription_analysis.update_one(
                {"prescriptionId": prescription_id},
                {
                    "$set": {
                        "processingStatus": ProcessingStatus.COMPLETED.value,
                        "ocrText": ocr_text,
                        "extractedData": structured,
                        "productMatching": matches,
                    }
                },
            )

            logger.info(f"Pipeline completed: {prescription_id}")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            await AIPipeline._update_status(db, prescription_id, "failed")

    @staticmethod
    async def _ocr(doc):
        # MOCK OCR (replace later with PaddleOCR)
        return "paracetamol 500mg twice daily"

    @staticmethod
    async def _llm_extract(text: str):
        # MOCK LLM (replace with Qwen/Llama later)
        return {
            "medications": [
                {"name": "paracetamol", "dose": "500mg", "frequency": "2/day"}
            ]
        }

    @staticmethod
    async def _match_products(structured):
        # MOCK matching
        return [
            {"drug": "paracetamol", "product_id": "P-001", "confidence": 0.92}
        ]

    @staticmethod
    async def _update_status(db, pid: str, status: str):
        await db.prescription_analysis.update_one(
            {"prescriptionId": pid},
            {"$set": {"processingStatus": status}},
        )