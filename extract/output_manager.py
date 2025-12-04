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
    """Save detailed request statistics to a separate JSON file."""
    from api_handler import get_request_details, get_request_counter
    
    request_details = get_request_details()
    total_requests = get_request_counter()
    
    if not request_details:
        return
    
    # Tính toán tổng hợp thống kê
    successful_requests = sum(1 for req in request_details if req['status'] == 'success')
    failed_requests = sum(1 for req in request_details if req['status'] == 'error')
    
    # Tính thời gian xử lý
    total_processing_time = sum(req.get('processing_time_seconds', 0) for req in request_details)
    avg_processing_time = total_processing_time / total_requests if total_requests > 0 else 0
    
    # Tính số entity trung bình
    total_entities_extracted = sum(req.get('entities_extracted', 0) for req in request_details)
    total_entities_processed = sum(req.get('entities_processed', 0) for req in request_details)
    
    avg_entities_per_request = total_entities_extracted / successful_requests if successful_requests > 0 else 0
    
    # Thống kê theo file
    requests_by_file = {}
    for req in request_details:
        file_path = req['file_path']
        if file_path not in requests_by_file:
            requests_by_file[file_path] = {
                'request_count': 0,
                'entities_extracted': 0,
                'entities_processed': 0
            }
        requests_by_file[file_path]['request_count'] += 1
        requests_by_file[file_path]['entities_extracted'] += req.get('entities_extracted', 0)
        requests_by_file[file_path]['entities_processed'] += req.get('entities_processed', 0)
    
    # Thống kê theo topic
    requests_by_topic = {}
    for req in request_details:
        topic = req['topic']
        if topic not in requests_by_topic:
            requests_by_topic[topic] = {
                'request_count': 0,
                'entities_extracted': 0,
                'entities_processed': 0
            }
        requests_by_topic[topic]['request_count'] += 1
        requests_by_topic[topic]['entities_extracted'] += req.get('entities_extracted', 0)
        requests_by_topic[topic]['entities_processed'] += req.get('entities_processed', 0)
    
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
    
    # In thống kê theo file
    print(f"\n=== REQUESTS BY FILE ===")
    for file_path, stats in requests_by_file.items():
        filename = os.path.basename(file_path)
        print(f"{filename}: {stats['request_count']} requests, {stats['entities_processed']} entities")


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