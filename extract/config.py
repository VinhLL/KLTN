"""Cấu hình và hằng số cho hệ thống."""

import os
from typing import List

# ===== DeepSeek API Configuration =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # deepseek-chat cho extraction, deepseek-reasoner cho reasoning phức tạp

# Legacy: Google API (không còn sử dụng)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Các loại thực thể hợp lệ
VALID_ENTITY_TYPES = [
    "Nhân Vật",
    "Tổ chức", 
    "Quốc gia",
    "Sự kiện",
    "Chiến dịch/Trận đánh",
    "Hội nghị",
    "Văn kiện/Hiệp định",
    "Địa điểm",
    "Chiến lược/Chủ trương",
    "Khái niệm",
    "Công trình"
]

# ===== JSON INPUT (Format mới - ưu tiên sử dụng) =====
JSON_INPUT_FILE = r"SGK\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
USE_JSON_FORMAT = True  # Set False để dùng format txt cũ

# ===== Token Optimization =====
MAX_TOKENS_PER_CHUNK = 800  # Giảm từ mặc định để tối ưu API calls
OVERLAP_SENTENCES = 1  # Số câu overlap giữa chunks
USE_COMPACT_CONTEXT = True  # Dùng context ngắn gọn

# Danh sách file đầu vào (format txt cũ - backup)
INPUT_FILES = [
    "SGK/Nguồn/Chủ đề 1/Bài 1.txt",
    "SGK/Nguồn/Chủ đề 1/Bài 2.txt",
    "SGK/Nguồn/Chủ đề 1/Bài 3.txt",
    "SGK/Nguồn/Chủ đề 2/Bài 4.txt",
    "SGK/Nguồn/Chủ đề 2/Bài 5.txt",
    "SGK/Nguồn/Chủ đề 3/Bài 6.txt",
    "SGK/Nguồn/Chủ đề 3/Bài 7.txt",
    "SGK/Nguồn/Chủ đề 3/Bài 8.txt",
    "SGK/Nguồn/Chủ đề 3/Bài 9.txt",
    "SGK/Nguồn/Chủ đề 4/Bài 10.txt",
    "SGK/Nguồn/Chủ đề 4/Bài 11.txt",
    "SGK/Nguồn/Chủ đề 5/Bài 12.txt",
    "SGK/Nguồn/Chủ đề 5/Bài 13.txt",
    "SGK/Nguồn/Chủ đề 5/Bài 14.txt",
    "SGK/Nguồn/Chủ đề 6/Bài 15.txt",
    "SGK/Nguồn/Chủ đề 6/Bài 16.txt",
    "SGK/Nguồn/Chủ đề 6/Bài 17.txt",
]

# Cấu hình xử lý
WINDOW_SIZE = 5
API_DELAY_SECONDS = 2  # DeepSeek có rate limit tốt hơn Gemini
SIMILARITY_THRESHOLD = 0.95
TIMELINE_SIMILARITY_THRESHOLD = 0.9
MAX_SENTENCES_PER_DATE = 3
MAX_TEXTS_PER_GROUP = 3