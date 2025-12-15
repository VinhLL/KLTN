# Kiến trúc Hệ thống Relationship Extraction (Extract_kg)

## Tổng quan

Hệ thống **Extract_kg** (Relationship Extraction) được thiết kế để trích xuất **quan hệ (relationships/triplets)** giữa các thực thể lịch sử đã được trích xuất trước đó từ hệ thống `extract`. Mục tiêu cuối cùng là xây dựng **Knowledge Graph** hoàn chỉnh với các nodes (entities) và edges (relationships).

## So sánh với Extract (Entity Extraction)

| Tiêu chí | Extract (Entity) | Extract_kg (Relationship) |
|----------|------------------|---------------------------|
| **Input** | SGK JSON | SGK JSON + entities.json |
| **Output** | entities.json | knowledge_graph.json |
| **Mục tiêu** | Trích xuất thực thể | Trích xuất quan hệ |
| **Chunks** | 76 → 195 (split) | 76 → 311 (với overlap) |
| **API calls** | ~195 | ~311 |

## Sơ đồ Component

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INPUT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   SGK JSON Input    │     │   Entities JSON     │                   │
│  │   (Sách giáo khoa)  │     │   (625 entities)    │                   │
│  └──────────┬──────────┘     └──────────┬──────────┘                   │
│             │                           │                               │
│             └───────────┬───────────────┘                               │
└─────────────────────────┼───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   JSON Processor    │────▶│   Semantic Chunks   │                   │
│  │  json_processor.py  │     │  76 → 311 (overlap) │                   │
│  └─────────────────────┘     └──────────┬──────────┘                   │
│         │                               │                               │
│         │ config                        │                               │
│         ▼                               ▼                               │
│  ┌─────────────────────┐     ┌─────────────────────┐                   │
│  │   Entity Lookup     │────▶│   Text Processor    │                   │
│  │  entity_processor   │     │  text_processor.py  │                   │
│  │  (625 entities)     │     │  (Context windows)  │                   │
│  └─────────────────────┘     └──────────┬──────────┘                   │
│         │                               │                               │
│         ▼                               │                               │
│  ┌─────────────────────┐                │                               │
│  │   Topic Processor   │────────────────┤                               │
│  │  topic_processor.py │                │                               │
│  │  (Prompt đặc thù)   │                │                               │
│  └─────────────────────┘                │                               │
│                                         ▼                               │
│                              ┌─────────────────────┐                    │
│                              │Relationship Processor│                   │
│                              │relationship_processor│                   │
│                              │  (Extract triplets) │                    │
│                              └──────────┬──────────┘                    │
└─────────────────────────────────────────┼───────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                                │
│  │    API Handler      │  Gọi DeepSeek API với prompt relationship     │
│  │   api_handler.py    │  JSON parsing, retry logic, error handling    │
│  └──────────┬──────────┘                                                │
│             │                                                            │
│             ▼                                                            │
│  ┌─────────────────────┐                                                │
│  │   DeepSeek API      │  Model: deepseek-chat                         │
│  │   (External)        │  Trích xuất relationships dạng JSON           │
│  └──────────┬──────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         KG BUILDING LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                                │
│  │     KG Builder      │  Build knowledge graph từ relationships       │
│  │   kg_builder.py     │  Merge, validate, supplement unconnected      │
│  └──────────┬──────────┘                                                │
│             │                                                            │
│             ▼                                                            │
│  ┌─────────────────────┐                                                │
│  │   Output Manager    │  Save knowledge_graph.json                    │
│  │  output_manager.py  │  Statistics, diagnostics                      │
│  └──────────┬──────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    knowledge_graph.json                          │   │
│  │   ┌─────────────┐            ┌─────────────┐                    │   │
│  │   │  Entities   │            │  Triplets   │                    │   │
│  │   │  (625 nodes)│────────────│ (1500+ edges│                    │   │
│  │   └─────────────┘            └─────────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Mô tả các Component

### 1. Input Layer

#### Input Files
- **SGK JSON**: `SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json` - Sách giáo khoa dạng JSON
- **Entities JSON**: `entities_20251210_103252.json` - 625 entities đã trích xuất

### 2. Processing Layer

#### `json_processor.py` (22KB)
- **Class `SemanticChunk`**: Đơn vị ngữ nghĩa từ sách
- **Class `JSONTextbookProcessor`**: Xử lý file JSON
- **Chiến lược Overlap Chunking**: 7 câu/chunk, 5 câu overlap
- Chia chunks dài (>10 câu hoặc >1200 chars) thành nhiều phần
- **Output**: 76 chunks gốc → 311 chunks sau khi chia với overlap

#### `entity_processor.py` (5KB)
- Xử lý và validate entities
- Tạo entity lookup dictionary từ file entities.json

#### `text_processor.py` (15KB)
- `find_context_windows_combined()`: Tìm context windows
- `get_compact_context()`: Tạo context ngắn gọn
- Mapping entities với text chunks

#### `topic_processor.py` (237KB - file lớn nhất!)
- **Class `TopicProcessor`**: Xử lý đặc thù theo chủ đề
- Prompt riêng cho từng chủ đề lịch sử
- Xử lý các patterns, keywords, acronyms đặc thù

#### `relationship_processor.py` (25KB)
- **`validate_relationship()`**: Validate relationship với entity lookup
- **`merge_relationships()`**: Gộp relationships trùng lặp
- **`extract_relationships_from_json_chunk()`**: Trích xuất từ chunk
- **`process_json_chunks_for_relationships()`**: Xử lý tất cả chunks

### 3. API Layer

#### `api_handler.py` (9KB)
- **`get_deepseek_client()`**: Khởi tạo DeepSeek client
- **`call_deepseek_api()`**: Gọi API với retry logic
- **`fix_json_string()`**: Sửa JSON malformed
- **`extract_json_from_text()`**: Parse JSON từ response
- Tracking: API_REQUEST_COUNT, API_ERROR_COUNT

### 4. KG Building Layer

#### `kg_builder.py` (33KB)
- **Class `KnowledgeGraphBuilder`**: Builder chính
  - **`build_from_json()`**: Build KG từ JSON format
  - **`_process_lesson_json()`**: Xử lý từng lesson
  - **`_add_relationships_from_json()`**: Thêm relationships
  - **`supplement_unconnected_entities()`**: Bổ sung entities chưa có quan hệ
  - **`process_thematic_groups()`**: Xử lý nhóm chủ đề
  - **`_create_knowledge_graph()`**: Tạo KG model cuối cùng

#### `output_manager.py` (7KB)
- Lưu Knowledge Graph ra JSON
- Tạo báo cáo thống kê

### 5. Support Modules

#### `models.py` (3KB)
- **Class `Entity`**: Model entity
- **Class `Triplet`**: Model triplet (Subject, Predicate, Object)
- **Class `KnowledgeGraph`**: Model KG hoàn chỉnh

#### `topic_config.py` (29KB)
- Cấu hình đặc thù cho từng chủ đề
- Keywords, patterns, acronyms

#### `utils.py` (5KB)
- Utility functions dùng chung

## Pipeline Flow (benchmark_extract_kg.ipynb)

```
1. [Setup] Nhập API Key → Set environment variable
           ↓
2. [Config] Load config.py → Verify JSON + Entity files
           ↓
3. [Test API] Gọi DeepSeek API test → Verify connection
           ↓
4. [Load Entities] Load 625 entities → Tạo entity_lookup
           ↓
5. [Statistics] JSONTextbookProcessor.get_statistics()
           → 76 chunks, 6 chủ đề, 17 bài, 782 câu
           ↓
6. [Split Chunks with Overlap]
           → 76 chunks → 311 chunks (7 câu/chunk, 5 overlap)
           ↓
7. [Process Loop] For each chunk:
   │  a. Filter entities trong chunk text
   │  b. Tạo relationship extraction prompt
   │  c. Gọi DeepSeek API
   │  d. Parse JSON response
   │  e. Validate relationships với entity_lookup
   │  f. Merge duplicate relationships
   │  └─→ Thêm vào all_relationships list
           ↓
8. [Post-Process] validate, merge, deduplicate
           ↓
9. [Build KG] KnowledgeGraphBuilder
           → Tạo nodes từ entities
           → Tạo edges từ relationships
           → Supplement unconnected entities
           ↓
10. [Output] Save knowledge_graph.json
```

## Relationship/Triplet Structure

```json
{
  "subject": "Liên hợp quốc",
  "predicate": "được thành lập vào năm",
  "object": "1945",
  "evidence": "Liên hợp quốc được thành lập vào năm 1945...",
  "source": {
    "topic": "Chủ đề 1",
    "lesson": "Bài 1",
    "section": "Một số vấn đề cơ bản về Liên hợp quốc"
  },
  "occurrence_count": 3
}
```

## Metrics từ benchmark_extract_kg.ipynb

- **Input Entities**: 625 entities (11 types)
- **Input Chunks**: 76 semantic chunks
- **After Split**: 311 chunks (với overlap 7 câu/chunk, 5 overlap)
- **API calls**: 311 requests to DeepSeek
- **Raw relationships**: ~3000+
- **Valid relationships**: ~1500+ (sau khi validate với entity_lookup)
- **Output**: knowledge_graph_historical_v4.json

## Entity Statistics (Input)

| Type | Count |
|------|-------|
| Địa điểm | 147 |
| Tổ chức | 103 |
| Khái niệm | 86 |
| Văn kiện/Hiệp định | 59 |
| Sự kiện | 50 |
| Quốc gia | 44 |
| Chiến lược/Chủ trương | 36 |
| Hội nghị | 30 |
| Chiến dịch/Trận đánh | 27 |
| Nhân Vật | 25 |
| Công trình | 18 |
| **Total** | **625** |
