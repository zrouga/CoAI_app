"""
End-to-end test for the complete pipeline flow
Tests the full workflow from API request to database results
"""
import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlmodel import select

from app.database.db import get_session, create_db_and_tables
from app.models.models import Keyword, DiscoveredProduct, TrafficIntelligence
from api.main import app


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is set up before tests"""
    create_db_and_tables()
    
    # Clean up any existing test data
    with get_session() as session:
        # Delete test keyword data if it exists
        test_keyword = session.exec(
            select(Keyword).where(Keyword.keyword == "atlas_test")
        ).first()
        
        if test_keyword:
            # Delete related products and traffic data
            products = session.exec(
                select(DiscoveredProduct).where(
                    DiscoveredProduct.keyword_id == test_keyword.id
                )
            ).all()
            
            for product in products:
                traffic_data = session.exec(
                    select(TrafficIntelligence).where(
                        TrafficIntelligence.discovered_product_id == product.id
                    )
                ).all()
                
                for traffic in traffic_data:
                    session.delete(traffic)
                
                session.delete(product)
            
            session.delete(test_keyword)
            session.commit()


@pytest.mark.asyncio
async def test_full_pipeline_e2e(async_client: AsyncClient):
    """Test the complete pipeline from API call to database results"""
    
    # Step 1: Submit pipeline run request
    response = await async_client.post(
        "/pipeline/run",
        json={
            "keyword": "atlas_test",
            "max_ads": 5,  # Small number for faster test
        }
    )
    
    assert response.status_code == 200
    initial_status = response.json()
    assert initial_status["keyword"] == "atlas_test"
    assert initial_status["status"] in ["not_started", "running_step1"]
    
    # Step 2: Connect to SSE stream for real-time updates
    pipeline_events = []
    
    async def collect_sse_events():
        """Collect SSE events from the stream"""
        async with async_client.stream("GET", f"/pipeline/stream/atlas_test") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    pipeline_events.append({"type": event_type, "timestamp": datetime.now()})
                    
                    # Stop collecting after pipeline completes or errors
                    if event_type in ["pipeline_complete", "pipeline_error"]:
                        break
    
    # Start SSE collection in background
    sse_task = asyncio.create_task(collect_sse_events())
    
    # Step 3: Poll status endpoint while pipeline runs
    max_wait_time = 120  # 2 minutes timeout
    start_time = time.time()
    final_status = None
    
    while time.time() - start_time < max_wait_time:
        response = await async_client.get(f"/pipeline/status/atlas_test")
        
        if response.status_code == 200:
            status = response.json()
            
            # Check for completion
            if status["status"] in ["completed", "failed"]:
                final_status = status
                break
        
        await asyncio.sleep(2)  # Poll every 2 seconds
    
    # Cancel SSE collection if still running
    sse_task.cancel()
    try:
        await sse_task
    except asyncio.CancelledError:
        pass
    
    # Step 4: Verify pipeline completed successfully
    assert final_status is not None, "Pipeline did not complete within timeout"
    assert final_status["status"] == "completed", f"Pipeline failed: {final_status.get('errors', [])}"
    
    # Verify metrics
    assert final_status["step1_products"] > 0, "No products discovered in Step 1"
    assert final_status["step2_enriched"] >= 0, "Step 2 enrichment count missing"
    
    # Step 5: Verify database records
    with get_session() as session:
        # Check keyword record
        keyword = session.exec(
            select(Keyword).where(Keyword.keyword == "atlas_test")
        ).first()
        
        assert keyword is not None, "Keyword record not created"
        assert keyword.status == "completed"
        assert keyword.total_products_discovered == final_status["step1_products"]
        
        # Check products
        products = session.exec(
            select(DiscoveredProduct).where(
                DiscoveredProduct.keyword_id == keyword.id
            )
        ).all()
        
        assert len(products) >= 1, "No products saved to database"
        assert len(products) == final_status["step1_products"], "Product count mismatch"
        
        # Verify product data
        for product in products:
            assert product.product_page_url is not None
            assert product.brand_domain is not None
            assert product.first_discovered is not None
        
        # Check traffic data
        traffic_records = session.exec(
            select(TrafficIntelligence).join(DiscoveredProduct).where(
                DiscoveredProduct.keyword_id == keyword.id
            )
        ).all()
        
        assert len(traffic_records) >= 1, "No traffic data saved"
        assert len(traffic_records) == final_status["step2_enriched"], "Traffic data count mismatch"
    
    # Step 6: Test results API endpoint
    response = await async_client.get(f"/results/products?keyword=atlas_test")
    assert response.status_code == 200
    
    products_response = response.json()
    assert products_response["total"] == final_status["step1_products"]
    assert len(products_response["items"]) > 0
    
    # Verify product response structure
    first_product = products_response["items"][0]
    assert "id" in first_product
    assert "product_page_url" in first_product
    assert "brand_domain" in first_product
    assert "traffic_data" in first_product
    
    # Step 7: Verify metrics endpoint
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    
    metrics_text = response.text
    assert "pipeline_runs_total" in metrics_text
    assert "pipeline_success_total" in metrics_text
    assert "db_products_total" in metrics_text
    
    # Step 8: Verify SSE events were received
    assert len(pipeline_events) > 0, "No SSE events received"
    
    event_types = [e["type"] for e in pipeline_events]
    assert "pipeline_start" in event_types or "connected" in event_types
    assert "pipeline_complete" in event_types or "pipeline_error" in event_types


@pytest.mark.asyncio
async def test_pipeline_error_handling(async_client: AsyncClient):
    """Test pipeline error handling with invalid keyword"""
    
    # Submit pipeline with problematic keyword
    response = await async_client.post(
        "/pipeline/run",
        json={
            "keyword": "",  # Empty keyword should fail
            "max_ads": 5,
        }
    )
    
    # API should still accept the request
    assert response.status_code in [200, 422]  # Either accepts or validates


@pytest.mark.asyncio
async def test_concurrent_pipeline_runs(async_client: AsyncClient):
    """Test handling of concurrent pipeline runs for same keyword"""
    
    # Start first pipeline
    response1 = await async_client.post(
        "/pipeline/run",
        json={
            "keyword": "concurrent_test",
            "max_ads": 3,
        }
    )
    assert response1.status_code == 200
    
    # Immediately try to start another for same keyword
    response2 = await async_client.post(
        "/pipeline/run",
        json={
            "keyword": "concurrent_test",
            "max_ads": 3,
        }
    )
    
    # Should return existing status, not start new pipeline
    assert response2.status_code == 200
    status2 = response2.json()
    assert status2["status"] in ["running_step1", "running_step2"] 