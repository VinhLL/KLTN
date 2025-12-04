"""Xử lý API Gemini."""

import json
import re
import time
from datetime import datetime
from typing import List, Dict, Any
import google.generativeai as genai
import config
import utils
import text_processor
from topic_processor import TopicProcessor
from entity_processor import (
    should_skip_entity, validate_entity_type_for_topic,
    apply_topic_specific_rules, enhance_properties_for_topic,
    create_topic_specific_metadata
)

# Biến toàn cục để theo dõi request
REQUEST_COUNTER = 0
REQUEST_DETAILS = []


def extract_entities_with_gemini(window: Dict, file_path: str) -> List[Dict]:
    """Use Gemini API to extract entities from text với xử lý theo chủ đề."""
    global REQUEST_COUNTER, REQUEST_DETAILS
    
    topic, lesson = utils.extract_topic_and_lesson(file_path)
    
    # Xác định cấu hình theo chủ đề
    topic_config = TopicProcessor.get_topic_config(topic)
    
    # Chuẩn bị văn bản với từ viết tắt đã được mở rộng
    processed_text = text_processor.expand_acronyms(window['text'], topic_config)
    window_copy = window.copy()
    window_copy['text'] = processed_text
    
    # Tạo prompt đặc thù cho chủ đề
    prompt = TopicProcessor.create_topic_prompt(processed_text, file_path, topic_config)
    
    try:
        REQUEST_COUNTER += 1
        request_start_time = time.time()
        
        current_request = {
            'request_number': REQUEST_COUNTER,
            'file_path': file_path,
            'topic': topic,
            'lesson': lesson,
            'window_index': window['window_index'],
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'text_length': len(window['text']),
            'sentences_count': len(window['sentences']),
            'topic_specific': bool(topic_config),
            'acronyms_expanded': len(topic_config.get('acronyms', {})) if topic_config else 0
        }
        
        topic_short = topic[:30] + "..." if len(topic) > 30 else topic
        print(f"  [Request #{REQUEST_COUNTER}] {topic_short} - {lesson} - Window {window['window_index'] + 1}")
        
        time.sleep(config.API_DELAY_SECONDS)
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        
        current_request.update({
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processing_time_seconds': round(processing_time, 2),
            'status': 'success',
            'response_length': len(response.text) if response.text else 0
        })
        
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                entities_data = json.loads(json_match.group())
                entities_count = len(entities_data.get('entities', []))
                
                current_request.update({
                    'entities_extracted': entities_count,
                    'response_valid': True
                })
                
                processed_entities = []
                
                for entity in entities_data.get('entities', []):
                    # KIỂM TRA NGUYÊN TẮC: Không extract entity quá chung
                    if should_skip_entity(entity, topic_config):
                        continue
                    
                    # Áp dụng rules đặc thù theo chủ đề
                    entity = apply_topic_specific_rules(entity, topic, topic_config)
                    
                    # Find occurrences in the window
                    occurrences = text_processor.find_entity_occurrences(entity, window, topic, lesson)
                    
                    if not occurrences:
                        continue
                    
                    # Tăng cường properties với thông tin thời gian
                    enhanced_properties = enhance_properties_for_topic(entity, window['text'], topic_config)
                    
                    processed_entity = {
                        'id': entity.get('id', '').strip(),
                        'label': utils.clean_labels([entity['id']] + entity.get('label', [])),
                        'type': validate_entity_type_for_topic(entity.get('type', ''), topic_config),
                        'description': entity.get('description', ''),
                        'original_text': occurrences,
                        'properties': enhanced_properties,
                        'confidence': entity.get('confidence', 0.9),
                        'metadata': create_topic_specific_metadata(entity, window, topic, lesson, topic_config),
                        'occurrence_count': len(occurrences),
                        'window_indices': [window['window_index']],
                        'topic_period': topic_config.get('time_period', '') if topic_config else ''
                    }
                    processed_entities.append(processed_entity)
                
                current_request['entities_processed'] = len(processed_entities)
                
            except json.JSONDecodeError as e:
                current_request.update({
                    'entities_extracted': 0,
                    'entities_processed': 0,
                    'response_valid': False,
                    'error_message': f'JSON decode error: {e}'
                })
                processed_entities = []
        else:
            current_request.update({
                'entities_extracted': 0,
                'entities_processed': 0,
                'response_valid': False
            })
            processed_entities = []
            
        REQUEST_DETAILS.append(current_request)
        print(f"  [Request #{REQUEST_COUNTER}] Completed - Extracted {len(processed_entities)} entities")
        
        return processed_entities
            
    except Exception as e:
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        
        current_request.update({
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processing_time_seconds': round(processing_time, 2),
            'status': 'error',
            'error_message': str(e),
            'entities_extracted': 0,
            'entities_processed': 0,
            'response_valid': False
        })
        
        REQUEST_DETAILS.append(current_request)
        print(f"  [Request #{REQUEST_COUNTER}] Error: {e}")
        return []


def get_request_details() -> List[Dict]:
    """Lấy danh sách chi tiết request."""
    return REQUEST_DETAILS


def get_request_counter() -> int:
    """Lấy số lượng request."""
    return REQUEST_COUNTER


def reset_request_counter() -> None:
    """Reset bộ đếm request."""
    global REQUEST_COUNTER, REQUEST_DETAILS
    REQUEST_COUNTER = 0
    REQUEST_DETAILS = []