# -*- coding: utf-8 -*-
"""Xử lý API DeepSeek cho Entity Extraction."""

import os
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
import config
import utils
import text_processor
from topic_processor import TopicProcessor
from entity_processor import (
    should_skip_entity, validate_entity_type_for_topic,
    apply_topic_specific_rules, enhance_properties_for_topic,
    create_topic_specific_metadata
)

# API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Biến toàn cục để theo dõi request
REQUEST_COUNTER = 0
REQUEST_DETAILS = []


def get_deepseek_client():
    """Get DeepSeek API client."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )


def call_deepseek_api(prompt: str, max_retries: int = 3, model: str = None) -> Optional[str]:
    """
    Call DeepSeek API với error handling.
    
    Returns:
        Response text hoặc None nếu lỗi
    """
    # Sử dụng model từ config nếu không được chỉ định
    if model is None:
        model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-chat')
    
    for attempt in range(max_retries):
        try:
            time.sleep(1)  # Rate limiting
            
            client = get_deepseek_client()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý trích xuất thực thể lịch sử Việt Nam. Luôn trả về kết quả dưới dạng JSON hợp lệ."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            print(f"API Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None
    
    return None


def extract_entities_with_gemini(window: Dict, file_path: str) -> List[Dict]:
    """
    Use DeepSeek API to extract entities from text với xử lý theo chủ đề.
    (Backward compatibility - tên hàm giữ nguyên)
    """
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
            'api': 'deepseek'
        }
        
        topic_short = topic[:30] + "..." if len(topic) > 30 else topic
        print(f"  [DeepSeek #{REQUEST_COUNTER}] {topic_short} - {lesson} - Window {window['window_index'] + 1}")
        
        time.sleep(config.API_DELAY_SECONDS)
        
        response_text = call_deepseek_api(prompt)
        
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        
        current_request.update({
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processing_time_seconds': round(processing_time, 2),
            'status': 'success' if response_text else 'error',
            'response_length': len(response_text) if response_text else 0
        })
        
        if not response_text:
            REQUEST_DETAILS.append(current_request)
            return []
        
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
        print(f"  [DeepSeek #{REQUEST_COUNTER}] Completed - Extracted {len(processed_entities)} entities")
        
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
        print(f"  [DeepSeek #{REQUEST_COUNTER}] Error: {e}")
        return []


def extract_entities_from_json_window(window: Dict) -> List[Dict]:
    """
    Extract entities từ JSON format window sử dụng DeepSeek API.
    Hỗ trợ cả hierarchical format mới và legacy format.
    """
    global REQUEST_COUNTER, REQUEST_DETAILS
    
    # Lấy metadata - hỗ trợ cả format mới và cũ
    topic = window.get('topic_id', window.get('topic', 'Unknown'))
    topic_desc = window.get('topic_description', '')
    lesson = window.get('lesson_id', window.get('lesson', 'Unknown'))
    lesson_title = window.get('lesson_title', '')
    
    # Xác định cấu hình theo chủ đề
    topic_config = TopicProcessor.get_topic_config(topic)
    
    # Lấy nội dung - hỗ trợ cả format mới (sentences list) và cũ (text string)
    if 'sentences' in window and isinstance(window['sentences'], list):
        raw_text = " ".join(window['sentences'])
    else:
        raw_text = window.get('text', window.get('combined_content', ''))
    
    # Chuẩn bị văn bản
    processed_text = text_processor.expand_acronyms(raw_text, topic_config)
    
    # Tạo context đầy đủ cho hierarchical format
    section_title = window.get('section_title', '')
    subsection_title = window.get('subsection_title', '')
    section_idx = window.get('section_index', '')
    subsection_label = window.get('subsection_label', '')
    
    # Context từ subsections lân cận (nếu có)
    context_before = window.get('context_before', '')
    context_after = window.get('context_after', '')
    
    # Tao compact context cho logging
    context_parts = [topic]
    if lesson:
        context_parts.append(lesson)
    if section_idx:
        context_parts.append(f"S{section_idx}")
    if subsection_label:
        context_parts.append(f"({subsection_label})")
    
    compact_context = " > ".join(context_parts)
    
    # Lay cau hinh theo topic description
    topic_for_path = topic_desc if topic_desc else topic
    topic_config = TopicProcessor.get_topic_config(topic_for_path)
    
    # Su dung prompt chi tiet de trich xuat nhieu entities
    prompt = _create_hierarchical_entity_prompt(
        text=processed_text,
        topic=topic,
        topic_desc=topic_desc,
        lesson=lesson,
        lesson_title=lesson_title,
        section_title=section_title,
        subsection_title=subsection_title,
        context_before=context_before,
        context_after=context_after,
        topic_config=topic_config
    )
    
    try:
        REQUEST_COUNTER += 1
        request_start_time = time.time()
        
        current_request = {
            'request_number': REQUEST_COUNTER,
            'topic': topic,
            'lesson': lesson,
            'section': section_title,
            'subsection': subsection_title,
            'window_index': window.get('window_index', 0),
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'text_length': len(processed_text),
            'format': 'json_hierarchical',
            'has_context': bool(context_before or context_after),
            'api': 'deepseek'
        }
        
        print(f"  [DeepSeek #{REQUEST_COUNTER}] {compact_context}")
        
        time.sleep(config.API_DELAY_SECONDS)
        
        response_text = call_deepseek_api(prompt)
        
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        
        current_request.update({
            'processing_time_seconds': round(processing_time, 2),
            'status': 'success' if response_text else 'error',
        })
        
        if not response_text:
            print(f"  [DeepSeek #{REQUEST_COUNTER}] ERROR: Empty response")
            REQUEST_DETAILS.append(current_request)
            return []
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                entities_data = json.loads(json_match.group())
                raw_entities = entities_data.get('entities', [])
                
                # Log số entities raw trước khi filter
                if not raw_entities:
                    print(f"  [DeepSeek #{REQUEST_COUNTER}] WARNING: API trả về 0 entities trong JSON")
                
                processed_entities = []
                skipped_count = 0
                
                for entity in raw_entities:
                    if should_skip_entity(entity, topic_config):
                        skipped_count += 1
                        continue
                    
                    entity = apply_topic_specific_rules(entity, topic, topic_config)
                    
                    # Tìm occurrences trong văn bản
                    try:
                        occurrences = text_processor.find_entity_occurrences(
                            entity, window, topic, lesson
                        )
                    except Exception as e:
                        # Fallback nếu có lỗi - thêm sentence_index để tránh KeyError
                        occurrences = [{
                            'topic': topic,
                            'lesson': lesson,
                            'sentence_index': 0,
                            'label': [entity.get('id', '')],
                            'exact_text': processed_text[:200] + '...',
                            'section': section_title,
                            'subsection': subsection_title
                        }]
                    
                    # Không bỏ qua entity nếu không tìm thấy - tạo occurrence mặc định
                    if not occurrences:
                        occurrences = [{
                            'topic': topic,
                            'lesson': lesson,
                            'sentence_index': 0,
                            'label': [entity.get('id', '')],
                            'exact_text': processed_text[:200] + '...',
                            'section': section_title,
                            'subsection': subsection_title,
                            'note': 'Auto-generated occurrence'
                        }]
                    
                    enhanced_properties = enhance_properties_for_topic(
                        entity, processed_text, topic_config
                    )
                    
                    processed_entity = {
                        'id': entity.get('id', '').strip(),
                        'label': utils.clean_labels([entity['id']] + entity.get('label', [])),
                        'type': validate_entity_type_for_topic(entity.get('type', ''), topic_config),
                        'description': entity.get('description', ''),
                        'original_text': occurrences,
                        'properties': enhanced_properties,
                        'confidence': entity.get('confidence', 0.9),
                        'metadata': {
                            'topic': topic,
                            'lesson': lesson,
                            'section': section_title,
                            'subsection': subsection_title,
                            'source_format': 'json_hierarchical'
                        },
                        'occurrence_count': len(occurrences),
                        'window_indices': [window.get('window_index', 0)],
                    }
                    processed_entities.append(processed_entity)
                
                current_request['entities_processed'] = len(processed_entities)
                
            except json.JSONDecodeError as e:
                current_request['error_message'] = f'JSON decode error: {e}'
                processed_entities = []
        else:
            processed_entities = []
        
        REQUEST_DETAILS.append(current_request)
        print(f"  [DeepSeek #{REQUEST_COUNTER}] Completed - Extracted {len(processed_entities)} entities")
        
        return processed_entities
        
    except Exception as e:
        print(f"  [DeepSeek #{REQUEST_COUNTER}] Error: {e}")
        return []


def _create_hierarchical_entity_prompt(
    text: str,
    topic: str,
    topic_desc: str,
    lesson: str,
    lesson_title: str,
    section_title: str,
    subsection_title: str,
    context_before: str,
    context_after: str,
    topic_config: Dict
) -> str:
    """
    Tạo prompt chi tiết để trích xuất nhiều entities.
    """
    entity_types = ", ".join(config.VALID_ENTITY_TYPES)
    
    # Prompt tiếng Việt có dấu, rõ ràng
    prompt = f"""Bạn là chuyên gia trích xuất thực thể từ sách giáo khoa Lịch sử Việt Nam.

**NGỮ CẢNH:**
- Chủ đề: {topic_desc}
- Bài học: {lesson_title}
- Phần: {section_title}
- Mục: {subsection_title}

**VĂN BẢN CẦN PHÂN TÍCH:**
{text}

**YÊU CẦU:** Hãy trích xuất TẤT CẢ các thực thể lịch sử từ văn bản trên.

**CÁC LOẠI THỰC THỂ CẦN TRÍCH XUẤT:**
1. Nhân Vật: Hồ Chí Minh, Võ Nguyên Giáp, Đờ Ca-xtơ-ri...
2. Tổ chức: Đảng Cộng sản, Việt Minh, Mặt trận Liên Việt...
3. Quốc gia: Việt Nam, Pháp, Mỹ, Liên Xô, Trung Quốc...
4. Sự kiện: Cách mạng tháng Tám, Chiến tranh Đông Dương...
5. Chiến dịch/Trận đánh: Điện Biên Phủ, Chiến dịch Việt Bắc, Chiến dịch Biên giới...
6. Hội nghị: Hội nghị Tê-hê-ran, Hội nghị I-an-ta, Đại hội đại biểu...
7. Văn kiện/Hiệp định: Hiệp định Sơ bộ, Hiệp định Giơ-ne-vơ, Luật Cải cách ruộng đất...
8. Địa điểm: Hà Nội, Việt Bắc, Đông Khê, Điện Biên Phủ...
9. Chiến lược/Chủ trương: Đường lối kháng chiến, Kế hoạch Na-va...
10. Công trình: Đường số 4, Sân bay Mường Thanh...
11. Khái niệm: Chiến tranh lạnh, Kháng chiến toàn quốc...

**QUY TẮC:**
- Trích xuất MỌI tên riêng, tổ chức, địa danh xuất hiện trong văn bản
- Mỗi entity phải có id (tên chuẩn), type (loại), và description (mô tả ngắn)
- PHẢI trích xuất đầy đủ, không bỏ sót

**ĐỊNH DẠNG JSON (BẮT BUỘC):**
```json
{{"entities": [
    {{"id": "Hồ Chí Minh", "label": ["Bác Hồ", "Chủ tịch Hồ Chí Minh"], "type": "Nhân Vật", "description": "Chủ tịch nước Việt Nam"}},
    {{"id": "Chiến dịch Điện Biên Phủ", "label": ["Điện Biên Phủ"], "type": "Chiến dịch/Trận đánh", "description": "Chiến dịch lớn 1954"}}
]}}
```

Chỉ trả về JSON, không giải thích thêm."""

    return prompt


def _create_optimized_entity_prompt(text: str, context: str, topic_config: Dict) -> str:
    """
    Tạo prompt tối ưu token cho entity extraction.
    Ngắn gọn nhưng đầy đủ thông tin.
    """
    entity_types = ", ".join(config.VALID_ENTITY_TYPES)
    
    # Prompt ngắn gọn, tối ưu token
    prompt = f"""Ngữ cảnh: {context}

Trích xuất entities lịch sử từ văn bản sau. Output JSON.

Văn bản: {text}

Loại entity hợp lệ: {entity_types}

Output format:
{{"entities": [{{"id": "tên chính", "label": ["tên khác"], "type": "loại", "description": "mô tả ngắn 1 câu"}}]}}

Quy tắc:
- Chỉ extract entity là danh từ riêng (tên người, tổ chức, sự kiện cụ thể)
- KHÔNG extract: ngày tháng đơn, khái niệm chung, khẩu hiệu
- Mỗi entity phải có tên trong văn bản

Trả về JSON, không giải thích."""

    return prompt


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