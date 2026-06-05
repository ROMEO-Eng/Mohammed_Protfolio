"""Unit tests for database document models."""

import pytest
import uuid

import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "pharmacy_ai_test")

from app.models.database import (
    PrescriptionDocument,
    ProcessingLogDocument,
    ProcessingStatus,
    ProcessingStage,
    OriginalImageDoc,
    OCRResultsDoc,
    ExtractedMedicationDoc,
    ExtractedDataDoc,
    ProductMatchDoc,
)


def _make_doc(**kwargs) -> PrescriptionDocument:
    defaults = dict(
        prescriptionId=str(uuid.uuid4()),
        userId="user-001",
        originalImage=OriginalImageDoc(
            filename="rx.jpg",
            filepath="uploads/rx.jpg",
            file_size=1024,
            mime_type="image/jpeg",
        ),
    )
    defaults.update(kwargs)
    return PrescriptionDocument(**defaults)


class TestPrescriptionDocument:
    def test_default_status_is_pending(self):
        doc = _make_doc()
        assert doc.processing_status == ProcessingStatus.PENDING

    def test_to_mongo_uses_camel_case(self):
        doc = _make_doc()
        d = doc.to_mongo()
        assert "prescriptionId" in d
        assert "userId" in d
        assert "processingStatus" in d
        assert "prescription_id" not in d  # snake_case must NOT appear

    def test_to_mongo_status_is_string(self):
        doc = _make_doc()
        d = doc.to_mongo()
        assert d["processingStatus"] == "pending"

    def test_from_mongo_round_trip(self):
        doc = _make_doc()
        d = doc.to_mongo()
        restored = PrescriptionDocument.from_mongo(d)
        assert restored.prescription_id == doc.prescription_id
        assert restored.user_id == doc.user_id

    def test_from_mongo_strips_id_field(self):
        doc = _make_doc()
        d = doc.to_mongo()
        d["_id"] = "some-mongo-object-id"
        # Should not raise
        restored = PrescriptionDocument.from_mongo(d)
        assert restored.prescription_id == doc.prescription_id

    def test_empty_product_matching_defaults(self):
        doc = _make_doc()
        assert doc.product_matching == []
        assert doc.processing_errors == []
        assert doc.overall_confidence == 0.0


class TestOCRResultsDoc:
    def test_can_be_attached_to_prescription(self):
        ocr = OCRResultsDoc(
            raw_text="Amoxicillin 500mg 3x daily 7 days",
            confidence=0.95,
            processing_time_ms=1200,
        )
        doc = _make_doc()
        doc.ocr_results = ocr
        d = doc.to_mongo()
        assert d["ocrResults"]["rawText"] == "Amoxicillin 500mg 3x daily 7 days"
        assert d["ocrResults"]["confidence"] == 0.95


class TestExtractedDataDoc:
    def test_multiple_medications(self):
        data = ExtractedDataDoc(
            medications=[
                ExtractedMedicationDoc(
                    drug_name="Amoxicillin",
                    dosage="500mg",
                    frequency="3 times daily",
                    duration="7 days",
                    confidence=0.95,
                ),
                ExtractedMedicationDoc(
                    drug_name="Ibuprofen",
                    dosage="400mg",
                    frequency="twice daily",
                    duration="3 days",
                    confidence=0.88,
                ),
            ]
        )
        assert len(data.medications) == 2
        assert data.medications[0].drug_name == "Amoxicillin"


class TestProductMatchDoc:
    def test_default_availability_false(self):
        m = ProductMatchDoc(
            extracted_drug="Amoxicillin",
            matched_product_id="prod-123",
            matched_product_name="Amoxicillin 500mg Caps",
            match_confidence=0.98,
            price_per_unit=45.0,
        )
        assert m.is_available is False
        assert m.match_method == "fuzzy"


class TestProcessingLogDocument:
    def test_to_mongo_uses_camel_case(self):
        log = ProcessingLogDocument(
            prescriptionId="presc-001",
            stage=ProcessingStage.OCR,
        )
        d = log.to_mongo()
        assert "prescriptionId" in d
        assert d["stage"] == "ocr"
        assert d["status"] == "started"
