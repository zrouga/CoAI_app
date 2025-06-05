"""
Pipeline router for handling pipeline execution requests
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models.schemas import RunRequest, KeywordStatus
from api.services.pipeline_service import running_tasks, run_pipeline, get_keyword_status

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
