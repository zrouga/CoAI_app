#!/bin/bash
#
# Stack startup script for Windsurf development environment
# Starts the FastAPI backend and Next.js frontend with Docker Compose

# Set strict error handling
set -euo pipefail

APP_DIR="/Users/salimzrouga/Desktop/COai product research/step1/minimal_app"
cd "${APP_DIR}"

# Create docker-compose.dev.yml file with log configurations
echo "🔄 Creating development Docker Compose file with log configurations..."
cat > "${APP_DIR}/docker-compose.dev.yml" << EOF
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - CORS_ORIGIN=http://localhost:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 10s
    command: >
      sh -c "python app_server.py 2>&1 | tee /app/logs/backend.log"
    # Reason 1: Capturing logs to a file enables persistent debugging
    # Reason 2: Using tee maintains console output while also logging to file

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./logs:/app/logs
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api
    command: >
      sh -c "node server.js 2>&1 | tee /app/logs/ui.log"
    # Reason 1: Frontend logs are crucial for debugging UI rendering issues
    # Reason 2: Separation of UI logs from backend simplifies issue tracking
EOF
# Reason 1: Custom dev compose file allows development-specific configurations
# Reason 2: Separating dev from production compose improves deployment pipeline safety

echo "🔄 Loading environment variables from .env..."
# Source environment variables
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
    # Reason 1: Environment variables configure app behavior properly
    # Reason 2: Loading .env ensures consistent configuration across services
else
    echo "⚠️ Warning: .env file not found, using default configurations"
fi

# Ensure log directory exists
mkdir -p logs
# Reason 1: Logs directory must exist before container mounting
# Reason 2: Ensures Docker doesn't create directory with root ownership

echo "🔄 Starting services with Docker Compose..."
docker compose -f docker-compose.dev.yml up --build -d
# Reason 1: Building ensures latest code changes are included
# Reason 2: Detached mode (-d) allows script to continue for health checks

echo "🔄 Waiting for services to be healthy..."
# Function to check if API is healthy
check_api_health() {
    curl -s http://localhost:8000/health > /dev/null
    return $?
}

# Function to check if frontend is running
check_frontend_health() {
    curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|304"
    return $?
}

# Wait for API to become healthy
echo "  ⏳ Waiting for API to become available..."
COUNTER=0
until check_api_health || [ $COUNTER -eq 30 ]; do
    echo -n "."
    sleep 2
    ((COUNTER++))
done

if [ $COUNTER -eq 30 ]; then
    echo "❌ API failed to start properly within timeout period"
    echo "   Check logs at: ${APP_DIR}/logs/backend.log"
    exit 1
fi
echo "✅ API is healthy!"

# Wait for frontend to become healthy
echo "  ⏳ Waiting for frontend to become available..."
COUNTER=0
until check_frontend_health || [ $COUNTER -eq 30 ]; do
    echo -n "."
    sleep 2
    ((COUNTER++))
done

if [ $COUNTER -eq 30 ]; then
    echo "❌ Frontend failed to start properly within timeout period"
    echo "   Check logs at: ${APP_DIR}/logs/ui.log"
    exit 1
fi
echo "✅ Frontend is healthy!"

# Start tailing logs with Windsurf
echo "🔄 Starting log streaming with Windsurf..."
( windsurf logs --combined > ./logs/windsurf.log 2>&1 & )
# Reason 1: Background streaming ensures logs are captured from the beginning
# Reason 2: Combined logs provide a chronological view of the entire stack

echo ""
echo "🟢 STACK READY"
echo "   API: http://localhost:8000"
echo "   UI: http://localhost:3000"
echo "   Logs: ${APP_DIR}/logs/"
