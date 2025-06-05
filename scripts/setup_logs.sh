#!/bin/bash
#
# Log setup script for Windsurf development environment
# Creates and configures daily-rotating log files with proper permissions

# Set strict error handling
set -e

APP_DIR="/Users/salimzrouga/Desktop/COai product research/step1/minimal_app"
LOG_DIR="${APP_DIR}/logs"

echo "🔄 Setting up logging environment..."

# Ensure logs directory exists
mkdir -p "${LOG_DIR}"
# Reason 1: Directory might not exist in fresh clones
# Reason 2: Ensures consistent location for all log files

# Create log files with proper permissions if they don't exist
touch "${LOG_DIR}/backend.log"
# Reason 1: Backend logs need to be collected for debugging FastAPI issues
# Reason 2: Pre-creating the file ensures proper ownership and permissions

touch "${LOG_DIR}/ui.log"
# Reason 1: UI logs help debug frontend Next.js rendering and API call issues
# Reason 2: Separating frontend logs from backend helps with focused debugging

touch "${LOG_DIR}/windsurf.log"
# Reason 1: Windsurf CLI logs need separate tracking to isolate framework issues
# Reason 2: Centralizing Windsurf logs helps troubleshoot configuration problems

# Create log rotation configuration
cat > "${APP_DIR}/logrotate.conf" << EOF
${LOG_DIR}/backend.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(id -gn)
    postrotate
        touch ${LOG_DIR}/backend.log
    endscript
}

${LOG_DIR}/ui.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(id -gn)
    postrotate
        touch ${LOG_DIR}/ui.log
    endscript
}

${LOG_DIR}/windsurf.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(id -gn)
    postrotate
        touch ${LOG_DIR}/windsurf.log
    endscript
}
EOF
# Reason 1: Log rotation prevents disk space issues from log growth
# Reason 2: Daily rotation with 7-day history provides sufficient debugging trail

# Configure Windsurf to tail logs
cat > "${APP_DIR}/.windsurf.yml" << EOF
log_config:
  enabled: true
  live_tail: true
  files:
    - path: ${LOG_DIR}/backend.log
      type: backend
      # Reason 1: Identifying backend logs helps filter views in the Windsurf dashboard
      # Reason 2: Backend logs need higher priority for debugging API issues
      
    - path: ${LOG_DIR}/ui.log
      type: frontend
      # Reason 1: UI logs need separate tracking from backend for cleaner debugging
      # Reason 2: Different formatting rules apply to frontend vs backend logs
      
    - path: ${LOG_DIR}/windsurf.log
      type: system
      # Reason 1: System logs from Windsurf need different parsing rules
      # Reason 2: Separating Windsurf logs allows targeted debugging of the framework
EOF
# Reason 1: Windsurf needs explicit configuration to know which logs to tail
# Reason 2: Configuration ensures consistent log management across team environments

echo "✅ Log setup complete! Logs will be available in ${LOG_DIR}"
echo "✅ Windsurf configured to tail logs in real-time"
