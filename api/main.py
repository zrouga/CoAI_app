"""
FastAPI Backend Main Entry Point for Market Intelligence Pipeline

This module assembles the FastAPI application using the modularized components 
from the API structure.
"""
import os
import sys
import time
import uuid
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import enhanced logging configuration
from api.logging_config import get_logger, LogContext

# Create logger for this module
logger = get_logger("market_intel_api")

# Import routers
from api.routers import pipeline, results, dashboard, metrics, settings
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
app.include_router(settings.router)
app.include_router(metrics.router)

# Add exception handler for better error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.exception(
        "Unhandled exception",
        extra={
            "url": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": str(exc),
            "correlation_id": correlation_id
        }
    )

# Add request logging middleware with correlation ID
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Generate correlation ID for this request
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    # Start timer
    start_time = time.time()
    
    # Use logging context for correlation ID
    with LogContext(correlation_id=correlation_id):
        logger.info(
            "Request started",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            from api.routers.metrics import metrics
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            logger.info(
                "Request completed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3)
                }
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failed request
            from api.routers.metrics import metrics
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration=duration
            )
            
            logger.exception(
                "Request failed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_seconds": round(duration, 3),
                    "error": str(e)
                }
            )
            raise

# Add health check endpoint
@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint for the API"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "market_intel_api",
        "version": "1.0.0"
    }


# Frontend logging endpoint
@app.post("/log")
async def log_frontend_error(request: Request):
    """Log errors from frontend"""
    try:
        body = await request.json()
        logger.error(
            f"Frontend error: {body.get('message')}",
            extra={
                "context": body.get('context'),
                "stack": body.get('stack'),
                "frontend": True,
                "correlation_id": getattr(request.state, "correlation_id", None)
            }
        )
        return {"status": "logged"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/", tags=["root"])
async def root():
    """Root endpoint that provides API information"""
    return {
        "message": "Market Intelligence API is running",
        "docs_url": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "pipeline": "/pipeline",
            "results": "/results", 
            "dashboard": "/dashboard",
            "metrics": "/metrics",
            "health": "/health"
        }
    }
