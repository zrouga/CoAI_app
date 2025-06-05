#!/usr/bin/env python3
"""
Simple Free Traffic Analyzer for SimilarWeb Data

Uses ScraperAPI to get traffic data from SimilarWeb's extension API endpoint.
"""

import asyncio
import aiohttp
import ssl
import logging
import os
import json
import re
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, quote
from datetime import datetime
from sqlmodel import select
from dotenv import load_dotenv

from app.models.models import TrafficIntelligence, DiscoveredProduct
from app.database.db import get_session

# Load environment variables
load_dotenv()

# ScraperAPI config
SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY', '990100cafd68de7809030daf24118e2b')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic configurations
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds


def get_scraperapi_url(url: str) -> str:
    """
    Get ScraperAPI URL for rotating IPs
    
    Args:
        url: Target URL to proxy
        
    Returns:
        ScraperAPI-formatted URL
    """
    return f"http://{SCRAPER_API_KEY}:@proxy.scraperapi.com:8001?url={quote(url)}"


async def fetch_traffic_data(domain: str, retry_count: int = 0) -> Tuple[Optional[int], str]:
    """
    Fetch traffic data from SimilarWeb extension API using ScraperAPI
    
    Args:
        domain: Domain to check
        retry_count: Current retry attempt
        
    Returns:
        Tuple of (monthly visits or None, source or error message)
    """
    try:
        if retry_count >= MAX_RETRIES:
            return None, f"Max retries ({MAX_RETRIES}) exceeded"
            
        logger.info(f"Fetching traffic for {domain} (attempt {retry_count + 1})")
        
        # Normalize domain (remove www if present)
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Use the extension API endpoint which is fast and typically allows more free requests
        extension_url = f"https://extension.similarweb.com/lookup?domain={domain}"
        url = get_scraperapi_url(extension_url)
            
        # Create SSL context that allows for default certificate verification failures
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'chrome-extension://hoklmmgfnpapgjgcpechhaamimifchmp',
            'Referer': 'chrome-extension://hoklmmgfnpapgjgcpechhaamimifchmp/index.html'
        }
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'site_data' in data and 'general_data' in data['site_data']:
                            # Parse visits data - format is typically like "402K"
                            visits_raw = data['site_data']['general_data'].get('visits', None)
                            
                            if not visits_raw or visits_raw == 'null':
                                return None, "No visits data found in response"
                                
                            visits = parse_visits_number(visits_raw)
                            if visits and visits > 0:
                                logger.info(f"Success: Found {visits:,} monthly visits for {domain}")
                                return visits, "extension"
                            else:
                                return None, f"Invalid visits value found: {visits_raw}"
                        else:
                            return None, "Unexpected response format"
                            
                    elif response.status in [429, 403, 503, 502, 504]:
                        # Rate limiting or server errors - retry with exponential backoff
                        delay = RETRY_DELAY * (2 ** retry_count) 
                        logger.warning(f"HTTP {response.status} for {domain}, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        return await fetch_traffic_data(domain, retry_count + 1)
                        
                    else:
                        return None, f"HTTP Error: {response.status}"
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {domain} (attempt {retry_count + 1})")
                await asyncio.sleep(RETRY_DELAY)
                return await fetch_traffic_data(domain, retry_count + 1)
                
    except Exception as e:
        logger.error(f"Error fetching traffic for {domain}: {e}")
        return None, f"Exception: {str(e)}"


def parse_visits_number(visits_text: str) -> Optional[int]:
    """
    Parse visits number from text format like 402K or 1.5M
    
    Args:
        visits_text: Text representation of visits number
        
    Returns:
        Integer visits count or None if parsing failed
    """
    if not visits_text or visits_text == 'null' or visits_text == '<1K':
        return None
        
    try:
        visits_text = str(visits_text).strip().upper()
        
        # Handle format like "402K" or "1.5M"
        if 'K' in visits_text:
            return int(float(visits_text.replace('K', '')) * 1000)
        elif 'M' in visits_text:
            return int(float(visits_text.replace('M', '')) * 1000000)
        elif 'B' in visits_text:
            return int(float(visits_text.replace('B', '')) * 1000000000)
        else:
            # Direct number or other format
            return int(float(visits_text.replace(',', '')))
            
    except (ValueError, TypeError):
        return None


def get_traffic_data(domain: str) -> Tuple[Optional[int], str]:
    """
    Synchronous wrapper for fetch_traffic_data function
    
    Args:
        domain: Domain to check
        
    Returns:
        Tuple of (monthly visits or None, source or error message)
    """
    try:
        return asyncio.run(fetch_traffic_data(domain))
    except Exception as e:
        error_msg = f"Error in sync wrapper for {domain}: {e}"
        logger.error(error_msg)
        return None, error_msg


def save_traffic_data(domain: str, product_id: int, visits: Optional[int], source: str) -> None:
    """
    Save traffic intelligence data to database
    
    Args:
        domain: Domain that was analyzed
        product_id: Foreign key to the discovered product
        visits: Monthly visits (None if error)
        source: Data source tier (extension, html, api)
    """
    try:
        with get_session() as session:
            # Check if we already have traffic data for this product
            query = select(TrafficIntelligence).where(TrafficIntelligence.discovered_product_id == product_id)
            existing = session.exec(query).first()
            
            if existing:
                # Update existing record
                existing.monthly_visits = visits
                existing.data_source = source
                existing.updated_at = datetime.now()
                session.add(existing)
            else:
                # Create new record
                traffic_intel = TrafficIntelligence(
                    domain=domain,
                    monthly_visits=visits,
                    data_source=source,
                    updated_at=datetime.now(),
                    discovered_product_id=product_id
                )
                session.add(traffic_intel)
                
            session.commit()
            logger.info(f"Saved traffic data for {domain}: {visits if visits else 'No data'} visits")
    except Exception as e:
        logger.error(f"Failed to save traffic data for {domain}: {e}")


# Legacy compatibility function
def fetch_estimated_visits_sync(domain: str) -> Optional[int]:
    """
    Legacy wrapper for backwards compatibility
    
    Args:
        domain: Domain name to analyze
        
    Returns:
        Estimated monthly visits or None if data unavailable
    """
    visits, _ = get_traffic_data(domain)
    return visits
