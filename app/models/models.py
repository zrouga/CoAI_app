from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship


class KeywordStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductCategory(str, Enum):
    ECOMMERCE = "ecommerce"
    AFFILIATE = "affiliate"
    APP = "app"
    SERVICE = "service"
    CONTENT = "content"
    OTHER = "other"


class Keyword(SQLModel, table=True):
    """Keywords processed for market intelligence"""
    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str = Field(index=True, unique=True)
    status: KeywordStatus = Field(default=KeywordStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)
    processed_at: Optional[datetime] = Field(default=None, index=True)
    
    # Processing results
    total_ads_found: Optional[int] = Field(default=0)
    total_products_discovered: Optional[int] = Field(default=0)
    processing_duration_seconds: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    
    # Relationships
    discovered_products: List["DiscoveredProduct"] = Relationship(back_populates="keyword")


class DiscoveredProduct(SQLModel, table=True):
    """Products discovered through Facebook ad intelligence"""
    id: Optional[int] = Field(default=None, primary_key=True)
    keyword_id: Optional[int] = Field(default=None, foreign_key="keyword.id", index=True)
    
    # Product Identity
    product_page_url: str = Field(index=True, unique=True)  # Landing page URL
    brand_domain: str = Field(index=True)                   # Root domain (e.g., shopify.com)
    brand_name: Optional[str] = Field(default=None)         # Brand/business name
    facebook_page_url: Optional[str] = Field(default=None)  # Facebook business page
    facebook_page_id: Optional[str] = Field(default=None, index=True)
    
    # Discovery Timeline
    first_discovered: datetime = Field(default_factory=datetime.now, index=True)
    last_seen_advertising: Optional[datetime] = Field(default=None, index=True)
    
    # === AD INTELLIGENCE DATA ===
    
    # Campaign Duration & Activity
    ad_campaign_duration_days: Optional[int] = Field(default=None, index=True)  # How long they've been advertising
    total_active_ads: Optional[int] = Field(default=None)                       # Number of different ads running
    
    # Ad Spend Intelligence (monthly estimates)
    min_monthly_ad_spend: Optional[int] = Field(default=None)      # Minimum spend range
    max_monthly_ad_spend: Optional[int] = Field(default=None)      # Maximum spend range  
    estimated_monthly_ad_spend: Optional[int] = Field(default=None, index=True)  # Best estimate
    
    # Impression & Reach Data
    min_monthly_impressions: Optional[int] = Field(default=None)      # Minimum impression range
    max_monthly_impressions: Optional[int] = Field(default=None)      # Maximum impression range
    estimated_monthly_impressions: Optional[int] = Field(default=None, index=True)  # Best estimate
    
    # Platform & Geographic Intelligence
    advertising_platforms_count: Optional[int] = Field(default=None)     # Number of platforms (FB, IG, etc.)
    advertising_platforms: Optional[str] = Field(default=None)           # Comma-separated platform list
    target_countries_count: Optional[int] = Field(default=None)          # Geographic targeting breadth
    target_countries: Optional[str] = Field(default=None)                # Comma-separated country list
    
    # === MARKETING PSYCHOLOGY ANALYSIS ===
    
    # Promotional Strategies
    features_discount_offer: Optional[bool] = Field(default=None)    # Uses discount/sale language
    features_urgency_language: Optional[bool] = Field(default=None)  # Uses urgency tactics ("limited time")
    features_purchase_cta: Optional[bool] = Field(default=None)      # Has direct purchase call-to-action
    features_social_proof: Optional[bool] = Field(default=None)      # Uses testimonials/reviews
    features_free_shipping: Optional[bool] = Field(default=None)     # Mentions free shipping
    
    # Creative Elements
    primary_call_to_action: Optional[str] = Field(default=None)      # Main CTA type (shop_now, buy_now, etc.)
    ad_creative_themes: Optional[str] = Field(default=None)          # Comma-separated themes
    
    # Properties for backward compatibility with existing code
    @property
    def landing_url(self) -> str:
        return self.product_page_url
        
    @property
    def root_domain(self) -> str:
        return self.brand_domain
        
    @property
    def days_running(self) -> Optional[int]:
        return self.ad_campaign_duration_days
            
    @property
    def avg_ad_spend(self) -> Optional[int]:
        return self.estimated_monthly_ad_spend
        
    @property
    def avg_impressions(self) -> Optional[int]:
        return self.estimated_monthly_impressions
    
    # Relationships
    keyword: Optional[Keyword] = Relationship(back_populates="discovered_products")
    traffic_intelligence: List["TrafficIntelligence"] = Relationship(back_populates="discovered_product")
    content_analysis: List["ContentAnalysis"] = Relationship(back_populates="discovered_product")


class TrafficIntelligence(SQLModel, table=True):
    """Website traffic intelligence for discovered products"""
    id: Optional[int] = Field(default=None, primary_key=True)
    discovered_product_id: int = Field(foreign_key="discoveredproduct.id", index=True)
    
    # Website Performance Metrics
    estimated_monthly_website_visits: Optional[int] = Field(default=None, index=True)
    website_global_rank: Optional[int] = Field(default=None)
    website_country_rank: Optional[int] = Field(default=None)
    bounce_rate_percentage: Optional[float] = Field(default=None)
    avg_session_duration_seconds: Optional[int] = Field(default=None)
    pages_per_session: Optional[float] = Field(default=None)
    
    # Traffic Sources
    direct_traffic_percentage: Optional[float] = Field(default=None)
    search_traffic_percentage: Optional[float] = Field(default=None)
    social_traffic_percentage: Optional[float] = Field(default=None)
    paid_traffic_percentage: Optional[float] = Field(default=None)
    
    # Data Quality & Timing
    data_source: Optional[str] = Field(default="free_analysis")  # free_analysis, similarweb_api, etc.
    data_confidence_level: Optional[str] = Field(default="medium")  # low, medium, high
    data_collected_at: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = Field(default=None)
    
    # Backward compatibility properties
    @property
    def est_monthly_visits(self) -> Optional[int]:
        return self.estimated_monthly_website_visits
        
    @property
    def monthly_visits(self) -> Optional[int]:
        return self.estimated_monthly_website_visits
    
    # Relationships
    discovered_product: DiscoveredProduct = Relationship(back_populates="traffic_intelligence")


class ContentAnalysis(SQLModel, table=True):
    """AI-powered content analysis for discovered products"""
    id: Optional[int] = Field(default=None, primary_key=True)
    discovered_product_id: int = Field(foreign_key="discoveredproduct.id", index=True)
    
    # Product Classification
    product_category: Optional[ProductCategory] = Field(default=None, index=True)
    category_confidence_score: Optional[float] = Field(default=None)  # 0.0 to 1.0
    
    # Content Intelligence
    product_title: Optional[str] = Field(default=None)
    product_description_excerpt: Optional[str] = Field(default=None)
    key_features_detected: Optional[str] = Field(default=None)  # Comma-separated
    price_range_detected: Optional[str] = Field(default=None)   # "$20-30", "Under $50", etc.
    
    # E-commerce Intelligence
    has_multiple_variants: Optional[bool] = Field(default=None)     # Size/color options
    has_customer_reviews: Optional[bool] = Field(default=None)      # Review system present
    has_live_chat: Optional[bool] = Field(default=None)            # Customer support
    checkout_complexity: Optional[str] = Field(default=None)        # simple, moderate, complex
    
    # Analysis Metadata
    analysis_method: Optional[str] = Field(default="ai_analysis")   # ai_analysis, manual, pre_filter
    processing_time_seconds: Optional[float] = Field(default=None)
    raw_ai_response: Optional[str] = Field(default=None)
    analyzed_at: datetime = Field(default_factory=datetime.now)
    
    # Backward compatibility properties
    @property
    def category(self) -> Optional[ProductCategory]:
        return self.product_category
        
    @property
    def confidence(self) -> Optional[float]:
        return self.category_confidence_score
    
    # Relationships
    discovered_product: DiscoveredProduct = Relationship(back_populates="content_analysis")


# Legacy compatibility aliases for existing code
LandingPage = DiscoveredProduct
TrafficMetric = TrafficIntelligence
PageCategory = ContentAnalysis
CategoryType = ProductCategory