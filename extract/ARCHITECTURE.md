# Kiến trúc Hệ thống Entity Extraction

## Tổng quan

Hệ thống Entity Extraction được thiết kế để trích xuất các thực thể lịch sử từ sách giáo khoa Lịch sử 12 (Kết Nối Tri Thức). Hệ thống sử dụng DeepSeek API để phân tích văn bản và trích xuất các thực thể như nhân vật, sự kiện, tổ chức, địa điểm, v.v.

## Sơ đồ Component

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INPUT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                                │
│  │   SGK JSON Input    │  SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json         │
│  │   (Sách giáo khoa)  │  Cấu trúc: Chủ đề → Bài → Section → Subsection│
│  └──────────┬──────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   JSON Processor    │────▶│   Semantic Chunks   │                   │
│  │  json_processor.py  │     │  76 → 195 chunks    │                   │
│  └─────────────────────┘     └──────────┬──────────┘                   │
│         │                               │                               │
│         │ config                        │                               │
│         ▼                               ▼                               │
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   Topic Config      │────▶│   Text Processor    │                   │
│  │  topic_config.py    │     │  text_processor.py  │                   │
│  └─────────────────────┘     └──────────┬──────────┘                   │
│         │                               │                               │
│         ▼                               │                               │
│  ┌─────────────────────┐                │                               │
│  │   Topic Processor   │────────────────┤                               │
│  │  topic_processor.py │                │                               │
│  │  (Prompt đặc thù)   │                │                               │
│  └─────────────────────┘                │                               │
└─────────────────────────────────────────┼───────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                                │
│  │    API Handler      │  Gọi DeepSeek API với prompt đặc thù          │
│  │   api_handler.py    │  Rate limiting, retry logic, error handling   │
│  └──────────┬──────────┘                                                │
│             │                                                            │
│             ▼                                                            │
│  ┌─────────────────────┐                                                │
│  │   DeepSeek API      │  Model: deepseek-chat                         │
│  │   (External)        │  Trích xuất entities dạng JSON                │
│  └──────────┬──────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         POST-PROCESSING LAYER                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                                │
│  │  Entity Processor   │  Parse JSON response, merge entities          │
│  │ entity_processor.py │  Validate types, deduplicate, apply rules     │
│  └──────────┬──────────┘                                                │
│             │                                                            │
│             ▼                                                            │
│  ┌─────────────────────┐                                                │
│  │   Output Manager    │  Save entities.json, statistics.json          │
│  │  output_manager.py  │  Generate extraction statistics               │
│  └──────────┬──────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   entities.json     │     │   statistics.json   │                   │
│  │   (Knowledge Base)  │     │   (Request stats)   │                   │
│  └─────────────────────┘     └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Mô tả các Component

### 1. Input Layer

#### `config.py`
- Cấu hình toàn cục cho hệ thống
- API keys (DeepSeek)
- Đường dẫn file JSON input
- Các hằng số: WINDOW_SIZE, API_DELAY, SIMILARITY_THRESHOLD
- Danh sách VALID_ENTITY_TYPES

### 2. Processing Layer

#### `json_processor.py`
- **Class `SemanticChunk`**: Đại diện cho một đơn vị ngữ nghĩa từ sách
- **Class `JSONTextbookProcessor`**: Xử lý file JSON sách giáo khoa
- Chiến lược Hierarchical: Chủ đề → Bài → Section → Subsection
- Chia nhỏ chunks quá dài (>30 câu hoặc >2000 ký tự) thành 4 phần
- **Output**: 76 chunks gốc → 195 chunks sau khi split

#### `json_reader.py`
- Đọc và parse file JSON SGK
- Tạo TextChunk với metadata đầy đủ
- Hỗ trợ backward compatibility với format cũ

#### `text_processor.py`
- Xử lý văn bản: tách câu, tạo windows
- Tìm occurrences của entity trong text
- Mở rộng từ viết tắt (acronyms)

#### `topic_config.py`
- **Class `TopicConfig`**: Cấu hình cho từng chủ đề
- **Class `TopicConfigManager`**: Quản lý cấu hình tất cả chủ đề
- Định nghĩa priority_entities, required_keywords, acronyms cho mỗi chủ đề

#### `topic_processor.py`
- **Class `TopicProcessor`**: Xử lý đặc thù theo chủ đề
- Tạo prompt riêng cho từng chủ đề:
  - Chủ đề 1: Thế giới trong và sau Chiến tranh Lạnh
  - Chủ đề 2: ASEAN
  - Chủ đề 3: Lịch sử quân sự Việt Nam
  - Chủ đề 4: Công cuộc Đổi mới
  - Chủ đề 5: Lịch sử Đối ngoại
  - Chủ đề 6: Hồ Chí Minh

### 3. API Layer

#### `api_handler.py`
- Quản lý kết nối DeepSeek API
- **`call_deepseek_api()`**: Gọi API với retry logic
- **`extract_entities_from_json_window()`**: Trích xuất entities từ window
- Tạo prompt tối ưu với context hierarchical
- Theo dõi REQUEST_COUNTER và REQUEST_DETAILS

### 4. Post-Processing Layer

#### `entity_processor.py`
- **`find_similar_entity()`**: Tìm entity tương tự để merge
- **`merge_entities()`**: Gộp entities trùng lặp
- **`post_process_entities()`**: Xử lý hậu kỳ
- **`cleanup_entities()`**: Làm sạch danh sách cuối cùng
- Áp dụng rules đặc thù: HCM, Đổi mới, ASEAN, etc.

#### `output_manager.py`
- **`save_entities()`**: Lưu entities ra JSON
- **`save_request_statistics()`**: Lưu thống kê chi tiết

### 5. Support Modules

#### `models.py`
- **Class `Entity`**: Pydantic model cho entity
- **Class `RequestDetail`**: Chi tiết request API

#### `utils.py`
- `split_sentences_vietnamese()`: Tách câu tiếng Việt
- `clean_labels()`: Làm sạch labels
- `validate_entity_type()`: Validate loại entity
- `group_consecutive_occurrences()`: Nhóm occurrences liên tiếp

## Pipeline Flow (benchmark_extract.ipynb)

```
1. [Setup] Nhập API Key → Set environment variable
           ↓
2. [Config] Load config.py → Kiểm tra JSON file tồn tại
           ↓
3. [Test API] Gọi DeepSeek API test → Verify connection
           ↓
4. [Statistics] JSONTextbookProcessor.get_statistics()
           → Hiển thị: 76 chunks, 6 chủ đề, 17 bài, 782 câu
           ↓
5. [Import] Load all modules: text_processor, api_handler,
           entity_processor, output_manager, json_processor
           ↓
6. [Split Chunks] get_all_chunks_with_split()
           → 76 chunks → 195 chunks (chia nhỏ chunks dài)
           ↓
7. [Process Loop] For each chunk:
   │  a. Lấy topic_config từ TopicProcessor
   │  b. Tạo hierarchical prompt
   │  c. Gọi DeepSeek API
   │  d. Parse JSON response
   │  e. Validate entity types
   │  f. Find/merge similar entities
   │  g. Apply topic-specific rules
   │  └─→ Thêm vào all_entities list
           ↓
8. [Post-Process] cleanup_entities(), post_process_entities()
           ↓
9. [Output] save_entities() → entities.json
           save_request_statistics() → statistics.json
```

## Entity Types (Loại thực thể)

| Type | Mô tả | Ví dụ |
|------|-------|-------|
| Nhân Vật | Người lịch sử | Hồ Chí Minh, Ních-xơn |
| Tổ chức | Tổ chức, đảng phái | ASEAN, Liên hợp quốc |
| Quốc gia | Nước, vùng lãnh thổ | Việt Nam, Liên Xô |
| Sự kiện | Sự kiện lịch sử | Chiến tranh lạnh |
| Chiến dịch/Trận đánh | Chiến dịch quân sự | Điện Biên Phủ |
| Hội nghị | Hội nghị, đại hội | Hội nghị I-an-ta |
| Văn kiện/Hiệp định | Văn bản pháp lý | Hiến chương LHQ |
| Địa điểm | Địa danh | Xan Phran-xi-xcô |
| Chiến lược/Chủ trương | Đường lối, chính sách | Đổi mới |
| Khái niệm | Thuật ngữ | Toàn cầu hoá |
| Công trình | Công trình xây dựng | Lăng Chủ tịch |

## Metrics từ benchmark_extract.ipynb

- **Input**: 76 semantic chunks
- **After split**: 195 chunks (40 chunks được chia nhỏ)
- **API calls**: 195 requests to DeepSeek
- **Processing time**: ~6.5 phút (với API_DELAY=2s)
- **Output**: entities.json với ~300+ entities
