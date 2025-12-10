import json
import re
import time
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from api_handler import call_deepseek_api
from config import MAX_RETRIES, MIN_EVIDENCE_LENGTH, MIN_PREDICATE_LENGTH, MAX_PREDICATE_LENGTH
from utils import get_timestamp

# Import JSON processor neu co
try:
    from json_processor import SemanticChunk, create_relationship_prompt
    JSON_PROCESSOR_AVAILABLE = True
except ImportError:
    JSON_PROCESSOR_AVAILABLE = False
    SemanticChunk = None

def validate_relationship(relationship: Dict, entity_lookup: Dict[str, Dict]) -> bool:
    """
    Validate if a relationship is valid (yêu cầu nghiêm ngặt).
    
    Điều kiện:
    - Subject và Object PHẢI tồn tại trong Entity Lookup (theo ID hoặc labels)
    - Subject và Object không được trùng nhau
    - Predicate phải có độ dài tối thiểu 2 ký tự
    - Evidence phải có độ dài tối thiểu 8 ký tự và chứa ít nhất một thực thể hoặc keyword
    """
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    # Kiểm tra cơ bản - các trường bắt buộc
    if not subject_id or not object_id or not predicate:
        return False
    
    # Subject và Object không được trùng nhau
    if subject_id == object_id:
        return False
    
    # ===== KIỂM TRA NGHIÊM NGẶT: CẢ HAI PHẢI TỒN TẠI =====
    
    # Kiểm tra Subject tồn tại (theo ID)
    subject_exists = subject_id in entity_lookup
    
    # Nếu không tồn tại theo ID, thử tìm qua labels
    if not subject_exists:
        for entity in entity_lookup.values():
            entity_labels = entity.get('label', [])
            if isinstance(entity_labels, str):
                entity_labels = [entity_labels]
            # Kiểm tra exact match hoặc case-insensitive match
            if subject_id in entity_labels or any(subject_id.lower() == label.lower() for label in entity_labels):
                subject_exists = True
                break
    
    # Kiểm tra Object tồn tại (theo ID)
    object_exists = object_id in entity_lookup
    
    # Nếu không tồn tại theo ID, thử tìm qua labels
    if not object_exists:
        for entity in entity_lookup.values():
            entity_labels = entity.get('label', [])
            if isinstance(entity_labels, str):
                entity_labels = [entity_labels]
            # Kiểm tra exact match hoặc case-insensitive match
            if object_id in entity_labels or any(object_id.lower() == label.lower() for label in entity_labels):
                object_exists = True
                break
    
    # YÊU CẦU NGHIÊM NGẶT: CẢ HAI subject VÀ object PHẢI tồn tại
    if not subject_exists or not object_exists:
        return False
    
    # Kiểm tra predicate có độ dài tối thiểu
    if len(predicate) < 2:
        return False
    
    # Kiểm tra evidence có độ dài tối thiểu
    if len(evidence) < 8:
        return False
    
    # Kiểm tra evidence chứa ít nhất một thực thể hoặc keyword liên kết
    evidence_lower = evidence.lower()
    
    # Tìm subject trong evidence
    subject_found = False
    for entity in entity_lookup.values():
        if entity.get('id') == subject_id:
            for label in entity.get('label', []):
                if label.lower() in evidence_lower:
                    subject_found = True
                    break
            break
    
    # Tìm object trong evidence
    object_found = False
    for entity in entity_lookup.values():
        if entity.get('id') == object_id:
            for label in entity.get('label', []):
                if label.lower() in evidence_lower:
                    object_found = True
                    break
            break
    
    # Chấp nhận nếu có ít nhất MỘT thực thể xuất hiện trong evidence
    # HOẶC evidence chứa từ khóa liên kết quan hệ
    if not subject_found and not object_found:
        common_keywords = ['với', 'của', 'cho', 'tại', 'trong', 'bởi', 'là', 'được', 'do', 'từ', 'đến', 'và']
        if not any(keyword in evidence_lower for keyword in common_keywords):
            return False
    
    return True

def merge_relationships(relationships: List[Dict]) -> List[Dict]:
    """Merge duplicate relationships and update occurrence counts."""
    relationship_key_map = {}
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        
        if key in relationship_key_map:
            existing_rel = relationship_key_map[key]
            existing_rel['occurrence_count'] = existing_rel.get('occurrence_count', 1) + 1
            
            if 'supporting_sentences' not in existing_rel:
                existing_rel['supporting_sentences'] = []
            
            new_evidence = {
                'evidence': rel.get('evidence', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': get_timestamp()
            }
            
            evidence_exists = False
            for existing_evidence in existing_rel['supporting_sentences']:
                if existing_evidence.get('evidence') == new_evidence['evidence']:
                    evidence_exists = True
                    break
            
            if not evidence_exists:
                existing_rel['supporting_sentences'].append(new_evidence)
            
            existing_rel['confidence'] = max(existing_rel.get('confidence', 0.9), rel.get('confidence', 0.9))
            
        else:
            rel['occurrence_count'] = 1
            rel['supporting_sentences'] = [{
                'evidence': rel.get('evidence', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': get_timestamp()
            }]
            rel['properties'] = rel.get('properties', {})
            relationship_key_map[key] = rel
    
    return list(relationship_key_map.values())

def post_process_relationships(relationships: List[Dict]) -> Tuple[List[Dict], Dict]:
    """Post-process relationships and return diagnostics."""
    diagnostics = {
        "initial_relationships": len(relationships),
        "valid_relationships": 0,
        "duplicate_relationships": 0,
        "final_relationships": 0
    }
    
    valid_relationships = []
    for rel in relationships:
        if (rel.get('subject_id') and rel.get('object_id') and 
            rel.get('predicate') and rel.get('subject_id') != rel.get('object_id')):
            valid_relationships.append(rel)
    
    diagnostics["valid_relationships"] = len(valid_relationships)
    
    merged_relationships = merge_relationships(valid_relationships)
    diagnostics["duplicate_relationships"] = len(valid_relationships) - len(merged_relationships)
    diagnostics["final_relationships"] = len(merged_relationships)
    
    return merged_relationships, diagnostics

def create_enhanced_prompt_for_entity(entity_info: Dict) -> str:
    """Create enhanced prompt for relationship extraction focusing on specific entity."""
    entity_id = entity_info['id']
    entity_type = entity_info.get('type', 'Unknown')
    entity_description = entity_info.get('description', '')
    entity_labels = entity_info.get('label', [])
    occurrence_count = len(entity_info.get('original_text', []))
    
    timeline_info = ""
    if 'metadata' in entity_info and 'timeline_summary' in entity_info['metadata']:
        timeline_summary = entity_info['metadata']['timeline_summary']
        if timeline_summary:
            timeline_info = "\nCác mốc thời gian liên quan:\n"
            for time_key in list(timeline_summary.keys())[:3]:
                timeline_info += f"- {time_key}\n"
    
    prompt_template = f"""Bạn là chuyên gia phân tích lịch sử Việt Nam. Tìm các mối quan hệ có ý nghĩa cho thực thể:

THỰC THỂ TRỌNG TÂM:
- ID: {entity_id}
- Loại: {entity_type}
- Tên/Khác: {', '.join(entity_labels[:10])}
- Mô tả: {entity_description}
- Số lần xuất hiện: {occurrence_count}
{timeline_info}

YÊU CẦU:
1. Tìm ít nhất 1-2 quan hệ cho thực thể này với các thực thể khác trong danh sách
2. Quan hệ phải dựa trên thông tin thực tế trong văn bản
3. Ưu tiên các loại quan hệ phù hợp với loại thực thể:"""
    
    relationship_suggestions = {
        'Nhân Vật': ['lãnh_đạo', 'tham_gia', 'thành_lập', 'đề_xuất', 'ký_kết', 'đại_diện', 'chỉ_huy', 'thúc_đẩy'],
        'Tổ chức': ['thành_lập', 'lãnh_đạo', 'tham_gia', 'hợp_tác', 'thuộc_về', 'đại_diện', 'thành_viên_của', 'tổ_chức'],
        'Sự kiện': ['diễn_ra_tại', 'tổ_chức', 'tham_gia', 'liên_quan_đến', 'kết_thúc_với', 'bắt_đầu_tại', 'được_tổ_chức_bởi'],
        'Địa điểm': ['diễn_ra_tại', 'thuộc_về', 'tại', 'ở', 'trong', 'gần', 'cạnh'],
        'Chiến dịch/Trận đánh': ['diễn_ra_tại', 'lãnh_đạo', 'tham_gia', 'kết_thúc_với', 'bắt_đầu_tại', 'thắng_lợi_tại'],
        'Văn kiện/Hiệp định': ['ký_kết', 'thông_qua', 'đề_xuất', 'liên_quan_đến', 'ban_hành', 'phê_chuẩn'],
        'Quốc gia': ['hợp_tác', 'ủng_hộ', 'phản_đối', 'đại_diện', 'có_quan_hệ_với', 'thiết_lập_ngoại_giao', 'xung_đột_với'],
        'Chiến lược/Chủ trương': ['đề_ra', 'thực_hiện', 'triển_khai', 'ảnh_hưởng_đến', 'được_thông_qua_bởi'],
        'Khái niệm': ['liên_quan_đến', 'ảnh_hưởng', 'được_định_nghĩa_bởi', 'thể_hiện_trong'],
        'Hội nghị': ['diễn_ra_tại', 'tổ_chức', 'tham_gia', 'chủ_trì', 'thông_qua'],
        'Công trình': ['xây_dựng_tại', 'khánh_thành', 'phục_vụ', 'thuộc_về'],
    }
    
    suggestions = relationship_suggestions.get(entity_type, ['liên_quan_đến', 'tham_gia', 'liên_kết_với', 'có_mối_quan_hệ_với'])
    prompt_template += f"\n- {', '.join(suggestions)}\n\n"
    
    examples = {
        'Nhân Vật': "Ví dụ: 'Hồ Chí Minh thành_lập Việt Minh', 'Võ Nguyên Giáp chỉ_huy Điện Biên Phủ'",
        'Tổ chức': "Ví dụ: 'Việt Minh thành_lập Uỷ ban Dân tộc giải phóng', 'ASEAN hợp_tác với Liên hợp quốc'",
        'Sự kiện': "Ví dụ: 'Cách mạng tháng Tám diễn_ra_tại Hà Nội', 'Đại hội Quốc dân thông_qua 10 chính sách'",
        'Địa điểm': "Ví dụ: 'Tân Trào là nơi diễn_ra Đại hội Quốc dân', 'Hà Nội là thủ_đô của Việt Nam'",
    }
    
    if entity_type in examples:
        prompt_template += f"{examples[entity_type]}\n\n"
    
    prompt_template += """ĐỊNH DẠNG ĐẦU RA JSON:
{
  "relationships": [
    {
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn cụ thể chứng minh quan hệ",
      "confidence": 0.8
    }
  ]
}

QUAN TRỌNG:
1. Subject_id và object_id phải tồn tại trong danh sách thực thể được cung cấp
2. Mỗi quan hệ phải có bằng chứng cụ thể từ văn bản
3. Nếu không tìm thấy quan hệ trực tiếp, có thể đề xuất quan hệ dựa trên bối cảnh lịch sử chung
4. Cố gắng tìm ít nhất 1 quan hệ cho thực thể trọng tâm"""
    
    return prompt_template

def extract_relationships_from_window(
    start_idx: int,
    window_sentences: List[str],
    entity_lookup: Dict[str, Dict],
    file_info: Dict[str, str],
    target_entity_id: str = None
) -> Optional[Dict]:
    """Extract relationships from a window using Gemini API."""
    
    entity_summary = []
    entity_ids = list(entity_lookup.keys())
    
    if target_entity_id:
        entity = entity_lookup.get(target_entity_id)
        if not entity:
            print(f"Target entity {target_entity_id} not found in lookup")
            return None
        
        enhanced_prompt = create_enhanced_prompt_for_entity(entity)
        
        entity_summary.append(f"- {target_entity_id} ({entity.get('type', 'Unknown')})")
        
        target_type = entity.get('type', '')
        connection_categories = {
            'Nhân Vật': ['Tổ chức', 'Sự kiện', 'Chiến dịch/Trận đánh', 'Văn kiện/Hiệp định', 'Địa điểm'],
            'Tổ chức': ['Nhân Vật', 'Quốc gia', 'Sự kiện', 'Chiến lược/Chủ trương', 'Địa điểm'],
            'Sự kiện': ['Địa điểm', 'Nhân Vật', 'Tổ chức', 'Chiến dịch/Trận đánh', 'Quốc gia'],
            'Địa điểm': ['Sự kiện', 'Chiến dịch/Trận đánh', 'Tổ chức', 'Quốc gia', 'Nhân Vật'],
            'Chiến lược/Chủ trương': ['Nhân Vật', 'Tổ chức', 'Quốc gia', 'Sự kiện'],
            'Văn kiện/Hiệp định': ['Nhân Vật', 'Tổ chức', 'Quốc gia', 'Sự kiện'],
            'Quốc gia': ['Tổ chức', 'Nhân Vật', 'Sự kiện', 'Chiến lược/Chủ trương'],
            'Chiến dịch/Trận đánh': ['Địa điểm', 'Nhân Vật', 'Tổ chức', 'Quốc gia'],
        }
        
        categories_to_include = connection_categories.get(target_type, ['Tổ chức', 'Nhân Vật', 'Sự kiện', 'Quốc gia'])
        
        related_entity_ids = set()
        for occ in entity.get('original_text', []):
            exact_text = occ.get('exact_text', '').lower()
            for other_id in entity_ids:
                if other_id == target_entity_id:
                    continue
                other_entity = entity_lookup[other_id]
                for label in other_entity.get('label', []):
                    if label.lower() in exact_text and len(label) > 2:
                        related_entity_ids.add(other_id)
                        break
        
        for entity_id in related_entity_ids:
            if len(entity_summary) >= 20:
                break
            other_entity = entity_lookup[entity_id]
            entity_summary.append(f"- {entity_id} ({other_entity.get('type', 'Unknown')})")
        
        for entity_id in entity_ids:
            if len(entity_summary) >= 25:
                break
            if entity_id == target_entity_id or entity_id in related_entity_ids:
                continue
            other_entity = entity_lookup[entity_id]
            if other_entity.get('type') in categories_to_include:
                entity_summary.append(f"- {entity_id} ({other_entity.get('type', 'Unknown')})")
        
        existing_entities_str = "\n".join(entity_summary)
        window_text = " ".join(window_sentences)
        
        full_prompt = f"""{enhanced_prompt}

DANH SÁCH CÁC THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

VĂN BẢN NGỮ CẢNH:
{window_text}

HƯỚNG DẪN BỔ SUNG:
1. Tập trung tìm quan hệ cho thực thể: {target_entity_id}
2. Nếu trong ngữ cảnh này không có thông tin trực tiếp, hãy xem xét các quan hệ gián tiếp hoặc bối cảnh lịch sử
3. Ưu tiên các quan hệ có bằng chứng rõ ràng từ văn bản
4. Có thể đề xuất quan hệ dựa trên vai trò, vị trí của thực thể trong lịch sử

Chỉ trả về JSON hợp lệ, không thêm nội dung khác."""
        
    else:
        for entity_id in entity_ids[:500]:
            entity = entity_lookup[entity_id]
            if entity_id == entity['id']:
                entity_summary.append(f"- {entity_id} ({entity.get('type', 'Unknown')})")
        
        existing_entities_str = "\n".join(entity_summary)
        window_text = " ".join(window_sentences)
        
        full_prompt = f"""Bạn là chuyên gia phân tích văn bản lịch sử Việt Nam. Hãy trích xuất các mối quan hệ có ý nghĩa giữa các thực thể dựa trên nội dung văn bản.

DANH SÁCH THỰC THỂ HIỆN CÓ (chỉ sử dụng các thực thể này):
{existing_entities_str}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

QUY TẮC QUAN TRỌNG:
1. CHỈ sử dụng các thực thể có trong danh sách trên
2. Mỗi quan hệ phải kết nối 2 thực thể KHÁC NHAU
3. Quan hệ phải dựa trên thông tin thực tế trong văn bản
4. Mô tả quan hệ bằng động từ/cụm động từ tiếng Việt tự nhiên
5. Mỗi quan hệ cần có bằng chứng rõ ràng từ văn bản

LOẠI QUAN HỆ GỢI Ý (có thể sử dụng hoặc tự đề xuất quan hệ phù hợp):
- tham_gia: Tham gia sự kiện, tổ chức, hội nghị
- tổ_chức: Tổ chức sự kiện, hội nghị
- thành_lập: Thành lập tổ chức, đảng phái
- lãnh_đạo: Lãnh đạo, chỉ huy
- đại_diện: Đại diện cho quốc gia, tổ chức
- ký_kết: Ký kết hiệp định, văn kiện
- diễn_ra_tại: Sự kiện diễn ra tại địa điểm
- thuộc_về: Thuộc quốc gia, tổ chức
- ảnh_hưởng: Có ảnh hưởng đến
- hợp_tác: Hợp tác với
- phản_đối: Phản đối, chống lại
- ủng_hộ: Ủng hộ, giúp đỡ
- đề_xuất: Đề xuất, kiến nghị
- thông_qua: Thông qua văn kiện, nghị quyết

ĐỊNH DẠNG ĐẦU RA JSON:
{{
  "relationships": [
    {{
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn cụ thể chứng minh quan hệ",
      "confidence": 0.9
    }}
  ]
}}

Chỉ trả về JSON hợp lệ, không thêm nội dung khác."""
    
    result = call_deepseek_api(full_prompt, MAX_RETRIES)
    if not result:
        return None
    
    validated_relationships = []
    for rel in result.get('relationships', []):
        if validate_relationship(rel, entity_lookup):
            rel['window_info'] = {
                'start_idx': start_idx,
                'sentences': window_sentences,
                'file_info': file_info,
                'target_entity_focus': target_entity_id if target_entity_id else None
            }
            
            if target_entity_id and (rel.get('subject_id') == target_entity_id or rel.get('object_id') == target_entity_id):
                rel['confidence'] = min(0.95, rel.get('confidence', 0.9) * 1.1)
            
            validated_relationships.append(rel)
    
    return {
        'relationships': validated_relationships,
        'window_index': start_idx,
        'target_entity': target_entity_id
    }


def extract_relationships_from_json_chunk(
    chunk: Any,  # SemanticChunk from json_processor
    entity_lookup: Dict[str, Dict],
    chunk_index: int = 0
) -> Optional[Dict]:
    """
    Extract relationships from a JSON semantic chunk.
    
    Args:
        chunk: SemanticChunk object from json_processor
        entity_lookup: Dictionary of entities
        chunk_index: Index of this chunk
        
    Returns:
        Dictionary with extracted relationships (never None)
    """
    if not JSON_PROCESSOR_AVAILABLE:
        print("[Warning] json_processor not available")
        return {'relationships': [], 'chunk_index': chunk_index, 'chunk_path': '', 'error': 'json_processor not available'}
    
    # Tao prompt tu json_processor
    entities_list = list(entity_lookup.values())
    prompt = create_relationship_prompt(chunk, entities_list)
    
    # Goi API
    result = call_deepseek_api(prompt, MAX_RETRIES)
    
    # Handle API failure - return empty result instead of None
    if not result:
        print(f"   [!] API returned no result for chunk {chunk_index}")
        return {
            'relationships': [],
            'chunk_index': chunk_index,
            'chunk_path': chunk.full_path,
            'status': 'api_failed'
        }
    
    # Get raw relationships from API
    raw_relationships = result.get('relationships', [])
    
    # Validate relationships
    validated_relationships = []
    validation_stats = {
        'total': len(raw_relationships),
        'valid': 0,
        'invalid_subject': 0,
        'invalid_object': 0,
        'same_entity': 0,
        'missing_predicate': 0
    }
    
    for rel in raw_relationships:
        # Check basic structure
        subject_id = rel.get('subject_id', '')
        object_id = rel.get('object_id', '')
        predicate = rel.get('predicate', '')
        
        # Skip if missing predicate
        if not predicate:
            validation_stats['missing_predicate'] += 1
            continue
            
        # Skip if same entity
        if subject_id and object_id and subject_id.lower() == object_id.lower():
            validation_stats['same_entity'] += 1
            continue
        
        # Validate with entity lookup
        if validate_relationship(rel, entity_lookup):
            rel['chunk_info'] = {
                'chunk_index': chunk_index,
                'topic': chunk.topic_description,
                'lesson': chunk.lesson_title,
                'section': chunk.section_title,
                'subsection': chunk.subsection_title,
                'full_path': chunk.full_path
            }
            validated_relationships.append(rel)
            validation_stats['valid'] += 1
        else:
            # Log why validation failed
            if subject_id not in entity_lookup:
                validation_stats['invalid_subject'] += 1
            elif object_id not in entity_lookup:
                validation_stats['invalid_object'] += 1
    
    # Log validation summary if there were issues
    if validation_stats['total'] > 0 and validation_stats['valid'] == 0:
        print(f"   [!] No relationships extracted (raw: {validation_stats['total']}, "
              f"invalid_subj: {validation_stats['invalid_subject']}, "
              f"invalid_obj: {validation_stats['invalid_object']}, "
              f"same_entity: {validation_stats['same_entity']})")
    elif validation_stats['total'] > validation_stats['valid']:
        rejected = validation_stats['total'] - validation_stats['valid']
        print(f"   [Validation] {validation_stats['valid']}/{validation_stats['total']} valid "
              f"(rejected: {rejected})")
    
    return {
        'relationships': validated_relationships,
        'chunk_index': chunk_index,
        'chunk_path': chunk.full_path,
        'validation_stats': validation_stats
    }


def process_json_chunks_for_relationships(
    json_path: str,
    entity_lookup: Dict[str, Dict],
    max_chunks: int = None
) -> List[Dict]:
    """
    Process all JSON chunks to extract relationships.
    
    Args:
        json_path: Path to JSON textbook file
        entity_lookup: Dictionary of entities
        max_chunks: Maximum chunks to process (for testing)
        
    Returns:
        List of all extracted relationships
    """
    if not JSON_PROCESSOR_AVAILABLE:
        print("[Error] json_processor not available")
        return []
    
    from json_processor import JSONTextbookProcessor
    
    processor = JSONTextbookProcessor(json_path)
    
    # Sử dụng chunks với overlap để xử lý context dài
    # 7 câu/chunk, 5 câu overlap (step = 2)
    print("\n[INFO] Đang chia chunks với overlap (7 câu/chunk, 5 câu overlap)...")
    chunks = processor.get_all_chunks_with_overlap()
    
    if max_chunks:
        chunks = chunks[:max_chunks]
    
    print(f"\n[JSON Relationship Extraction]")
    print(f"Total chunks: {len(chunks)}")
    print("=" * 60)
    
    all_relationships = []
    
    for i, chunk in enumerate(chunks):
        print(f"\n[{i+1}/{len(chunks)}] {chunk.full_path}")
        print(f"   Section: {chunk.section_title}")
        print(f"   Subsection: {chunk.subsection_title}")
        
        result = extract_relationships_from_json_chunk(
            chunk=chunk,
            entity_lookup=entity_lookup,
            chunk_index=i
        )
        
        if result and result.get('relationships'):
            rels = result['relationships']
            all_relationships.extend(rels)
            print(f"   [OK] Extracted {len(rels)} relationships")
        else:
            print(f"   [!] No relationships extracted")
    
    # Merge duplicate relationships
    merged = merge_relationships(all_relationships)
    
    print("\n" + "=" * 60)
    print(f"Total relationships: {len(merged)}")
    print("=" * 60)
    
    return merged