#!/usr/bin/env python3
"""
End-to-End validation test for the Market Intelligence Pipeline
Tests that the keyword pipeline runs correctly and saves products
"""

import requests
import time
import pytest
import json
import sys
from datetime import datetime

# API Base URL
API_BASE = "http://localhost:8000"

def test_keyword_pipeline():
    """Test the full keyword pipeline flow from submission to completion"""
    
    print(f"\n🚀 Starting pipeline test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Run pipeline with test keyword
    test_keyword = "windsurf_test"
    print(f"Step 1: Running pipeline for keyword '{test_keyword}'")
    
    response = requests.post(
        f"{API_BASE}/pipeline/run", 
        json={"keyword": test_keyword}
    )
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to start pipeline. Status code: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    result = response.json()
    
    print(f"Pipeline started with status: {result['status']}")
    
    # 2. Poll for completion
    print("\nStep 2: Polling for pipeline completion")
    max_polls = 30  # Maximum number of polling attempts
    poll_interval = 2  # Seconds between polls
    
    for i in range(max_polls):
        response = requests.get(f"{API_BASE}/pipeline/status/{test_keyword}")
        
        if response.status_code != 200:
            print(f"❌ ERROR: Failed to get status. Status code: {response.status_code}")
            print(response.text)
            sys.exit(1)
            
        status_data = response.json()
        current_status = status_data["status"]
        
        print(f"Poll {i+1}/{max_polls}: Pipeline status = {current_status}")
        
        if current_status == "completed":
            break
        elif current_status == "error":
            print(f"❌ ERROR: Pipeline failed with error: {status_data.get('error_message', 'Unknown error')}")
            sys.exit(1)
        
        time.sleep(poll_interval)
    else:
        print("❌ ERROR: Pipeline never finished within the timeout period")
        sys.exit(1)
    
    # 3. Verify data saved
    print("\nStep 3: Verifying data saved to database")
    
    # Get results for the keyword
    response = requests.get(f"{API_BASE}/results/{test_keyword}")
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to get results. Status code: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    products = response.json()
    product_count = len(products)
    
    if product_count < 1:
        print("❌ ERROR: No products were saved to the database")
        sys.exit(1)
        
    print(f"✅ SUCCESS: Found {product_count} products for keyword '{test_keyword}'")
    print(f"🎉 Test completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True

if __name__ == "__main__":
    test_keyword_pipeline()
