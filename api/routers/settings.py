"""
Settings management router
"""
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.logging_config import get_logger

router = APIRouter(tags=["settings"])
logger = get_logger("settings")

class SettingsUpdate(BaseModel):
    max_ads: int = None
    poll_interval: int = None
    actor_concurrency: int = None
    min_ad_spend: int = None
    timeout: int = None

@router.get("/settings")
async def get_settings():
    """Get current settings from environment"""
    return {
        "max_ads": int(os.getenv("MAX_ADS", "50")),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "15")),
        "actor_concurrency": int(os.getenv("ACTOR_CONCURRENCY", "5")),
        "min_ad_spend": int(os.getenv("MIN_AD_SPEND", "0")),
        "timeout": int(os.getenv("TIMEOUT", "900"))
    }

@router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings (in memory only for now)"""
    updated = {}
    
    # In production, you'd persist these to a database
    # For now, we'll just update environment variables
    if settings.max_ads is not None:
        os.environ["MAX_ADS"] = str(settings.max_ads)
        updated["max_ads"] = settings.max_ads
    
    if settings.poll_interval is not None:
        os.environ["POLL_INTERVAL"] = str(settings.poll_interval)
        updated["poll_interval"] = settings.poll_interval
    
    if settings.actor_concurrency is not None:
        os.environ["ACTOR_CONCURRENCY"] = str(settings.actor_concurrency)
        updated["actor_concurrency"] = settings.actor_concurrency
        
    if settings.min_ad_spend is not None:
        os.environ["MIN_AD_SPEND"] = str(settings.min_ad_spend)
        updated["min_ad_spend"] = settings.min_ad_spend
        
    if settings.timeout is not None:
        os.environ["TIMEOUT"] = str(settings.timeout)
        updated["timeout"] = settings.timeout
    
    logger.info(f"Settings updated: {updated}")
    return {"status": "success", "updated": updated} 