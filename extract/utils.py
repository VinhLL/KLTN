"""Tiện ích chung."""

import re
import hashlib
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
from collections import defaultdict
import config


def split_sentences_vietnamese(text: str) -> List[str]:
    """Split Vietnamese text into sentences."""
    sentence_endings = r'[.!?]+[\s]*'
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def extract_topic_and_lesson(file_path: str) -> Tuple[str, str]:
    """Extract topic and lesson from file path."""
    path_parts = file_path.split('/')
    topic = path_parts[2] if len(path_parts) > 2 else "Unknown"
    lesson = path_parts[3].replace('.txt', '') if len(path_parts) > 3 else "Unknown"
    return topic, lesson


def clean_labels(labels: List[str]) -> List[str]:
    """Clean and deduplicate labels, normalizing case to avoid duplicates like 'abc' vs 'Abc'."""
    if not labels:
        return []
    
    # Dictionary to track the best label for each lowercase version
    # We prefer labels that start with uppercase
    best_labels = {}
    
    for label in labels:
        if not label or not label.strip():
            continue
        
        clean_label = label.strip()
        label_lower = clean_label.lower()
        
        if label_lower not in best_labels:
            best_labels[label_lower] = clean_label
        else:
            # Already have this label (case-insensitive), choose the better one
            existing = best_labels[label_lower]
            
            # Prefer label starting with uppercase
            if clean_label[0].isupper() and not existing[0].isupper():
                best_labels[label_lower] = clean_label
            # If both have same case, prefer shorter one
            elif clean_label[0].isupper() == existing[0].isupper():
                if len(clean_label) < len(existing):
                    best_labels[label_lower] = clean_label
    
    # Return unique labels, maintaining original order for first occurrence
    result = []
    seen_lower = set()
    
    for label in labels:
        if not label or not label.strip():
            continue
        label_lower = label.strip().lower()
        if label_lower not in seen_lower:
            seen_lower.add(label_lower)
            result.append(best_labels[label_lower])
    
    return result


def validate_entity_type(entity_type: str) -> str:
    """Validate and correct entity type."""
    if entity_type in config.VALID_ENTITY_TYPES:
        return entity_type
    
    # Map similar types to valid ones
    type_mapping = {
        "Nhân vật": "Nhân Vật",
        "Tổ chức/quốc tế": "Tổ chức",
        "Sự kiện lịch sử": "Sự kiện",
        "Chiến dịch": "Chiến dịch/Trận đánh",
        "Trận đánh": "Chiến dịch/Trận đánh",
        "Hiệp định": "Văn kiện/Hiệp định",
        "Văn kiện": "Văn kiện/Hiệp định",
        "Địa danh": "Địa điểm",
        "Chiến lược": "Chiến lược/Chủ trương",
        "Chủ trương": "Chiến lược/Chủ trương",
        "Tổ chức quốc tế": "Tổ chức",
        "Hội nghị quốc tế": "Hội nghị",
        "Hiệp ước": "Văn kiện/Hiệp định",
        "Văn bản quốc tế": "Văn kiện/Hiệp định",
        "Nhân vật lịch sử": "Nhân Vật",
        "Cường quốc": "Quốc gia",
        "Chiến tranh": "Sự kiện",
        "Địa danh": "Địa điểm"
    }
    
    return type_mapping.get(entity_type, "Khái niệm")


def calculate_entity_fingerprint(entity: Dict[str, Any]) -> str:
    """Calculate a fingerprint for entity comparison based on ID and type."""
    normalized_id = entity['id'].lower().strip()
    normalized_type = entity['type'].strip()
    
    # Remove ordinal numbers to prevent incorrect merging
    ordinal_pattern = r'\b(thứ\s+(nhất|hai|ba|tư|năm|sáu|bảy|tám|chín|mười|một|hai|ba|bốn|năm|sáu|bảy|tám|chín))\b'
    
    # Check if entity contains ordinal numbers
    if re.search(ordinal_pattern, normalized_id):
        # Include ordinal in fingerprint
        fingerprint_str = f"{normalized_id}|{normalized_type}"
    else:
        # For non-ordinal entities, use a more general approach
        # Remove common prefixes/suffixes
        base_name = re.sub(r'^(cuộc|chiến|hội|hiệp|vụ|sự|trận)\s+', '', normalized_id)
        fingerprint_str = f"{base_name}|{normalized_type}"
    
    return hashlib.md5(fingerprint_str.encode()).hexdigest()


def group_consecutive_occurrences(occurrences: List[Dict]) -> List[Dict]:
    """Group consecutive occurrences to reduce JSON size with improved deduplication."""
    if not occurrences:
        return []
    
    # Đảm bảo tất cả occurrences có các trường cần thiết (với giá trị mặc định nếu thiếu)
    for occ in occurrences:
        if 'sentence_index' not in occ:
            occ['sentence_index'] = 0
        if 'label' not in occ:
            occ['label'] = []
        if 'topic' not in occ:
            occ['topic'] = ''
        if 'lesson' not in occ:
            occ['lesson'] = ''
        if 'exact_text' not in occ:
            occ['exact_text'] = ''
    
    # Sort occurrences by topic, lesson, and sentence_index - using .get() for safety
    try:
        occurrences.sort(key=lambda x: (
            str(x.get('topic', '')), 
            str(x.get('lesson', '')), 
            int(x.get('sentence_index', 0))
        ))
    except (TypeError, ValueError) as e:
        # Fallback: sort by topic and lesson only if sentence_index has issues
        occurrences.sort(key=lambda x: (
            str(x.get('topic', '')), 
            str(x.get('lesson', ''))
        ))
    
    grouped = []
    current_group = None
    
    for occ in occurrences:
        if current_group is None:
            current_group = {
                'topic': occ.get('topic', ''),
                'lesson': occ.get('lesson', ''),
                'labels': occ.get('label', []),
                'texts': [occ.get('exact_text', '')],
                'sentence_range': [occ.get('sentence_index', 0), occ.get('sentence_index', 0)]
            }
        else:
            # Check if this occurrence can be grouped with current
            # Also check for similar texts to avoid grouping duplicates
            can_group = (occ.get('topic', '') == current_group['topic'] and 
                        occ.get('lesson', '') == current_group['lesson'] and
                        occ.get('sentence_index', 0) <= current_group['sentence_range'][1] + 5)
            
            # Check if text is too similar to existing texts in group
            if can_group:
                is_similar = False
                exact_text = occ.get('exact_text', '')
                for existing_text in current_group['texts']:
                    if exact_text and existing_text:
                        similarity = SequenceMatcher(None, exact_text, existing_text).ratio()
                        if similarity > 0.8:  # 80% similarity threshold
                            is_similar = True
                            break
                
                if not is_similar:
                    current_group['texts'].append(exact_text)
                    current_group['sentence_range'][1] = max(current_group['sentence_range'][1], occ.get('sentence_index', 0))
                    # Merge labels
                    current_group['labels'] = list(set(current_group['labels'] + occ.get('label', [])))
                else:
                    # Text is too similar, don't add but update sentence range
                    current_group['sentence_range'][1] = max(current_group['sentence_range'][1], occ.get('sentence_index', 0))
            else:
                # Finalize current group
                finalize_group(current_group)
                grouped.append(current_group)
                
                # Start new group
                current_group = {
                    'topic': occ.get('topic', ''),
                    'lesson': occ.get('lesson', ''),
                    'labels': occ.get('label', []),
                    'texts': [occ.get('exact_text', '')],
                    'sentence_range': [occ.get('sentence_index', 0), occ.get('sentence_index', 0)]
                }
    
    # Add the last group
    if current_group:
        finalize_group(current_group)
        grouped.append(current_group)
    
    return grouped


def finalize_group(group: Dict) -> None:
    """Finalize a grouped occurrence."""
    group['text_count'] = len(group['texts'])
    
    # Get unique texts (case-insensitive)
    unique_texts = []
    seen_texts = set()
    
    for text in group['texts']:
        normalized = text.lower().strip()
        if normalized not in seen_texts:
            seen_texts.add(normalized)
            unique_texts.append(text)
    
    # If still too many unique texts, show representative ones
    if len(unique_texts) > config.MAX_TEXTS_PER_GROUP:
        # Try to find texts that are not too similar
        representative_texts = []
        for text in unique_texts:
            is_similar = False
            for rep_text in representative_texts:
                similarity = SequenceMatcher(None, text.lower(), rep_text.lower()).ratio()
                if similarity > 0.7:
                    is_similar = True
                    break
            if not is_similar and len(representative_texts) < config.MAX_TEXTS_PER_GROUP:
                representative_texts.append(text)
        
        group['exact_text'] = " [...] ".join(representative_texts)
        if len(unique_texts) > len(representative_texts):
            group['exact_text'] += f" [...] (và {len(unique_texts) - len(representative_texts)} đoạn khác)"
    else:
        group['exact_text'] = " [...] ".join(unique_texts)
    
    del group['texts']