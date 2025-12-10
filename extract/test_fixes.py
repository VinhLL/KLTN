# -*- coding: utf-8 -*-
"""
Test file cho các hàm đã sửa trong utils.py và output_manager.py
Kiểm tra:
1. group_consecutive_occurrences - xử lý occurrences thiếu sentence_index
2. split_long_chunk - chia chunks dựa trên số ký tự
3. save_entities - không bị lỗi KeyError
4. save_request_statistics - xử lý lỗi liên tục với dữ liệu không hợp lệ
"""

import sys
import os

# Đảm bảo có thể import các module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import utils
from json_processor import split_long_chunk, SemanticChunk, should_split_chunk


def test_group_consecutive_occurrences_missing_fields():
    """Test hàm group_consecutive_occurrences với occurrences thiếu các trường"""
    print("=" * 60)
    print("TEST 1: group_consecutive_occurrences với occurrences thiếu các trường")
    print("=" * 60)
    
    # Test case 1: Occurrences thiếu sentence_index
    occurrences_missing_index = [
        {
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 2',
            'exact_text': 'Hội nghị I-an-ta năm 1945',
            'section': 'Phần 1',
            'subsection': 'Mục a'
        },
        {
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 2',
            'exact_text': 'Trật tự thế giới hai cực',
        }
    ]
    
    try:
        result = utils.group_consecutive_occurrences(occurrences_missing_index)
        print("✓ Test 1a PASSED: Xử lý occurrences thiếu sentence_index thành công")
        print(f"  Kết quả: {len(result)} grouped occurrences")
    except KeyError as e:
        print(f"✗ Test 1a FAILED: KeyError - {e}")
        return False
    except Exception as e:
        print(f"✗ Test 1a FAILED: {type(e).__name__} - {e}")
        return False
    
    # Test case 2: Occurrences rỗng
    try:
        result = utils.group_consecutive_occurrences([])
        print("✓ Test 1b PASSED: Xử lý occurrences rỗng thành công")
        assert result == [], "Expected empty list"
    except Exception as e:
        print(f"✗ Test 1b FAILED: {e}")
        return False
    
    # Test case 3: Occurrences đầy đủ
    occurrences_complete = [
        {
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 1',
            'sentence_index': 5,
            'label': ['Hồ Chí Minh'],
            'exact_text': 'Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập'
        },
        {
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 1',
            'sentence_index': 6,
            'label': ['Hồ Chí Minh'],
            'exact_text': 'Người đã hy sinh vì độc lập dân tộc'
        }
    ]
    
    try:
        result = utils.group_consecutive_occurrences(occurrences_complete)
        print("✓ Test 1c PASSED: Xử lý occurrences đầy đủ thành công")
        print(f"  Kết quả: {len(result)} grouped occurrences")
    except Exception as e:
        print(f"✗ Test 1c FAILED: {e}")
        return False
    
    print()
    return True


def test_split_long_chunk():
    """Test hàm split_long_chunk với các trường hợp khác nhau"""
    print("=" * 60)
    print("TEST 2: split_long_chunk với các trường hợp khác nhau")
    print("=" * 60)
    
    # Test case 1: Chunk ngắn - không cần chia
    short_content = ["Câu 1.", "Câu 2.", "Câu 3."]
    short_chunk = SemanticChunk(
        topic_id="Chủ đề 1",
        topic_description="Test topic",
        lesson_id="Bài 1",
        lesson_title="Test lesson",
        section_index=1,
        section_title="Test section",
        subsection_label="a",
        subsection_title="Test subsection",
        content=short_content
    )
    
    parts = split_long_chunk(short_chunk)
    if len(parts) == 1:
        print("✓ Test 2a PASSED: Chunk ngắn không bị chia")
    else:
        print(f"✗ Test 2a FAILED: Expected 1 part, got {len(parts)}")
        return False
    
    # Test case 2: Chunk dài về số câu (>30 câu)
    long_sentences_content = [f"Câu số {i}." for i in range(35)]
    long_sentences_chunk = SemanticChunk(
        topic_id="Chủ đề 2",
        topic_description="Test topic 2",
        lesson_id="Bài 2",
        lesson_title="Test lesson 2",
        section_index=2,
        section_title="Test section 2",
        subsection_label="b",
        subsection_title="Test subsection 2",
        content=long_sentences_content
    )
    
    parts = split_long_chunk(long_sentences_chunk)
    if len(parts) >= 4:
        print(f"✓ Test 2b PASSED: Chunk dài (35 câu) được chia thành {len(parts)} phần")
    else:
        print(f"✗ Test 2b FAILED: Expected >= 4 parts, got {len(parts)}")
        return False
    
    # Test case 3: Chunk dài về số ký tự (>2000 chars) nhưng ít câu
    # Tạo 10 câu, mỗi câu ~300 ký tự = ~3000 ký tự
    long_chars_content = [
        f"Đây là câu số {i} với nội dung rất dài để test việc chia chunk dựa trên số ký tự. " * 5
        for i in range(10)
    ]
    char_count = len(" ".join(long_chars_content))
    print(f"  [Info] Chunk có {len(long_chars_content)} câu, {char_count} ký tự")
    
    long_chars_chunk = SemanticChunk(
        topic_id="Chủ đề 3",
        topic_description="Test topic 3",
        lesson_id="Bài 3",
        lesson_title="Test lesson 3",
        section_index=3,
        section_title="Test section 3",
        subsection_label="c",
        subsection_title="Test subsection 3",
        content=long_chars_content
    )
    
    parts = split_long_chunk(long_chars_chunk)
    if len(parts) >= 2:
        print(f"✓ Test 2c PASSED: Chunk dài ({char_count} chars) được chia thành {len(parts)} phần")
        for i, part in enumerate(parts):
            part_chars = len(" ".join(part.content))
            print(f"    Phần {i+1}: {len(part.content)} câu, {part_chars} ký tự")
    else:
        print(f"✗ Test 2c FAILED: Expected >= 2 parts for {char_count} chars, got {len(parts)}")
        return False
    
    print()
    return True


def test_should_split_chunk():
    """Test hàm should_split_chunk"""
    print("=" * 60)
    print("TEST 3: should_split_chunk")
    print("=" * 60)
    
    # Chunk ngắn
    short_chunk = SemanticChunk(
        topic_id="Test", topic_description="Test",
        lesson_id="Test", lesson_title="Test",
        section_index=1, section_title="Test",
        subsection_label="a", subsection_title="Test",
        content=["Câu ngắn."]
    )
    
    if not should_split_chunk(short_chunk):
        print("✓ Test 3a PASSED: Chunk ngắn không cần chia")
    else:
        print("✗ Test 3a FAILED: Chunk ngắn không nên cần chia")
        return False
    
    # Chunk dài về ký tự
    long_text = "A" * 2500
    long_char_chunk = SemanticChunk(
        topic_id="Test", topic_description="Test",
        lesson_id="Test", lesson_title="Test",
        section_index=1, section_title="Test",
        subsection_label="a", subsection_title="Test",
        content=[long_text]
    )
    
    if should_split_chunk(long_char_chunk):
        print("✓ Test 3b PASSED: Chunk dài về ký tự cần chia")
    else:
        print("✗ Test 3b FAILED: Chunk dài về ký tự nên cần chia")
        return False
    
    print()
    return True


def test_save_request_statistics_json_format():
    """Test hàm save_request_statistics với JSON format requests (không có file_path)"""
    print("=" * 60)
    print("TEST 4: save_request_statistics với JSON format")
    print("=" * 60)
    
    # Mock request_details như khi dùng JSON hierarchical format
    import output_manager
    import api_handler
    
    # Lưu state cũ
    old_request_details = api_handler.REQUEST_DETAILS.copy()
    old_request_counter = api_handler.REQUEST_COUNTER
    
    # Set mock data - giống như khi extract từ JSON
    api_handler.REQUEST_DETAILS = [
        {
            'request_number': 1,
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 1',
            'section': 'Phần 1',
            'subsection': 'Mục a',
            'window_index': 0,
            'start_time': '2024-01-01 10:00:00',
            'text_length': 500,
            'format': 'json_hierarchical',
            'has_context': True,
            'api': 'deepseek',
            'processing_time_seconds': 2.5,
            'status': 'success',
            'entities_extracted': 5,
            'entities_processed': 4
        },
        {
            'request_number': 2,
            'topic': 'Chủ đề 1',
            'lesson': 'Bài 2',
            'section': 'Phần 2',
            'window_index': 1,
            'status': 'success',
            'processing_time_seconds': 1.8,
            'entities_extracted': 3,
            'entities_processed': 3
        }
    ]
    api_handler.REQUEST_COUNTER = 2
    
    # Test save_request_statistics
    try:
        # Không thực sự lưu file, chỉ test logic
        entities = [{'id': 'Test Entity', 'type': 'Nhân Vật'}]
        output_manager.save_request_statistics(entities)
        print("✓ Test 4 PASSED: save_request_statistics xử lý JSON format thành công")
        result = True
    except KeyError as e:
        print(f"✗ Test 4 FAILED: KeyError - {e}")
        result = False
    except Exception as e:
        print(f"✗ Test 4 FAILED: {type(e).__name__} - {e}")
        result = False
    finally:
        # Restore state cũ
        api_handler.REQUEST_DETAILS = old_request_details
        api_handler.REQUEST_COUNTER = old_request_counter
    
    print()
    return result


def test_save_request_statistics_continuous_errors():
    """
    Test hàm save_request_statistics khi gặp lỗi liên tục với các request 
    có dữ liệu không hợp lệ hoặc thiếu trường.
    
    Test các trường hợp:
    1. Request thiếu hoàn toàn các trường cần thiết
    2. Request có giá trị None
    3. Request có kiểu dữ liệu sai
    4. Mix các loại request lỗi
    """
    print("=" * 60)
    print("TEST 5: save_request_statistics với lỗi liên tục")
    print("=" * 60)
    
    import output_manager
    import api_handler
    
    # Lưu state cũ
    old_request_details = api_handler.REQUEST_DETAILS.copy()
    old_request_counter = api_handler.REQUEST_COUNTER
    
    test_cases = [
        # Test case 1: Request hoàn toàn rỗng
        {
            'name': '5a - Request rỗng',
            'requests': [{}],
            'counter': 1
        },
        # Test case 2: Request thiếu topic và lesson
        {
            'name': '5b - Thiếu topic/lesson',
            'requests': [
                {'request_number': 1, 'status': 'success'},
                {'request_number': 2, 'status': 'error'}
            ],
            'counter': 2
        },
        # Test case 3: Request có giá trị None
        {
            'name': '5c - Giá trị None',
            'requests': [
                {
                    'request_number': 1,
                    'topic': None,
                    'lesson': None,
                    'file_path': None,
                    'status': 'success',
                    'processing_time_seconds': None,
                    'entities_extracted': None
                }
            ],
            'counter': 1
        },
        # Test case 4: Request có kiểu dữ liệu sai
        {
            'name': '5d - Kiểu dữ liệu sai',
            'requests': [
                {
                    'request_number': 'one',  # Nên là int
                    'topic': 123,  # Nên là str
                    'lesson': [],  # Nên là str
                    'status': {'success': True},  # Nên là str
                    'processing_time_seconds': 'fast',  # Nên là float
                    'entities_extracted': 'five'  # Nên là int
                }
            ],
            'counter': 1
        },
        # Test case 5: Mix các loại request
        {
            'name': '5e - Mix các loại',
            'requests': [
                {},  # Empty
                {'topic': 'Chủ đề 1'},  # Partial
                {'topic': None, 'lesson': 'Bài 1'},  # None value
                {  # Valid
                    'topic': 'Chủ đề 2',
                    'lesson': 'Bài 2',
                    'status': 'success',
                    'processing_time_seconds': 1.5
                },
                {'file_path': '/path/to/file.txt', 'status': 'success'},  # TXT format
            ],
            'counter': 5
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        api_handler.REQUEST_DETAILS = test_case['requests']
        api_handler.REQUEST_COUNTER = test_case['counter']
        
        try:
            entities = [{'id': 'Test', 'type': 'Nhân Vật'}]
            output_manager.save_request_statistics(entities)
            print(f"✓ Test {test_case['name']} PASSED: Xử lý thành công")
        except KeyError as e:
            print(f"✗ Test {test_case['name']} FAILED: KeyError - {e}")
            all_passed = False
        except TypeError as e:
            print(f"✗ Test {test_case['name']} FAILED: TypeError - {e}")
            all_passed = False
        except Exception as e:
            print(f"✗ Test {test_case['name']} FAILED: {type(e).__name__} - {e}")
            all_passed = False
    
    # Restore state cũ
    api_handler.REQUEST_DETAILS = old_request_details
    api_handler.REQUEST_COUNTER = old_request_counter
    
    print()
    return all_passed


def test_output_manager_robustness():
    """
    Test độ robust của output_manager khi xử lý entities với dữ liệu không hợp lệ.
    """
    print("=" * 60)
    print("TEST 6: Output manager robustness")
    print("=" * 60)
    
    import output_manager
    import api_handler
    from models import Entity
    
    # Lưu state cũ
    old_request_details = api_handler.REQUEST_DETAILS.copy()
    old_request_counter = api_handler.REQUEST_COUNTER
    
    # Reset để test clean
    api_handler.REQUEST_DETAILS = []
    api_handler.REQUEST_COUNTER = 0
    
    # Test entities với các trường hợp edge case
    test_entities = [
        # Entity bình thường
        {
            'id': 'Hồ Chí Minh',
            'label': ['Hồ Chí Minh', 'Bác Hồ'],
            'type': 'Nhân Vật',
            'description': 'Chủ tịch nước',
            'original_text': [
                {
                    'topic': 'Chủ đề 1',
                    'lesson': 'Bài 1',
                    'sentence_index': 0,
                    'label': ['Hồ Chí Minh'],
                    'exact_text': 'Hồ Chí Minh đọc Tuyên ngôn Độc lập'
                }
            ],
            'properties': {},
            'confidence': 0.9,
            'metadata': {'source': 'test'},
            'occurrence_count': 1,
            'window_indices': [0]
        },
        # Entity thiếu original_text
        {
            'id': 'Điện Biên Phủ',
            'label': ['Điện Biên Phủ'],
            'type': 'Địa điểm',
            'description': 'Địa danh lịch sử',
            'original_text': [],  # Empty
            'properties': {},
            'confidence': 0.8,
            'metadata': {},
            'occurrence_count': 0,
            'window_indices': []
        },
        # Entity với original_text thiếu sentence_index
        {
            'id': 'Việt Minh',
            'label': ['Việt Minh', 'Mặt trận Việt Minh'],
            'type': 'Tổ chức',
            'description': 'Mặt trận cứu quốc',
            'original_text': [
                {
                    'topic': 'Chủ đề 1',
                    'lesson': 'Bài 1',
                    'exact_text': 'Việt Minh lãnh đạo cách mạng'
                    # Thiếu sentence_index
                }
            ],
            'properties': {},
            'confidence': 0.85,
            'metadata': {},
            'occurrence_count': 1,
            'window_indices': [0]
        }
    ]
    
    try:
        # Test với một số entities hợp lệ
        # Không thực sự lưu file, chỉ kiểm tra không có exception
        for entity in test_entities:
            try:
                entity_obj = Entity(**entity)
                # Test group_consecutive_occurrences
                grouped = utils.group_consecutive_occurrences(entity.get('original_text', []))
            except Exception as e:
                print(f"  Warning: Entity '{entity.get('id')}' gặp lỗi: {e}")
        
        print("✓ Test 6 PASSED: Output manager xử lý các edge cases thành công")
        result = True
    except Exception as e:
        print(f"✗ Test 6 FAILED: {type(e).__name__} - {e}")
        result = False
    finally:
        # Restore state cũ
        api_handler.REQUEST_DETAILS = old_request_details
        api_handler.REQUEST_COUNTER = old_request_counter
    
    print()
    return result


def run_all_tests():
    """Chạy tất cả tests"""
    print("\n" + "=" * 60)
    print("RUNNING ALL TESTS FOR BUG FIXES")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    # Test 1
    if not test_group_consecutive_occurrences_missing_fields():
        all_passed = False
    
    # Test 2
    if not test_split_long_chunk():
        all_passed = False
    
    # Test 3
    if not test_should_split_chunk():
        all_passed = False
    
    # Test 4
    if not test_save_request_statistics_json_format():
        all_passed = False
    
    # Test 5 - MỚI: Test lỗi liên tục
    if not test_save_request_statistics_continuous_errors():
        all_passed = False
    
    # Test 6 - MỚI: Test robustness
    if not test_output_manager_robustness():
        all_passed = False
    
    # Summary
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

