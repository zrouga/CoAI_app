"""
Results router for handling results and logs requests
"""
import json
import time
import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select, col, func
from sse_starlette.sse import EventSourceResponse

from api.models.schemas import ProductResult, LogEntry, TrafficSparkline, DashboardStats, KeywordStatus
from api.services.pipeline_service import running_tasks, task_logs, get_log_file_path, get_keyword_status
from app.database.db import get_session
from app.models.models import DiscoveredProduct, TrafficIntelligence, Keyword
from datetime import datetime

router = APIRouter(tags=["results"])


@router.get("/results/keywords")
async def get_keywords(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """Get all unique keywords"""
    with get_session() as session:
        # Get all unique keywords
        keywords = session.exec(
            select(Keyword.keyword)
            .where(Keyword.keyword != None)
            .where(Keyword.keyword != '')
            .distinct()
            .order_by(Keyword.keyword)
        ).all()
        
        # Apply pagination
        skip = (page - 1) * page_size
        paginated_keywords = keywords[skip:skip + page_size]
        
        return {
            "items": paginated_keywords,
            "total": len(keywords),
            "page": page,
            "page_size": page_size,
            "pages": (len(keywords) + page_size - 1) // page_size
        }


@router.get("/results/products")
async def get_products(
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=5, le=100, description="Items per page"),
    sort_by: str = Query("first_discovered", description="Field to sort by"),
    sort_desc: bool = Query(True, description="Sort in descending order")
):
    """Get products with optional keyword filter"""
    skip = (page - 1) * page_size
    
    with get_session() as session:
        # Build base query for products
        products_query = select(DiscoveredProduct)
        
        # If keyword is provided, filter by it
        if keyword:
            # First, get the keyword record
            keyword_record = session.exec(
                select(Keyword).where(Keyword.keyword == keyword)
            ).first()
            
            if keyword_record:
                products_query = products_query.where(
                    DiscoveredProduct.keyword_id == keyword_record.id
                )
            else:
                # No keyword found, return empty result
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "pages": 0
                }
        
        # Get total count
        if keyword and keyword_record:
            total_count = session.exec(
                select(func.count(DiscoveredProduct.id))
                .where(DiscoveredProduct.keyword_id == keyword_record.id)
            ).one()
        else:
            total_count = session.exec(
                select(func.count(DiscoveredProduct.id))
            ).one()
        
        # Apply sorting
        if sort_by in ["brand_name", "brand_domain", "first_discovered", "estimated_monthly_ad_spend"]:
            sort_col = getattr(DiscoveredProduct, sort_by)
            if sort_desc:
                products_query = products_query.order_by(sort_col.desc())
            else:
                products_query = products_query.order_by(sort_col)
        
        # Apply pagination
        products = session.exec(
            products_query
            .offset(skip)
            .limit(page_size)
        ).all()
        
        # Prepare results with traffic data
        results = []
        for product in products:
            # Get traffic data
            traffic_data = session.exec(
                select(TrafficIntelligence)
                .where(TrafficIntelligence.discovered_product_id == product.id)
            ).first()
            
            # Get keyword name if we have keyword_id
            keyword_name = None
            if product.keyword_id:
                kw = session.exec(
                    select(Keyword).where(Keyword.id == product.keyword_id)
                ).first()
                if kw:
                    keyword_name = kw.keyword
            
            results.append({
                "id": product.id,
                "brand_name": product.brand_name or "Unknown",
                "brand_domain": product.brand_domain,
                "product_page_url": product.product_page_url,
                "keyword": keyword_name,
                "first_discovered": product.first_discovered.isoformat() if product.first_discovered else None,
                "estimated_monthly_ad_spend": product.estimated_monthly_ad_spend,
                "traffic_data": {
                    "monthly_visits": traffic_data.estimated_monthly_website_visits if traffic_data else None,
                    "data_source": traffic_data.data_source if traffic_data else None
                } if traffic_data else None
            })
        
        return {
            "items": results,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "pages": (total_count + page_size - 1) // page_size
        }


@router.get("/results/{keyword}", response_model=List[ProductResult])
async def get_results(
    keyword: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=5, le=100, description="Items per page"),
    sort_by: str = Query("monthly_visits", description="Field to sort by"),
    sort_desc: bool = Query(True, description="Sort in descending order")
):
    """Get the results for a keyword pipeline run"""
    skip = (page - 1) * page_size
    
    with get_session() as session:
        # Get the keyword record
        keyword_record = session.exec(
            select(Keyword).where(Keyword.keyword == keyword)
        ).first()
        
        if not keyword_record:
            raise HTTPException(status_code=404, detail=f"Keyword not found: {keyword}")
        
        # Build base query for products
        products_query = (
            select(DiscoveredProduct)
            .where(DiscoveredProduct.keyword_id == keyword_record.id)
        )
        
        # Get total count for pagination info
        total_count = session.exec(
            select(func.count(DiscoveredProduct.id))
            .where(DiscoveredProduct.keyword_id == keyword_record.id)
        ).one()
        
        # Apply sorting
        if sort_by == "monthly_visits":
            # Special case for monthly_visits which is in related table
            products = session.exec(products_query).all()
            
            # Fetch all traffic data
            product_ids = [p.id for p in products]
            traffic_data = {}
            if product_ids:
                traffic_results = session.exec(
                    select(TrafficIntelligence)
                    .where(TrafficIntelligence.discovered_product_id.in_(product_ids))
                ).all()
                
                for t in traffic_results:
                    traffic_data[t.discovered_product_id] = t
            
            # Sort products by monthly_visits
            def get_visits(product):
                t = traffic_data.get(product.id)
                return t.estimated_monthly_website_visits if t and t.estimated_monthly_website_visits else 0
            
            products.sort(key=get_visits, reverse=sort_desc)
            
            # Apply pagination
            products = products[skip:skip + page_size]
        else:
            # Sort by product fields
            if sort_by in ["brand_name", "brand_domain", "first_discovered"]:
                sort_col = getattr(DiscoveredProduct, sort_by)
                if sort_desc:
                    products_query = products_query.order_by(sort_col.desc())
                else:
                    products_query = products_query.order_by(sort_col)
            
            # Apply pagination
            products = session.exec(
                products_query
                .offset(skip)
                .limit(page_size)
            ).all()
        
        if not products:
            raise HTTPException(status_code=404, detail=f"No results found for keyword: {keyword}")
        
        # Prepare results with traffic data
        results = []
        for product in products:
            # Get traffic data
            traffic_data = session.exec(
                select(TrafficIntelligence)
                .where(TrafficIntelligence.discovered_product_id == product.id)
            ).first()
            
            monthly_visits = None
            data_source = None
            traffic_sparkline = None
            
            if traffic_data:
                monthly_visits = traffic_data.estimated_monthly_website_visits
                data_source = traffic_data.data_source
                
                # Create sparkline data if monthly visits are available
                if monthly_visits:
                    # For demo purposes, create synthetic sparkline data
                    # In a real application, this would come from historical data
                    import random
                    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    values = [max(0, int(monthly_visits * random.uniform(0.7, 1.3))) for _ in range(12)]
                    traffic_sparkline = TrafficSparkline(months=months, values=values)
            
            # Count ads with same domain
            ads_count = session.exec(
                select(func.count(DiscoveredProduct.id))
                .where(
                    DiscoveredProduct.keyword_id == keyword_record.id,
                    DiscoveredProduct.brand_domain == product.brand_domain,
                    DiscoveredProduct.brand_domain != None  # Ensure domain is not null
                )
            ).one() if product.brand_domain else 1
            
            results.append(ProductResult(
                id=product.id,
                brand_name=product.brand_name,
                brand_domain=product.brand_domain,
                product_page_url=product.product_page_url,
                discovery_keyword=keyword,  # Use the keyword string passed in
                monthly_visits=monthly_visits,
                traffic_sparkline=traffic_sparkline,
                ads_count=ads_count,
                data_source=data_source,
                discovered_at=product.first_discovered  # Changed from discovered_at to first_discovered
            ))
        
        return results


@router.get("/logs/{keyword}", response_model=List[LogEntry])
async def get_logs(
    keyword: str,
    limit: int = Query(100, ge=10, le=1000, description="Maximum number of log entries to return")
):
    """Get logs for a keyword pipeline run"""
    # Check if we have logs in memory
    if keyword in task_logs:
        logs = task_logs[keyword][-limit:]
        return [
            LogEntry(
                timestamp=entry.get("timestamp", ""),
                level=entry.get("level", "INFO"),
                message=entry.get("message", ""),
                keyword=entry.get("keyword"),
                context={k: v for k, v in entry.items() if k not in ["timestamp", "level", "message", "keyword"]}
            ) for entry in logs
        ]
    
    # If no logs in memory, try to read from log file
    log_file = get_log_file_path(keyword)
    if log_file.exists():
        with open(log_file, "r") as f:
            logs = []
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    logs.append(LogEntry(
                        timestamp=entry.get("timestamp", ""),
                        level=entry.get("level", "INFO"),
                        message=entry.get("message", ""),
                        keyword=entry.get("keyword"),
                        context={k: v for k, v in entry.items() if k not in ["timestamp", "level", "message", "keyword"]}
                    ))
                    if len(logs) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
            return logs
    
    # No logs found
    raise HTTPException(status_code=404, detail=f"No logs found for keyword: {keyword}")


@router.get("/sse/status/{keyword}")
async def sse_status(keyword: str):
    """Server-sent events endpoint for real-time status updates"""
    async def event_generator():
        initial_status = None
        try:
            if keyword in running_tasks:
                initial_status = running_tasks[keyword]
            else:
                # Try to get status from database
                try:
                    initial_status = await get_keyword_status(keyword)
                except HTTPException:
                    initial_status = KeywordStatus(
                        keyword=keyword,
                        status="not_started"
                    )
            
            # Send initial status
            yield {
                "event": "status",
                "id": str(time.time()),
                "data": json.dumps(initial_status.dict())
            }
            
            # If status is already completed or failed, just return initial status
            if initial_status.status in ["completed", "failed"]:
                return
            
            # Otherwise, keep sending updates until status changes to completed or failed
            last_status = initial_status.status
            while True:
                await asyncio.sleep(1)  # Check every second
                
                current_status = None
                if keyword in running_tasks:
                    current_status = running_tasks[keyword]
                
                if current_status and current_status.status != last_status:
                    yield {
                        "event": "status",
                        "id": str(time.time()),
                        "data": json.dumps(current_status.dict())
                    }
                    last_status = current_status.status
                    
                    # Break if completed or failed
                    if current_status.status in ["completed", "failed"]:
                        break
                        
                # Max duration 15 minutes
                if time.time() - float(initial_status.started_at.timestamp() if initial_status.started_at else time.time()) > 900:
                    break
        except Exception as e:
            # Send error
            yield {
                "event": "error",
                "id": str(time.time()),
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())


@router.delete("/results/{keyword}")
async def delete_results(keyword: str):
    """Delete all results for a keyword"""
    with get_session() as session:
        # Get products for the keyword
        products = session.exec(
            select(DiscoveredProduct)
            .where(DiscoveredProduct.keyword_id == keyword)
        ).all()
        
        if not products:
            raise HTTPException(status_code=404, detail=f"No results found for keyword: {keyword}")
        
        product_ids = [p.id for p in products]
        
        # Delete traffic data
        for product_id in product_ids:
            traffic_data = session.exec(
                select(TrafficIntelligence)
                .where(TrafficIntelligence.discovered_product_id == product_id)
            ).all()
            
            for t in traffic_data:
                session.delete(t)
        
        # Delete products
        for product in products:
            session.delete(product)
        
        session.commit()
        
        # Remove from running tasks and logs
        if keyword in running_tasks:
            del running_tasks[keyword]
        
        if keyword in task_logs:
            del task_logs[keyword]
        
        return {"status": "success", "message": f"Deleted all results for keyword: {keyword}"}


@router.delete("/results")
async def delete_multiple_results(keywords: List[str]):
    """Delete results for multiple keywords"""
    deleted = []
    for keyword in keywords:
        try:
            await delete_results(keyword)
            deleted.append(keyword)
        except HTTPException:
            pass
    
    return {"status": "success", "deleted_keywords": deleted}


@router.delete("/products/{product_id}")
async def delete_product(product_id: int):
    """Soft delete a single product"""
    with get_session() as session:
        product = session.exec(
            select(DiscoveredProduct).where(DiscoveredProduct.id == product_id)
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Delete related traffic data first
        traffic = session.exec(
            select(TrafficIntelligence).where(TrafficIntelligence.discovered_product_id == product_id)
        ).all()
        for t in traffic:
            session.delete(t)
        
        session.delete(product)
        session.commit()
        
        return {"status": "success", "message": f"Product {product_id} deleted"}
