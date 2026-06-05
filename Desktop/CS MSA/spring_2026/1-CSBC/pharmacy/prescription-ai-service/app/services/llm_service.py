import json


class LLMService:
    async def extract_medications(self, text: str) -> dict:
        """
        Converts OCR text → structured medications
        """

        # TEMP logic (replace with Qwen later)
        # but NOT mock — rule-based baseline AI

        lines = text.split("\n")

        meds = []

        for line in lines:
            if any(char.isdigit() for char in line):
                meds.append({
                    "raw": line,
                    "name": line.split()[0],
                    "dosage": "unknown",
                    "frequency": "unknown"
                })

        return {
            "medications": meds,
            "raw_text": text
        }