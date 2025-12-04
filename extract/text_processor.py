"""Xử lý văn bản và tạo windows."""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher
import utils


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
    
    for i, sentence in enumerate(window['sentences']):
        sentence_idx = window['start_idx'] + i
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
            # Get expanded context (current sentence ± 2 sentences)
            context_start = max(0, i - 2)
            context_end = min(len(window['sentences']), i + 3)
            context_sentences = window['sentences'][context_start:context_end]
            context_text = ' '.join(context_sentences)
            
            occurrence = {
                'topic': topic,
                'lesson': lesson,
                'sentence_index': sentence_idx,
                'label': found_labels,
                'exact_text': context_text,
                'context_range': (context_start + window['start_idx'], context_end + window['start_idx'] - 1)
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