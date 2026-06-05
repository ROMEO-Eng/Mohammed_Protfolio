"""Analysis and processing-related models"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool = Field(description="Whether request was successful")
    message: str = Field(description="Response message")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[dict] = Field(default=None, description="Error details if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation successful",
                "data": {},
                "error": None,
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    database_connected: bool = Field(description="Database connection status")
    redis_connected: bool = Field(description="Redis connection status")
    timestamp: datetime = Field(description="Check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "database_connected": True,
                "redis_connected": True,
                "timestamp": "2024-06-04T12:00:00Z",
            }
        }


class ProcessingStage(BaseModel):
    """Processing stage tracking"""

    stage: str = Field(description="Processing stage name")
    status: str = Field(description="Stage status")
    start_time: datetime = Field(description="Stage start time")
    end_time: Optional[datetime] = Field(description="Stage end time")
    duration: Optional[float] = Field(description="Duration in seconds")
    error_message: Optional[str] = Field(description="Error if failed")


class MetricsResponse(BaseModel):
    """System metrics response"""

    uptime_seconds: float = Field(description="Service uptime")
    total_prescriptions_processed: int
    average_processing_time: float
    success_rate: float
    active_processing_jobs: int
    database_connection_pool_size: int
    cache_hit_rate: float

    class Config:
        json_schema_extra = {
            "example": {
                "uptime_seconds": 3600,
                "total_prescriptions_processed": 150,
                "average_processing_time": 28.5,
                "success_rate": 0.92,
                "active_processing_jobs": 5,
                "database_connection_pool_size": 10,
                "cache_hit_rate": 0.75,
            }
        }
