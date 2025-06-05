"""
FastAPI Backend Main Entry Point for Market Intelligence Pipeline

This module assembles the FastAPI application using the modularized components 
from the API structure.
"""
import os
import sys
import structlog
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger("market_intel_api")

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

# Create log directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint that provides API information"""
    return {
        "message": "Market Intelligence API is running",
        "docs_url": "/docs",
        "version": "1.0.0"
    }
