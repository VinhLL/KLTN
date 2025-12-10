"""Xử lý văn bản và tạo windows."""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher
import utils
import config

# Import JSON reader cho format mới
try:
    from json_reader import (
        load_textbook_json,
        create_windows_for_entity_extraction,
        create_compact_context,
        iterate_lessons,
        iterate_sections,
        iterate_subsections
    )
    JSON_READER_AVAILABLE = True
except ImportError:
    JSON_READER_AVAILABLE = False


def read_files(file_paths: List[str]) -> Dict[str, str]:
    """Read all input files and return their contents."""
    contents = {}
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contents[file_path] = f.read()
        except FileNotFoundError:
            print(f"Warning: File {file_path} not found")
            contents[file_path] = ""
    return contents

def create_non_overlapping_windows(sentences: List[str], window_size: int = 5) -> List[Dict]:
    """Create non-overlapping windows of sentences."""
    windows = []
    for i in range(0, len(sentences), window_size):
        window = sentences[i:i + window_size]
        if window:
            windows.append({
                'text': ' '.join(window),
                'sentences': window,
                'start_idx': i,
                'end_idx': i + len(window) - 1,
                'window_index': len(windows)
            })
    return windows


def find_entity_occurrences(entity: Dict, window: Dict, topic: str, lesson: str) -> List[Dict]:
    """Find all occurrences of an entity in the window and return structured occurrences with expanded context."""
    occurrences = []
    entity_labels = [entity['id']] + entity.get('label', [])
    
    # Lấy sentences - hỗ trợ cả list và text
    sentences = window.get('sentences', [])
    if not sentences and 'text' in window:
        # Fallback: split text thành sentences
        sentences = [s.strip() for s in window['text'].split('.') if s.strip()]
    
    # Lấy start_idx - mặc định là 0 nếu không có
    start_idx = window.get('start_idx', window.get('window_index', 0))
    
    for i, sentence in enumerate(sentences):
        sentence_idx = start_idx + i
        found_labels = []
        
        # Check for each label in the sentence
        for label in entity_labels:
            if label and len(label) > 2:
                # Use word boundary matching for better accuracy
                pattern = r'\b' + re.escape(label) + r'\b'
                if re.search(pattern, sentence):
                    found_labels.append(label)
        
        # If we found any labels, add as occurrence with expanded context
        if found_labels:
            # Get expanded context (current sentence +/- 2 sentences)
            context_start = max(0, i - 2)
            context_end = min(len(sentences), i + 3)
            context_sentences = sentences[context_start:context_end]
            context_text = ' '.join(context_sentences)
            
            occurrence = {
                'topic': topic,
                'lesson': lesson,
                'sentence_index': sentence_idx,
                'label': found_labels,
                'exact_text': context_text,
                'context_range': (context_start + start_idx, context_end + start_idx - 1),
                # Thêm metadata từ JSON format nếu có
                'section': window.get('section_title', ''),
                'subsection': window.get('subsection_title', '')
            }
            occurrences.append(occurrence)
    
    return occurrences


def extract_timeline_events(text: str) -> List[Dict]:
    """Extract timeline events with their full context and avoid duplicates."""
    events = []
    
    # Pattern for dates and years
    date_patterns = [
        r'ngày\s+(\d+\s*–\s*\d+\s*–\s*\d+)',
        r'tháng\s+(\d+\s*–\s*\d+)',
        r'năm\s+(\d{4})',
        r'\b(19\d{2}|20\d{2})\b',
        r'(\d+\s*–\s*\d+\s*–\s*\d+)\s*(?:đến|–)\s*(\d+\s*–\s*\d+\s*–\s*\d+)'
    ]
    
    sentences = utils.split_sentences_vietnamese(text)
    
    # Track seen sentences to avoid duplicates
    seen_sentences = set()
    
    for sentence in sentences:
        # Skip if sentence is too short or similar to already processed
        if len(sentence) < 2:
            continue
        
        normalized_sentence = sentence.lower().strip()
        is_duplicate = False
        
        for seen in seen_sentences:
            similarity = SequenceMatcher(None, normalized_sentence, seen).ratio()
            if similarity > config.TIMELINE_SIMILARITY_THRESHOLD:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        seen_sentences.add(normalized_sentence)
        
        event_data = {
            'sentence': sentence,
            'dates': [],
            'years': []
        }
        
        # Extract dates
        for pattern in date_patterns:
            matches = re.findall(pattern, sentence)
            if matches:
                if pattern == r'(\d+\s*–\s*\d+\s*–\s*\d+)\s*(?:đến|–)\s*(\d+\s*–\s*\d+\s*–\s*\d+)':
                    for match in matches:
                        if isinstance(match, tuple):
                            event_data['dates'].extend([m.strip() for m in match])
                else:
                    for match in matches:
                        if isinstance(match, tuple):
                            event_data['dates'].append(match[0].strip())
                        else:
                            event_data['dates'].append(match.strip())
        
        # Extract years separately
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', sentence)
        if year_matches:
            event_data['years'] = list(set(year_matches))
        
        if event_data['dates'] or event_data['years']:
            events.append(event_data)
    
    return events


def expand_acronyms(text: str, topic_config: Dict) -> str:
    """Mở rộng từ viết tắt trong văn bản dựa trên cấu hình chủ đề."""
    if not topic_config or 'acronyms' not in topic_config:
        return text
    
    acronyms = topic_config['acronyms']
    for acronym, expansion in acronyms.items():
        # Tìm từ viết tắt và thay thế
        pattern = r'\b' + re.escape(acronym) + r'\b'
        text = re.sub(pattern, f"{acronym} ({expansion})", text)
    
    return text


# ============ JSON Format Functions (New) ============

def read_json_input() -> List[Dict[str, Any]]:
    """
    Đọc file JSON input mới.
    Returns danh sách lessons từ JSON.
    """
    if not JSON_READER_AVAILABLE:
        raise ImportError("json_reader module not available")
    
    if not hasattr(config, 'JSON_INPUT_FILE'):
        raise ValueError("JSON_INPUT_FILE not configured in config.py")
    
    return load_textbook_json(config.JSON_INPUT_FILE)


def create_windows_from_json(window_size: int = None) -> List[Dict[str, Any]]:
    """
    Tạo windows từ JSON file (format mới).
    Tối ưu token bằng cách sử dụng cấu trúc có sẵn.
    
    Returns:
        List windows với metadata đầy đủ
    """
    if not JSON_READER_AVAILABLE:
        raise ImportError("json_reader module not available")
    
    if window_size is None:
        window_size = getattr(config, 'WINDOW_SIZE', 5)
    
    return create_windows_for_entity_extraction(
        config.JSON_INPUT_FILE,
        window_size=window_size
    )


def get_windows_for_extraction() -> List[Dict[str, Any]]:
    """
    Hàm wrapper để lấy windows cho entity extraction.
    Tự động chọn JSON format nếu được cấu hình.
    """
    use_json = getattr(config, 'USE_JSON_FORMAT', False)
    
    if use_json and JSON_READER_AVAILABLE:
        print(f"[INFO] Using JSON format: {config.JSON_INPUT_FILE}")
        return create_windows_from_json()
    else:
        # Fallback to old txt format
        print("[INFO] Using legacy TXT format")
        file_contents = read_files(config.INPUT_FILES)
        all_windows = []
        
        for file_path, content in file_contents.items():
            if not content:
                continue
            sentences = utils.split_sentences_vietnamese(content)
            windows = create_non_overlapping_windows(
                sentences, 
                getattr(config, 'WINDOW_SIZE', 5)
            )
            
            # Add file metadata
            for window in windows:
                topic, lesson = utils.extract_topic_and_lesson(file_path)
                window['topic'] = topic
                window['lesson'] = lesson
                window['file_path'] = file_path
            
            all_windows.extend(windows)
        
        return all_windows


def get_compact_context_for_window(window: Dict[str, Any]) -> str:
    """
    Tạo context ngắn gọn cho window (tối ưu token).
    """
    if JSON_READER_AVAILABLE and getattr(config, 'USE_COMPACT_CONTEXT', False):
        return create_compact_context(window)
    
    # Fallback: tạo context đơn giản
    parts = []
    if window.get('topic'):
        parts.append(window['topic'])
    if window.get('lesson'):
        parts.append(window['lesson'])
    return " > ".join(parts) if parts else ""