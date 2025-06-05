"""
Dashboard router for handling dashboard analytics requests
"""
from fastapi import APIRouter
from sqlmodel import select, col, func
from datetime import datetime

from api.models.schemas import DashboardStats
from app.database.db import get_session
from app.models.models import DiscoveredProduct, TrafficIntelligence

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics"""
    with get_session() as session:
        # Get total products
        total_products = session.exec(
            select(func.count(DiscoveredProduct.id))
        ).one()
        
        # Get total unique domains
        unique_domains = session.exec(
            select(DiscoveredProduct.brand_domain)
            .where(DiscoveredProduct.brand_domain != None)
            .distinct()
        ).all()
        
        # Get total enriched domains
        enriched_domains = session.exec(
            select(func.count(TrafficIntelligence.id))
            .where(TrafficIntelligence.monthly_visits != None)
        ).one()
        
        # Get total keywords
        from app.models.models import Keyword
        
        total_keywords = session.exec(
            select(Keyword.keyword)
            .join(DiscoveredProduct, Keyword.id == DiscoveredProduct.keyword_id)
            .distinct()
        ).all()
        
        # Get recent keywords (last 5)
        recent_data = session.exec(
            select(Keyword.keyword, DiscoveredProduct.first_discovered)
            .join(DiscoveredProduct, Keyword.id == DiscoveredProduct.keyword_id)
            .distinct()
            .order_by(col(DiscoveredProduct.first_discovered).desc())
            .limit(5)
        ).all()
        
        recent_keywords = [k[0] for k in recent_data]
        
        return DashboardStats(
            total_products=total_products,
            unique_domains=len(unique_domains),
            enriched_domains=enriched_domains,
            total_keywords=len(total_keywords),
            recent_keywords=recent_keywords,
        )


@router.get("/keywords")
async def get_keywords():
    """Get all keywords that have been processed"""
    with get_session() as session:
        from app.models.models import Keyword
        
        keywords = session.exec(
            select(Keyword.keyword)
            .join(DiscoveredProduct, Keyword.id == DiscoveredProduct.keyword_id)
            .distinct()
        ).all()
        
        return keywords


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
