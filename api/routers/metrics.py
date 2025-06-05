"""
Metrics router for exposing Prometheus-style metrics
"""
import time
from typing import Dict, Any
from datetime import datetime
from collections import defaultdict

from fastapi import APIRouter, Response
from sqlmodel import select, func

from app.database.db import get_session
from app.models.models import Keyword, DiscoveredProduct, TrafficIntelligence
from api.services.pipeline_service import running_tasks

router = APIRouter(prefix="/metrics", tags=["monitoring"])

# Metrics storage
class MetricsCollector:
    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.pipeline_runs = defaultdict(int)
        self.pipeline_success = defaultdict(int)
        self.pipeline_failures = defaultdict(int)
        self.start_time = time.time()
    
    def record_request(self, method: str, path: str, status_code: int, duration: float):
        key = f"{method}_{path}_{status_code}"
        self.request_count[key] += 1
        self.request_duration[key].append(duration)
    
    def record_pipeline_run(self, keyword: str, success: bool):
        self.pipeline_runs[keyword] += 1
        if success:
            self.pipeline_success[keyword] += 1
        else:
            self.pipeline_failures[keyword] += 1

# Global metrics collector
metrics = MetricsCollector()

@router.get("", response_class=Response)
async def get_metrics():
    """
    Export metrics in Prometheus format
    """
    lines = []
    
    # Add header
    lines.append("# HELP uptime_seconds Time since service started")
    lines.append("# TYPE uptime_seconds gauge")
    lines.append(f"uptime_seconds {time.time() - metrics.start_time:.2f}")
    lines.append("")
    
    # Request metrics
    lines.append("# HELP http_requests_total Total number of HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    for key, count in metrics.request_count.items():
        method, path, status = key.split("_", 2)
        lines.append(f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')
    lines.append("")
    
    # Request duration metrics
    lines.append("# HELP http_request_duration_seconds HTTP request latency")
    lines.append("# TYPE http_request_duration_seconds summary")
    for key, durations in metrics.request_duration.items():
        if durations:
            method, path, status = key.split("_", 2)
            avg_duration = sum(durations) / len(durations)
            lines.append(f'http_request_duration_seconds{{method="{method}",path="{path}",status="{status}"}} {avg_duration:.4f}')
    lines.append("")
    
    # Pipeline metrics
    lines.append("# HELP pipeline_runs_total Total number of pipeline runs")
    lines.append("# TYPE pipeline_runs_total counter")
    total_runs = sum(metrics.pipeline_runs.values())
    lines.append(f"pipeline_runs_total {total_runs}")
    lines.append("")
    
    lines.append("# HELP pipeline_success_total Total number of successful pipeline runs")
    lines.append("# TYPE pipeline_success_total counter")
    total_success = sum(metrics.pipeline_success.values())
    lines.append(f"pipeline_success_total {total_success}")
    lines.append("")
    
    lines.append("# HELP pipeline_failures_total Total number of failed pipeline runs")
    lines.append("# TYPE pipeline_failures_total counter")
    total_failures = sum(metrics.pipeline_failures.values())
    lines.append(f"pipeline_failures_total {total_failures}")
    lines.append("")
    
    # Active pipeline runs
    lines.append("# HELP pipeline_active_runs Number of currently running pipelines")
    lines.append("# TYPE pipeline_active_runs gauge")
    active_runs = sum(1 for task in running_tasks.values() if task.status in ["running_step1", "running_step2"])
    lines.append(f"pipeline_active_runs {active_runs}")
    lines.append("")
    
    # Database metrics
    with get_session() as session:
        # Total keywords
        total_keywords = session.exec(select(func.count(Keyword.id))).one()
        lines.append("# HELP db_keywords_total Total number of keywords in database")
        lines.append("# TYPE db_keywords_total gauge")
        lines.append(f"db_keywords_total {total_keywords}")
        lines.append("")
        
        # Total products
        total_products = session.exec(select(func.count(DiscoveredProduct.id))).one()
        lines.append("# HELP db_products_total Total number of products in database")
        lines.append("# TYPE db_products_total gauge")
        lines.append(f"db_products_total {total_products}")
        lines.append("")
        
        # Products with traffic data
        products_with_traffic = session.exec(
            select(func.count(func.distinct(TrafficIntelligence.discovered_product_id)))
        ).one()
        lines.append("# HELP db_products_with_traffic_total Products with traffic data")
        lines.append("# TYPE db_products_with_traffic_total gauge")
        lines.append(f"db_products_with_traffic_total {products_with_traffic}")
        lines.append("")
    
    # Success rate
    if total_runs > 0:
        success_rate = (total_success / total_runs) * 100
        lines.append("# HELP pipeline_success_rate_percentage Pipeline success rate")
        lines.append("# TYPE pipeline_success_rate_percentage gauge")
        lines.append(f"pipeline_success_rate_percentage {success_rate:.2f}")
    
    return Response(content="\n".join(lines), media_type="text/plain")

@router.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check with component status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - metrics.start_time,
        "components": {}
    }
    
    # Check database
    try:
        with get_session() as session:
            session.exec(select(1)).one()
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check active pipelines
    active_pipelines = [
        {"keyword": k, "status": v.status}
        for k, v in running_tasks.items()
        if v.status in ["running_step1", "running_step2"]
    ]
    health_status["components"]["pipeline"] = {
        "status": "healthy",
        "active_runs": len(active_pipelines),
        "details": active_pipelines
    }
    
    # Memory usage (approximate)
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    health_status["components"]["memory"] = {
        "status": "healthy",
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024
    }
    
    return health_status 