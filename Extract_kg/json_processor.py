# -*- coding: utf-8 -*-
"""
json_processor.py - Xu ly JSON cho Extract_kg
Dua tren cau truc tu D:/KLTN/KLTN/SGK/SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json

Chien luoc xử lý:
- Overlapping chunks: 7 câu mỗi chunk, overlap 5 câu để duy trì ngữ nghĩa
- Tránh mất thông tin do việc chia cắt ngữ cảnh
"""

import json
import os
from typing import Dict, List, Any, Iterator, Optional, Tuple
from dataclasses import dataclass, field

# ===== CHUNKING CONFIGURATION =====
# Số câu tối đa mỗi chunk
SENTENCES_PER_CHUNK = 7
# Số câu overlap (7 - 2 = 5 câu overlap để giữ ngữ nghĩa)
OVERLAP_SENTENCES = 5
# Bước nhảy = SENTENCES_PER_CHUNK - OVERLAP_SENTENCES = 2
STEP_SIZE = SENTENCES_PER_CHUNK - OVERLAP_SENTENCES

# Ngưỡng chia chunk
MAX_SENTENCES_BEFORE_SPLIT = 10  # Nếu > 10 câu thì cần chia
MAX_CHARS_BEFORE_SPLIT = 1200   # Nếu > 1200 chars thì cần chia


def should_split_content(content: List[str]) -> bool:
    """
    Kiểm tra xem content có cần chia nhỏ không.
    
    Args:
        content: Danh sách các câu
        
    Returns:
        True nếu cần chia nhỏ
    """
    if len(content) > MAX_SENTENCES_BEFORE_SPLIT:
        return True
    
    combined_text = " ".join(content)
    if len(combined_text) > MAX_CHARS_BEFORE_SPLIT:
        return True
    
    return False


def split_content_with_overlap(
    content: List[str],
    sentences_per_chunk: int = SENTENCES_PER_CHUNK,
    overlap: int = OVERLAP_SENTENCES
) -> List[Tuple[List[str], int, int]]:
    """
    Chia content thành các chunks với overlap để giữ ngữ nghĩa.
    
    Ví dụ với 7 câu/chunk và overlap 5:
    - Chunk 1: câu 0-6 (7 câu)
    - Chunk 2: câu 2-8 (bắt đầu từ 2, chồng lấp 5 câu với chunk 1)
    - Chunk 3: câu 4-10 (bắt đầu từ 4, chồng lấp 5 câu với chunk 2)
    
    Args:
        content: Danh sách các câu
        sentences_per_chunk: Số câu mỗi chunk (mặc định 7)
        overlap: Số câu overlap (mặc định 5)
        
    Returns:
        List of (sentences, start_idx, end_idx) tuples
    """
    if not content:
        return []
    
    # Nếu content ngắn, không cần chia
    if len(content) <= sentences_per_chunk:
        return [(content, 0, len(content))]
    
    if len(" ".join(content)) <= MAX_CHARS_BEFORE_SPLIT:
        return [(content, 0, len(content))]
    
    step = sentences_per_chunk - overlap
    if step <= 0:
        step = 1  # Đảm bảo luôn tiến lên ít nhất 1 câu
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = min(start + sentences_per_chunk, len(content))
        chunk_content = content[start:end]
        
        # Nếu chunk cuối quá ngắn, merge với chunk trước
        if len(chunk_content) < 3 and chunks:
            # Mở rộng chunk trước thay vì tạo chunk mới quá ngắn
            prev_content, prev_start, prev_end = chunks[-1]
            extended_content = content[prev_start:end]
            chunks[-1] = (extended_content, prev_start, end)
        else:
            chunks.append((chunk_content, start, end))
        
        start += step
        
        # Tránh vòng lặp vô tận nếu start không thay đổi
        if start == 0:
            break
    
    return chunks


@dataclass
class SemanticChunk:
    """Dai dien mot subsection (don vi ngu nghia nho nhat)."""
    topic_id: str
    topic_description: str
    lesson_id: str
    lesson_title: str
    section_index: int
    section_title: str
    subsection_label: str
    subsection_title: str
    content: List[str]  # Danh sach cac cau
    
    # Context lan can
    context_before: str = ""
    context_after: str = ""
    
    @property
    def full_path(self) -> str:
        """Tao duong dan day du."""
        return f"{self.topic_id}/{self.lesson_id}/Section {self.section_index}/{self.subsection_label}"
    
    @property
    def text(self) -> str:
        """Noi dung dang text."""
        return " ".join(self.content)
    
    def to_window(self) -> Dict[str, Any]:
        """Chuyen thanh format window tuong thich."""
        return {
            'topic_id': self.topic_id,
            'topic_description': self.topic_description,
            'topic': self.topic_id,
            'lesson_id': self.lesson_id,
            'lesson_title': self.lesson_title,
            'lesson': self.lesson_id,
            'section_index': self.section_index,
            'section_title': self.section_title,
            'subsection_label': self.subsection_label,
            'subsection_title': self.subsection_title,
            'sentences': self.content,
            'text': self.text,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'full_path': self.full_path,
            'window_index': 0
        }


class JSONTextbookProcessor:
    """Xu ly file JSON sach giao khoa."""
    
    def __init__(self, json_path: str):
        """
        Khoi tao processor.
        
        Args:
            json_path: Duong dan toi file JSON
        """
        self.json_path = json_path
        self.data = []
        self.chunks: List[SemanticChunk] = []
        
        self._load_json()
        self._build_chunks()
    
    def _load_json(self):
        """Load file JSON."""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def _build_chunks(self):
        """Xay dung danh sach chunks tu JSON data."""
        self.chunks = []
        
        for lesson_data in self.data:
            topic_id = lesson_data.get('topic_id', '')
            topic_desc = lesson_data.get('topic_description', '')
            lesson_id = lesson_data.get('lesson_id', '')
            lesson_title = lesson_data.get('lesson_title', '')
            
            sections = lesson_data.get('sections', [])
            for section in sections:
                section_idx = section.get('index', 0)
                section_title = section.get('title', '')
                
                subsections = section.get('subsections', [])
                for subsection in subsections:
                    sub_label = subsection.get('label', '')
                    sub_title = subsection.get('title', '')
                    content = subsection.get('content', [])
                    
                    if content:  # Chỉ them subsection co noi dung
                        chunk = SemanticChunk(
                            topic_id=topic_id,
                            topic_description=topic_desc,
                            lesson_id=lesson_id,
                            lesson_title=lesson_title,
                            section_index=section_idx,
                            section_title=section_title,
                            subsection_label=sub_label,
                            subsection_title=sub_title,
                            content=content
                        )
                        self.chunks.append(chunk)
        
        # Them context lan can
        self._add_context()
    
    def _add_context(self):
        """Them context tu subsections lan can."""
        for i, chunk in enumerate(self.chunks):
            # Context truoc
            if i > 0:
                prev_chunk = self.chunks[i - 1]
                if prev_chunk.lesson_id == chunk.lesson_id:
                    chunk.context_before = " ".join(prev_chunk.content[-2:])
            
            # Context sau
            if i < len(self.chunks) - 1:
                next_chunk = self.chunks[i + 1]
                if next_chunk.lesson_id == chunk.lesson_id:
                    chunk.context_after = " ".join(next_chunk.content[:2])
    
    def get_all_chunks(self) -> List[SemanticChunk]:
        """Lay tat ca chunks."""
        return self.chunks
    
    def get_all_windows(self) -> List[Dict[str, Any]]:
        """Lay tat ca windows (format tuong thich)."""
        windows = []
        for i, chunk in enumerate(self.chunks):
            window = chunk.to_window()
            window['window_index'] = i
            windows.append(window)
        return windows
    
    def get_chunks_by_topic(self) -> Dict[str, List[SemanticChunk]]:
        """Nhom chunks theo topic."""
        result = {}
        for chunk in self.chunks:
            key = f"{chunk.topic_id}: {chunk.topic_description}"
            if key not in result:
                result[key] = []
            result[key].append(chunk)
        return result
    
    def get_chunks_by_lesson(self) -> Dict[str, List[SemanticChunk]]:
        """Nhom chunks theo lesson."""
        result = {}
        for chunk in self.chunks:
            key = f"{chunk.topic_id}/{chunk.lesson_id}"
            if key not in result:
                result[key] = []
            result[key].append(chunk)
        return result
    
    def iter_chunks(self) -> Iterator[SemanticChunk]:
        """Iterator qua tat ca chunks."""
        for chunk in self.chunks:
            yield chunk
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lay thong ke ve du lieu."""
        topics = set()
        lessons = set()
        total_sentences = 0
        
        for chunk in self.chunks:
            topics.add(chunk.topic_id)
            lessons.add(f"{chunk.topic_id}/{chunk.lesson_id}")
            total_sentences += len(chunk.content)
        
        return {
            'total_chunks': len(self.chunks),
            'total_topics': len(topics),
            'total_lessons': len(lessons),
            'total_sentences': total_sentences,
            'avg_sentences_per_chunk': total_sentences / len(self.chunks) if self.chunks else 0
        }
    
    def get_all_chunks_with_overlap(self) -> List[SemanticChunk]:
        """
        Lấy tất cả chunks với việc chia nhỏ các chunk dài.
        Sử dụng chiến lược overlap 7 câu/chunk, 5 câu overlap.
        
        Returns:
            List[SemanticChunk]: Danh sách chunks đã được tối ưu
        """
        result = []
        split_count = 0
        
        for chunk in self.chunks:
            if should_split_content(chunk.content):
                # Chia chunk theo overlap
                split_parts = split_content_with_overlap(chunk.content)
                num_parts = len(split_parts)
                split_count += 1
                
                print(f"   [Split] {chunk.full_path}: {len(chunk.content)} sentences, "
                      f"{len(' '.join(chunk.content))} chars -> {num_parts} parts")
                
                for part_idx, (part_content, start_idx, end_idx) in enumerate(split_parts):
                    part_label = f"{chunk.subsection_label}_p{part_idx+1}" if chunk.subsection_label else f"p{part_idx+1}"
                    part_title = f"{chunk.subsection_title} (P{part_idx+1}/{num_parts})" if chunk.subsection_title else f"Phần {part_idx+1}/{num_parts}"
                    
                    # Context từ các phần liền kề
                    context_before = ""
                    context_after = ""
                    
                    if part_idx == 0:
                        # Phần đầu: giữ context_before gốc
                        context_before = chunk.context_before
                    else:
                        # Các phần sau: lấy context từ phần trước (overlap)
                        prev_content = split_parts[part_idx - 1][0]
                        context_before = " ".join(prev_content[-2:])
                    
                    if part_idx == num_parts - 1:
                        # Phần cuối: giữ context_after gốc
                        context_after = chunk.context_after
                    else:
                        # Các phần trước: lấy context từ phần sau (overlap)
                        next_content = split_parts[part_idx + 1][0]
                        context_after = " ".join(next_content[:2])
                    
                    new_chunk = SemanticChunk(
                        topic_id=chunk.topic_id,
                        topic_description=chunk.topic_description,
                        lesson_id=chunk.lesson_id,
                        lesson_title=chunk.lesson_title,
                        section_index=chunk.section_index,
                        section_title=chunk.section_title,
                        subsection_label=part_label,
                        subsection_title=part_title,
                        content=part_content,
                        context_before=context_before,
                        context_after=context_after
                    )
                    result.append(new_chunk)
            else:
                result.append(chunk)
        
        if split_count > 0:
            print(f"\n[INFO] Đã chia {split_count} chunks dài (>{MAX_SENTENCES_BEFORE_SPLIT} câu hoặc >{MAX_CHARS_BEFORE_SPLIT} chars)")
            print(f"[INFO] Tổng chunks sau khi chia: {len(result)} (trước: {len(self.chunks)})")
        
        return result
    
    def iter_chunks_with_overlap(self) -> Iterator[SemanticChunk]:
        """
        Iterator qua tất cả chunks với việc chia nhỏ các chunk dài.
        Sử dụng chiến lược overlap 7 câu/chunk, 5 câu overlap.
        """
        for chunk in self.get_all_chunks_with_overlap():
            yield chunk
    
    def get_statistics_with_split(self) -> Dict[str, Any]:
        """
        Thống kê bao gồm cả chunks sau khi split.
        """
        base_stats = self.get_statistics()
        split_chunks = self.get_all_chunks_with_overlap()
        
        base_stats['total_chunks_after_split'] = len(split_chunks)
        base_stats['split_ratio'] = len(split_chunks) / len(self.chunks) if self.chunks else 0
        
        return base_stats


def filter_entities_in_text(
    text: str, 
    entities: List[Dict],
    topic: str = None,
    lesson: str = None
) -> List[Dict]:
    """
    Lọc entities thực sự xuất hiện trong text.
    
    Chiến lược lọc:
    1. Nếu có topic/lesson: Kiểm tra original_text xem entity có xuất hiện trong context này không
    2. Kiểm tra labels từ original_text nếu có
    3. Fall back: Kiểm tra entity ID và labels chung trong text
    
    Args:
        text: Văn bản cần kiểm tra
        entities: Danh sách tất cả entities
        topic: Topic hiện tại (ví dụ: "Chủ đề 1")
        lesson: Lesson hiện tại (ví dụ: "Bài 1")
        
    Returns:
        Danh sách entities xuất hiện trong text với labels phù hợp
    """
    text_lower = text.lower()
    found_entities = []
    seen_ids = set()
    
    for entity in entities:
        entity_id = entity.get('id', '')
        if entity_id in seen_ids:
            continue
        
        # Chiến lược 1: Kiểm tra original_text (nếu có topic/lesson)
        if topic or lesson:
            original_texts = entity.get('original_text', [])
            context_labels = None
            found_in_context = False
            
            for occ in original_texts:
                occ_topic = occ.get('topic', '')
                occ_lesson = occ.get('lesson', '')
                
                # Kiểm tra có trong cùng topic/lesson không
                topic_match = (not topic) or (topic and topic in occ_topic) or (occ_topic in topic)
                lesson_match = (not lesson) or (lesson and lesson in occ_lesson) or (occ_lesson in lesson)
                
                if topic_match and lesson_match:
                    # Lấy labels cụ thể cho context này
                    context_labels = occ.get('labels', [])
                    
                    # Kiểm tra xem các labels có xuất hiện trong text không
                    for label in context_labels:
                        if len(label) > 2 and label.lower() in text_lower:
                            found_in_context = True
                            break
                    
                    if found_in_context:
                        break
            
            if found_in_context and context_labels:
                # Tạo entity copy với labels phù hợp cho context
                entity_copy = entity.copy()
                entity_copy['context_labels'] = list(set(context_labels))
                found_entities.append(entity_copy)
                seen_ids.add(entity_id)
                continue
        
        # Chiến lược 2: Fall back - Kiểm tra entity ID trong text
        if entity_id.lower() in text_lower:
            found_entities.append(entity)
            seen_ids.add(entity_id)
            continue
        
        # Chiến lược 3: Kiểm tra các labels chung của entity
        labels = entity.get('label', [])
        if isinstance(labels, str):
            labels = [labels]
        
        for label in labels:
            if len(label) > 2 and label.lower() in text_lower:
                found_entities.append(entity)
                seen_ids.add(entity_id)
                break
    
    return found_entities


def create_relationship_prompt(chunk: SemanticChunk, entities: List[Dict]) -> str:
    """
    Tao prompt de trich xuat quan he tu chunk.
    
    Args:
        chunk: Semantic chunk can xu ly
        entities: Danh sach entities da biet
        
    Returns:
        Prompt string
    """
    # Lọc entities xuất hiện trong chunk text (bao gồm context)
    full_text = f"{chunk.context_before} {chunk.text} {chunk.context_after}"
    
    # Lọc entities thực sự xuất hiện trong text, sử dụng topic/lesson để lọc chính xác hơn
    relevant_entities = filter_entities_in_text(
        full_text, 
        entities,
        topic=chunk.topic_id,
        lesson=chunk.lesson_id
    )
    
    # Nếu không tìm thấy entity nào, thử với text gốc không context
    if not relevant_entities:
        relevant_entities = filter_entities_in_text(
            chunk.text, entities,
            topic=chunk.topic_id,
            lesson=chunk.lesson_id
        )
    
    # Giới hạn 30 entities để tránh prompt quá dài
    relevant_entities = relevant_entities[:30]
    
    # Format entity list với thông tin type
    if relevant_entities:
        entity_lines = []
        for e in relevant_entities:
            entity_id = e.get('id', e.get('name', ''))
            entity_type = e.get('type', 'Unknown')
            labels = e.get('label', [])
            if isinstance(labels, list) and len(labels) > 1:
                aliases = ', '.join(labels[1:4])  # 3 aliases đầu tiên
                entity_lines.append(f"- {entity_id} ({entity_type}) [alias: {aliases}]")
            else:
                entity_lines.append(f"- {entity_id} ({entity_type})")
        entity_list = "\n".join(entity_lines)
    else:
        entity_list = "Khong tim thay entity nao trong doan van nay"
    
    # Thêm thông báo nếu không có entities
    entity_note = ""
    if not relevant_entities:
        entity_note = "\nCHU Y: Khong tim thay entity trong ENTITY_FILE. Co the trich xuat cac thuc the moi neu tim thay trong van ban.\n"
    
    prompt = f"""TRICH XUAT QUAN HE TU VAN BAN LICH SU VIET NAM

NGU CANH: {chunk.topic_description}
BAI: {chunk.lesson_title}
PHAN: {chunk.section_title} / {chunk.subsection_title}

VAN BAN:
{chunk.text}

ENTITIES XUAT HIEN TRONG DOAN VAN ({len(relevant_entities)} entities):
{entity_list}
{entity_note}
YEU CAU:
Trich xuat TAT CA quan he giua cac thuc the TRONG VAN BAN TREN.
Chi su dung cac entity da liet ke o tren (uu tien) hoac entity moi xuat hien trong van ban.
Moi quan he bao gom: subject_id, predicate, object_id, evidence.

LOAI QUAN HE PHO BIEN:
- thanh_lap (to chuc thanh lap)
- lanh_dao (nguoi lanh dao to chuc/su kien)  
- tham_gia (tham gia su kien/to chuc)
- dien_ra_tai (su kien dien ra tai dia diem)
- ket_qua_cua (ket qua/hau qua)
- nguyen_nhan (nguyen nhan)
- lien_quan_den (lien quan)
- ky_ket (ky ket hiep dinh/van kien)
- chien_dau (chien dau trong tran danh/chien dich)
- hop_tac (hop tac quoc te)
- thuoc_ve (thanh vien cua to chuc)
- thong_qua (thong qua van kien/quyet dinh)
- cong_nhan (cong nhan/phe chuan)

DINH DANG JSON:
{{"relationships": [
    {{"subject_id": "ten thuc the 1", "predicate": "loai_quan_he", "object_id": "ten thuc the 2", "evidence": "cau van trong van ban"}}
]}}

Neu khong tim thay quan he nao, tra ve: {{"relationships": []}}
Tra ve JSON hop le."""

    return prompt


# Test
if __name__ == "__main__":
    import config
    
    json_path = os.path.join(config.ROOT_DIR, config.JSON_INPUT_FILE)
    
    print(f"Loading: {json_path}")
    processor = JSONTextbookProcessor(json_path)
    
    stats = processor.get_statistics()
    print("\n=== THONG KE ===")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n=== MAU CHUNKS ===")
    for i, chunk in enumerate(processor.iter_chunks()):
        if i >= 3:
            break
        print(f"\n[{i+1}] {chunk.full_path}")
        print(f"    {chunk.subsection_title}")
        print(f"    Sentences: {len(chunk.content)}")
