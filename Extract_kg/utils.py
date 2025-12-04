# utils.py
import re
import json
import time
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict
import unicodedata

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    return sentences

def split_sentences_vietnamese(text: str) -> List[str]:
    """Split Vietnamese text into sentences."""
    sentence_endings = r'[.!?]+[\s]*'
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    return sentences

def extract_topic_and_lesson(file_path: str) -> Tuple[str, str]:
    """Extract topic and lesson from file path."""
    try:
        # Normalize path separators
        file_path = file_path.replace('\\', '/')
        
        # Try multiple patterns to extract topic and lesson
        patterns = [
            r'SGK/Nguồn/([^/]+)/([^/]+)\.txt',  # Pattern: SGK/Nguồn/topic/lesson.txt
            r'Nguồn/([^/]+)/([^/]+)\.txt',      # Pattern: Nguồn/topic/lesson.txt
            r'([^/]+)/([^/]+)\.txt',            # Pattern: topic/lesson.txt
        ]
        
        for pattern in patterns:
            match = re.search(pattern, file_path)
            if match:
                topic = match.group(1).strip()
                lesson = match.group(2).replace('.txt', '').strip()
                return topic, lesson
        
        # Fallback: extract from filename or directory structure
        parts = file_path.split('/')
        if len(parts) >= 2:
            # Try to get topic from directory name
            topic = parts[-2] if len(parts) >= 2 else "Unknown"
            # Try to get lesson from filename
            filename = parts[-1]
            lesson = filename.replace('.txt', '').strip()
            
            # Clean up common issues
            if topic == "Nguồn" and len(parts) >= 3:
                topic = parts[-3]
            
            return topic, lesson
        
        return "Unknown", "Unknown"
        
    except Exception as e:
        print(f"Error extracting topic/lesson from {file_path}: {e}")
        return "Unknown", "Unknown"

def create_overlapping_windows(sentences: List[str], window_size: int = 10, step: int = 3) -> List[Tuple[int, List[str]]]:
    """Create overlapping windows of sentences."""
    windows = []
    for i in range(0, len(sentences) - window_size + 1, step):
        window = sentences[i:i+window_size]
        windows.append((i, window))
    return windows

def clean_text_for_matching(text: str) -> str:
    """Clean text for better matching."""
    text = re.sub(r'[^\w\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠ-ỹ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for comparison."""
    text = unicodedata.normalize('NFC', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1, text2).ratio()

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries with list concatenation for common keys."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], list) and isinstance(value, list):
                result[key].extend(value)
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result

def get_timestamp() -> str:
    """Get current timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def create_file_info(file_path: str) -> Dict[str, Any]:
    """Create standardized file information dictionary."""
    topic, lesson = extract_topic_and_lesson(file_path)
    return {
        'file_path': file_path,
        'filename': file_path.split('/')[-1],
        'topic': topic,
        'lesson': lesson,
        'processed_at': get_timestamp()
    }