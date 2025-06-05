"""
FastAPI Backend Main Entry Point for Market Intelligence Pipeline

This module assembles the FastAPI application using the modularized components 
from the API structure.
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import enhanced logging configuration
from api.logging_config import get_logger

# Create logger for this module
logger = get_logger("market_intel_api")

# Import routers
from api.routers import pipeline, results, dashboard
from app.database.db import create_db_and_tables

# Create FastAPI app
app = FastAPI(
    title="Market Intelligence API",
    description="API for the Market Intelligence Pipeline",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables are created
create_db_and_tables()

# Register routers
app.include_router(pipeline.router)
app.include_router(results.router)
app.include_router(dashboard.router)

# Add exception handler for better error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", 
                    url=str(request.url),
                    method=request.method,
                    exception=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)}
    )

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request started", path=request.url.path, method=request.method)
    try:
        response = await call_next(request)
        logger.info(f"Request completed", 
                   path=request.url.path, 
                   method=request.method,
                   status_code=response.status_code)
        return response
    except Exception as e:
        logger.exception(f"Request failed", 
                        path=request.url.path, 
                        method=request.method,
                        error=str(e))
        raise

# Add health check endpoint
@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint for the API"""
    logger.info("Health check requested")
    return {"status": "ok", "service": "market_intel_api"}


@app.get("/", tags=["root"])
async def root():
    """Root endpoint that provides API information"""
    return {
        "message": "Market Intelligence API is running",
        "docs_url": "/docs",
        "version": "1.0.0"
    }
