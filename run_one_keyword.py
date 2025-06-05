#!/usr/bin/env python3
"""
Single Keyword Runner - Minimal Working Pipeline
Runs Steps 1-2 sequentially: Scrape → Traffic Enrichment → Results
"""

import sys
import os
import argparse
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project to path
sys.path.append('.')

from app.core.step1_keyword_scraper import run_scraper
from app.core.free_traffic_analyzer import get_traffic_data, save_traffic_data
from app.database.db import create_db_and_tables, get_session
from app.models.models import DiscoveredProduct, TrafficIntelligence
from sqlmodel import select

# Configure explicit pipeline logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [PIPELINE] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('pipeline')

def log_step_start(step_num: int, step_name: str, details: str):
    """Log the start of a pipeline step"""
    print(f"\n👉 STEP {step_num} START: {step_name}")
    print(f"   ├─ {details}")
    logger.info(f"STEP {step_num} START: {step_name} - {details}")

def log_step_end(step_num: int, step_name: str, result: str):
    """Log the end of a pipeline step"""
    print(f"✅ STEP {step_num} END: {step_name}")
    print(f"   └─ {result}")
    logger.info(f"STEP {step_num} END: {step_name} - {result}")

def log_api_call(api_name: str, input_data: str, expected_output: str):
    """Log an API call with input and expected output"""
    print(f"   🔌 API CALL: {api_name}")
    print(f"      • Input: {input_data}")
    print(f"      • Expected: {expected_output}")
    logger.info(f"API CALL: {api_name} | Input: {input_data} | Expected: {expected_output}")

def log_domain_processing(domain: str, action: str, result: str):
    """Log processing of individual domains"""
    print(f"   🏢 DOMAIN: {domain}")
    print(f"      • Action: {action}")
    print(f"      • Result: {result}")
    logger.info(f"DOMAIN: {domain} | Action: {action} | Result: {result}")

def run_single_keyword_pipeline(keyword: str, max_ads: int = 20, keyword_id: int = None) -> Dict[str, Any]:
    """
    Complete pipeline for a single keyword
    
    Args:
        keyword: Keyword to process
        max_ads: Maximum ads to scrape
        keyword_id: ID of the keyword in the database (optional)
        
    Returns:
        Results dictionary with statistics
    """
    print(f"🚀 SINGLE KEYWORD PIPELINE: '{keyword}'")
    print("=" * 80)
    print(f"📋 Configuration: max_ads={max_ads}, keyword='{keyword}'")
    logger.info(f"PIPELINE START: keyword='{keyword}', max_ads={max_ads}")
    
    results = {
        "keyword": keyword,
        "started_at": datetime.now(),
        "step1_products": 0,
        "step2_enriched": 0,
        "errors": [],
        "completed_at": None
    }
    
    try:
        # Ensure database exists
        create_db_and_tables()
        print("📊 Database tables verified/created")
        
        # STEP 1: Scrape Facebook ads
        log_step_start(1, "Facebook Ad Scraping", f"Scrape ads for keyword '{keyword}' via Apify API")
        log_api_call("Apify Facebook Ad Library Scraper", f"keyword='{keyword}', max_ads={max_ads}", f"Raw ad data + landing page URLs")
        
        step1_start = time.time()
        
        scraped_products = run_scraper(
            keyword=keyword,
            max_ads=max_ads,
            timeout_seconds=300,
            keyword_id=keyword_id,  # Pass the keyword_id to properly link products
            enrich_traffic=False  # We'll do this manually in Step 2
        )
        
        step1_duration = time.time() - step1_start
        results["step1_products"] = len(scraped_products)
        
        log_step_end(1, "Facebook Ad Scraping", f"Found {len(scraped_products)} products in {step1_duration:.1f}s")
        
        if not scraped_products:
            print("⚠️  No products found. Pipeline complete.")
            logger.warning("PIPELINE END: No products discovered")
            results["completed_at"] = datetime.now()
            return results
        
        # Get the newly created products from database
        with get_session() as session:
            # Get recent products (last 5 minutes) to ensure we get the ones we just created
            recent_cutoff = datetime.now() - timedelta(minutes=5)
            recent_products = session.exec(
                select(DiscoveredProduct)
                .where(DiscoveredProduct.first_discovered >= recent_cutoff)
                .limit(max_ads)
            ).all()
            
            print(f"📊 Database Query: Found {len(recent_products)} recent products for enrichment")
            logger.info(f"DATABASE: Retrieved {len(recent_products)} recent products for processing")
        
        # STEP 2: Enrich with traffic data
        log_step_start(2, "Traffic Data Enrichment", f"Enrich {len(recent_products[:10])} domains with traffic data")
        log_api_call("Free Traffic Analyzer", "domain URLs", "Monthly website visits estimate")
        
        step2_start = time.time()
        step2_enriched = 0
        
        for i, product in enumerate(recent_products[:10], 1):  # Limit to 10 for speed
            domain = product.brand_domain
            
            domain = product.brand_domain
            try:
                log_domain_processing(domain, "Fetch traffic", "Requesting traffic data...")
                
                # Use our new traffic analyzer
                visits, source = get_traffic_data(domain)
                
                # Save traffic data to database
                save_traffic_data(domain, product.id, visits, source)
                
                if visits:
                    log_domain_processing(domain, "Traffic data", f"{visits:,} monthly visits (via {source})")
                    step2_enriched += 1
                else:
                    log_domain_processing(domain, "Traffic data", f"No traffic data available: {source}")
            
            except Exception as e:
                log_domain_processing(domain, "Traffic lookup", f"ERROR: {e}")
                results["errors"].append(f"Traffic lookup failed for {domain}: {e}")
        
        step2_duration = time.time() - step2_start
        results["step2_enriched"] = step2_enriched
        log_step_end(2, "Traffic Enrichment", f"Enriched {step2_enriched}/{len(recent_products)} domains in {step2_duration:.1f}s")
        
        results["completed_at"] = datetime.now()
        total_duration = (results["completed_at"] - results["started_at"]).total_seconds()
        
        print(f"\n🎉 PIPELINE COMPLETE!")
        print(f"⏱️  Total Duration: {total_duration:.1f}s")
        print(f"📊 Final Results:")
        print(f"   ├─ Products Discovered: {results['step1_products']}")
        print(f"   └─ Traffic Enriched: {results['step2_enriched']}")
        
        if results["errors"]:
            print(f"⚠️  Errors Encountered: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"   • {error}")
        
        logger.info(f"PIPELINE COMPLETE: {total_duration:.1f}s | Products: {results['step1_products']} | Enriched: {results['step2_enriched']}")
        
        return results
        
    except Exception as e:
        print(f"💥 PIPELINE FAILED: {e}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"PIPELINE FAILED: {e}")
        results["errors"].append(f"Pipeline error: {e}")
        results["completed_at"] = datetime.now()
        return results

def main():
    """CLI interface for single keyword processing"""
    parser = argparse.ArgumentParser(description='Single Keyword Market Intelligence Pipeline')
    parser.add_argument('--keyword', '-k', required=True, help='Keyword to process (e.g., "keto")')
    parser.add_argument('--max-ads', '-m', type=int, default=20, help='Maximum ads to scrape (default: 20)')
    
    args = parser.parse_args()
    
    # Run the pipeline
    results = run_single_keyword_pipeline(args.keyword, args.max_ads)
    
    # Exit with error code if pipeline failed
    if results["errors"]:
        print(f"\n❌ Pipeline completed with {len(results['errors'])} errors")
        sys.exit(1)
    else:
        print(f"\n✅ Pipeline completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main() 