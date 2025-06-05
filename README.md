# Market Intelligence Pipeline

A production-ready, real-time market intelligence pipeline that discovers and analyzes competitor products through Facebook ads and enriches them with traffic data.

## 🏗️ Architecture

```
┌─────────────────┐     SSE      ┌──────────────────┐     ┌─────────────────┐
│  Next.js UI     │◄────────────►│  FastAPI Backend │────▶│  SQLite DB      │
│  (Port 3000)    │              │  (Port 8000)     │     │                 │
│                 │              │                  │     └─────────────────┘
│ • Dashboard     │              │ • REST API       │              │
│ • Real-time     │              │ • SSE Streaming  │              ▼
│   Progress      │              │ • Metrics        │     ┌──────────────┐
│ • Results View  │              │ • Health Checks  │────▶│ External APIs│
└─────────────────┘              └──────────────────┘     │ • Apify      │
                                                           │ • ScraperAPI │
                                                           └──────────────┘
```

### Key Features
- **Real-time Progress Streaming**: Server-Sent Events (SSE) for live pipeline updates
- **Structured Logging**: JSON logs with correlation IDs for request tracing
- **Metrics & Monitoring**: Prometheus-compatible `/metrics` endpoint
- **Retry Logic**: Exponential backoff for external API resilience
- **Full Observability**: Health checks, detailed logging, and error tracking

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Start the entire stack
docker compose up --build

# Access the application
# UI: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd frontend && npm install

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys:
# - APIFY_TOKEN
# - SCRAPER_API_KEY

# 3. Start backend
python app_server.py

# 4. Start frontend (new terminal)
cd frontend && npm run dev
```

## 🔧 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `APIFY_TOKEN` | Apify API token for Facebook ad scraping | Yes |
| `SCRAPER_API_KEY` | ScraperAPI key for traffic data | Yes |
| `CORS_ORIGIN` | Frontend URL for CORS (default: http://localhost:3000) | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No |

## 📊 API Endpoints

### Pipeline Management
- `POST /pipeline/run` - Start analysis for a keyword
- `GET /pipeline/status/{keyword}` - Get pipeline status
- `GET /pipeline/stream/{keyword}` - SSE stream for real-time updates

### Results & Analytics  
- `GET /results/products` - Query discovered products
- `GET /results/traffic` - Get traffic intelligence data
- `GET /dashboard/stats` - Dashboard statistics

### Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /metrics/health/detailed` - Detailed component health

## 🧪 Testing

```bash
# Run backend tests
pytest tests/backend/test_e2e_pipeline.py -v

# Run specific e2e test
pytest tests/backend/test_e2e_pipeline.py::test_full_pipeline_e2e -v

# Run with coverage
pytest --cov=api --cov=app tests/
```

### Test Coverage
- E2E pipeline test with `atlas_test` keyword
- Concurrent pipeline handling
- Error scenarios
- API endpoint verification
- Database integrity checks

## 📈 Monitoring & Observability

### Metrics
Access Prometheus-compatible metrics at `http://localhost:8000/metrics`:
- Request counts and latency
- Pipeline success/failure rates  
- Database statistics
- Memory usage

### Logs
Structured JSON logs are written to `logs/app.log` with:
- Correlation IDs for request tracing
- Log rotation (10MB max, 5 backups)
- Real-time streaming to UI

### Health Checks
- Basic: `GET /health`
- Detailed: `GET /metrics/health/detailed`

## 🚦 Common Operations

### Run Analysis for a Keyword
```bash
# Via API
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"keyword": "fitness", "max_ads": 20}'

# Via CLI
python run_one_keyword.py --keyword "fitness" --max-ads 20
```

### Monitor Real-time Progress
1. Open dashboard at http://localhost:3000
2. Enter keyword and click "Run Pipeline" 
3. Watch live progress with streaming logs

### Export Results
```bash
# Get products as JSON
curl "http://localhost:8000/results/products?keyword=fitness&format=json" > products.json

# Get traffic data
curl "http://localhost:8000/results/traffic?keyword=fitness" > traffic.json
```

## 🔍 Troubleshooting

### Pipeline Failures
1. Check logs: `tail -f logs/app.log | jq .`
2. Verify API keys in `.env`
3. Check external API quotas
4. Review correlation ID in logs for failed request

### Connection Issues
- Frontend can't reach backend: Check CORS settings
- SSE disconnects: Check nginx/proxy buffering settings
- Database locked: Ensure single writer with SQLite

### Performance Issues
- Slow Step 1: Apify API latency (normal: 15-20s)
- Slow Step 2: Rate limiting on traffic API
- High memory: Check `/metrics/health/detailed`

## 📊 Database Schema

### Core Tables
- `keyword` - Search keywords and their status
- `discoveredproduct` - Products found via Facebook ads
- `trafficintelligence` - Website traffic metrics
- `contentanalysis` - AI-powered content classification

### Key Relationships
```
keyword (1) ─── (N) discoveredproduct (1) ─── (N) trafficintelligence
                           │
                           └──── (N) contentanalysis
```

## 🚀 Scaling Roadmap

### Phase 1: Current (SQLite + Single Instance)
- ✅ Suitable for <100 concurrent users
- ✅ Handles ~1000 keywords/day
- ✅ Simple deployment

### Phase 2: PostgreSQL + Redis
- Multiple API instances
- Redis for caching & queues
- PostgreSQL for concurrency
- ~10,000 keywords/day

### Phase 3: Distributed Processing  
- Celery for task distribution
- S3 for result storage
- Kubernetes deployment
- Unlimited scale

## 🛠️ Development

### Code Structure
```
minimal_app/
├── api/                 # FastAPI backend
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   └── utils/          # Helpers
├── app/                # Core pipeline
│   ├── core/          # Scraping logic
│   └── models/        # Database models  
├── frontend/          # Next.js UI
└── tests/            # Test suites
```

### Adding New Features
1. Add router in `api/routers/`
2. Implement service in `api/services/`
3. Update models if needed
4. Add tests
5. Update API docs

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit pull request

## 📝 License

This project is proprietary and confidential.