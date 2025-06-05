"""
Pipeline service module for handling the execution of the market intelligence pipeline
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import structlog
from sqlmodel import select

from api.models.schemas import KeywordStatus, PipelineStatus, RunRequest
from app.database.db import get_session
from app.models.models import DiscoveredProduct, TrafficIntelligence
from run_one_keyword import run_single_keyword_pipeline

logger = structlog.get_logger("pipeline_service")

# Store running tasks and their status
running_tasks: Dict[str, KeywordStatus] = {}
task_logs: Dict[str, List[Dict[str, Any]]] = {}

# Create log directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


def get_log_file_path(keyword: str) -> Path:
    """Get the log file path for a keyword"""
    return log_dir / f"{keyword}_{datetime.now().strftime('%Y%m%d')}.log"


def log_to_file(keyword: str, entry: Dict[str, Any]):
    """Log an entry to a keyword-specific file"""
    log_file = get_log_file_path(keyword)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also store in memory for recent logs
    if keyword not in task_logs:
        task_logs[keyword] = []
    
    task_logs[keyword].append(entry)
    # Keep only the 1000 most recent log entries
    if len(task_logs[keyword]) > 1000:
        task_logs[keyword] = task_logs[keyword][-1000:]


async def run_pipeline(keyword: str, config: RunRequest):
    """
    Run the pipeline in the background and update status
    """
    try:
        # Initialize status
        status = running_tasks[keyword]
        status.status = PipelineStatus.RUNNING_STEP1
        status.started_at = datetime.now()
        
        # Log start
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Starting pipeline for keyword: {keyword}",
            "keyword": keyword,
            "config": config.dict()
        }
        log_to_file(keyword, log_entry)
        logger.info(
            "pipeline_start",
            keyword=keyword,
            **{k: v for k, v in config.dict().items() if k != "keyword"}
        )

        # Run pipeline with our config 
        # Currently run_single_keyword_pipeline only accepts keyword and max_ads
        # We can extend it later to accept more parameters
        results = run_single_keyword_pipeline(keyword, config.max_ads)
        
        # Update status with results
        status.step1_products = results.get("step1_products", 0)
        status.step2_enriched = results.get("step2_enriched", 0)
        status.completed_at = datetime.now()
        if status.started_at:
            status.duration_seconds = (status.completed_at - status.started_at).total_seconds()
        status.errors = results.get("errors", [])
        status.status = PipelineStatus.COMPLETED
        
        # Log completion
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Pipeline completed for keyword: {keyword}",
            "keyword": keyword,
            "results": {
                "step1_products": status.step1_products,
                "step2_enriched": status.step2_enriched,
                "duration_seconds": status.duration_seconds
            }
        }
        log_to_file(keyword, log_entry)
        logger.info("pipeline_complete", 
                    keyword=keyword, 
                    step1_products=status.step1_products,
                    step2_enriched=status.step2_enriched,
                    duration_seconds=status.duration_seconds)

    except Exception as e:
        # Handle errors and update status
        error_msg = f"Pipeline failed: {str(e)}"
        
        if keyword in running_tasks:
            status = running_tasks[keyword]
            status.status = PipelineStatus.FAILED
            status.errors.append(error_msg)
            status.completed_at = datetime.now()
            if status.started_at:
                status.duration_seconds = (status.completed_at - status.started_at).total_seconds()
        
        # Log error
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "message": error_msg,
            "keyword": keyword,
            "error": str(e)
        }
        log_to_file(keyword, log_entry)
        logger.error("pipeline_error", keyword=keyword, error=str(e))


async def get_keyword_status(keyword: str) -> Optional[KeywordStatus]:
    """
    Get the status of a keyword pipeline, either from memory or reconstructed from the database
    """
    if keyword in running_tasks:
        return running_tasks[keyword]
    
    # Check if we have any data for this keyword in the database
    with get_session() as session:
        products = session.exec(
            select(DiscoveredProduct)
            .where(DiscoveredProduct.discovery_keyword == keyword)
        ).all()
        
        if products:
            # Create status from database
            status = KeywordStatus(
                keyword=keyword,
                status=PipelineStatus.COMPLETED,
                step1_products=len(products),
                started_at=min([p.discovered_at for p in products]),
                completed_at=max([p.discovered_at for p in products])
            )
            
            # Count enriched products
            enriched_count = 0
            for product in products:
                traffic_data = session.exec(
                    select(TrafficIntelligence)
                    .where(TrafficIntelligence.discovered_product_id == product.id)
                ).first()
                if traffic_data and traffic_data.monthly_visits:
                    enriched_count += 1
            
            status.step2_enriched = enriched_count
            
            # Calculate duration
            if status.started_at and status.completed_at:
                status.duration_seconds = (status.completed_at - status.started_at).total_seconds()
            
            running_tasks[keyword] = status
            return status
    
    return None
