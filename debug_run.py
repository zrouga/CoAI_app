#!/usr/bin/env python3
"""
Debug Run Script for Market Intelligence Application

This script runs both the backend API and frontend with enhanced debugging
and monitoring features to help identify and troubleshoot any issues.
"""

import os
import sys
import time
import logging
import subprocess
import threading
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/debug_run.log", mode="a")
    ]
)
logger = logging.getLogger("debug_runner")

# Ensure log directory exists
Path("logs").mkdir(exist_ok=True)

# Function to run a command with live output streaming
def run_command_with_output(command, cwd=None, env=None, log_prefix=""):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )
    
    logger.info(f"{log_prefix} Process started with PID: {process.pid}")
    
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        logger.info(f"{log_prefix} {line.rstrip()}")
        
    return_code = process.wait()
    if return_code != 0:
        logger.error(f"{log_prefix} Process exited with code {return_code}")
    else:
        logger.info(f"{log_prefix} Process completed successfully")
    
    return return_code

# Function to start the backend API server
def start_backend():
    logger.info("Starting backend API server...")
    
    # Set environment variables for enhanced debugging
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # Ensure Python output is unbuffered
    env["LOGLEVEL"] = "DEBUG"      # Set log level to DEBUG
    
    cmd = [sys.executable, "app_server.py"]
    
    return run_command_with_output(
        cmd, 
        cwd=os.path.abspath("."), 
        env=env,
        log_prefix="[BACKEND]"
    )

# Function to start the frontend
def start_frontend():
    logger.info("Starting frontend development server...")
    
    # Wait for backend to initialize
    time.sleep(5)
    
    # Set environment variables
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = "http://localhost:8000"
    
    cmd = ["npm", "run", "dev"]
    
    return run_command_with_output(
        cmd, 
        cwd=os.path.abspath("frontend"),
        env=env,
        log_prefix="[FRONTEND]"
    )

# Start both services in separate threads
def main():
    logger.info("=== Starting Market Intelligence App in Debug Mode ===")
    
    backend_thread = threading.Thread(target=start_backend)
    frontend_thread = threading.Thread(target=start_frontend)
    
    try:
        backend_thread.start()
        frontend_thread.start()
        
        logger.info("Services started. Access the frontend at http://localhost:3000")
        logger.info("API documentation is available at http://localhost:8000/docs")
        logger.info("Logs are being written to the logs/ directory")
        logger.info("Press Ctrl+C to stop all services")
        
        # Wait for threads to complete (or KeyboardInterrupt)
        backend_thread.join()
        frontend_thread.join()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Stopping services...")
        sys.exit(0)

if __name__ == "__main__":
    main()
