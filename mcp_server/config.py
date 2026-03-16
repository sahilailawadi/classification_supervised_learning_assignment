"""Configuration for MCP server"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Server configuration
SERVER_NAME = "perf-test-analyzer"
SERVER_VERSION = "0.1.0"

# Mode (academic or work)
MODE = os.getenv('LLM_MODE', 'work')

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
