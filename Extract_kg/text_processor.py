# text_processor.py
import re
from typing import List, Dict, Any, Tuple
from utils import create_overlapping_windows, split_into_sentences, extract_topic_and_lesson

def read_source_files(file_paths: List[str]) -> Dict[str, str]:
    """Read all source files and return their contents."""
    contents = {}
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contents[file_path] = f.read()
        except FileNotFoundError:
            print(f"Cảnh báo: Không tìm thấy file {file_path}")
            contents[file_path] = ""
    return contents

def extract_exact_text_positions(content: str, exact_text: str) -> List[int]:
    """Find positions of exact text in content."""
    positions = []
    
    clean_content = content.lower()
    clean_exact = exact_text.lower()
    
    start = 0
    while True:
        pos = clean_content.find(clean_exact, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    
    return positions

def position_to_sentence_index(content: str, sentences: List[str], position: int) -> int:
    """Convert character position to sentence index."""
    char_count = 0
    for idx, sentence in enumerate(sentences):
        if char_count <= position < char_count + len(sentence):
            return idx
        char_count += len(sentence) + 1
    
    for idx, sentence in enumerate(sentences):
        sentence_start = content.find(sentence)
        sentence_end = sentence_start + len(sentence)
        if sentence_start <= position <= sentence_end:
            return idx
    
    return -1

def create_text_windows(sentences: List[str], window_size: int = 10) -> List[Dict[str, Any]]:
    """Create overlapping windows of text for analysis."""
    windows = []
    for i in range(0, len(sentences), window_size//2):
        window_end = min(i + window_size, len(sentences))
        window_text = ' '.join(sentences[i:window_end])
        
        if len(window_text.strip()) > 20:
            windows.append({
                'text': window_text,
                'start_idx': i,
                'end_idx': window_end - 1,
                'sentences': sentences[i:window_end]
            })
    
    return windows

def find_context_windows_for_entity(
    entity_id: str,
    entity_lookup: Dict[str, Dict],
    source_files: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Find context windows for a specific entity using original_text information."""
    entity = entity_lookup.get(entity_id)
    if not entity:
        print(f"Entity {entity_id} not found in lookup")
        return []
    
    context_windows = []
    
    for occurrence in entity.get('original_text', []):
        try:
            topic = occurrence.get('topic', 'Unknown')
            lesson = occurrence.get('lesson', 'Unknown')
            
            file_path = f"SGK/Nguồn/{topic}/{lesson}.txt"
            
            if file_path not in source_files:
                continue
            
            content = source_files[file_path]
            if not content:
                continue
            
            sentences = split_into_sentences(content)
            if not sentences:
                continue
            
            exact_text = occurrence.get('exact_text', '')
            if not exact_text:
                continue
            
            sentence_range = occurrence.get('sentence_range', [])
            if len(sentence_range) >= 2:
                if sentence_range[0] > 0:
                    start_idx = max(0, sentence_range[0] - 1 - 3)
                    end_idx = min(len(sentences), sentence_range[0] + 5)
                else:
                    start_idx = max(0, sentence_range[0] - 3)
                    end_idx = min(len(sentences), sentence_range[1] + 5)
                
                if end_idx - start_idx >= 3:
                    context_sentences = sentences[start_idx:end_idx]
                    
                    context_windows.append({
                        'sentences': context_sentences,
                        'start_idx': start_idx,
                        'file_info': {
                            'file_path': file_path,
                            'topic': topic,
                            'lesson': lesson
                        },
                        'entity_id': entity_id,
                        'entity_type': entity.get('type', 'Unknown'),
                        'exact_text': exact_text[:500]
                    })
            else:
                positions = extract_exact_text_positions(content, exact_text)
                if positions:
                    for position in positions[:3]:
                        sentence_idx = position_to_sentence_index(content, sentences, position)
                        if sentence_idx >= 0:
                            start_idx = max(0, sentence_idx - 3)
                            end_idx = min(len(sentences), sentence_idx + 6)
                            
                            if end_idx - start_idx >= 3:
                                context_sentences = sentences[start_idx:end_idx]
                                
                                context_windows.append({
                                    'sentences': context_sentences,
                                    'start_idx': start_idx,
                                    'file_info': {
                                        'file_path': file_path,
                                        'topic': topic,
                                        'lesson': lesson
                                    },
                                    'entity_id': entity_id,
                                    'entity_type': entity.get('type', 'Unknown'),
                                    'exact_text': exact_text[:100]
                                })
                                break
                
        except Exception as e:
            print(f"Error processing occurrence for {entity_id}: {e}")
            continue
    
    if not context_windows:
        entity_labels = entity.get('label', [])
        
        for file_path, content in source_files.items():
            if not content:
                continue
            
            sentences = split_into_sentences(content)
            
            for label in entity_labels:
                if len(label) < 3:
                    continue
                    
                for idx, sentence in enumerate(sentences):
                    if label in sentence:
                        start_idx = max(0, idx - 3)
                        end_idx = min(len(sentences), idx + 6)
                        
                        if end_idx - start_idx >= 3:
                            topic, lesson = extract_topic_and_lesson(file_path)
                            context_windows.append({
                                'sentences': sentences[start_idx:end_idx],
                                'start_idx': start_idx,
                                'file_info': {
                                    'file_path': file_path,
                                    'topic': topic,
                                    'lesson': lesson
                                },
                                'entity_id': entity_id,
                                'entity_type': entity.get('type', 'Unknown'),
                                'found_by': 'label_match'
                            })
                            break
                if context_windows:
                    break
    
    print(f"Found {len(context_windows)} context windows for {entity_id}")
    return context_windows

def extract_key_sections(text: str, section_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Extract key sections from text based on keywords."""
    sentences = split_into_sentences(text)
    sections = {section_name: [] for section_name in section_keywords.keys()}
    sections['other'] = []
    
    current_section = 'other'
    current_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_section = None
        max_matches = 0
        
        for section_name, keywords in section_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_section = section_name
        
        if detected_section and max_matches > 0:
            if current_sentences:
                sections[current_section].extend(current_sentences)
            
            current_section = detected_section
            current_sentences = [sentence]
        else:
            current_sentences.append(sentence)
    
    if current_sentences:
        sections[current_section].extend(current_sentences)
    
    return {k: v for k, v in sections.items() if v}