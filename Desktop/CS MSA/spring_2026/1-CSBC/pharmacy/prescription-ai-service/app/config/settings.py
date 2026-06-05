"""Application settings and configuration management"""

from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    # Application
    app_name: str = "Prescription AI Service"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = False

    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "pharmacy_ai"
    mongodb_timeout: int = 5000

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Spring Boot Backend
    spring_boot_base_url: str = "http://localhost:8080"
    spring_boot_api_key: str = ""

    # OCR Settings
    ocr_language: str = "en"
    ocr_use_gpu: bool = False
    ocr_confidence_threshold: float = 0.5

    # LLM Settings
    llm_model_type: str = "qwen"
    qwen_model_name: str = "Qwen/Qwen1.5-7B-Chat"
    llama_model_name: str = "meta-llama/Llama-2-7b-chat-hf"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    # File Storage
    file_upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    retention_days: int = 30

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Monitoring
    prometheus_metrics_enabled: bool = True
    sentry_dsn: Optional[str] = None

    # Medical Databases
    medical_db_path: str = "./data/medical_terminology.json"
    drug_synonyms_path: str = "./data/drug_synonyms.json"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()