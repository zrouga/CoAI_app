"""
Enhanced logging configuration for the Market Intelligence API

This module sets up structured logging with detailed formatting
to help with debugging and troubleshooting.
"""
import os
import sys
import logging
import structlog
from pathlib import Path

# Ensure log directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure standard logging with file handler
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, "api_debug.log"), mode="a")
    ]
)

# Configure structured logging with enhanced processors
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create a special handler for the detailed debug log file
file_handler = logging.FileHandler(os.path.join(log_dir, "api_detailed.log"), mode="a")
file_handler.setLevel(logging.DEBUG)

# Create a processor formatter for the file handler
processor_formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(colors=False)
)
file_handler.setFormatter(processor_formatter)

# Add the special handler to the root logger
logging.getLogger().addHandler(file_handler)

# Set SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Helper function to get a structured logger
def get_logger(name):
    """Get a structured logger with the given name"""
    return structlog.get_logger(name)
