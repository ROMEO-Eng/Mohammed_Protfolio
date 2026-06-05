"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config.database import MongoDatabase
from app.config.settings import settings
from app.core.exceptions import CustomException


# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan (Startup / Shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Prescription AI Service...")

    try:
        await MongoDatabase.connect()
        logger.info("Application started successfully")
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        raise

    yield

    logger.info("Shutting down Prescription AI Service...")

    try:
        await MongoDatabase.disconnect()
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="AI-powered prescription analysis microservice",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# CORS (⚠️ tighten in production)
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": str(exc) if settings.debug else None,
        },
    )


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.include_router(api_router)


# ─────────────────────────────────────────────
# Root Endpoint
# ─────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Prescription AI Service API",
        "version": settings.app_version,
        "status": "running",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


# ─────────────────────────────────────────────
# Custom OpenAPI
# ─────────────────────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered prescription analysis microservice",
        routes=app.routes,
    )

    openapi_schema["info"]["x-logo"] = {
        "url": "https://your-domain.com/logo.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ─────────────────────────────────────────────
# Local run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )