#!/bin/bash
#
# Kill script for resetting Windsurf development environment
# Identifies and terminates orphaned backend and frontend processes

# Set strict error handling
set -e

echo "🔄 Starting environment reset process..."

# Kill Python processes (Backend FastAPI)
echo "🔍 Finding and killing Python processes..."
pkill -f "uvicorn.*api.main:app" || echo "No FastAPI processes found" 
# Reason 1: FastAPI runs with uvicorn that might leave orphaned processes
# Reason 2: We specifically target api.main:app to avoid killing unrelated Python processes

# Kill Node.js processes (Frontend Next.js)
echo "🔍 Finding and killing Node.js processes..."
pkill -f "node.*server.js" || echo "No Next.js processes found"
# Reason 1: Next.js server processes can continue running even after Docker is stopped
# Reason 2: We target server.js to specifically kill the Next.js server

# Kill any Docker containers related to our stack
echo "🔍 Stopping Docker containers..."
docker compose -f docker-compose.yml down 2>/dev/null || echo "No Docker containers to stop"
# Reason 1: Docker containers may still be running and need to be explicitly stopped
# Reason 2: Using compose down ensures volumes and networks are properly cleaned up

# Free up specific ports
echo "🔍 Checking and freeing ports..."
# Port 3000 (UI)
lsof -ti:3000 | xargs kill -9 2>/dev/null || echo "Port 3000 is free"
# Reason 1: Port 3000 is used by the Next.js frontend and must be available for restart
# Reason 2: Force kill (-9) ensures the port is freed even if process is hanging

# Port 8000 (API)
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "Port 8000 is free" 
# Reason 1: Port 8000 is used by the FastAPI backend and must be available for restart
# Reason 2: Using lsof ensures we kill processes regardless of what application is using them

# Port 9229 (Node.js Debug)
lsof -ti:9229 | xargs kill -9 2>/dev/null || echo "Port 9229 is free"
# Reason 1: Port 9229 is used for Node.js debugging and must be freed
# Reason 2: Debugging sessions can often be orphaned when development is interrupted

echo "✅ Environment successfully reset!"
