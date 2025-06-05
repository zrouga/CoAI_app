// API Types for Market Intelligence Pipeline

export enum PipelineStatus {
  NOT_STARTED = "not_started",
  RUNNING_STEP1 = "running_step1",
  COMPLETED_STEP1 = "completed_step1",
  RUNNING_STEP2 = "running_step2",
  COMPLETED_STEP2 = "completed_step2",
  COMPLETED = "completed",
  FAILED = "failed"
}

// Request model for running the pipeline
export interface RunRequest {
  keyword: string;
  
  // Apify settings
  max_ads?: number;
  apify_actor?: string;
  country_code?: string;
  poll_interval_seconds?: number;
  apify_concurrency?: number;
  apify_timeout_seconds?: number;
  min_ad_spend_usd?: number;
  
  // Traffic/ScraperAPI settings
  scraper_api_key?: string;
  max_domains_per_minute?: number;
  domain_batch_size?: number;
  retry_attempts?: number;
  cache_ttl_days?: number;
  html_fallback_enabled?: boolean;
  
  // General settings
  log_level?: string;
  dry_run_mode?: boolean;
}

// Default values for RunRequest
export const DEFAULT_RUN_CONFIG: Omit<RunRequest, 'keyword'> = {
  max_ads: 50,
  apify_actor: "igolaizola/facebook-ad-library-scraper",
  country_code: "US",
  poll_interval_seconds: 15,
  apify_concurrency: 5,
  apify_timeout_seconds: 900,
  min_ad_spend_usd: 0,
  max_domains_per_minute: 40,
  domain_batch_size: 15,
  retry_attempts: 2,
  cache_ttl_days: 30,
  html_fallback_enabled: true,
  log_level: "INFO",
  dry_run_mode: false,
};

// Status response model
export interface KeywordStatus {
  keyword: string;
  status: PipelineStatus;
  step1_products: number;
  step2_enriched: number;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  errors: string[];
}

// Sparkline data for traffic (12 months)
export interface TrafficSparkline {
  months: string[];
  values: (number | null)[];
}

// Product result model
export interface ProductResult {
  id: number;
  brand_name?: string;
  brand_domain?: string;
  product_page_url: string;
  discovery_keyword: string;
  monthly_visits?: number;
  traffic_sparkline?: TrafficSparkline;
  ads_count: number;
  data_source?: string;
  discovered_at: string;
}

// Dashboard stats model
export interface DashboardStats {
  total_products: number;
  unique_domains: number;
  enriched_domains: number;
  total_keywords: number;
  recent_keywords: string[];
}

// Log entry model
export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  keyword?: string;
  context?: Record<string, any>;
}
