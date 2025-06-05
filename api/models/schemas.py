"""
API schemas for the Market Intelligence Pipeline API
Contains Pydantic models for request/response validation
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

# Pipeline status enum
class PipelineStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING_STEP1 = "running_step1"
    COMPLETED_STEP1 = "completed_step1"
    RUNNING_STEP2 = "running_step2" 
    COMPLETED_STEP2 = "completed_step2"
    COMPLETED = "completed"
    FAILED = "failed"

# Request model for running pipeline
class RunRequest(BaseModel):
    keyword: str
    
    # Apify settings
    max_ads: int = Field(default=50, ge=1, le=500, description="Maximum number of ads to scrape")
    apify_actor: str = Field(default="igolaizola/facebook-ad-library-scraper", description="Apify actor to use")
    country_code: str = Field(default="US", description="Country code for ad targeting")
    poll_interval_seconds: int = Field(default=15, ge=5, le=60, description="Apify poll interval in seconds")
    apify_concurrency: int = Field(default=5, ge=1, le=20, description="Number of concurrent Apify tasks")
    apify_timeout_seconds: int = Field(default=900, ge=60, le=3600, description="Apify timeout in seconds")
    min_ad_spend_usd: int = Field(default=0, ge=0, description="Minimum ad spend in USD")
    
    # Traffic/ScraperAPI settings
    scraper_api_key: Optional[str] = Field(default=None, description="ScraperAPI key (will use .env if not provided)")
    max_domains_per_minute: int = Field(default=40, ge=1, le=100, description="Maximum domains to process per minute")
    domain_batch_size: int = Field(default=15, ge=1, le=50, description="Number of domains to process in each batch")
    retry_attempts: int = Field(default=2, ge=0, le=5, description="Number of retry attempts for traffic data")
    cache_ttl_days: int = Field(default=30, ge=1, le=90, description="Cache TTL in days for traffic data")
    html_fallback_enabled: bool = Field(default=True, description="Whether to fall back to HTML scraping")
    
    # General settings
    log_level: str = Field(default="INFO", description="Log level for the pipeline")
    dry_run_mode: bool = Field(default=False, description="If true, skips database writes")

# Status response model
class KeywordStatus(BaseModel):
    keyword: str
    status: PipelineStatus
    step1_products: int = 0
    step2_enriched: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    errors: List[str] = []

# Sparkline data for traffic (12 months)
class TrafficSparkline(BaseModel):
    months: List[str] = []
    values: List[Optional[int]] = []

# Product result model
class ProductResult(BaseModel):
    id: int
    brand_name: Optional[str] = None
    brand_domain: Optional[str] = None
    product_page_url: str
    discovery_keyword: str
    monthly_visits: Optional[int] = None
    traffic_sparkline: Optional[TrafficSparkline] = None
    ads_count: int = 1
    data_source: Optional[str] = None
    discovered_at: datetime

# Dashboard stats model
class DashboardStats(BaseModel):
    total_products: int = 0
    unique_domains: int = 0
    enriched_domains: int = 0
    total_keywords: int = 0
    recent_keywords: List[str] = []

# Log entry model
class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    keyword: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
