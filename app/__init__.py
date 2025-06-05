"""
Step 1: Keyword Scraper Application Package
Enhanced e-commerce product research with winner detection
"""

import sys
import os
from pathlib import Path

# Ensure the project root is in the Python path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

__version__ = "2.0.0"
__author__ = "E-Commerce Research Team" 