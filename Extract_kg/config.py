#config.py
import os
from typing import List, Dict, Any

# Get the root directory (KLTN folder)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ===== JSON INPUT (Format mới - ưu tiên sử dụng) =====
JSON_INPUT_FILE = r"SGK\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
USE_JSON_FORMAT = True  # Set False để dùng format txt cũ

# ===== Token Optimization =====
MAX_TOKENS_PER_CHUNK = 1200  # Giảm từ mặc định để tối ưu API calls
OVERLAP_SENTENCES = 1  # Số câu overlap giữa chunks
USE_COMPACT_CONTEXT = True  # Dùng context ngắn gọn

# File paths
ENTITY_FILE = os.path.join(ROOT_DIR, "outputs", "entities", "entities_20251210_103252.json")
OUTPUT_JSON = os.path.join(ROOT_DIR, "outputs", "kg", "knowledge_graph_historical_v4.json")

# Input files (format txt cũ - backup)
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

# ===== DeepSeek API Configuration =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # deepseek-chat cho extraction, deepseek-reasoner cho reasoning

# Legacy: Google API (không còn sử dụng)
def get_api_key() -> str:
    """Get DeepSeek API key from environment variables."""
    return os.environ.get("DEEPSEEK_API_KEY", "")

# Processing parameters
WINDOW_SIZE = 10
STEP_SIZE = 3
MAX_ENTITIES_PER_PROMPT = 300
MAX_RETRIES = 3
REQUEST_DELAY = 2

# Validation parameters
MIN_EVIDENCE_LENGTH = 10
MIN_PREDICATE_LENGTH = 3
MAX_PREDICATE_LENGTH = 200

# Topic-specific processing flags
ENABLE_TOPIC_SPECIFIC_PROCESSING = True
ENABLE_SUPPLEMENTAL_EXTRACTION = True
ENABLE_THEMATIC_GROUPING = True