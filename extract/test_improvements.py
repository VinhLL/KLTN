# -*- coding: utf-8 -*-
"""Script kiểm tra các cải tiến trong entity extraction."""

import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, 'D:/KLTN/KLTN/extract')

from entity_processor import (
    should_skip_entity, 
    find_similar_entity, 
    merge_entities,
    cleanup_entities
)
from utils import clean_labels

def test_should_skip_entity():
    """Test hàm should_skip_entity với các trường hợp cần skip."""
    print("=" * 60)
    print("Testing should_skip_entity:")
    print("=" * 60)
    
    test_cases = [
        # Ngày tháng năm
        {"id": "ngày 30 tháng 4 năm 1977", "type": "Sự kiện", "description": ""},
        {"id": "30 – 4 – 1977", "type": "Sự kiện", "description": ""},
        {"id": "5 – 1 – 1978", "type": "Sự kiện", "description": ""},
        {"id": "1945", "type": "Sự kiện", "description": ""},
        
        # Khẩu hiệu, khái niệm
        {"id": "thắng lợi quân sự", "type": "Khái niệm", "description": ""},
        {"id": "vừa đánh, vừa đàm", "type": "Khái niệm", "description": ""},
        {"id": "cuộc chiến tranh phi nghĩa", "type": "Khái niệm", "description": ""},
        {"id": "Đảng mới 15 tuổi", "type": "Khái niệm", "description": ""},
        {"id": "an ninh nhân dân", "type": "Khái niệm", "description": ""},
        {"id": "công cuộc đổi mới", "type": "Khái niệm", "description": ""},
        
        # Entity hợp lệ - KHÔNG NÊN SKIP
        {"id": "Đại hội đại biểu toàn quốc lần thứ VI", "type": "Sự kiện", "description": ""},
        {"id": "Hồ Chí Minh", "type": "Nhân Vật", "description": ""},
        {"id": "Việt Nam", "type": "Quốc gia", "description": ""},
    ]
    
    for entity in test_cases:
        should_skip = should_skip_entity(entity, {})
        status = "SKIP" if should_skip else "KEEP"
        print(f"  [{status}] {entity['id']}")
    print()

def test_clean_labels():
    """Test hàm clean_labels với các trường hợp duplicate case."""
    print("=" * 60)
    print("Testing clean_labels:")
    print("=" * 60)
    
    test_cases = [
        ["An ninh nhân dân", "an ninh nhân dân"],
        ["Công cuộc Đổi mới", "công cuộc Đổi mới"],
        ["Hệ thống chính trị", "hệ thống chính trị"],
        ["Việt Nam", "việt nam", "VIỆT NAM"],
    ]
    
    for labels in test_cases:
        cleaned = clean_labels(labels)
        print(f"  Input:  {labels}")
        print(f"  Output: {cleaned}")
        print()

def test_ordinal_extraction():
    """Test trích xuất số thứ tự từ tên entity."""
    print("=" * 60)
    print("Testing ordinal extraction:")
    print("=" * 60)
    
    import re
    
    def extract_ordinal(name: str):
        name_lower = name.lower()
        
        # Roman patterns
        roman_patterns = [
            r'lần\s+thứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\bthứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\s(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\s*$',
            r'\b(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
        ]
        
        for pattern in roman_patterns:
            match = re.search(pattern, name_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    test_names = [
        "Đại hội VI",
        "Đại hội VII", 
        "Đại hội đại biểu toàn quốc lần thứ VI",
        "Đại hội đại biểu toàn quốc lần thứ VII",
        "Hội nghị Ban Chấp hành Trung ương lần thứ 15",
        "Quốc hội khoá VI",
    ]
    
    for name in test_names:
        ordinal = extract_ordinal(name)
        print(f"  '{name}' -> ordinal: '{ordinal}'")
    print()

def test_merge_protection():
    """Test việc bảo vệ không merge các entity có số thứ tự khác nhau."""
    print("=" * 60)
    print("Testing merge protection:")
    print("=" * 60)
    
    # Tạo các entity giả
    entity_vi = {
        'id': 'Đại hội đại biểu toàn quốc lần thứ VI',
        'type': 'Sự kiện',
        'label': ['Đại hội VI'],
        'description': '',
        'original_text': [],
        'window_indices': [],
        'metadata': {},
        'properties': {},
        'confidence': 0.9,
        'occurrence_count': 1
    }
    
    entity_vii = {
        'id': 'Đại hội VII',
        'type': 'Sự kiện', 
        'label': ['Đại hội VII', 'Đại hội đại biểu toàn quốc lần thứ VII'],
        'description': '',
        'original_text': [],
        'window_indices': [],
        'metadata': {},
        'properties': {},
        'confidence': 0.9,
        'occurrence_count': 1
    }
    
    # Test find_similar_entity
    similar = find_similar_entity(entity_vii, [entity_vi])
    print(f"  find_similar_entity('Đại hội VII', ['Đại hội VI']):")
    print(f"    Result: {'FOUND (BUG!)' if similar else 'None (CORRECT)'}")
    
    # Test merge_entities
    can_merge = merge_entities(entity_vi.copy(), entity_vii)
    print(f"  merge_entities('Đại hội VI', 'Đại hội VII'):")
    print(f"    Can merge: {can_merge} ({'BUG!' if can_merge else 'CORRECT'})")
    print()

def main():
    print("\n" + "=" * 60)
    print("ENTITY EXTRACTION IMPROVEMENTS TEST")
    print("=" * 60 + "\n")
    
    test_should_skip_entity()
    test_clean_labels()
    test_ordinal_extraction()
    test_merge_protection()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
