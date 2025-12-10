"""Quản lý đầu ra và thống kê."""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import config
import utils
from models import Entity


def save_request_statistics(entities: List[Dict]) -> None:
    """Save detailed request statistics to a separate JSON file.
    
    Hỗ trợ cả TXT format (có file_path) và JSON format (có topic/lesson/section).
    Xử lý an toàn các trường hợp thiếu trường hoặc giá trị None.
    """
    from api_handler import get_request_details, get_request_counter
    
    request_details = get_request_details()
    total_requests = get_request_counter()
    
    if not request_details:
        return
    
    # Tính toán tổng hợp thống kê - sử dụng .get() an toàn
    successful_requests = sum(1 for req in request_details if req.get('status') == 'success')
    failed_requests = sum(1 for req in request_details if req.get('status') == 'error')
    
    # Tính thời gian xử lý - xử lý an toàn giá trị None hoặc string
    total_processing_time = 0
    for req in request_details:
        time_val = req.get('processing_time_seconds', 0)
        if isinstance(time_val, (int, float)):
            total_processing_time += time_val
    
    avg_processing_time = total_processing_time / total_requests if total_requests > 0 else 0
    
    # Tính số entity trung bình - xử lý an toàn
    total_entities_extracted = 0
    total_entities_processed = 0
    for req in request_details:
        extracted = req.get('entities_extracted', 0)
        processed = req.get('entities_processed', 0)
        if isinstance(extracted, (int, float)):
            total_entities_extracted += int(extracted)
        if isinstance(processed, (int, float)):
            total_entities_processed += int(processed)
    
    avg_entities_per_request = total_entities_extracted / successful_requests if successful_requests > 0 else 0
    
    # Thống kê theo file/section (hỗ trợ cả TXT và JSON format)
    requests_by_file = {}
    for req in request_details:
        # Lấy file_path hoặc fallback sang section path cho JSON format
        file_path = req.get('file_path', '')
        if not file_path:
            # Tạo path từ topic/lesson/section cho JSON format
            topic = req.get('topic', 'Unknown')
            lesson = req.get('lesson', '')
            section = req.get('section', '')
            
            # Xử lý an toàn None values
            topic = str(topic) if topic else 'Unknown'
            lesson = str(lesson) if lesson else ''
            section = str(section) if section else ''
            
            file_path = f"{topic}/{lesson}/{section}" if section else f"{topic}/{lesson}"
        
        if file_path not in requests_by_file:
            requests_by_file[file_path] = {
                'request_count': 0,
                'entities_extracted': 0,
                'entities_processed': 0
            }
        requests_by_file[file_path]['request_count'] += 1
        
        # Xử lý an toàn khi cộng entities
        extracted = req.get('entities_extracted', 0)
        processed = req.get('entities_processed', 0)
        if isinstance(extracted, (int, float)):
            requests_by_file[file_path]['entities_extracted'] += int(extracted)
        if isinstance(processed, (int, float)):
            requests_by_file[file_path]['entities_processed'] += int(processed)
    
    # Thống kê theo topic
    requests_by_topic = {}
    for req in request_details:
        topic = req.get('topic', 'Unknown')
        topic = str(topic) if topic else 'Unknown'
        
        if topic not in requests_by_topic:
            requests_by_topic[topic] = {
                'request_count': 0,
                'entities_extracted': 0,
                'entities_processed': 0
            }
        requests_by_topic[topic]['request_count'] += 1
        
        # Xử lý an toàn khi cộng entities
        extracted = req.get('entities_extracted', 0)
        processed = req.get('entities_processed', 0)
        if isinstance(extracted, (int, float)):
            requests_by_topic[topic]['entities_extracted'] += int(extracted)
        if isinstance(processed, (int, float)):
            requests_by_topic[topic]['entities_processed'] += int(processed)
    
    # Tạo summary
    summary = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'success_rate': round(successful_requests / total_requests * 100, 2) if total_requests > 0 else 0,
        'total_processing_time_seconds': round(total_processing_time, 2),
        'average_processing_time_seconds': round(avg_processing_time, 2),
        'total_entities_extracted': total_entities_extracted,
        'total_entities_processed': total_entities_processed,
        'average_entities_per_request': round(avg_entities_per_request, 2),
        'requests_by_file': requests_by_file,
        'requests_by_topic': requests_by_topic,
        'final_entities_count': len(entities)
    }
    
    # Lưu chi tiết request và summary
    output_data = {
        'summary': summary,
        'request_details': request_details
    }
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stats_filename = f"entities/request_statistics_{timestamp}.json"
    
    # Đảm bảo thư mục tồn tại
    os.makedirs('entities', exist_ok=True)
    
    with open(stats_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== REQUEST STATISTICS ===")
    print(f"Total API Requests: {total_requests}")
    print(f"Successful: {successful_requests} ({summary['success_rate']}%)")
    print(f"Failed: {failed_requests}")
    print(f"Total Processing Time: {total_processing_time:.2f}s")
    print(f"Average per Request: {avg_processing_time:.2f}s")
    print(f"Total Entities Extracted: {total_entities_extracted}")
    print(f"Total Entities Processed: {total_entities_processed}")
    print(f"Final Unique Entities: {len(entities)}")
    print(f"Statistics saved to: {stats_filename}")
    
    # In thống kê theo file/section
    print(f"\n=== REQUESTS BY SOURCE ===")
    for file_path, stats in requests_by_file.items():
        # Lấy phần cuối của path để hiển thị ngắn gọn
        display_name = file_path.split('/')[-1] if '/' in file_path else os.path.basename(file_path)
        if not display_name:
            display_name = file_path[:50] + "..." if len(file_path) > 50 else file_path
        print(f"{display_name}: {stats['request_count']} requests, {stats['entities_processed']} entities")


def save_entities(entities: List[Dict]) -> None:
    """Save entities to JSON file with compact format."""
    # Convert to Entity objects for validation
    entity_objects = []
    for entity_dict in entities:
        try:
            entity_obj = Entity(**entity_dict)
            entity_objects.append(entity_obj)
        except Exception as e:
            print(f"Error creating Entity object: {e}")
            continue
    
    # Đảm bảo thư mục tồn tại
    os.makedirs('entities', exist_ok=True)
    
    # Save entities to JSON with compact format
    output_data = []
    for entity in entity_objects:
        entity_dict = entity.dict()
        
        # Compact the original_text by grouping consecutive occurrences
        grouped_occurrences = utils.group_consecutive_occurrences(entity_dict['original_text'])
        entity_dict['original_text'] = grouped_occurrences
        
        output_data.append(entity_dict)
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    entities_filename = f"entities/entities_{timestamp}.json"
    
    with open(entities_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, separators=(',', ':'))
    
    # Lưu thống kê request
    save_request_statistics(entities)
    
    # Print summary
    type_count = defaultdict(int)
    for entity in entity_objects:
        type_count[entity.type] += 1
    
    print("\n" + "=" * 60)
    print("=== EXTRACTION SUMMARY ===")
    print(json.dumps(dict(type_count), ensure_ascii=False, indent=2))
    print(f"Total unique entities: {len(entity_objects)}")
    print(f"Entities saved to: {entities_filename}")
    print("=" * 60)