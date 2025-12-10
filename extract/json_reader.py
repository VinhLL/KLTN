# -*- coding: utf-8 -*-
"""
Module đọc và xử lý JSON SGK format mới.
Tối ưu hóa việc chunking để giảm số token khi gọi API.
"""

import json
from typing import List, Dict, Any, Generator, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Đại diện cho một đoạn văn bản đã được chunk."""
    text: str
    topic_id: str
    topic_description: str
    lesson_id: str
    lesson_title: str
    section_index: int
    section_title: str
    subsection_label: str
    subsection_title: str
    content_indices: Tuple[int, int]  # (start, end) trong content array


def load_textbook_json(file_path: str) -> List[Dict[str, Any]]:
    """Load file JSON SGK."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_full_context_path(chunk: TextChunk) -> str:
    """Tạo context path đầy đủ cho chunk."""
    parts = [chunk.topic_id]
    if chunk.topic_description:
        parts.append(f"({chunk.topic_description})")
    parts.append(f"> {chunk.lesson_id}")
    if chunk.lesson_title:
        parts.append(f": {chunk.lesson_title}")
    if chunk.section_title:
        parts.append(f"> Mục {chunk.section_index}. {chunk.section_title}")
    if chunk.subsection_label and chunk.subsection_title:
        parts.append(f"> {chunk.subsection_label}) {chunk.subsection_title}")
    return " ".join(parts)


def create_chunks_from_subsection(
    subsection: Dict[str, Any],
    lesson: Dict[str, Any],
    section: Dict[str, Any],
    max_tokens: int = 800,
    overlap_sentences: int = 1
) -> List[TextChunk]:
    """
    Tạo chunks từ một subsection với overlap.
    Tối ưu: chunk theo số câu thay vì window cố định.
    """
    chunks = []
    content = subsection.get("content", [])
    
    if not content:
        return chunks
    
    # Ước tính: 1 token ≈ 4 ký tự tiếng Việt
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    
    current_chunk_content = []
    current_chars = 0
    start_idx = 0
    
    for i, sentence in enumerate(content):
        sentence_chars = len(sentence)
        
        # Nếu thêm câu này vượt quá limit, tạo chunk mới
        if current_chars + sentence_chars > max_chars and current_chunk_content:
            chunk = TextChunk(
                text=" ".join(current_chunk_content),
                topic_id=lesson.get("topic_id", ""),
                topic_description=lesson.get("topic_description", ""),
                lesson_id=lesson.get("lesson_id", ""),
                lesson_title=lesson.get("lesson_title", ""),
                section_index=section.get("index", 0),
                section_title=section.get("title", ""),
                subsection_label=subsection.get("label", ""),
                subsection_title=subsection.get("title", ""),
                content_indices=(start_idx, i - 1)
            )
            chunks.append(chunk)
            
            # Overlap: giữ lại vài câu cuối
            overlap_start = max(0, len(current_chunk_content) - overlap_sentences)
            current_chunk_content = current_chunk_content[overlap_start:]
            current_chars = sum(len(s) for s in current_chunk_content)
            start_idx = i - len(current_chunk_content)
        
        current_chunk_content.append(sentence)
        current_chars += sentence_chars
    
    # Chunk cuối cùng
    if current_chunk_content:
        chunk = TextChunk(
            text=" ".join(current_chunk_content),
            topic_id=lesson.get("topic_id", ""),
            topic_description=lesson.get("topic_description", ""),
            lesson_id=lesson.get("lesson_id", ""),
            lesson_title=lesson.get("lesson_title", ""),
            section_index=section.get("index", 0),
            section_title=section.get("title", ""),
            subsection_label=subsection.get("label", ""),
            subsection_title=subsection.get("title", ""),
            content_indices=(start_idx, len(content) - 1)
        )
        chunks.append(chunk)
    
    return chunks


def iterate_lessons(data: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
    """Iterate qua tất cả các bài học."""
    for lesson in data:
        yield lesson


def iterate_sections(lesson: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """Iterate qua tất cả các sections trong một lesson."""
    for section in lesson.get("sections", []):
        yield section


def iterate_subsections(section: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """Iterate qua tất cả các subsections trong một section."""
    for subsection in section.get("subsections", []):
        yield subsection


def create_all_chunks(
    file_path: str,
    max_tokens: int = 800,
    overlap_sentences: int = 1
) -> List[TextChunk]:
    """
    Tạo tất cả chunks từ file JSON.
    
    Args:
        file_path: Đường dẫn tới file JSON
        max_tokens: Số token tối đa mỗi chunk
        overlap_sentences: Số câu overlap giữa các chunks
    
    Returns:
        Danh sách TextChunk
    """
    data = load_textbook_json(file_path)
    all_chunks = []
    
    for lesson in iterate_lessons(data):
        for section in iterate_sections(lesson):
            for subsection in iterate_subsections(section):
                chunks = create_chunks_from_subsection(
                    subsection, lesson, section,
                    max_tokens, overlap_sentences
                )
                all_chunks.extend(chunks)
    
    return all_chunks


def create_windows_for_entity_extraction(
    file_path: str,
    window_size: int = 5
) -> List[Dict[str, Any]]:
    """
    Tạo windows cho entity extraction từ format JSON mới.
    Tối ưu: sử dụng cấu trúc JSON có sẵn thay vì chunking lại.
    
    Returns:
        List[Dict] với keys: text, topic, lesson, section, subsection, sentences
    """
    data = load_textbook_json(file_path)
    windows = []
    
    for lesson in iterate_lessons(data):
        topic = lesson.get("topic_id", "")
        topic_desc = lesson.get("topic_description", "")
        lesson_id = lesson.get("lesson_id", "")
        lesson_title = lesson.get("lesson_title", "")
        
        for section in iterate_sections(lesson):
            section_idx = section.get("index", 0)
            section_title = section.get("title", "")
            
            for subsection in iterate_subsections(section):
                content = subsection.get("content", [])
                if not content:
                    continue
                
                sub_label = subsection.get("label", "")
                sub_title = subsection.get("title", "")
                
                # Tạo windows từ content
                for i in range(0, len(content), window_size):
                    window_content = content[i:i + window_size]
                    
                    window = {
                        "text": " ".join(window_content),
                        "sentences": window_content,
                        "start_idx": i,
                        "end_idx": i + len(window_content) - 1,
                        "window_index": len(windows),
                        # Metadata
                        "topic": topic,
                        "topic_description": topic_desc,
                        "lesson": lesson_id,
                        "lesson_title": lesson_title,
                        "section_index": section_idx,
                        "section_title": section_title,
                        "subsection_label": sub_label,
                        "subsection_title": sub_title,
                    }
                    windows.append(window)
    
    return windows


def get_lesson_text(lesson: Dict[str, Any]) -> str:
    """Lấy toàn bộ text từ một lesson."""
    texts = []
    for section in iterate_sections(lesson):
        for subsection in iterate_subsections(section):
            content = subsection.get("content", [])
            texts.extend(content)
    return " ".join(texts)


def get_lesson_summary(lesson: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo summary ngắn gọn cho lesson (tối ưu token)."""
    return {
        "topic_id": lesson.get("topic_id", ""),
        "topic_description": lesson.get("topic_description", ""),
        "lesson_id": lesson.get("lesson_id", ""),
        "lesson_title": lesson.get("lesson_title", ""),
        "section_count": len(lesson.get("sections", [])),
        "subsection_count": sum(
            len(s.get("subsections", []))
            for s in lesson.get("sections", [])
        ),
        "total_sentences": sum(
            len(sub.get("content", []))
            for s in lesson.get("sections", [])
            for sub in s.get("subsections", [])
        )
    }


def create_compact_context(window: Dict[str, Any]) -> str:
    """
    Tạo context ngắn gọn cho window (tối ưu token).
    Thay vì include full description, chỉ dùng IDs.
    """
    parts = []
    
    # Format compact: "CHỦ ĐỀ 1 > Bài 1 > Mục 1a: Title"
    if window.get("topic"):
        parts.append(window["topic"].upper())
    
    if window.get("lesson"):
        parts.append(window["lesson"])
    
    section_part = []
    if window.get("section_index"):
        section_part.append(f"Mục {window['section_index']}")
    if window.get("subsection_label"):
        section_part.append(window["subsection_label"])
    if section_part:
        parts.append("".join(section_part))
    
    if window.get("subsection_title"):
        parts.append(window["subsection_title"])
    
    return " > ".join(parts) if parts else ""


# ============ Utility functions for backward compatibility ============

def convert_to_legacy_format(window: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert window mới sang format cũ để tương thích với code hiện tại.
    """
    return {
        "text": window.get("text", ""),
        "sentences": window.get("sentences", []),
        "start_idx": window.get("start_idx", 0),
        "end_idx": window.get("end_idx", 0),
        "window_index": window.get("window_index", 0),
        # Legacy fields
        "topic": window.get("topic", ""),
        "lesson": window.get("lesson", ""),
    }


def extract_topic_and_lesson_from_window(window: Dict[str, Any]) -> Tuple[str, str]:
    """Extract topic và lesson từ window (cho backward compatibility)."""
    return (
        window.get("topic", "Unknown"),
        window.get("lesson", "Unknown")
    )
