"""Điểm khởi đầu chính của ứng dụng - Hỗ trợ JSON Hierarchical Processing."""

import os
import time
from datetime import datetime
import config
import text_processor
import api_handler
import entity_processor
import output_manager
from api_handler import reset_request_counter

# Import JSON processor mới
try:
    from json_processor import JSONTextbookProcessor, create_hierarchical_prompt
    JSON_PROCESSOR_AVAILABLE = True
except ImportError:
    JSON_PROCESSOR_AVAILABLE = False

# Fallback: json_reader cũ
try:
    from json_reader import create_windows_for_entity_extraction
    JSON_READER_AVAILABLE = True
except ImportError:
    JSON_READER_AVAILABLE = False


def process_entities_json_hierarchical() -> list:
    """
    Process entities từ JSON format với xử lý hierarchical theo section.
    Đảm bảo ngữ nghĩa hoàn chỉnh theo cấu trúc sách giáo khoa.
    
    LƯU Ý: Hàm này duyệt qua TẤT CẢ windows đã được chia nhỏ (bao gồm cả _part1, _part2...)
    thay vì duyệt qua chunks gốc.
    """
    reset_request_counter()
    all_entities = []
    
    print(f"\n{'='*60}")
    print("[JSON HIERARCHICAL MODE]")
    print(f"Loading from: {config.JSON_INPUT_FILE}")
    print(f"{'='*60}")
    
    # Load JSON với processor mới
    processor = JSONTextbookProcessor(config.JSON_INPUT_FILE, add_context=True)
    
    # In thống kê
    stats = processor.get_statistics()
    print(f"\nThống kê dữ liệu:")
    print(f"  - Tổng chunks (subsections): {stats['total_chunks']}")
    print(f"  - Tổng chủ đề: {stats['total_topics']}")
    print(f"  - Tổng bài: {stats['total_lessons']}")
    print(f"  - Tổng câu: {stats['total_sentences']}")
    print(f"  - Trung bình câu/chunk: {stats['avg_sentences_per_chunk']:.1f}")
    
    # Lấy windows theo format mới (đã bao gồm các chunks được chia nhỏ)
    windows = processor.to_windows_format(split_long_chunks=True)
    
    print(f"\nTotal semantic chunks (sau khi chia): {len(windows)}")
    print(f"Estimated processing time: {len(windows) * config.API_DELAY_SECONDS / 60:.1f} minutes")
    print("=" * 60)
    
    total_chunks = len(windows)
    current_topic = None
    topic_chunk_count = 0
    
    # Duyệt qua TẤT CẢ windows (bao gồm cả các phần đã chia)
    for current_chunk, window in enumerate(windows, 1):
        topic_id = window.get('topic_id', 'Unknown')
        topic_desc = window.get('topic_description', '')
        topic_name = f"{topic_id}: {topic_desc}" if topic_desc else topic_id
        
        # Hiển thị header topic khi chuyển sang topic mới
        if current_topic != topic_id:
            if current_topic is not None:
                print(f"   [Đã xử lý {topic_chunk_count} chunks trong topic trước]")
            
            # Đếm số chunks trong topic này
            topic_chunk_count = sum(1 for w in windows if w.get('topic_id') == topic_id)
            
            print(f"\n{'='*60}")
            print(f"[TOPIC] {topic_name}")
            print(f"   {topic_chunk_count} chunks trong chủ đề này")
            print("=" * 60)
            
            current_topic = topic_id
            topic_chunk_count = 0
        
        topic_chunk_count += 1
        
        # Hiển thị tiến độ chi tiết
        section_title = window.get('section_title', '')
        subsection_title = window.get('subsection_title', '')
        full_path = window.get('full_path', f"{topic_id}/{window.get('lesson_id', '')}")
        is_split = window.get('is_split_part', False)
        
        print(f"\n[{current_chunk}/{total_chunks}] {full_path}" + (" [SPLIT]" if is_split else ""))
        print(f"   Section: {section_title}")
        print(f"   Subsection: {subsection_title}")
        
        # Sử dụng hàm extract đã được cập nhật
        entities = api_handler.extract_entities_from_json_window(window)
        
        if not entities:
            print(f"   [!] No entities extracted")
            continue
        
        print(f"   [OK] Extracted {len(entities)} entities")
        
        for entity in entities:
            similar_entity = entity_processor.find_similar_entity(entity, all_entities)
            
            if similar_entity:
                if entity_processor.merge_entities(similar_entity, entity):
                    print(f"      [Merged] {entity['id']}")
            else:
                all_entities.append(entity)
                print(f"      [New] {entity['id']} ({entity['type']})")
    
    # Post-process all entities
    print(f"\n{'='*60}")
    print("POST-PROCESSING")
    print("=" * 60)
    
    all_entities = entity_processor.post_process_entities(all_entities)
    
    # Áp dụng làm sạch cuối cùng nếu có
    if hasattr(entity_processor, 'cleanup_entities'):
        all_entities = entity_processor.cleanup_entities(all_entities)
    
    print(f"Final entities count: {len(all_entities)}")
    
    return all_entities


def process_entities_json() -> list:
    """Process entities từ JSON format (fallback to old method if needed)."""
    # Ưu tiên dùng hierarchical processor mới
    if JSON_PROCESSOR_AVAILABLE:
        return process_entities_json_hierarchical()
    
    # Fallback to old json_reader
    if not JSON_READER_AVAILABLE:
        print("[ERROR] No JSON processor available!")
        return []
    
    reset_request_counter()
    all_entities = []
    
    print(f"\n[JSON MODE - Legacy] Loading from: {config.JSON_INPUT_FILE}")
    
    windows = create_windows_for_entity_extraction(
        config.JSON_INPUT_FILE, 
        window_size=config.WINDOW_SIZE
    )
    
    print(f"Total windows: {len(windows)}")
    print(f"Estimated processing time: {len(windows) * config.API_DELAY_SECONDS / 60:.1f} minutes")
    print("=" * 60)
    
    for idx, window in enumerate(windows):
        print(f"\n[Progress: {idx + 1}/{len(windows)} windows]")
        
        entities = api_handler.extract_entities_from_json_window(window)
        
        for entity in entities:
            similar_entity = entity_processor.find_similar_entity(entity, all_entities)
            
            if similar_entity:
                if entity_processor.merge_entities(similar_entity, entity):
                    print(f"    Merged entity: {entity['id']}")
            else:
                all_entities.append(entity)
                print(f"    New entity: {entity['id']} ({entity['type']})")
    
    all_entities = entity_processor.post_process_entities(all_entities)
    
    return all_entities


def process_entities_txt() -> list:
    """Process entities từ TXT format (cũ)."""
    reset_request_counter()
    all_entities = []
    
    file_contents = text_processor.read_files(config.INPUT_FILES)
    
    total_windows = 0
    for file_path, content in file_contents.items():
        if not content:
            continue
        sentences = text_processor.split_sentences_vietnamese(content)
        windows = text_processor.create_non_overlapping_windows(sentences, window_size=config.WINDOW_SIZE)
        total_windows += len(windows)
    
    print(f"\n[TXT MODE] Total estimated API requests (windows): {total_windows}")
    print(f"Estimated processing time: {total_windows * config.API_DELAY_SECONDS / 60:.1f} minutes")
    print("=" * 60)
    
    current_window = 0
    
    for file_path, content in file_contents.items():
        if not content:
            continue
            
        print(f"\nProcessing {file_path}...")
        
        sentences = text_processor.split_sentences_vietnamese(content)
        windows = text_processor.create_non_overlapping_windows(sentences, window_size=config.WINDOW_SIZE)
        
        for window in windows:
            current_window += 1
            print(f"\n[Progress: {current_window}/{total_windows} windows]")
            
            entities = api_handler.extract_entities_with_gemini(window, file_path)
            
            for entity in entities:
                similar_entity = entity_processor.find_similar_entity(entity, all_entities)
                
                if similar_entity:
                    if entity_processor.merge_entities(similar_entity, entity):
                        print(f"    Merged entity: {entity['id']}")
                else:
                    all_entities.append(entity)
                    print(f"    New entity: {entity['id']} ({entity['type']})")
    
    all_entities = entity_processor.post_process_entities(all_entities)
    
    return all_entities


def process_entities() -> list:
    """Main function to process all files and extract entities.
    Tự động chọn JSON hoặc TXT format dựa trên config.
    """
    use_json = getattr(config, 'USE_JSON_FORMAT', False)
    
    if use_json:
        json_file = getattr(config, 'JSON_INPUT_FILE', None)
        if json_file and os.path.exists(json_file):
            if JSON_PROCESSOR_AVAILABLE:
                print("[MODE] JSON Hierarchical Processing (semantic chunking)")
                return process_entities_json_hierarchical()
            elif JSON_READER_AVAILABLE:
                print("[MODE] JSON Legacy Processing")
                return process_entities_json()
            else:
                print("[WARNING] No JSON processor available!")
                print("[FALLBACK] Using TXT format...")
        else:
            print(f"[WARNING] JSON file not found: {json_file}")
            print("[FALLBACK] Using TXT format...")
    
    print("[MODE] TXT Processing")
    return process_entities_txt()


def main():
    """Hàm main chính."""
    print("=" * 60)
    print("ENTITY EXTRACTION - DeepSeek API")
    print("=" * 60)
    print(f"USE_JSON_FORMAT: {getattr(config, 'USE_JSON_FORMAT', False)}")
    print(f"JSON_PROCESSOR_AVAILABLE: {JSON_PROCESSOR_AVAILABLE}")
    print(f"API: DeepSeek ({config.DEEPSEEK_BASE_URL})")
    print(f"Model: {getattr(config, 'DEEPSEEK_MODEL', 'deepseek-chat')}")
    
    # Kiểm tra API key
    if not os.environ.get('DEEPSEEK_API_KEY'):
        print("\n[ERROR] DEEPSEEK_API_KEY environment variable is not set!")
        print("Hãy set biến môi trường trước khi chạy:")
        print("  PowerShell: $env:DEEPSEEK_API_KEY = 'your-key'")
        print("  CMD: set DEEPSEEK_API_KEY=your-key")
        return
    
    print(f"API Key: {os.environ.get('DEEPSEEK_API_KEY')[:8]}...OK")
    
    # Xử lý entities
    entities = process_entities()
    
    # Lưu kết quả
    output_manager.save_entities(entities)
    
    print("\n" + "=" * 60)
    print("Entity extraction completed!")
    print(f"Total entities: {len(entities)}")
    print("=" * 60)


if __name__ == "__main__":
    main()