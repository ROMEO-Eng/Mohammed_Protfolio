"""MongoDB document models — define exact shapes stored in the database"""

from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    UPLOAD = "upload"
    OCR = "ocr"
    CLEANING = "cleaning"
    LLM = "llm"
    MATCHING = "matching"
    SCORING = "scoring"
    COMPLETED = "completed"


# ─────────────────────────────────────────────
# Sub-documents
# ─────────────────────────────────────────────

class OriginalImageDoc(BaseModel):
    """Stored image metadata"""
    filename: str
    filepath: str
    file_size: int = 0
    mime_type: str = "image/jpeg"


class BoundingBox(BaseModel):
    """OCR bounding box coordinates"""
    x: float
    y: float
    width: float
    height: float
    text: str
    confidence: float


class OCRResultsDoc(BaseModel):
    """OCR extraction results"""
    raw_text: str = ""
    cleaned_text: str = ""
    confidence: float = 0.0
    bounding_boxes: List[BoundingBox] = []
    processing_time_ms: int = 0
    language_detected: str = "en"


class LLMAnalysisDoc(BaseModel):
    """LLM analysis results"""
    model_used: str = ""
    raw_response: str = ""
    processing_time_ms: int = 0
    tokens_used: int = 0
    prompt_version: str = "v1"


class ExtractedMedicationDoc(BaseModel):
    """Single extracted medication"""
    drug_name: str
    dosage: str = ""
    frequency: str = ""
    duration: str = ""
    instructions: str = ""
    confidence: float = 0.0
    raw_text_span: str = ""          # the original text this was found in


class ExtractedDataDoc(BaseModel):
    """All extracted medications from LLM"""
    medications: List[ExtractedMedicationDoc] = []
    extraction_warnings: List[str] = []


class ProductMatchDoc(BaseModel):
    """Product match result"""
    extracted_drug: str
    matched_product_id: str = ""
    matched_product_name: str = ""
    match_confidence: float = 0.0
    price_per_unit: float = 0.0
    is_available: bool = False
    match_method: str = "fuzzy"      # fuzzy / exact / synonym


# ─────────────────────────────────────────────
# Main documents
# ─────────────────────────────────────────────

class PrescriptionDocument(BaseModel):
    """
    Main MongoDB document for prescription analysis.
    Stored in collection: prescription_analysis
    """
    prescription_id: str = Field(..., alias="prescriptionId")
    user_id: str = Field(..., alias="userId")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, alias="uploadTimestamp")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, alias="processingStatus"
    )
    priority: str = "normal"

    # Stage data (filled progressively during processing)
    original_image: Optional[OriginalImageDoc] = Field(None, alias="originalImage")
    ocr_results: Optional[OCRResultsDoc] = Field(None, alias="ocrResults")
    llm_analysis: Optional[LLMAnalysisDoc] = Field(None, alias="llmAnalysis")
    extracted_data: Optional[ExtractedDataDoc] = Field(None, alias="extractedData")
    product_matching: List[ProductMatchDoc] = Field(default=[], alias="productMatching")

    # Final scores
    overall_confidence: float = Field(default=0.0, alias="overallConfidence")
    total_processing_time_ms: int = Field(default=0, alias="totalProcessingTimeMs")

    # Errors & warnings
    processing_errors: List[str] = Field(default=[], alias="processingErrors")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    class Config:
        populate_by_name = True   # allow both snake_case and camelCase
        use_enum_values = True

    def to_mongo(self) -> dict:
        """Convert to MongoDB-compatible dict (camelCase keys)"""
        return self.model_dump(by_alias=True, exclude_none=False)

    @classmethod
    def from_mongo(cls, data: dict) -> "PrescriptionDocument":
        """Build from MongoDB document"""
        if data and "_id" in data:
            data.pop("_id", None)
        return cls(**data)


class ProcessingLogDocument(BaseModel):
    """
    Processing stage log.
    Stored in collection: processing_logs
    """
    prescription_id: str = Field(..., alias="prescriptionId")
    stage: ProcessingStage
    status: str = "started"        # started / completed / failed
    start_time: datetime = Field(default_factory=datetime.utcnow, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    duration_ms: Optional[int] = Field(None, alias="durationMs")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True
        use_enum_values = True

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=False)

    @classmethod
    def from_mongo(cls, data: dict) -> "ProcessingLogDocument":
        if data and "_id" in data:
            data.pop("_id", None)
        return cls(**data)
