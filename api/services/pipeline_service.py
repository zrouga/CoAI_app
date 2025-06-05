"""
Pipeline service module for handling the execution of the market intelligence pipeline
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlmodel import select

from api.models.schemas import KeywordStatus, PipelineStatus, RunRequest
from api.services.event_stream import PipelineEventEmitter
from api.logging_config import get_logger
from app.database.db import get_session
from app.models.models import DiscoveredProduct, TrafficIntelligence, Keyword as KeywordModel
from app.core.step1_keyword_scraper import run_scraper
from app.core.free_traffic_analyzer import get_traffic_data, save_traffic_data

logger = get_logger("pipeline_service")

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
    # Create event emitter for real-time updates
    emitter = PipelineEventEmitter(keyword)
    
    try:
        # Initialize status
        status = running_tasks[keyword]
        status.status = PipelineStatus.RUNNING_STEP1
        status.started_at = datetime.now()
        
        # Emit pipeline start event
        await emitter.emit_start(config.dict())
        
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
            extra={
                "keyword": keyword,
                **{k: v for k, v in config.dict().items() if k != "keyword"}
            }
        )
        
        # First, create or get the Keyword record in the database
        keyword_id = None
        
        with get_session() as session:
            # Check if keyword already exists
            existing_keyword = session.exec(
                select(KeywordModel).where(KeywordModel.keyword == keyword)
            ).first()
            
            if existing_keyword:
                keyword_id = existing_keyword.id
                await emitter.emit_log("info", f"Using existing keyword record: {keyword}, id={keyword_id}")
            else:
                # Create new keyword record
                new_keyword = KeywordModel(keyword=keyword)
                session.add(new_keyword)
                session.commit()
                session.refresh(new_keyword)
                keyword_id = new_keyword.id
                await emitter.emit_log("info", f"Created new keyword record: {keyword}, id={keyword_id}")

        # STEP 1: Scrape Facebook ads
        await emitter.emit_step_start(1, "Facebook Ad Scraping", f"Scrape ads for keyword '{keyword}' via Apify API")
        
        step1_start = time.time()
        scraped_products = []
        
        try:
            # Run scraper synchronously in executor to not block event loop
            scraped_products = await asyncio.get_event_loop().run_in_executor(
                None,
                run_scraper,
                keyword,
                config.max_ads,
                300,  # timeout_seconds
                None,  # save_callback
                keyword_id,  # keyword_id
                None,  # filters
                False  # enrich_traffic
            )
            
            step1_duration = time.time() - step1_start
            status.step1_products = len(scraped_products)
            
            await emitter.emit_step_complete(1, {
                "products_found": len(scraped_products),
                "duration_seconds": round(step1_duration, 1)
            })
            
        except Exception as e:
            await emitter.emit_error(f"Step 1 failed: {str(e)}", step=1)
            raise
        
        if not scraped_products:
            await emitter.emit_log("warning", "No products found. Pipeline complete.")
            status.status = PipelineStatus.COMPLETED
            status.completed_at = datetime.now()
            await emitter.emit_pipeline_complete({
                "products_discovered": 0,
                "traffic_enriched": 0
            })
            return
        
        # Get recent products from database
        with get_session() as session:
            from datetime import timedelta
            recent_cutoff = datetime.now() - timedelta(minutes=5)
            recent_products = session.exec(
                select(DiscoveredProduct)
                .where(DiscoveredProduct.first_discovered >= recent_cutoff)
                .limit(config.max_ads)
            ).all()
            
            await emitter.emit_log("info", f"Found {len(recent_products)} recent products for enrichment")
        
        # STEP 2: Enrich with traffic data
        await emitter.emit_step_start(2, "Traffic Data Enrichment", f"Enrich {len(recent_products[:10])} domains with traffic data")
        
        step2_start = time.time()
        step2_enriched = 0
        
        for i, product in enumerate(recent_products[:10], 1):  # Limit to 10 for speed
            domain = product.brand_domain
            
            try:
                await emitter.emit_step_progress(2, i-1, len(recent_products[:10]), f"Processing {domain}")
                
                # Run traffic analysis in executor
                visits, source = await asyncio.get_event_loop().run_in_executor(
                    None,
                    get_traffic_data,
                    domain
                )
                
                # Save traffic data
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    save_traffic_data,
                    domain,
                    product.id,
                    visits,
                    source
                )
                
                if visits:
                    await emitter.emit_log("info", f"Traffic data for {domain}: {visits:,} monthly visits (via {source})")
                    step2_enriched += 1
                else:
                    await emitter.emit_log("warning", f"No traffic data available for {domain}: {source}")
            
            except Exception as e:
                await emitter.emit_log("error", f"Traffic lookup failed for {domain}: {e}")
                status.errors.append(f"Traffic lookup failed for {domain}: {e}")
        
        step2_duration = time.time() - step2_start
        status.step2_enriched = step2_enriched
        
        await emitter.emit_step_complete(2, {
            "domains_enriched": step2_enriched,
            "domains_processed": len(recent_products[:10]),
            "duration_seconds": round(step2_duration, 1)
        })
        
        # Update final status
        status.completed_at = datetime.now()
        status.duration_seconds = (status.completed_at - status.started_at).total_seconds()
        status.status = PipelineStatus.COMPLETED
        
        # Emit completion event
        await emitter.emit_pipeline_complete({
            "products_discovered": status.step1_products,
            "traffic_enriched": status.step2_enriched,
            "total_duration_seconds": round(status.duration_seconds, 1)
        })
        
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
        logger.info("pipeline_complete", extra={
            "keyword": keyword, 
            "step1_products": status.step1_products,
            "step2_enriched": status.step2_enriched,
            "duration_seconds": status.duration_seconds
        })

    except Exception as e:
        # Handle errors and update status
        error_msg = f"Pipeline failed: {str(e)}"
        
        # Emit error event
        await emitter.emit_error(error_msg)
        
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
        logger.error("pipeline_error", extra={"keyword": keyword, "error": str(e)})


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
