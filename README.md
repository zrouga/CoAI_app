# Minimal Market Intelligence Pipeline

A lean, standalone implementation of a 2-step market intelligence pipeline:
1. **Keyword → Facebook Ads → Landing URLs** (via Apify)
2. **Domain → Free Traffic Enrichment** (via SimilarWeb + ScraperAPI)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline
python run_one_keyword.py --keyword "keto" --max-ads 10
```

## Project Structure

```
minimal_app/
├─ run_one_keyword.py      # Main pipeline runner
├─ .env                    # API keys (already configured)
├─ .env.example           # Example environment variables
├─ requirements.txt        # Minimal dependencies
├─ app/
│   ├─ core/
│   │   ├─ step1_keyword_scraper.py      # Facebook ad scraper
│   │   └─ free_traffic_analyzer.py      # SimilarWeb traffic data enrichment
│   ├─ models/
│   │   └─ models.py       # SQLModel database schemas
│   └─ database/
│       └─ db.py           # Database connection
├─ app/config/
│   └─ blacklisted_domains.csv     # Domains to exclude
└─ data/
    └─ database.db         # SQLite database (auto-created)
```

## Environment Variables

The `.env` file should be configured with these API keys:
- `APIFY_TOKEN` - For Facebook ad scraping (Step 1)
- `SCRAPER_API_KEY` - For SimilarWeb traffic data via ScraperAPI proxy (Step 2)

## Usage Examples

### Basic Pipeline Run
```bash
python run_one_keyword.py --keyword "supplements" --max-ads 20
```

### Try Different Keywords
```bash
python run_one_keyword.py --keyword "keto" --max-ads 10
python run_one_keyword.py --keyword "skincare" --max-ads 15
python run_one_keyword.py --keyword "fitness" --max-ads 25
```

## Expected Output

```
🚀 SINGLE KEYWORD PIPELINE: 'keto'
================================================================================
📋 Configuration: max_ads=10, keyword='keto'

👉 STEP 1 START: Facebook Ad Scraping
✅ STEP 1 END: Found 8 products in 15.2s

👉 STEP 2 START: Traffic Data Enrichment
✅ STEP 2 END: Enriched 3/8 domains in 8.1s

🎉 PIPELINE COMPLETE!
⏱️  Total Duration: 23.3s
📊 Final Results:
   ├─ Products Discovered: 8
   └─ Traffic Enriched: 3
```

## Performance Notes

- **Step 1**: ~15-20 seconds (Apify API calls)
- **Step 2**: ~1-2 seconds per domain (SimilarWeb traffic data via ScraperAPI)
- **Total**: ~20-30 seconds for 10 products

## Troubleshooting

### No products found
- Try different keywords: "jewelry", "fitness", "skincare"
- Increase `--max-ads` parameter
- Check Apify token validity

### Traffic data unavailable
- Normal for new/small domains
- SimilarWeb may not have data for very new or low-traffic sites
- ScraperAPI quota may be exhausted

## Database Schema

All data is stored in SQLite with two main tables:
- `discoveredproduct` - Facebook ad intelligence from Step 1
- `trafficintelligence` - Website traffic data from Step 2

See `app/models/models.py` for complete schema.

## Next Steps

1. **Scale Up**: Process multiple keywords in batch
2. **Export Data**: Query SQLite database directly
3. **Improve Traffic Analysis**: Add more data sources or fallback options if needed
4. **Add Custom Analytics**: Build reporting on top of the collected data

---

This is a minimal, production-ready implementation focusing on the core Steps 1-2 functionality.