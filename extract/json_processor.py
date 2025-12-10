# -*- coding: utf-8 -*-
"""
json_processor.py
Xử lý file JSON sách giáo khoa với chiến lược hierarchical để đảm bảo ngữ nghĩa.

Chiến lược xử lý:
1. Hierarchical: Chủ đề → Bài → Section → Subsection
2. Context-aware: Mỗi chunk giữ context đầy đủ (topic, lesson, section)
3. Semantic chunking: Dựa trên cấu trúc văn bản, không cắt cứng theo số câu
"""

import json
from typing import List, Dict, Any, Generator
from dataclasses import dataclass
from pathlib import Path
import math

# Configuration cho việc chia nhỏ chunk
MAX_CONTENT_LENGTH_FOR_SPLIT = 28  # Số câu tối đa trước khi chia nhỏ
MAX_CHAR_LENGTH_FOR_SPLIT = 1500  # Số ký tự tối đa trước khi chia nhỏ
NUM_PARTS_TO_SPLIT = 4  # Chia thành 4 phần


def should_split_chunk(chunk: 'SemanticChunk') -> bool:
    """
    Kiểm tra xem chunk có cần chia nhỏ không dựa trên số câu hoặc số ký tự.
    
    Returns:
        True nếu chunk cần chia nhỏ
    """
    content = chunk.content
    
    # Kiểm tra số câu
    if len(content) > MAX_CONTENT_LENGTH_FOR_SPLIT:
        return True
    
    # Kiểm tra số ký tự trong combined content
    combined_text = " ".join(content)
    if len(combined_text) > MAX_CHAR_LENGTH_FOR_SPLIT:
        return True
    
    return False


def split_long_chunk(chunk: 'SemanticChunk') -> list:
    """
    Chia nhỏ chunk có nội dung quá dài thành nhiều phần.
    Chia dựa trên số câu HOẶC số ký tự (>2000 chars).
    
    Args:
        chunk: SemanticChunk cần chia
        
    Returns:
        Danh sách các SemanticChunk nhỏ hơn, hoặc [chunk] nếu không cần chia
    """
    content = chunk.content
    combined_text = " ".join(content)
    
    # Không cần chia nếu nội dung đủ ngắn (cả về số câu và số ký tự)
    if len(content) <= MAX_CONTENT_LENGTH_FOR_SPLIT and len(combined_text) <= MAX_CHAR_LENGTH_FOR_SPLIT:
        return [chunk]
    
    # Xác định số phần cần chia
    # Dựa trên cả số câu và số ký tự
    parts_by_sentences = max(1, (len(content) + MAX_CONTENT_LENGTH_FOR_SPLIT - 1) // MAX_CONTENT_LENGTH_FOR_SPLIT)
    parts_by_chars = max(1, (len(combined_text) + MAX_CHAR_LENGTH_FOR_SPLIT - 1) // MAX_CHAR_LENGTH_FOR_SPLIT)
    num_parts = max(parts_by_sentences, parts_by_chars, NUM_PARTS_TO_SPLIT)
    
    # Giới hạn số phần tối đa
    num_parts = min(num_parts, 8)
    
    # Tính số câu mỗi phần
    part_size = max(1, (len(content) + num_parts - 1) // num_parts)
    
    parts = []
    for i in range(num_parts):
        start_idx = i * part_size
        end_idx = min((i + 1) * part_size, len(content))
        
        if start_idx >= len(content):
            break
            
        part_content = content[start_idx:end_idx]
        
        # Tạo subsection label mới cho phần này
        part_label = f"{chunk.subsection_label}_part{i+1}" if chunk.subsection_label else f"part{i+1}"
        part_title = f"{chunk.subsection_title} (Phần {i+1}/{num_parts})" if chunk.subsection_title else f"Phần {i+1}/{num_parts}"
        
        part_chunk = SemanticChunk(
            topic_id=chunk.topic_id,
            topic_description=chunk.topic_description,
            lesson_id=chunk.lesson_id,
            lesson_title=chunk.lesson_title,
            section_index=chunk.section_index,
            section_title=chunk.section_title,
            subsection_label=part_label,
            subsection_title=part_title,
            content=part_content,
            context_before=chunk.context_before if i == 0 else "",
            context_after=chunk.context_after if i == num_parts - 1 else ""
        )
        
        parts.append(part_chunk)
    
    return parts


@dataclass
class SemanticChunk:
    """Một đơn vị ngữ nghĩa từ sách giáo khoa."""
    topic_id: str
    topic_description: str
    lesson_id: str
    lesson_title: str
    section_index: int
    section_title: str
    subsection_label: str
    subsection_title: str
    content: List[str]  # Danh sách các câu/đoạn
    
    # Metadata cho context
    context_before: str = ""  # Context từ subsection trước
    context_after: str = ""   # Context từ subsection sau
    
    @property
    def full_path(self) -> str:
        """Đường dẫn đầy đủ của chunk."""
        return f"{self.topic_id}/{self.lesson_id}/Section {self.section_index}/{self.subsection_label}"
    
    @property
    def combined_content(self) -> str:
        """Nội dung gộp thành văn bản."""
        return " ".join(self.content)
    
    @property
    def context_rich_content(self) -> str:
        """Nội dung với context."""
        parts = []
        if self.context_before:
            parts.append(f"[Trước đó]: {self.context_before}")
        parts.append(self.combined_content)
        if self.context_after:
            parts.append(f"[Tiếp theo]: {self.context_after}")
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển thành dict để tương thích với code cũ."""
        return {
            "topic_id": self.topic_id,
            "topic_description": self.topic_description,
            "lesson_id": self.lesson_id,
            "lesson_title": self.lesson_title,
            "section_index": self.section_index,
            "section_title": self.section_title,
            "subsection_label": self.subsection_label,
            "subsection_title": self.subsection_title,
            "content": self.content,
            "combined_content": self.combined_content,
            "full_path": self.full_path,
            "context_before": self.context_before,
            "context_after": self.context_after
        }


class JSONTextbookProcessor:
    """Xử lý file JSON sách giáo khoa theo cấu trúc hierarchical."""
    
    def __init__(self, json_path: str, add_context: bool = True):
        """
        Args:
            json_path: Đường dẫn file JSON
            add_context: Có thêm context từ subsections lân cận không
        """
        self.json_path = json_path
        self.add_context = add_context
        self.data = self._load_json()
        
    def _load_json(self) -> List[Dict]:
        """Load file JSON."""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_all_chunks(self) -> List[SemanticChunk]:
        """
        Lấy tất cả semantic chunks từ sách.
        Mỗi subsection là một chunk để đảm bảo ngữ nghĩa hoàn chỉnh.
        """
        chunks = []
        
        for lesson in self.data:
            topic_id = lesson.get("topic_id", "")
            topic_desc = lesson.get("topic_description", "")
            lesson_id = lesson.get("lesson_id", "")
            lesson_title = lesson.get("lesson_title", "")
            
            sections = lesson.get("sections", [])
            
            for section in sections:
                section_idx = section.get("index", 0)
                section_title = section.get("title", "")
                subsections = section.get("subsections", [])
                
                # Xử lý từng subsection
                for i, subsection in enumerate(subsections):
                    chunk = SemanticChunk(
                        topic_id=topic_id,
                        topic_description=topic_desc,
                        lesson_id=lesson_id,
                        lesson_title=lesson_title,
                        section_index=section_idx,
                        section_title=section_title,
                        subsection_label=subsection.get("label", ""),
                        subsection_title=subsection.get("title", ""),
                        content=subsection.get("content", [])
                    )
                    
                    # Thêm context nếu enabled
                    if self.add_context:
                        # Context từ subsection trước
                        if i > 0:
                            prev_content = subsections[i-1].get("content", [])
                            chunk.context_before = prev_content[-1] if prev_content else ""
                        
                        # Context từ subsection sau
                        if i < len(subsections) - 1:
                            next_content = subsections[i+1].get("content", [])
                            chunk.context_after = next_content[0] if next_content else ""
                    
                    chunks.append(chunk)
        
        return chunks
    
    def get_all_chunks_with_split(self) -> List[SemanticChunk]:
        """
        Lấy tất cả semantic chunks với việc chia nhỏ các chunk quá dài.
        Các chunk có nội dung > MAX_CONTENT_LENGTH_FOR_SPLIT câu HOẶC > MAX_CHAR_LENGTH_FOR_SPLIT ký tự 
        sẽ được chia thành nhiều phần.
        
        Returns:
            List[SemanticChunk]: Danh sách chunks đã được tối ưu kích thước
        """
        original_chunks = self.get_all_chunks()
        optimized_chunks = []
        split_count = 0
        
        for chunk in original_chunks:
            parts = split_long_chunk(chunk)
            if len(parts) > 1:
                split_count += 1
                char_count = len(" ".join(chunk.content))
                print(f"   [Split] {chunk.full_path}: {len(chunk.content)} sentences, {char_count} chars -> {len(parts)} parts")
            optimized_chunks.extend(parts)
        
        if split_count > 0:
            print(f"\n[INFO] Đã chia nhỏ {split_count} chunks quá dài (>30 câu hoặc >2000 ký tự)")
            print(f"[INFO] Tổng chunks sau khi chia: {len(optimized_chunks)} (trước: {len(original_chunks)})\n")
        
        return optimized_chunks
    
    def get_chunks_by_topic(self) -> Dict[str, List[SemanticChunk]]:
        """Nhóm chunks theo topic."""
        chunks = self.get_all_chunks()
        result = {}
        
        for chunk in chunks:
            key = f"{chunk.topic_id}: {chunk.topic_description}"
            if key not in result:
                result[key] = []
            result[key].append(chunk)
        
        return result
    
    def get_chunks_by_lesson(self) -> Dict[str, List[SemanticChunk]]:
        """Nhóm chunks theo lesson."""
        chunks = self.get_all_chunks()
        result = {}
        
        for chunk in chunks:
            key = f"{chunk.topic_id}/{chunk.lesson_id}: {chunk.lesson_title}"
            if key not in result:
                result[key] = []
            result[key].append(chunk)
        
        return result
    
    def iter_chunks(self) -> Generator[SemanticChunk, None, None]:
        """Iterator qua tất cả chunks."""
        for chunk in self.get_all_chunks():
            yield chunk
    
    def iter_chunks_with_split(self) -> Generator[SemanticChunk, None, None]:
        """Iterator qua tất cả chunks với việc chia nhỏ các chunk quá dài."""
        for chunk in self.get_all_chunks_with_split():
            yield chunk
    
    def get_statistics(self) -> Dict[str, Any]:
        """Thống kê về dữ liệu."""
        chunks = self.get_all_chunks()
        
        topics = set()
        lessons = set()
        sections = 0
        total_sentences = 0
        
        for chunk in chunks:
            topics.add(chunk.topic_id)
            lessons.add(f"{chunk.topic_id}/{chunk.lesson_id}")
            total_sentences += len(chunk.content)
        
        # Thống kê thêm về các chunks cần chia nhỏ
        long_chunks = [c for c in chunks if len(c.content) > MAX_CONTENT_LENGTH_FOR_SPLIT]
        
        return {
            "total_chunks": len(chunks),
            "total_topics": len(topics),
            "total_lessons": len(lessons),
            "total_sentences": total_sentences,
            "avg_sentences_per_chunk": total_sentences / len(chunks) if chunks else 0,
            "long_chunks_count": len(long_chunks),
            "long_chunks_paths": [c.full_path for c in long_chunks]
        }
    
    def to_windows_format(self, split_long_chunks: bool = True) -> List[Dict]:
        """
        Chuyển đổi sang format windows tương thích với code extract cũ.
        Mỗi chunk trở thành một window.
        
        Args:
            split_long_chunks: Nếu True, chia nhỏ các chunks quá dài thành nhiều phần
        """
        windows = []
        
        if split_long_chunks:
            chunks = self.get_all_chunks_with_split()
        else:
            chunks = self.get_all_chunks()
        
        for i, chunk in enumerate(chunks):
            window = {
                "window_index": i,
                "sentences": chunk.content,
                "text": chunk.combined_content,
                # Metadata
                "topic_id": chunk.topic_id,
                "topic_description": chunk.topic_description,
                "lesson_id": chunk.lesson_id,
                "lesson_title": chunk.lesson_title,
                "section_index": chunk.section_index,
                "section_title": chunk.section_title,
                "subsection_label": chunk.subsection_label,
                "subsection_title": chunk.subsection_title,
                "full_path": chunk.full_path,
                # Context
                "context_before": chunk.context_before,
                "context_after": chunk.context_after,
                # Để tương thích
                "file_path": f"JSON:{chunk.full_path}",
                "is_json_source": True,
                "is_split_part": "_part" in (chunk.subsection_label or "")
            }
            windows.append(window)
        
        return windows


def create_hierarchical_prompt(chunk: SemanticChunk, entity_types: List[str]) -> str:
    """
    Tạo prompt tối ưu cho một semantic chunk với context đầy đủ.
    """
    prompt = f"""TRÍCH XUẤT THỰC THỂ LỊCH SỬ - PHÂN TÍCH THEO NGỮ CẢNH

=== NGỮ CẢNH ===
Chủ đề: {chunk.topic_id} - {chunk.topic_description}
Bài: {chunk.lesson_id} - {chunk.lesson_title}
Phần: {chunk.section_index}. {chunk.section_title}
Mục: {chunk.subsection_label}) {chunk.subsection_title}

=== NỘI DUNG CẦN PHÂN TÍCH ===
{chunk.combined_content}

"""
    
    # Thêm context nếu có
    if chunk.context_before:
        prompt += f"\n[Context trước]: {chunk.context_before}\n"
    if chunk.context_after:
        prompt += f"\n[Context sau]: {chunk.context_after}\n"
    
    prompt += f"""
=== YÊU CẦU ===
Trích xuất các thực thể lịch sử quan trọng với các loại sau:
{', '.join(entity_types)}

Lưu ý đặc biệt cho chủ đề "{chunk.topic_description}":
- Tập trung vào các thực thể phù hợp với ngữ cảnh bài học
- Ghi nhận đầy đủ năm/ngày tháng trong properties
- Chỉ trích xuất tên riêng, không trích xuất khái niệm chung

=== OUTPUT JSON ===
{{"entities": [{{"id": "tên chuẩn", "label": ["tên chính", "tên phụ nếu có"], "type": "loại", "description": "mô tả ngắn", "properties": {{"năm": "", "địa_điểm": ""}}}}]}}

Chỉ trả về JSON hợp lệ."""
    
    return prompt


# Hàm tiện ích để sử dụng trong các module khác
def load_json_textbook(json_path: str) -> JSONTextbookProcessor:
    """Load và trả về processor cho file JSON sách giáo khoa."""
    return JSONTextbookProcessor(json_path)


def get_windows_from_json(json_path: str) -> List[Dict]:
    """Lấy danh sách windows từ file JSON để tương thích với code cũ."""
    processor = JSONTextbookProcessor(json_path)
    return processor.to_windows_format()


if __name__ == "__main__":
    # Test với file JSON
    import sys
    
    json_path = r"D:\KLTN\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    
    processor = JSONTextbookProcessor(json_path)
    
    # In thống kê
    stats = processor.get_statistics()
    print("=" * 60)
    print("THỐNG KÊ DỮ LIỆU JSON SÁCH GIÁO KHOA")
    print("=" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # In một số chunks đầu tiên
    print("\n" + "=" * 60)
    print("MẪU CHUNKS ĐẦU TIÊN")
    print("=" * 60)
    
    for chunk in list(processor.iter_chunks())[:3]:
        print(f"\n📍 {chunk.full_path}")
        print(f"   Title: {chunk.subsection_title}")
        print(f"   Content: {chunk.combined_content[:200]}...")
        if chunk.context_before:
            print(f"   [Before]: {chunk.context_before[:100]}...")
