"""Điểm khởi đầu chính của ứng dụng."""

import os
import time
from datetime import datetime
import config
import text_processor
import api_handler
import entity_processor
import output_manager
from api_handler import reset_request_counter


def process_entities() -> list:
    """Main function to process all files and extract entities."""
    # Reset counters
    reset_request_counter()
    
    all_entities = []
    
    file_contents = text_processor.read_files(config.INPUT_FILES)
    
    # Tính toán tổng số window trước để ước lượng
    total_windows = 0
    for file_path, content in file_contents.items():
        if not content:
            continue
        sentences = text_processor.split_sentences_vietnamese(content)
        windows = text_processor.create_non_overlapping_windows(sentences, window_size=config.WINDOW_SIZE)
        total_windows += len(windows)
    
    print(f"\nTotal estimated API requests (windows): {total_windows}")
    print(f"Estimated processing time: {total_windows * config.API_DELAY_SECONDS / 60:.1f} minutes (with rate limiting)")
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
            print(f"  Processing window {window['window_index'] + 1}/{len(windows)} of current file")
            
            entities = api_handler.extract_entities_with_gemini(window, file_path)
            
            for entity in entities:
                similar_entity = entity_processor.find_similar_entity(entity, all_entities)
                
                if similar_entity:
                    if entity_processor.merge_entities(similar_entity, entity):
                        print(f"    Merged entity: {entity['id']}")
                else:
                    all_entities.append(entity)
                    print(f"    New entity: {entity['id']} ({entity['type']})")
    
    # Post-process all entities
    all_entities = entity_processor.post_process_entities(all_entities)
    
    return all_entities


def main():
    """Hàm main chính."""
    print("Starting entity extraction with improved logic...")
    
    # Cấu hình API
    import google.generativeai as genai
    genai.configure(api_key=config.GOOGLE_API_KEY)
    
    # Xử lý entities
    entities = process_entities()
    
    # Lưu kết quả
    output_manager.save_entities(entities)
    
    print("Entity extraction completed.")


if __name__ == "__main__":
    main()