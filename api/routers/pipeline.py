"""
Pipeline router for handling pipeline execution requests
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.models.schemas import RunRequest, KeywordStatus
from api.services.pipeline_service import running_tasks, run_pipeline, get_keyword_status
from api.services.event_stream import event_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=KeywordStatus)
async def run_keyword_pipeline(request: RunRequest, background_tasks: BackgroundTasks):
    """Run the pipeline for a keyword with specified configuration"""
    keyword = request.keyword
    
    # Check if pipeline is already running for this keyword
    if keyword in running_tasks and running_tasks[keyword].status in [
        "running_step1", "running_step2"
    ]:
        return running_tasks[keyword]

    # Initialize status
    status = KeywordStatus(
        keyword=keyword,
        status="not_started",
        started_at=None
    )
    running_tasks[keyword] = status
    
    # Start pipeline in background
    background_tasks.add_task(run_pipeline, keyword, request)
    
    # Update status to running
    status.status = "running_step1"
    
    return status


@router.get("/status/{keyword}", response_model=KeywordStatus)
async def get_status(keyword: str):
    """Get the status of a keyword pipeline run"""
    status = await get_keyword_status(keyword)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"No data found for keyword: {keyword}")
    
    return status


@router.get("/stream/{keyword}")
async def stream_pipeline_events(keyword: str, request: Request):
    """Stream real-time pipeline events via Server-Sent Events (SSE)"""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for the client"""
        connection_id = str(uuid.uuid4())
        queue = await event_manager.add_connection(keyword, connection_id)
        
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {{\"connection_id\": \"{connection_id}\"}}\n\n"
            
            # Stream events from queue
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                    
                try:
                    # Wait for event with timeout to allow periodic disconnect checks
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f"event: ping\ndata: {{\"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                    
        except Exception as e:
            # Log error but don't expose internals to client
            logger.error(f"SSE stream error", keyword=keyword, error=str(e))
            yield f"event: error\ndata: {{\"error\": \"Stream error occurred\"}}\n\n"
            
        finally:
            # Clean up connection
            await event_manager.remove_connection(keyword, connection_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
