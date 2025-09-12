"""
IoT Telemetry Dashboard Backend - Main Application Entry Point

This module initializes the FastAPI application with async capabilities
for handling IoT telemetry data from MQTT sources and serving data via API endpoints.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvloop
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting IoT Telemetry Dashboard Backend")
    
    # Startup logic will be added here:
    # - Initialize database connections
    # - Start MQTT client
    # - Initialize InfluxDB connection
    
    yield
    
    # Shutdown logic will be added here:
    # - Close database connections
    # - Stop MQTT client
    # - Cleanup resources
    
    logger.info("Shutting down IoT Telemetry Dashboard Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="IoT Telemetry Dashboard API",
        description="Backend API for IoT device telemetry data ingestion and visualization",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Frontend dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint for monitoring."""
        return JSONResponse(
            content={"status": "healthy", "service": "iot-backend", "version": "0.1.0"}
        )

    # Root endpoint
    @app.get("/")
    async def root() -> JSONResponse:
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "message": "IoT Telemetry Dashboard API",
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/health",
            }
        )

    # API routes will be added here:
    # app.include_router(organizations_router, prefix="/api/v1")
    # app.include_router(telemetry_router, prefix="/api/v1")
    # app.include_router(auth_router, prefix="/api/v1")

    return app


def main() -> None:
    """Main entry point for running the application."""
    # Use uvloop for better async performance on Unix systems
    if sys.platform != "win32":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    app = create_app()
    
    # Run with uvicorn
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info",
    )


# Create app instance for uvicorn command line usage
app = create_app()


if __name__ == "__main__":
    main()