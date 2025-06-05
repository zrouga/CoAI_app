#!/usr/bin/env python3
"""
API Server Entry Point for Market Intelligence Pipeline

This file starts the FastAPI server using Uvicorn
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Run the FastAPI server
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",  # Updated import path to use modular structure
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    print("Server started at http://localhost:8000")
