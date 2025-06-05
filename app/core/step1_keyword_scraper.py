#!/usr/bin/env python3
import os
import sys
import requests
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Optional, List, Dict, Set, Callable, Any, Union
import tldextract
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from sqlmodel import select, Session, create_engine
import traceback

# Add the step1 directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import database models
from app.models.models import DiscoveredProduct, Keyword, KeywordStatus
from app.database.db import get_session, create_db_and_tables

# NOTE: blacklisted_domains.csv must be present in the app/config directory
BLACKLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "blacklisted_domains.csv")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "keywords_data")

# Correct Apify Actor Configuration (from working step1_keyword_scraper.py)
ACTOR_ID = "bo5X18oGenWEV9vVo"  # Facebook Ad Library Scraper
BASE_URL = "https://api.apify.com/v2"
HEADERS = {"Content-Type": "application/json"}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('market_intelligence_scraper')

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Quick Win: Environment variable validation
def validate_environment():
    """Validate required environment variables are present"""
    missing_vars = []
    
    if not os.getenv('APIFY_TOKEN'):
        missing_vars.append('APIFY_TOKEN')
    
    if missing_vars:
        print("❌ MISSING ENVIRONMENT VARIABLES:")
        for var in missing_vars:
            print(f"   • {var} not found in .env file")
        print("\n💡 SOLUTION:")
        print("   1. Check that .env file exists in the project root")
        print("   2. Ensure it contains:")
        for var in missing_vars:
            print(f"      {var}=your_api_key_here")
        print("   3. Restart the application")
        print("\n📖 See README.md for setup instructions")
        sys.exit(1)

# Call validation at module load
validate_environment()

def create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic for network issues"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def load_blacklisted_domains() -> Set[str]:
    """Load blacklisted domains from CSV file
    
    Returns:
        Set of blacklisted domain names
    """
    csv_path = BLACKLIST_FILE
    domains = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0: continue  # skip header
                dom = line.strip().lower()
                if dom:
                    domains.add(dom)
    logger.info(f"Loaded {len(domains)} blacklisted domains")
    return domains

def normalize_domain(url: str) -> Optional[str]:
    """Extract and normalize domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Normalized domain or None if extraction fails
    """
    try:
        ext = tldextract.extract(url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        return None
    except Exception:
        return None

def ensure_dir(d: str) -> None:
    """Create directory if it doesn't exist
    
    Args:
        d: Directory path to create
    """
    if not os.path.exists(d):
        os.makedirs(d)

def read_existing_domains() -> Set[str]:
    """Get all existing domains from the database
    
    Returns:
        Set of normalized domains already in the database
    """
    with get_session() as session:
        discovered_products = session.query(DiscoveredProduct).all()
        domains = {dp.brand_domain for dp in discovered_products if dp.brand_domain}
        logger.info(f"Found {len(domains)} existing domains in database")
        return domains

def upsert_discovered_product(session, product_data: Dict[str, Any], keyword_id: Optional[int] = None) -> bool:
    """Upsert a discovered product with improved intelligence if it already exists
    
    Args:
        session: Database session
        product_data: Product data dictionary
        keyword_id: Optional keyword ID
        
    Returns:
        True if new product was created, False if existing product was updated
    """
    product_page_url = product_data['product_page_url']
    brand_domain = normalize_domain(product_page_url)
    intelligence = product_data.get('ad_intelligence', {})
    
    # Check if domain already exists
    existing = session.exec(select(DiscoveredProduct).where(DiscoveredProduct.brand_domain == brand_domain)).first()
    
    if existing:
        # Update existing product with better intelligence data
        updated = False
        
        # Update ad spend estimates if new data is higher
        new_spend = intelligence.get('estimated_monthly_ad_spend', 0)
        if new_spend > (existing.estimated_monthly_ad_spend or 0):
            existing.min_monthly_ad_spend = intelligence.get('min_monthly_ad_spend')
            existing.max_monthly_ad_spend = intelligence.get('max_monthly_ad_spend')
            existing.estimated_monthly_ad_spend = new_spend
            updated = True
        
        # Update impression estimates if new data is higher
        new_impressions = intelligence.get('estimated_monthly_impressions', 0)
        if new_impressions > (existing.estimated_monthly_impressions or 0):
            existing.min_monthly_impressions = intelligence.get('min_monthly_impressions')
            existing.max_monthly_impressions = intelligence.get('max_monthly_impressions')
            existing.estimated_monthly_impressions = new_impressions
            updated = True
        
        # Update campaign duration if longer
        new_duration = intelligence.get('ad_campaign_duration_days', 0)
        if new_duration > (existing.ad_campaign_duration_days or 0):
            existing.ad_campaign_duration_days = new_duration
            updated = True
            
        # Update platform intelligence
        new_platform_count = intelligence.get('advertising_platforms_count', 0)
        if new_platform_count > (existing.advertising_platforms_count or 0):
            existing.advertising_platforms_count = new_platform_count
            existing.advertising_platforms = intelligence.get('advertising_platforms')
            updated = True
        
        # Update geographic intelligence
        new_country_count = intelligence.get('target_countries_count', 0)
        if new_country_count > (existing.target_countries_count or 0):
            existing.target_countries_count = new_country_count
            existing.target_countries = intelligence.get('target_countries')
            updated = True
        
        # Always update marketing psychology features (they might change)
        existing.features_discount_offer = intelligence.get('features_discount_offer')
        existing.features_urgency_language = intelligence.get('features_urgency_language')
        existing.features_purchase_cta = intelligence.get('features_purchase_cta')
        existing.features_social_proof = intelligence.get('features_social_proof')
        existing.features_free_shipping = intelligence.get('features_free_shipping')
        existing.primary_call_to_action = intelligence.get('primary_call_to_action')
        existing.ad_creative_themes = intelligence.get('ad_creative_themes')
        
        existing.last_seen_advertising = datetime.now()
        
        if updated:
            session.add(existing)
            logger.info(f"🔄 Updated existing product: {brand_domain} with enhanced intelligence")
        
        return False  # Existing product updated
    else:
        # Create new discovered product
        dp = DiscoveredProduct(
            keyword_id=keyword_id,
            product_page_url=product_page_url,
            brand_domain=brand_domain,
            brand_name=product_data.get('brand_name', ''),
            facebook_page_url=product_data.get('facebook_page_url', ''),
            facebook_page_id=product_data.get('facebook_page_id', ''),
            first_discovered=datetime.now(),
            last_seen_advertising=datetime.now(),
            
            # Ad Intelligence Data
            ad_campaign_duration_days=intelligence.get('ad_campaign_duration_days'),
            total_active_ads=intelligence.get('total_active_ads'),
            
            # Ad Spend Intelligence
            min_monthly_ad_spend=intelligence.get('min_monthly_ad_spend'),
            max_monthly_ad_spend=intelligence.get('max_monthly_ad_spend'),
            estimated_monthly_ad_spend=intelligence.get('estimated_monthly_ad_spend'),
            
            # Impression & Reach Data
            min_monthly_impressions=intelligence.get('min_monthly_impressions'),
            max_monthly_impressions=intelligence.get('max_monthly_impressions'),
            estimated_monthly_impressions=intelligence.get('estimated_monthly_impressions'),
            
            # Platform & Geographic Intelligence
            advertising_platforms_count=intelligence.get('advertising_platforms_count'),
            advertising_platforms=intelligence.get('advertising_platforms'),
            target_countries_count=intelligence.get('target_countries_count'),
            target_countries=intelligence.get('target_countries'),
            
            # Marketing Psychology Analysis
            features_discount_offer=intelligence.get('features_discount_offer'),
            features_urgency_language=intelligence.get('features_urgency_language'),
            features_purchase_cta=intelligence.get('features_purchase_cta'),
            features_social_proof=intelligence.get('features_social_proof'),
            features_free_shipping=intelligence.get('features_free_shipping'),
            primary_call_to_action=intelligence.get('primary_call_to_action'),
            ad_creative_themes=intelligence.get('ad_creative_themes')
        )
        session.add(dp)
        logger.info(f"✅ Discovered new product: {brand_domain}")
        return True  # New product created

def save_to_db(new_product_dicts: List[Dict[str, Any]], keyword_id: Optional[int] = None, 
              enrich_traffic: bool = False) -> Dict[str, int]:
    """Save new discovered products to database with upsert logic and optional traffic enrichment
    
    Args:
        new_product_dicts: List of dictionaries containing product data
        keyword_id: Optional ID of the keyword that generated these products
        enrich_traffic: Whether to automatically enrich with traffic data
        
    Returns:
        Dictionary with counts of new vs updated products
    """
    if not new_product_dicts:
        logger.info("No new products to save")
        return {"new": 0, "updated": 0}
        
    with get_session() as session:
        new_count = 0
        updated_count = 0
        new_product_ids = []  # Track new products for traffic enrichment
        
        for product in new_product_dicts:
            is_new = upsert_discovered_product(session, product, keyword_id)
            if is_new:
                new_count += 1
                # Get the ID of the newly created product for traffic enrichment
                if enrich_traffic:
                    # Find the product we just created
                    domain = normalize_domain(product.get('product_page_url', ''))
                    if domain:
                        discovered_product = session.exec(
                            select(DiscoveredProduct).where(DiscoveredProduct.brand_domain == domain)
                        ).first()
                        if discovered_product:
                            new_product_ids.append(discovered_product.id)
            else:
                updated_count += 1
        
        session.commit()
        logger.info(f"💾 Saved {new_count} new products, updated {updated_count} existing products")
        
        # Traffic enrichment disabled in minimal app - use Step 2 of pipeline instead
        if enrich_traffic and new_product_ids:
            logger.info(f"⚠️  Traffic enrichment requested but not available in minimal app")
            logger.info("Products saved successfully. Run Step 2 for traffic enrichment.")
        
        return {"new": new_count, "updated": updated_count}

def extract_ad_intelligence(ad: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract real market intelligence from Facebook ad data with optional filtering
    
    Args:
        ad: Raw Facebook ad data
        filters: Optional filtering criteria (min_spend, min_impressions, max_days)
        
    Returns:
        Dictionary containing market intelligence metrics, or None if filtered out
    """
    intelligence = {}
    
    # === AD SPEND INTELLIGENCE ===
    impressions = ad.get('impressions') or {}
    spend = ad.get('spend') or {}
    
    # Check if we have impressions_with_index as alternative
    impressions_with_index = ad.get('impressions_with_index', {})
    
    # Safe extraction with None checks for impressions
    if isinstance(impressions, dict) and impressions:
        intelligence['min_monthly_impressions'] = int(impressions.get('lower_bound', 0)) if impressions.get('lower_bound') else 0
        intelligence['max_monthly_impressions'] = int(impressions.get('upper_bound', 0)) if impressions.get('upper_bound') else 0
    else:
        # Try to extract from impressions_with_index
        imp_text = impressions_with_index.get('impressions_text', '')
        if imp_text and '-' in imp_text:
            try:
                parts = imp_text.split('-')
                intelligence['min_monthly_impressions'] = int(parts[0].strip())
                intelligence['max_monthly_impressions'] = int(parts[1].strip())
            except:
                intelligence['min_monthly_impressions'] = 0
                intelligence['max_monthly_impressions'] = 0
        else:
            intelligence['min_monthly_impressions'] = 0
            intelligence['max_monthly_impressions'] = 0
    
    intelligence['estimated_monthly_impressions'] = (intelligence['min_monthly_impressions'] + intelligence['max_monthly_impressions']) // 2
    
    # Safe extraction for spend
    if isinstance(spend, dict) and spend:
        intelligence['min_monthly_ad_spend'] = int(spend.get('lower_bound', 0)) if spend.get('lower_bound') else 0
        intelligence['max_monthly_ad_spend'] = int(spend.get('upper_bound', 0)) if spend.get('upper_bound') else 0
    else:
        intelligence['min_monthly_ad_spend'] = 0
        intelligence['max_monthly_ad_spend'] = 0
        
    intelligence['estimated_monthly_ad_spend'] = (intelligence['min_monthly_ad_spend'] + intelligence['max_monthly_ad_spend']) // 2
    
    # Apply filters early to skip low-performing ads (only if we have data)
    if filters and (intelligence['estimated_monthly_ad_spend'] > 0 or intelligence['estimated_monthly_impressions'] > 0):
        if filters.get('min_spend', 0) > intelligence['estimated_monthly_ad_spend']:
            return None  # Skip this ad
        if filters.get('min_impressions', 0) > intelligence['estimated_monthly_impressions']:
            return None  # Skip this ad
    
    # === CAMPAIGN DURATION INTELLIGENCE ===
    start_time = ad.get('ad_delivery_start_time')
    start_date = ad.get('start_date')
    
    if start_time:
        try:
            from datetime import datetime
            start_date_obj = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            days_running = (datetime.now().replace(tzinfo=start_date_obj.tzinfo) - start_date_obj).days
            intelligence['ad_campaign_duration_days'] = max(0, days_running)
        except:
            intelligence['ad_campaign_duration_days'] = 0
    elif start_date:
        try:
            from datetime import datetime
            # Handle Unix timestamp
            if isinstance(start_date, (int, float)):
                start_date_obj = datetime.fromtimestamp(start_date)
                days_running = (datetime.now() - start_date_obj).days
                intelligence['ad_campaign_duration_days'] = max(0, days_running)
            else:
                intelligence['ad_campaign_duration_days'] = 0
        except:
            intelligence['ad_campaign_duration_days'] = 0
    else:
        intelligence['ad_campaign_duration_days'] = 0
    
    # Apply max_days filter
    if filters and filters.get('max_days', float('inf')) < intelligence['ad_campaign_duration_days']:
        return None  # Skip this ad
    
    # === MARKETING PSYCHOLOGY ANALYSIS ===
    snapshot = ad.get('snapshot', {})

    # Safe extraction of creative text with type checking
    def safe_text_extract(value):
        """Safely extract text from potentially nested dict or string value"""
        if isinstance(value, str):
            return value.lower()
        elif isinstance(value, dict):
            # Try common text fields in nested dicts
            return (value.get('text') or value.get('content') or value.get('body') or '').lower()
        else:
            return ''

    creative_body = safe_text_extract(ad.get('ad_creative_body') or snapshot.get('body') or '')
    creative_title = safe_text_extract(ad.get('ad_creative_link_title') or snapshot.get('link_description') or '')
    
    # Promotional strategy detection
    discount_keywords = ['sale', 'off', '%', 'discount', 'save', 'deal', 'special']
    urgency_keywords = ['today', 'now', 'limited time', 'hurry', 'last chance', 'ending soon', 'while supplies last']
    social_proof_keywords = ['bestseller', 'popular', 'trending', 'viral', 'reviews', 'rated', 'testimonial']
    shipping_keywords = ['free shipping', 'free delivery', 'shipping included']
    
    intelligence['features_discount_offer'] = any(keyword in creative_body or keyword in creative_title 
                                                 for keyword in discount_keywords)
    intelligence['features_urgency_language'] = any(keyword in creative_body or keyword in creative_title 
                                                   for keyword in urgency_keywords)
    intelligence['features_social_proof'] = any(keyword in creative_body or keyword in creative_title 
                                               for keyword in social_proof_keywords)
    intelligence['features_free_shipping'] = any(keyword in creative_body or keyword in creative_title 
                                                for keyword in shipping_keywords)
    
    # Call to action analysis
    cta = (ad.get('call_to_action_type') or snapshot.get('cta_type') or '').lower()
    ecommerce_ctas = ['shop_now', 'buy_now', 'order_now', 'get_offer', 'sign_up', 'learn_more']
    intelligence['features_purchase_cta'] = cta in ecommerce_ctas
    intelligence['primary_call_to_action'] = cta if cta else None
    
    # === PLATFORM & GEOGRAPHIC INTELLIGENCE ===
    platforms = ad.get('publisher_platforms', []) or ad.get('publisher_platform', [])
    if isinstance(platforms, str):
        platforms = [platforms]
    intelligence['advertising_platforms_count'] = len(platforms) if platforms else 1
    intelligence['advertising_platforms'] = ','.join(platforms) if platforms else 'facebook'
    
    # Geographic reach
    regions = ad.get('region_distribution', []) or ad.get('targeted_or_reached_countries', [])
    if isinstance(regions, list) and regions:
        # Extract country names from region data
        countries = []
        for region in regions:
            if isinstance(region, dict):
                country = region.get('name') or region.get('country')
                if country:
                    countries.append(country)
            elif isinstance(region, str):
                countries.append(region)
        
        intelligence['target_countries_count'] = len(countries)
        intelligence['target_countries'] = ','.join(countries) if countries else None
    else:
        intelligence['target_countries_count'] = 1
        intelligence['target_countries'] = 'United States'  # Default assumption
    
    # === CREATIVE THEMES ANALYSIS ===
    # Extract themes from ad creative for market intelligence
    themes = []
    if 'health' in creative_body or 'wellness' in creative_body:
        themes.append('health_wellness')
    if 'beauty' in creative_body or 'skincare' in creative_body:
        themes.append('beauty_skincare')
    if 'fitness' in creative_body or 'workout' in creative_body:
        themes.append('fitness')
    if 'tech' in creative_body or 'gadget' in creative_body:
        themes.append('technology')
    if 'home' in creative_body or 'kitchen' in creative_body:
        themes.append('home_garden')
    if 'fashion' in creative_body or 'clothing' in creative_body:
        themes.append('fashion')
    
    intelligence['ad_creative_themes'] = ','.join(themes) if themes else None
    
    # Estimate total active ads (placeholder - would need more complex logic)
    intelligence['total_active_ads'] = 1  # At minimum, this ad
    
    return intelligence

def run_scraper(keyword: str, max_ads: int, timeout_seconds: int = 1800, 
              save_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
              keyword_id: Optional[int] = None,
              filters: Optional[Dict[str, Any]] = None,
              enrich_traffic: bool = False) -> List[Dict[str, Any]]:
    """Run the market intelligence scraper for a given keyword with enhanced filtering
    
    Args:
        keyword: Keyword to search for
        max_ads: Maximum number of ads to scrape
        timeout_seconds: Timeout for Apify actor run
        save_callback: Optional callback function to handle saving results
        keyword_id: Optional ID of the keyword being processed
        filters: Optional filtering criteria (min_spend, min_impressions, max_days)
        enrich_traffic: Whether to automatically enrich with traffic data
        
    Returns:
        List of dictionaries containing discovered product data
    """
    logger.info(f"🔍 Market Intelligence Scraping: {keyword} | Max ads: {max_ads} | Timeout: {timeout_seconds}s")
    if filters:
        logger.info(f"📊 Applied filters: {filters}")
    
    ensure_dir(DATA_DIR)
    blacklist_domains = load_blacklisted_domains()
    existing_domains = read_existing_domains()
    
    CATEGORY_MAPPING = {
        "All ads": "all",
        "Issues, elections or politics": "political_and_issue_ads",
        "Housing": "housing_ads",
        "Employment": "employment_ads",
        "Financial products and services": "credit_ads"
    }
    
    # Use EXACT working actor input format from step1_keyword_scraper.py
    actor_input = {
        "query": keyword,
        "maxItems": int(max_ads),
        "country": "US",
        "category": "all",
        "proxyConfiguration": {
            "useApifyProxy": True, 
            "apifyProxyGroups": ["RESIDENTIAL"]  # THIS WAS THE KEY DIFFERENCE!
        }
    }
    
    # Use EXACT working parameters format
    params = {
        "token": APIFY_TOKEN,
        "memory": 512,
        "timeout": timeout_seconds,
        "build": "latest"
    }
    
    # Use EXACT working API endpoint
    start_url = f"{BASE_URL}/acts/{ACTOR_ID}/runs"
    
    # Create session with retries
    session = create_session_with_retries()
    
    try:
        logger.info(f"🚀 Starting Apify actor run for keyword: {keyword}")
        
        # Test connectivity first
        try:
            test_resp = session.get(f"{BASE_URL}/acts", params={"token": APIFY_TOKEN}, timeout=10)
            test_resp.raise_for_status()
            logger.info("✅ Successfully connected to Apify API")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to connect to Apify API: {e}")
            logger.error(f"Please check your internet connection and APIFY_TOKEN")
            return []
        
        # Start the actor run
        resp = session.post(start_url, json=actor_input, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        run_data = resp.json().get("data", {})
        run_id = run_data.get('id')
        if not run_id:
            logger.error("❌ No run ID returned from Apify.")
            return []
        
        logger.info(f"📊 Started Apify run with ID: {run_id}")
        
        # Poll for completion
        status_url = f"{BASE_URL}/actor-runs/{run_id}"
        poll_interval = 15
        max_polls = int(timeout_seconds / poll_interval)
        
        for i in range(max_polls):
            try:
                status_resp = session.get(status_url, params={"token": APIFY_TOKEN}, timeout=30)
                status_resp.raise_for_status()
                run = status_resp.json().get("data", {})
                status = run.get("status")
                
                logger.info(f"⏳ Run status: {status} (poll {i+1}/{max_polls})")
                
                if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    break
                    
                time.sleep(poll_interval)
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️  Error checking status (attempt {i+1}): {e}")
                time.sleep(poll_interval)
                continue
        
        if status == "FAILED" or status == "ABORTED":
            logger.error(f"❌ Apify run failed with status: {status}")
            return []
        
        # If we reach here, either the run succeeded or timed out. In case of timeout,
        # we still want to process whatever data was collected before the timeout.
        if status == "TIMED-OUT":
            logger.warning(f"⚠️  Apify run timed out, but will continue processing collected data.")
        
        dataset_id = run.get('defaultDatasetId')
        if not dataset_id:
            logger.error("❌ No dataset ID returned from Apify.")
            return []
        
        # Fetch results
        items_url = f"{BASE_URL}/datasets/{dataset_id}/items"
        ads_data = []
        offset = 0
        limit = 1000
        
        while True:
            items_params = {
                "token": APIFY_TOKEN,
                "format": "json",
                "clean": "true",
                "offset": offset,
                "limit": limit
            }
            
            try:
                items_resp = session.get(items_url, params=items_params, timeout=60)
                items_resp.raise_for_status()
                items = items_resp.json()
                
                if not items:
                    break
                    
                ads_data.extend(items)
                offset += len(items)
                logger.info(f"📥 Fetched {len(ads_data)} ads so far...")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Error fetching results: {e}")
                break
    
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error during scraping: {e}")
        return []
    except Exception as e:
        logger.error(f"💥 Unexpected error during scraping: {e}")
        return []
    finally:
        session.close()
    
    # Save raw data
    if ads_data:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_path = os.path.join(DATA_DIR, f"{keyword.replace(' ', '_')}_{ts}_raw.json")
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(ads_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Saved raw ads to {raw_path} ({len(ads_data)} ads)")
    
    # Process and filter - maintain domain-level uniqueness
    unique = {}
    skipped_counts = {
        'no_url': 0,
        'blacklisted': 0,
        'existing': 0,
        'filtered': 0,
        'kept': 0
    }
    top_performers = []
    
    for ad in ads_data:
        # Find best landing page URL from multiple possible locations
        landing_page_url = None
        
        # Try direct properties first
        landing_page_url = ad.get('landing_page_url') or ad.get('link_url')
        
        # If not found, try snapshot link_url (most common location)
        if not landing_page_url:
            snapshot = ad.get('snapshot', {})
            landing_page_url = snapshot.get('link_url')
        
        # If still not found, try cards
        if not landing_page_url:
            cards = snapshot.get('cards', []) if 'snapshot' in ad else []
            for card in cards:
                if card.get('link_url'):
                    landing_page_url = card['link_url']
                    break
        
        # Skip if no landing page found
        if not landing_page_url or not landing_page_url.strip():
            skipped_counts['no_url'] += 1
            logger.debug(f"❌ No URL found for ad: {ad.get('ad_archive_id', 'unknown')}")
            continue
            
        # Get domain for filtering and uniqueness checks
        domain = normalize_domain(landing_page_url)
        if not domain:
            skipped_counts['no_url'] += 1
            continue
            
        # Skip blacklisted domains
        if domain in blacklist_domains:
            skipped_counts['blacklisted'] += 1
            logger.debug(f"🚫 Skipped blacklisted domain: {domain}")
            continue
            
        # Skip domains already in database (unless we're updating)
        if domain in existing_domains:
            skipped_counts['existing'] += 1
            logger.debug(f"🔄 Skipped existing domain: {domain}")
            continue
        
        # Extract and filter by market intelligence
        intelligence = extract_ad_intelligence(ad, filters)
        if intelligence is None:  # Filtered out by criteria
            skipped_counts['filtered'] += 1
            continue
        
        # Extract page information
        snapshot = ad.get('snapshot', {})
        page_id = ad.get('page_id', '')
        page_name = ad.get('page_name') or snapshot.get('page_name', '')
        
        product_data = {
            'product_page_url': landing_page_url,
            'facebook_page_url': f"https://www.facebook.com/{page_id}" if page_id else '',
            'brand_name': page_name,
            'facebook_page_id': str(page_id) if page_id else '',
            'keyword_first_seen': keyword,
            'first_seen_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ad_intelligence': intelligence
        }
        
        unique[domain] = product_data
        skipped_counts['kept'] += 1
        
        # Track top performers for logging
        spend = intelligence.get('estimated_monthly_ad_spend', 0)
        duration = intelligence.get('ad_campaign_duration_days', 0)
        if spend > 0 or duration > 30:  # Consider as top performer
            top_performers.append({
                'domain': domain,
                'spend': spend,
                'duration': duration,
                'impressions': intelligence.get('estimated_monthly_impressions', 0)
            })
    
    # Log processing statistics
    logger.info(f"📊 Processing results: {skipped_counts}")
    if top_performers:
        top_performers_sorted = sorted(top_performers, key=lambda x: x['spend'], reverse=True)[:5]
        logger.info(f"🏆 Top performers discovered:")
        for performer in top_performers_sorted:
            logger.info(f"  💰 {performer['domain']} - ${performer['spend']}/mo, {performer['duration']} days, {performer['impressions']:,} impressions")
    
    logger.info(f"✅ Discovered {len(unique)} unique products (by domain)")
    
    # If a save callback is provided, use it; otherwise use the default save_to_db method
    unique_values = list(unique.values())
    if save_callback:
        save_callback(unique_values)
    else:
        save_stats = save_to_db(unique_values, keyword_id, enrich_traffic)
        logger.info(f"💾 Database save stats: {save_stats}")
        
    return unique_values

def bulk_enrich_traffic_background() -> Dict[str, int]:
    """
    Convenience function to enrich all discovered products needing traffic data
    
    Note: Not available in minimal app - use Step 2 of the pipeline instead
    
    Returns:
        Processing statistics
    """
    logger.warning("⚠️  Bulk traffic enrichment not available in minimal app")
    logger.info("Use Step 2 of the pipeline for traffic enrichment")
    return {"processed": 0, "errors": 0, "total": 0}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Facebook Ad Market Intelligence Scraper with Advanced Filtering')
    parser.add_argument('keyword', help='Keyword to search for')
    parser.add_argument('max_ads', type=int, help='Maximum number of ads to scrape')
    parser.add_argument('--timeout', type=int, default=1800, help='Timeout in seconds')
    
    # Market intelligence filtering options
    parser.add_argument('--min-spend', type=int, default=0, help='Minimum monthly ad spend to consider')
    parser.add_argument('--min-impressions', type=int, default=0, help='Minimum monthly impressions to consider')
    parser.add_argument('--max-days', type=int, default=365, help='Maximum campaign duration to consider')
    
    # Analysis options
    parser.add_argument('--enrich-traffic', action='store_true', help='Automatically enrich with traffic intelligence')
    
    args = parser.parse_args()
    
    # Ensure database exists
    create_db_and_tables()
    
    # Build filters dictionary
    filters = {}
    if args.min_spend > 0:
        filters['min_spend'] = args.min_spend
    if args.min_impressions > 0:
        filters['min_impressions'] = args.min_impressions
    if args.max_days < 365:
        filters['max_days'] = args.max_days
    
    # Run the market intelligence scraper
    results = run_scraper(
        args.keyword, 
        args.max_ads, 
        args.timeout,
        filters=filters if filters else None,
        enrich_traffic=args.enrich_traffic
    )
    
    logger.info(f"🎉 Market intelligence gathering complete: {len(results)} products discovered")


