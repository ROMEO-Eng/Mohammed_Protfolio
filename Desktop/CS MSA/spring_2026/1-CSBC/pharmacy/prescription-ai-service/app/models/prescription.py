"""Prescription-related Pydantic models"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PrescriptionUploadRequest(BaseModel):
    """Prescription upload request model"""

    user_id: str = Field(..., description="User ID from Spring Boot")
    priority: str = Field(default="normal", description="Processing priority")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "priority": "normal",
            }
        }


class PrescriptionAnalysisResponse(BaseModel):
    """Response when prescription is uploaded for analysis"""

    prescription_id: str = Field(..., description="Unique prescription ID")
    status: str = Field(default="processing", description="Current processing status")
    estimated_processing_time: int = Field(default=30, description="Estimated time in seconds")
    message: str = Field(default="Prescription uploaded successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "prescription_id": "presc_123abc",
                "status": "processing",
                "estimated_processing_time": 30,
                "message": "Prescription uploaded successfully",
            }
        }


class AnalysisStatusResponse(BaseModel):
    """Response for prescription analysis status check"""

    prescription_id: str
    status: str = Field(description="enum[pending, processing, completed, failed]")
    progress: int = Field(description="Progress percentage (0-100)")
    estimated_time_remaining: Optional[int] = Field(description="Seconds remaining")
    current_stage: Optional[str] = Field(description="Current processing stage")

    class Config:
        json_schema_extra = {
            "example": {
                "prescription_id": "presc_123abc",
                "status": "processing",
                "progress": 75,
                "estimated_time_remaining": 5,
                "current_stage": "product_matching",
            }
        }


class MedicationExtraction(BaseModel):
    """Extracted medication information"""

    drug_name: str = Field(..., description="Drug name")
    dosage: str = Field(..., description="Dosage (e.g., 500mg)")
    frequency: str = Field(..., description="Frequency (e.g., 3 times daily)")
    duration: str = Field(..., description="Duration (e.g., 7 days)")
    instructions: Optional[str] = Field(description="Special instructions")
    confidence: float = Field(description="Confidence score (0-1)")


class ProductMatch(BaseModel):
    """Product matching result"""

    product_id: str = Field(..., description="Product ID from pharmacy DB")
    product_name: str = Field(..., description="Product name")
    price: float = Field(..., description="Price per unit")
    availability: bool = Field(..., description="Is product available")
    match_confidence: float = Field(..., description="Matching confidence (0-1)")


class MedicationWithMatches(MedicationExtraction):
    """Medication with matched products"""

    matched_products: List[ProductMatch] = Field(description="Matched products from catalog")


class PrescriptionResultsResponse(BaseModel):
    """Complete prescription analysis results"""

    prescription_id: str
    status: str
    confidence: float = Field(description="Overall confidence score")
    processing_time: float = Field(description="Processing time in seconds")
    medications: List[MedicationWithMatches] = Field(description="Extracted medications")
    warnings: List[str] = Field(default=[], description="Processing warnings")
    recommendations: List[str] = Field(default=[], description="User recommendations")
    raw_ocr_text: Optional[str] = Field(description="Raw OCR extracted text")

    class Config:
        json_schema_extra = {
            "example": {
                "prescription_id": "presc_123abc",
                "status": "completed",
                "confidence": 0.92,
                "processing_time": 28.5,
                "medications": [
                    {
                        "drug_name": "Amoxicillin",
                        "dosage": "500mg",
                        "frequency": "3 times daily",
                        "duration": "7 days",
                        "instructions": "Take with food",
                        "confidence": 0.95,
                        "matched_products": [
                            {
                                "product_id": "prod_123",
                                "product_name": "Amoxicillin 500mg Capsules",
                                "price": 45.00,
                                "availability": True,
                                "match_confidence": 0.98,
                            }
                        ],
                    }
                ],
                "warnings": [],
                "recommendations": ["Review dosage with pharmacist"],
                "raw_ocr_text": "Amoxicillin 500mg...",
            }
        }
