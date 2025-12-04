#config.py
import os
from typing import List, Dict, Any

# Get the root directory (KLTN folder)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths
ENTITY_FILE = os.path.join(ROOT_DIR, "extract", "entities", "entities_20251202_171911.json")
OUTPUT_JSON = os.path.join(ROOT_DIR, "knowledge_graph_historical_v2.json")

# Input files
INPUT_FILES = [
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 1", "Bài 1.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 1", "Bài 2.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 1", "Bài 3.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 2", "Bài 4.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 2", "Bài 5.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 3", "Bài 6.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 3", "Bài 7.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 3", "Bài 8.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 3", "Bài 9.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 4", "Bài 10.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 4", "Bài 11.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 5", "Bài 12.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 5", "Bài 13.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 5", "Bài 14.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 6", "Bài 15.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 6", "Bài 16.txt"),
    os.path.join(ROOT_DIR, "SGK", "Nguồn", "Chủ đề 6", "Bài 17.txt"),
]

# API Configuration
def get_api_key() -> str:
    """Get API key from environment variables."""
    for i in range(1, 9):
        key = os.environ.get(f"GOOGLE_API_KEY_{i}")
        if key:
            return key
    return os.environ.get("GOOGLE_API_KEY", "")

# Processing parameters
WINDOW_SIZE = 8
STEP_SIZE = 3
MAX_ENTITIES_PER_PROMPT = 500
MAX_RETRIES = 3
REQUEST_DELAY = 2

# Validation parameters
MIN_EVIDENCE_LENGTH = 5
MIN_PREDICATE_LENGTH = 2
MAX_PREDICATE_LENGTH = 300

# Topic-specific processing flags
ENABLE_TOPIC_SPECIFIC_PROCESSING = True
ENABLE_SUPPLEMENTAL_EXTRACTION = True
ENABLE_THEMATIC_GROUPING = True