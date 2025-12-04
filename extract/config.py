"""Cấu hình và hằng số cho hệ thống."""

import os
from typing import List

# Cấu hình API
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

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

# Danh sách file đầu vào
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
API_DELAY_SECONDS = 7
SIMILARITY_THRESHOLD = 0.95
TIMELINE_SIMILARITY_THRESHOLD = 0.9
MAX_SENTENCES_PER_DATE = 3
MAX_TEXTS_PER_GROUP = 3