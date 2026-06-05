from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.drug_matcher import DrugMatcher
from app.config.database import MongoDatabase


class PrescriptionPipeline:

    def __init__(self):
        self.ocr = OCRService()
        self.llm = LLMService()

    async def run(self, image_bytes: bytes, prescription_id: str):

        db = MongoDatabase.db
        matcher = DrugMatcher(db)

        # 1. OCR
        text = await self.ocr.extract_text(image_bytes)

        # 2. LLM extraction
        structured = await self.llm.extract_medications(text)

        # 3. Drug matching
        matches = await matcher.match(structured["medications"])

        # 4. save result
        await db.prescription_analysis.update_one(
            {"prescriptionId": prescription_id},
            {
                "$set": {
                    "ocrText": text,
                    "llmData": structured,
                    "matches": matches,
                    "status": "completed"
                }
            }
        )

        return matches