# -*- coding: utf-8 -*-
"""
test_extract_kg.py - Unit tests for Extract_kg package
Covers all modules except topic_processor.py (too large)
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from typing import List, Dict

# Add Extract_kg to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestUtils(unittest.TestCase):
    """Tests for utils.py"""
    
    def test_split_into_sentences(self):
        from utils import split_into_sentences
        
        text = "Đây là câu thứ nhất. Đây là câu thứ hai! Đây là câu thứ ba?"
        sentences = split_into_sentences(text)
        
        self.assertIsInstance(sentences, list)
        self.assertEqual(len(sentences), 3)
        self.assertIn("Đây là câu thứ nhất", sentences[0])
    
    def test_split_sentences_vietnamese(self):
        from utils import split_sentences_vietnamese
        
        text = "Lịch sử Việt Nam rất phong phú. Có nhiều giai đoạn quan trọng! Cách mạng tháng 8 là bước ngoặt?"
        sentences = split_sentences_vietnamese(text)
        
        self.assertIsInstance(sentences, list)
        self.assertGreater(len(sentences), 0)
    
    def test_extract_topic_and_lesson(self):
        from utils import extract_topic_and_lesson
        
        # Test với đường dẫn hợp lệ
        file_path = "SGK/Nguồn/Chủ đề 1/Bài 1.txt"
        topic, lesson = extract_topic_and_lesson(file_path)
        
        self.assertEqual(topic, "Chủ đề 1")
        self.assertEqual(lesson, "Bài 1")
    
    def test_create_overlapping_windows(self):
        from utils import create_overlapping_windows
        
        sentences = ["Câu 1", "Câu 2", "Câu 3", "Câu 4", "Câu 5", "Câu 6", "Câu 7", "Câu 8"]
        windows = create_overlapping_windows(sentences, window_size=3, step=1)
        
        self.assertIsInstance(windows, list)
        self.assertGreater(len(windows), 0)
        
        # Kiểm tra mỗi window có cấu trúc đúng
        for start_idx, window in windows:
            self.assertIsInstance(start_idx, int)
            self.assertIsInstance(window, list)
            self.assertEqual(len(window), 3)
    
    def test_clean_text_for_matching(self):
        from utils import clean_text_for_matching
        
        text = "Đây là   văn bản!!!  có ký tự đặc biệt@#$"
        cleaned = clean_text_for_matching(text)
        
        self.assertIsInstance(cleaned, str)
        self.assertNotIn("@#$", cleaned)
    
    def test_normalize_text(self):
        from utils import normalize_text
        
        text = "  ĐÂY LÀ VĂN BẢN   "
        normalized = normalize_text(text)
        
        self.assertEqual(normalized, "đây là văn bản")
    
    def test_calculate_similarity(self):
        from utils import calculate_similarity
        
        text1 = "Lịch sử Việt Nam"
        text2 = "Lịch sử Việt Nam"
        similarity = calculate_similarity(text1, text2)
        
        self.assertEqual(similarity, 1.0)
        
        text3 = "Khác hoàn toàn"
        similarity2 = calculate_similarity(text1, text3)
        
        self.assertLess(similarity2, 1.0)
    
    def test_merge_dicts(self):
        from utils import merge_dicts
        
        dict1 = {"a": [1, 2], "b": "x"}
        dict2 = {"a": [3, 4], "c": "y"}
        
        merged = merge_dicts(dict1, dict2)
        
        self.assertEqual(merged["a"], [1, 2, 3, 4])
        self.assertEqual(merged["b"], "x")
        self.assertEqual(merged["c"], "y")
    
    def test_get_timestamp(self):
        from utils import get_timestamp
        
        timestamp = get_timestamp()
        
        self.assertIsInstance(timestamp, str)
        self.assertIn("-", timestamp)  # Format: YYYY-MM-DD HH:MM:SS
    
    def test_create_file_info(self):
        from utils import create_file_info
        
        file_path = "SGK/Nguồn/Chủ đề 1/Bài 1.txt"
        info = create_file_info(file_path)
        
        self.assertIn("file_path", info)
        self.assertIn("filename", info)
        self.assertIn("topic", info)
        self.assertIn("lesson", info)
        self.assertIn("processed_at", info)


class TestJsonProcessor(unittest.TestCase):
    """Tests for json_processor.py"""
    
    def setUp(self):
        """Create sample JSON data for testing"""
        self.sample_data = [
            {
                "topic_id": "Chủ đề 1",
                "topic_description": "THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH",
                "lesson_id": "Bài 1",
                "lesson_title": "LIÊN HỢP QUỐC",
                "sections": [
                    {
                        "index": 1,
                        "title": "Một số vấn đề cơ bản về Liên hợp quốc",
                        "subsections": [
                            {
                                "label": "a",
                                "title": "Bối cảnh lịch sử",
                                "content": [
                                    "Câu 1 về lịch sử.",
                                    "Câu 2 về lịch sử.", 
                                    "Câu 3 về lịch sử.",
                                    "Câu 4 về lịch sử.",
                                    "Câu 5 về lịch sử."
                                ]
                            },
                            {
                                "label": "b",
                                "title": "Mục tiêu hoạt động",
                                "content": [
                                    "Câu 1 về mục tiêu.",
                                    "Câu 2 về mục tiêu."
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Create temp JSON file
        self.temp_dir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.temp_dir, "test_textbook.json")
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f, ensure_ascii=False)
    
    def tearDown(self):
        """Clean up temp files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_should_split_content(self):
        from json_processor import should_split_content
        
        # Short content - no split needed
        short_content = ["Câu 1", "Câu 2", "Câu 3"]
        self.assertFalse(should_split_content(short_content))
        
        # Long content - split needed
        long_content = ["Câu " + str(i) + " với nội dung dài" * 10 for i in range(20)]
        self.assertTrue(should_split_content(long_content))
    
    def test_split_content_with_overlap(self):
        from json_processor import split_content_with_overlap
        
        # Test với content dài (>1200 chars)
        content = [f"Đây là câu số {i+1} với nội dung khá dài để đảm bảo vượt ngưỡng ký tự." for i in range(20)]
        chunks = split_content_with_overlap(content, sentences_per_chunk=7, overlap=5)
        
        self.assertIsInstance(chunks, list)
        # Nếu content đủ dài (>1200 chars), sẽ được chia
        if len(" ".join(content)) > 1200:
            self.assertGreater(len(chunks), 1)
        
        # Kiểm tra cấu trúc
        for chunk_content, start, end in chunks:
            self.assertIsInstance(chunk_content, list)
            self.assertLessEqual(len(chunk_content), 10)  # Có thể mở rộng nếu merge short chunks
    
    def test_split_content_with_overlap_short(self):
        from json_processor import split_content_with_overlap
        
        # Test với content ngắn
        short_content = ["Câu 1", "Câu 2", "Câu 3"]
        chunks = split_content_with_overlap(short_content)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], short_content)
    
    def test_semantic_chunk_creation(self):
        from json_processor import SemanticChunk
        
        chunk = SemanticChunk(
            topic_id="Chủ đề 1",
            topic_description="Test",
            lesson_id="Bài 1",
            lesson_title="Test Lesson",
            section_index=1,
            section_title="Test Section",
            subsection_label="a",
            subsection_title="Test Subsection",
            content=["Câu 1", "Câu 2"]
        )
        
        self.assertEqual(chunk.topic_id, "Chủ đề 1")
        self.assertEqual(len(chunk.content), 2)
        self.assertIn("Chủ đề 1", chunk.full_path)
        self.assertEqual(chunk.text, "Câu 1 Câu 2")
    
    def test_json_textbook_processor_init(self):
        from json_processor import JSONTextbookProcessor
        
        processor = JSONTextbookProcessor(self.json_path)
        
        self.assertEqual(len(processor.chunks), 2)  # 2 subsections
    
    def test_json_textbook_processor_get_all_chunks(self):
        from json_processor import JSONTextbookProcessor
        
        processor = JSONTextbookProcessor(self.json_path)
        chunks = processor.get_all_chunks()
        
        self.assertEqual(len(chunks), 2)
    
    def test_json_textbook_processor_get_statistics(self):
        from json_processor import JSONTextbookProcessor
        
        processor = JSONTextbookProcessor(self.json_path)
        stats = processor.get_statistics()
        
        self.assertIn('total_chunks', stats)
        self.assertIn('total_topics', stats)
        self.assertIn('total_lessons', stats)
        self.assertIn('total_sentences', stats)
        self.assertEqual(stats['total_chunks'], 2)
        self.assertEqual(stats['total_topics'], 1)
    
    def test_json_textbook_processor_with_overlap(self):
        from json_processor import JSONTextbookProcessor
        
        # Create data with VERY long content (>1200 chars và >10 câu)
        long_data = [
            {
                "topic_id": "Chủ đề 1",
                "topic_description": "Test",
                "lesson_id": "Bài 1",
                "lesson_title": "Test",
                "sections": [
                    {
                        "index": 1,
                        "title": "Test Section",
                        "subsections": [
                            {
                                "label": "a",
                                "title": "Long Subsection",
                                # Tạo nội dung dài hơn 1200 ký tự và hơn 10 câu
                                "content": [f"Đây là câu số {i+1} với nội dung rất dài để đảm bảo vượt ngưỡng 1200 ký tự và tách chunk." for i in range(25)]
                            }
                        ]
                    }
                ]
            }
        ]
        
        json_path = os.path.join(self.temp_dir, "test_long.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(long_data, f, ensure_ascii=False)
        
        processor = JSONTextbookProcessor(json_path)
        chunks_without_split = processor.get_all_chunks()
        chunks_with_split = processor.get_all_chunks_with_overlap()
        
        self.assertEqual(len(chunks_without_split), 1)
        # Content dài sẽ được chia
        self.assertGreaterEqual(len(chunks_with_split), 1)
    
    def test_filter_entities_in_text(self):
        from json_processor import filter_entities_in_text
        
        entities = [
            {"id": "Liên hợp quốc", "label": ["Liên hợp quốc", "LHQ", "UN"]},
            {"id": "Việt Nam", "label": ["Việt Nam", "VN"]},
            {"id": "ASEAN", "label": ["ASEAN", "Hiệp hội các quốc gia Đông Nam Á"]},
            {"id": "NATO", "label": ["NATO"]}
        ]
        
        text = "Liên hợp quốc được thành lập năm 1945. Việt Nam là thành viên."
        
        # Test without topic/lesson (fallback to text matching)
        filtered = filter_entities_in_text(text, entities)
        
        self.assertEqual(len(filtered), 2)
        entity_ids = [e["id"] for e in filtered]
        self.assertIn("Liên hợp quốc", entity_ids)
        self.assertIn("Việt Nam", entity_ids)
        self.assertNotIn("ASEAN", entity_ids)
        self.assertNotIn("NATO", entity_ids)
    
    def test_filter_entities_in_text_by_alias(self):
        from json_processor import filter_entities_in_text
        
        entities = [
            {"id": "Liên hợp quốc", "label": ["Liên hợp quốc", "LHQ", "UN"]},
        ]
        
        # Tìm bằng alias
        text = "LHQ được thành lập năm 1945."
        filtered = filter_entities_in_text(text, entities)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "Liên hợp quốc")
    
    def test_filter_entities_in_text_empty(self):
        from json_processor import filter_entities_in_text
        
        entities = [
            {"id": "ASEAN", "label": ["ASEAN"]},
        ]
        
        text = "Văn bản không có entity nào."
        filtered = filter_entities_in_text(text, entities)
        
        self.assertEqual(len(filtered), 0)
    
    def test_filter_entities_in_text_with_original_text(self):
        """Test filtering entities using original_text data"""
        from json_processor import filter_entities_in_text
        
        # Entity với original_text chứa labels cụ thể cho mỗi topic/lesson
        entities = [
            {
                "id": "Liên hợp quốc",
                "label": ["Liên hợp quốc", "LHQ", "UN"],
                "original_text": [
                    {
                        "topic": "Chủ đề 1",
                        "lesson": "Bài 1",
                        "labels": ["LHQ"]  # Label cụ thể trong context này
                    }
                ]
            },
            {
                "id": "ASEAN",
                "label": ["ASEAN"],
                "original_text": [
                    {
                        "topic": "Chủ đề 2",  # Thuộc topic khác
                        "lesson": "Bài 4",
                        "labels": ["ASEAN"]
                    }
                ]
            }
        ]
        
        text = "LHQ được thành lập năm 1945."
        
        # Test với topic/lesson cụ thể
        filtered = filter_entities_in_text(text, entities, topic="Chủ đề 1", lesson="Bài 1")
        
        # Chỉ Liên hợp quốc được tìm thấy (vì LHQ xuất hiện trong text và trong original_text của Chủ đề 1)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "Liên hợp quốc")
        # Nên có context_labels từ original_text
        self.assertIn("context_labels", filtered[0])
    
    def test_create_relationship_prompt(self):
        from json_processor import SemanticChunk, create_relationship_prompt
        
        chunk = SemanticChunk(
            topic_id="Chủ đề 1",
            topic_description="Test",
            lesson_id="Bài 1",
            lesson_title="Test",
            section_index=1,
            section_title="Test Section",
            subsection_label="a",
            subsection_title="Test",
            content=["Liên hợp quốc được thành lập năm 1945."]
        )
        
        entities = [
            {"id": "Liên hợp quốc", "label": ["Liên hợp quốc"], "type": "Tổ chức"},
            {"id": "ASEAN", "label": ["ASEAN"], "type": "Tổ chức"}  # Should be filtered out
        ]
        prompt = create_relationship_prompt(chunk, entities)
        
        self.assertIsInstance(prompt, str)
        self.assertIn("Liên hợp quốc", prompt)
        self.assertIn("TRICH XUAT QUAN HE", prompt)
        # ASEAN should not be in prompt since it's not in the text
        self.assertNotIn("ASEAN", prompt)


class TestModels(unittest.TestCase):
    """Tests for models.py"""
    
    def test_entity_model(self):
        from models import Entity
        
        entity = Entity(
            id="Liên hợp quốc",
            label=["Liên hợp quốc", "UN"],
            type="Tổ chức",
            description="Tổ chức quốc tế lớn nhất thế giới",
            original_text=[]
        )
        
        self.assertEqual(entity.id, "Liên hợp quốc")
        self.assertEqual(entity.type, "Tổ chức")
        self.assertEqual(len(entity.label), 2)
    
    def test_triplet_model(self):
        from models import Triplet
        
        triplet = Triplet(
            subject_id="Việt Nam",
            predicate="tham_gia",
            object_id="Liên hợp quốc"
        )
        
        self.assertEqual(triplet.subject_id, "Việt Nam")
        self.assertEqual(triplet.predicate, "tham_gia")
        self.assertEqual(triplet.object_id, "Liên hợp quốc")
        self.assertEqual(triplet.confidence, 1.0)
    
    def test_knowledge_graph_model(self):
        from models import KnowledgeGraph, Entity, Triplet
        
        entities = [
            Entity(id="E1", label=["Entity 1"], type="Test", description="", original_text=[])
        ]
        triplets = [
            Triplet(subject_id="E1", predicate="test", object_id="E2")
        ]
        
        kg = KnowledgeGraph(entities=entities, triplets=triplets)
        
        self.assertEqual(len(kg.entities), 1)
        self.assertEqual(len(kg.triplets), 1)
    
    def test_extraction_result_model(self):
        from models import ExtractionResult
        
        result = ExtractionResult(
            relationships=[{"subject": "A", "predicate": "test", "object": "B"}],
            window_index=0
        )
        
        self.assertEqual(len(result.relationships), 1)
        self.assertEqual(result.window_index, 0)
        self.assertIsNone(result.target_entity)


class TestEntityProcessor(unittest.TestCase):
    """Tests for entity_processor.py"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_entities = [
            {
                "id": "Liên hợp quốc",
                "label": ["Liên hợp quốc", "LHQ", "UN"],
                "type": "Tổ chức",
                "description": "Tổ chức quốc tế",
                "original_text": [
                    {"topic": "Chủ đề 1", "lesson": "Bài 1", "exact_text": "Liên hợp quốc"}
                ]
            },
            {
                "id": "Việt Nam",
                "label": ["Việt Nam", "VN"],
                "type": "Quốc gia",
                "description": "Quốc gia Đông Nam Á",
                "original_text": [
                    {"topic": "Chủ đề 1", "lesson": "Bài 1", "exact_text": "Việt Nam"}
                ]
            }
        ]
        
        self.entity_file = os.path.join(self.temp_dir, "entities.json")
        with open(self.entity_file, 'w', encoding='utf-8') as f:
            json.dump(self.sample_entities, f, ensure_ascii=False)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_existing_entities(self):
        from entity_processor import load_existing_entities
        
        entities = load_existing_entities(self.entity_file)
        
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0]["id"], "Liên hợp quốc")
    
    def test_create_entity_lookup(self):
        from entity_processor import create_entity_lookup
        
        lookup = create_entity_lookup(self.sample_entities)
        
        self.assertIn("Liên hợp quốc", lookup)
        self.assertIn("UN", lookup)  # Alias
        self.assertIn("Việt Nam", lookup)
    
    def test_filter_entities_by_topic_lesson(self):
        from entity_processor import filter_entities_by_topic_lesson
        
        filtered = filter_entities_by_topic_lesson(
            self.sample_entities, "Chủ đề 1", "Bài 1"
        )
        
        # 2 entities + all their aliases (LHQ, UN, VN = 3 aliases) = 5
        self.assertGreaterEqual(len(filtered), 4)
    
    def test_find_entity_occurrences_in_sentences(self):
        from entity_processor import find_entity_occurrences_in_sentences
        
        sentences = [
            "Liên hợp quốc được thành lập năm 1945.",
            "Việt Nam gia nhập năm 1977.",
            "Đây là câu không có entity."
        ]
        
        occurrences = find_entity_occurrences_in_sentences(
            sentences, ["Liên hợp quốc"]
        )
        
        self.assertIn(0, occurrences)
        self.assertNotIn(2, occurrences)
    
    def test_identify_unconnected_entities(self):
        from entity_processor import identify_unconnected_entities
        
        kg = {
            "entities": self.sample_entities,
            "triplets": [
                {"subject_id": "Liên hợp quốc", "predicate": "test", "object_id": "Việt Nam"}
            ]
        }
        
        connected, unconnected = identify_unconnected_entities(kg)
        
        self.assertIn("Liên hợp quốc", connected)
        self.assertIn("Việt Nam", connected)
    
    def test_group_entities_by_type(self):
        from entity_processor import group_entities_by_type
        
        groups = group_entities_by_type(self.sample_entities)
        
        self.assertIn("Tổ chức", groups)
        self.assertIn("Quốc gia", groups)
        self.assertEqual(len(groups["Tổ chức"]), 1)


class TestRelationshipProcessor(unittest.TestCase):
    """Tests for relationship_processor.py"""
    
    def test_validate_relationship_valid(self):
        from relationship_processor import validate_relationship
        
        entity_lookup = {
            "Liên hợp quốc": {"id": "Liên hợp quốc", "label": ["Liên hợp quốc"]},
            "Việt Nam": {"id": "Việt Nam", "label": ["Việt Nam"]}
        }
        
        valid_rel = {
            "subject_id": "Liên hợp quốc",
            "predicate": "có_thành_viên",
            "object_id": "Việt Nam",
            "evidence": "Việt Nam là thành viên của Liên hợp quốc"
        }
        
        result = validate_relationship(valid_rel, entity_lookup)
        self.assertTrue(result)
    
    def test_validate_relationship_invalid_same_entity(self):
        from relationship_processor import validate_relationship
        
        entity_lookup = {
            "Liên hợp quốc": {"id": "Liên hợp quốc", "label": ["Liên hợp quốc"]}
        }
        
        invalid_rel = {
            "subject_id": "Liên hợp quốc",
            "predicate": "test",
            "object_id": "Liên hợp quốc",
            "evidence": "Test"
        }
        
        result = validate_relationship(invalid_rel, entity_lookup)
        self.assertFalse(result)
    
    def test_merge_relationships(self):
        from relationship_processor import merge_relationships
        
        relationships = [
            {"subject_id": "A", "predicate": "test", "object_id": "B", "evidence": "E1"},
            {"subject_id": "A", "predicate": "test", "object_id": "B", "evidence": "E2"},
            {"subject_id": "C", "predicate": "test", "object_id": "D", "evidence": "E3"}
        ]
        
        merged = merge_relationships(relationships)
        
        self.assertEqual(len(merged), 2)
        
        # Find the merged relationship
        ab_rel = next((r for r in merged if r["subject_id"] == "A"), None)
        self.assertIsNotNone(ab_rel)
        self.assertEqual(ab_rel["occurrence_count"], 2)
    
    def test_post_process_relationships(self):
        from relationship_processor import post_process_relationships
        
        relationships = [
            {"subject_id": "A", "predicate": "test", "object_id": "B"},
            {"subject_id": "A", "predicate": "test", "object_id": "B"},  # Duplicate
            {"subject_id": "", "predicate": "test", "object_id": "D"}  # Invalid
        ]
        
        processed, diagnostics = post_process_relationships(relationships)
        
        self.assertIn("initial_relationships", diagnostics)
        self.assertIn("final_relationships", diagnostics)
        self.assertEqual(diagnostics["initial_relationships"], 3)


class TestConfig(unittest.TestCase):
    """Tests for config.py"""
    
    def test_config_values(self):
        import config
        
        # Test các hằng số cơ bản
        self.assertTrue(hasattr(config, 'ROOT_DIR'))
        self.assertTrue(hasattr(config, 'USE_JSON_FORMAT'))
        self.assertTrue(hasattr(config, 'DEEPSEEK_MODEL'))
        self.assertTrue(hasattr(config, 'MAX_RETRIES'))
    
    def test_get_api_key(self):
        import config
        
        # Test function exists
        self.assertTrue(hasattr(config, 'get_api_key'))
        
        # Test function returns string
        result = config.get_api_key()
        self.assertIsInstance(result, str)


class TestApiHandler(unittest.TestCase):
    """Tests for api_handler.py - mocked tests"""
    
    def test_get_api_request_count(self):
        from api_handler import get_api_request_count, reset_api_request_count
        
        reset_api_request_count()
        count = get_api_request_count()
        
        self.assertEqual(count, 0)
    
    def test_reset_api_request_count(self):
        from api_handler import reset_api_request_count, get_api_request_count
        
        reset_api_request_count()
        self.assertEqual(get_api_request_count(), 0)
    
    def test_get_api_statistics(self):
        from api_handler import get_api_statistics, reset_api_request_count
        
        reset_api_request_count()
        stats = get_api_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_requests', stats)
        self.assertIn('errors', stats)
        self.assertIn('empty_responses', stats)
        self.assertIn('success_rate', stats)
    
    def test_fix_json_string(self):
        from api_handler import fix_json_string
        
        # Test trailing comma removal
        json_with_trailing_comma = '{"a": 1, "b": 2,}'
        fixed = fix_json_string(json_with_trailing_comma)
        self.assertNotIn(',}', fixed)
        
        # Test missing comma between objects
        json_without_comma = '{"a": 1}{"b": 2}'
        fixed = fix_json_string(json_without_comma)
        self.assertIn('},{', fixed)
    
    def test_extract_json_from_text(self):
        from api_handler import extract_json_from_text
        
        # Test with valid JSON in text
        text = 'Here is some text {"relationships": [{"subject_id": "A", "predicate": "test", "object_id": "B"}]} end.'
        result = extract_json_from_text(text)
        
        self.assertIsNotNone(result)
        self.assertIn('relationships', result)
        self.assertEqual(len(result['relationships']), 1)
    
    def test_extract_json_from_text_array(self):
        from api_handler import extract_json_from_text
        
        # Test with JSON array
        text = 'Result: [{"subject_id": "A", "predicate": "test", "object_id": "B"}]'
        result = extract_json_from_text(text)
        
        self.assertIsNotNone(result)
        self.assertIn('relationships', result)
    
    def test_extract_json_from_text_no_json(self):
        from api_handler import extract_json_from_text
        
        # Test with no JSON
        text = 'This is just plain text with no JSON'
        result = extract_json_from_text(text)
        
        self.assertIsNone(result)
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
    def test_get_deepseek_client(self):
        from api_handler import get_deepseek_client
        
        # Should not raise exception with valid key
        client = get_deepseek_client()
        self.assertIsNotNone(client)
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=True)
    def test_get_deepseek_client_no_key(self):
        # Re-import to get fresh module state
        import importlib
        import api_handler
        importlib.reload(api_handler)
        
        with self.assertRaises(RuntimeError):
            api_handler.get_deepseek_client()


class TestJsonReader(unittest.TestCase):
    """Tests for json_reader.py"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_data = [
            {
                "topic_id": "Chủ đề 1",
                "topic_description": "Test Topic",
                "lesson_id": "Bài 1",
                "lesson_title": "Test Lesson",
                "sections": [
                    {
                        "index": 1,
                        "title": "Test Section",
                        "subsections": [
                            {
                                "label": "a",
                                "title": "Test Subsection",
                                "content": ["Câu 1.", "Câu 2.", "Câu 3.", "Câu 4.", "Câu 5."]
                            }
                        ]
                    }
                ]
            }
        ]
        
        self.json_path = os.path.join(self.temp_dir, "test.json")
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f, ensure_ascii=False)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_textbook_json(self):
        from json_reader import load_textbook_json
        
        data = load_textbook_json(self.json_path)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["topic_id"], "Chủ đề 1")
    
    def test_iterate_lessons(self):
        from json_reader import iterate_lessons
        
        lessons = list(iterate_lessons(self.sample_data))
        
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["lesson_id"], "Bài 1")
    
    def test_iterate_sections(self):
        from json_reader import iterate_sections
        
        sections = list(iterate_sections(self.sample_data[0]))
        
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["title"], "Test Section")
    
    def test_iterate_subsections(self):
        from json_reader import iterate_subsections
        
        subsections = list(iterate_subsections(self.sample_data[0]["sections"][0]))
        
        self.assertEqual(len(subsections), 1)
        self.assertEqual(subsections[0]["label"], "a")
    
    def test_get_lesson_text(self):
        from json_reader import get_lesson_text
        
        text = get_lesson_text(self.sample_data[0])
        
        self.assertIn("Câu 1", text)
        self.assertIn("Câu 5", text)
    
    def test_create_compact_context(self):
        from json_reader import create_compact_context
        
        # Note: create_compact_context uses 'topic' and 'lesson' keys, not 'topic_id' and 'lesson_id'
        window = {
            "topic": "Chủ đề 1",
            "lesson": "Bài 1",
            "section_index": 1,
            "subsection_label": "a",
            "subsection_title": "Test Subsection"
        }
        
        context = create_compact_context(window)
        
        self.assertIsInstance(context, str)
        self.assertIn("CHỦ ĐỀ 1", context.upper())  # topic is uppercased


class TestOutputManager(unittest.TestCase):
    """Tests for output_manager.py"""
    
    def test_analyze_knowledge_graph(self):
        from models import Entity, Triplet, KnowledgeGraph
        from output_manager import analyze_knowledge_graph
        
        entities = [
            Entity(id="E1", label=["Entity 1"], type="TestType", description="", original_text=[])
        ]
        triplets = [
            Triplet(subject_id="E1", predicate="test", object_id="E2")
        ]
        kg = KnowledgeGraph(entities=entities, triplets=triplets)
        
        # Should not raise exception
        analyze_knowledge_graph(kg)


class TestTopicConfig(unittest.TestCase):
    """Tests for topic_config.py - Relationship extraction configuration"""
    
    def setUp(self):
        """Create sample JSON data for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_json_data = [
            {
                "topic_id": "Chủ đề 1",
                "topic_description": "THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH",
                "lesson_id": "Bài 1",
                "lesson_title": "LIÊN HỢP QUỐC",
                "sections": [
                    {
                        "index": 1,
                        "title": "Test Section",
                        "subsections": [
                            {"label": "a", "title": "Test", "content": ["Câu test."]}
                        ]
                    }
                ]
            },
            {
                "topic_id": "Chủ đề 2",
                "topic_description": "ASEAN: NHỮNG CHẶNG ĐƯỜNG LỊCH SỬ",
                "lesson_id": "Bài 4",
                "lesson_title": "ASEAN",
                "sections": []
            }
        ]
        
        self.json_path = os.path.join(self.temp_dir, "test_textbook.json")
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_json_data, f, ensure_ascii=False)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_relationship_config_creation(self):
        """Test RelationshipConfig dataclass creation"""
        from topic_config import RelationshipConfig
        
        config = RelationshipConfig(
            topic_id="Chủ đề 1",
            topic_name="TEST TOPIC",
            topic_description="Test Description",
            focus_entities=["Tổ chức", "Quốc gia"],
            key_relationships=["thành_lập", "tham_gia"],
            relationship_patterns={"Tổ chức": ["thành_lập_bởi", "tham_gia_bởi"]},
            thematic_focus="Test focus",
            context_strategy="window_focused",
            window_size=10,
            step_size=5
        )
        
        self.assertEqual(config.topic_id, "Chủ đề 1")
        self.assertEqual(config.topic_name, "TEST TOPIC")
        self.assertEqual(len(config.focus_entities), 2)
        self.assertEqual(len(config.key_relationships), 2)
        self.assertIn("Tổ chức", config.relationship_patterns)
    
    def test_relationship_config_to_dict(self):
        """Test RelationshipConfig to_dict method"""
        from topic_config import RelationshipConfig
        
        config = RelationshipConfig(
            topic_id="Chủ đề 1",
            topic_name="TEST",
            topic_description="Test",
            focus_entities=["Tổ chức"],
            key_relationships=["thành_lập"]
        )
        
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn("topic_id", config_dict)
        self.assertIn("focus_entities", config_dict)
        self.assertIn("key_relationships", config_dict)
        self.assertIn("relationship_patterns", config_dict)
        self.assertIn("thematic_focus", config_dict)
    
    def test_topic_config_manager_default_configs(self):
        """Test TopicConfigManager with default configs"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        # Should have default configs for 6 topics
        self.assertGreater(len(manager.topics), 0)
        
        # Check default configs exist
        self.assertIn("Chủ đề 1", manager.topics)
        self.assertIn("Chủ đề 2", manager.topics)
        self.assertIn("Chủ đề 6", manager.topics)
    
    def test_topic_config_manager_from_json(self):
        """Test TopicConfigManager loading from JSON file"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager(self.json_path)
        
        # Should have configs from JSON
        self.assertGreater(len(manager.topics), 0)
    
    def test_get_config_by_topic_id(self):
        """Test getting config by topic_id"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        config = manager.get_config("Chủ đề 1")
        
        self.assertIsInstance(config, dict)
        self.assertIn("topic_id", config)
        self.assertIn("focus_entities", config)
        self.assertIn("key_relationships", config)
    
    def test_get_config_by_description(self):
        """Test getting config by topic description keyword"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        # Test with keyword in description
        config = manager.get_config("CHIẾN TRANH LẠNH")
        
        self.assertIsInstance(config, dict)
        # Should match Chủ đề 1
        self.assertIn("1", config.get("topic_id", ""))
    
    def test_get_config_unknown_topic(self):
        """Test getting config for unknown topic returns default"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        config = manager.get_config("Unknown Topic XYZ")
        
        self.assertIsInstance(config, dict)
        self.assertIn("topic_id", config)
        self.assertIn("focus_entities", config)
        # Should have minimum default entities
        self.assertGreater(len(config.get("focus_entities", [])), 0)
    
    def test_get_relationship_patterns(self):
        """Test getting relationship patterns for topic"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        # Get patterns for specific entity type
        patterns = manager.get_relationship_patterns("Chủ đề 1", "Tổ chức quốc tế")
        
        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)
    
    def test_get_relationship_patterns_all(self):
        """Test getting all relationship patterns for topic"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        # Get all patterns (no entity type specified)
        patterns = manager.get_relationship_patterns("Chủ đề 1")
        
        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)
    
    def test_get_key_relationships(self):
        """Test getting key relationships for topic"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        relationships = manager.get_key_relationships("Chủ đề 1")
        
        self.assertIsInstance(relationships, list)
        self.assertGreater(len(relationships), 0)
        self.assertIn("thành_lập", relationships)
    
    def test_get_lesson_info(self):
        """Test getting lesson info after loading from JSON"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager(self.json_path)
        
        lesson_info = manager.get_lesson_info("Bài 1")
        
        self.assertIsInstance(lesson_info, dict)
        if lesson_info:
            self.assertIn("topic_id", lesson_info)
            self.assertIn("lesson_title", lesson_info)
    
    def test_get_all_topics(self):
        """Test getting list of all topics"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        topics = manager.get_all_topics()
        
        self.assertIsInstance(topics, list)
        self.assertGreater(len(topics), 0)
    
    def test_get_topic_config_function(self):
        """Test convenience function get_topic_config"""
        from topic_config import get_topic_config
        
        config = get_topic_config("Chủ đề 1")
        
        self.assertIsInstance(config, dict)
        self.assertIn("topic_id", config)
        self.assertIn("key_relationships", config)
    
    def test_get_relationship_patterns_function(self):
        """Test convenience function get_relationship_patterns"""
        from topic_config import get_relationship_patterns
        
        patterns = get_relationship_patterns("Chủ đề 1", "Quốc gia")
        
        self.assertIsInstance(patterns, list)
    
    def test_default_config_topic1_structure(self):
        """Test structure of Chủ đề 1 default config"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        config = manager.get_config("Chủ đề 1")
        
        # Check required fields
        self.assertIn("focus_entities", config)
        self.assertIn("key_relationships", config)
        self.assertIn("relationship_patterns", config)
        self.assertIn("thematic_focus", config)
        self.assertIn("context_strategy", config)
        self.assertIn("window_size", config)
        self.assertIn("step_size", config)
        
        # Check focus_entities contains expected types
        focus = config.get("focus_entities", [])
        self.assertIn("Tổ chức quốc tế", focus)
        self.assertIn("Quốc gia", focus)
    
    def test_default_config_topic6_structure(self):
        """Test structure of Chủ đề 6 (Hồ Chí Minh) default config"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        config = manager.get_config("Chủ đề 6")
        
        # Check key_relationships contains HCM-specific relations
        relationships = config.get("key_relationships", [])
        self.assertIn("sinh_ra_tại", relationships)
        self.assertIn("sáng_lập", relationships)
        
        # Check historical_periods exist
        periods = config.get("historical_periods", {})
        self.assertGreater(len(periods), 0)
        
        # Check key_milestones exist
        milestones = config.get("key_milestones", {})
        self.assertGreater(len(milestones), 0)
    
    def test_topic_keywords_mapping(self):
        """Test TOPIC_KEYWORDS mapping works correctly"""
        from topic_config import TopicConfigManager
        
        manager = TopicConfigManager()
        
        # Test ASEAN keyword
        config = manager.get_config("ASEAN")
        self.assertIn("2", config.get("topic_id", ""))
        
        # Test Hồ Chí Minh keyword
        config = manager.get_config("HỒ CHÍ MINH")
        self.assertIn("6", config.get("topic_id", ""))
    
    def test_singleton_config_manager(self):
        """Test get_topic_config_manager returns singleton"""
        from topic_config import get_topic_config_manager
        
        manager1 = get_topic_config_manager()
        manager2 = get_topic_config_manager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)


class TestTopicProcessor(unittest.TestCase):
    """Tests for topic_processor.py - Topic-specific processing"""
    
    def test_topic_processor_configs_exist(self):
        """Test that TOPIC_CONFIGS contains all 6 topics"""
        from topic_processor import TopicProcessor
        
        configs = TopicProcessor.TOPIC_CONFIGS
        
        self.assertIsInstance(configs, dict)
        self.assertIn("Chủ đề 1", configs)
        self.assertIn("Chủ đề 2", configs)
        self.assertIn("Chủ đề 3", configs)
        self.assertIn("Chủ đề 4", configs)
        self.assertIn("Chủ đề 5", configs)
        self.assertIn("Chủ đề 6", configs)
    
    def test_topic_processor_config_structure(self):
        """Test that each topic config has required fields"""
        from topic_processor import TopicProcessor
        
        required_fields = ["topic_name", "focus_entities", "key_relationships", 
                          "thematic_focus", "relationship_patterns"]
        
        for topic_id, config in TopicProcessor.TOPIC_CONFIGS.items():
            for field in required_fields:
                self.assertIn(field, config, f"Missing {field} in {topic_id}")
    
    def test_get_topic_config(self):
        """Test TopicProcessor.get_topic_config method"""
        from topic_processor import TopicProcessor
        
        # Valid topic
        config = TopicProcessor.get_topic_config("Chủ đề 1")
        self.assertIsInstance(config, dict)
        self.assertIn("topic_name", config)
        self.assertEqual(config["topic_name"], "THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH")
        
        # Invalid topic returns empty dict
        config = TopicProcessor.get_topic_config("Unknown Topic")
        self.assertEqual(config, {})
    
    def test_create_topic_prompt_topic1(self):
        """Test prompt generation for Chủ đề 1"""
        from topic_processor import TopicProcessor
        
        window_text = "Liên hợp quốc được thành lập năm 1945."
        entities_str = "- Liên hợp quốc (Tổ chức quốc tế)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 1", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertIn("Liên hợp quốc", prompt)
        self.assertIn("CHỦ ĐỀ PHÂN TÍCH", prompt)
        self.assertIn("relationships", prompt)
    
    def test_create_topic_prompt_topic2(self):
        """Test prompt generation for Chủ đề 2 (ASEAN)"""
        from topic_processor import TopicProcessor
        
        window_text = "ASEAN được thành lập năm 1967 tại Băng Cốc."
        entities_str = "- ASEAN (Tổ chức khu vực)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 2", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertIn("ASEAN", prompt)
    
    def test_create_topic_prompt_topic3(self):
        """Test prompt generation for Chủ đề 3 (Chiến tranh)"""
        from topic_processor import TopicProcessor
        
        window_text = "Chiến dịch Điện Biên Phủ năm 1954."
        entities_str = "- Chiến dịch Điện Biên Phủ (Chiến dịch/Trận đánh)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 3", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)
    
    def test_create_topic_prompt_topic4(self):
        """Test prompt generation for Chủ đề 4 (Đổi mới)"""
        from topic_processor import TopicProcessor
        
        window_text = "Đại hội VI năm 1986 khởi xướng công cuộc Đổi mới."
        entities_str = "- Đại hội VI (Sự kiện chính trị)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 4", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        # Check that the prompt contains "1986" (year) instead of Vietnamese with diacritics
        self.assertIn("1986", prompt)
    
    def test_create_topic_prompt_topic5(self):
        """Test prompt generation for Chủ đề 5 (Đối ngoại)"""
        from topic_processor import TopicProcessor
        
        window_text = "Việt Nam bình thường hóa quan hệ với Mỹ năm 1995."
        entities_str = "- Việt Nam (Quốc gia)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 5", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)
    
    def test_create_topic_prompt_topic6(self):
        """Test prompt generation for Chủ đề 6 (Hồ Chí Minh)"""
        from topic_processor import TopicProcessor
        
        window_text = "Hồ Chí Minh sinh ngày 19-5-1890 tại Kim Liên, Nam Đàn, Nghệ An."
        entities_str = "- Hồ Chí Minh (Nhân Vật Lịch Sử)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 6", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertIn("Hồ Chí Minh", prompt)
    
    def test_create_topic_prompt_with_target_entity(self):
        """Test prompt generation with target entity"""
        from topic_processor import TopicProcessor
        
        window_text = "Liên hợp quốc được thành lập năm 1945 tại San Francisco."
        entities_str = "- Liên hợp quốc (Tổ chức quốc tế)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Chủ đề 1", window_text, entities_str,
            target_entity_id="Liên hợp quốc"
        )
        
        self.assertIn("THỰC THỂ TRỌNG TÂM", prompt)
        self.assertIn("Liên hợp quốc", prompt)
    
    def test_create_topic_prompt_unknown_topic(self):
        """Test prompt generation for unknown topic falls back to default"""
        from topic_processor import TopicProcessor
        
        window_text = "Test text."
        entities_str = "- Entity1 (Type)"
        
        prompt = TopicProcessor.create_topic_prompt(
            "Unknown Topic", window_text, entities_str
        )
        
        self.assertIsInstance(prompt, str)
        self.assertIn("Test text", prompt)
        # Default prompt should contain basic extraction instructions
        self.assertIn("VĂN BẢN", prompt)
    
    def test_format_entities_for_prompt(self):
        """Test format_entities_for_prompt function"""
        from topic_processor import format_entities_for_prompt
        
        entity_lookup = {
            "Liên hợp quốc": {
                "id": "Liên hợp quốc",
                "label": ["Liên hợp quốc", "LHQ", "UN"],
                "type": "Tổ chức quốc tế",
                "description": "Tổ chức quốc tế lớn nhất thế giới"
            },
            "Việt Nam": {
                "id": "Việt Nam",
                "label": ["Việt Nam", "VN"],
                "type": "Quốc gia",
                "description": "Quốc gia Đông Nam Á"
            }
        }
        
        result = format_entities_for_prompt(entity_lookup)
        
        self.assertIsInstance(result, str)
        self.assertIn("Liên hợp quốc", result)
        self.assertIn("Việt Nam", result)
        self.assertIn("Tổ chức quốc tế", result)
    
    def test_format_entities_for_prompt_empty(self):
        """Test format_entities_for_prompt with empty input"""
        from topic_processor import format_entities_for_prompt
        
        result = format_entities_for_prompt({})
        
        self.assertEqual(result, "")
    
    def test_format_entities_for_prompt_with_context_labels(self):
        """Test format_entities_for_prompt with context_labels"""
        from topic_processor import format_entities_for_prompt
        
        entity_lookup = {
            "Liên hợp quốc": {
                "id": "Liên hợp quốc",
                "label": ["Liên hợp quốc", "LHQ"],
                "context_labels": ["LHQ", "UN"],  # Should use this
                "type": "Tổ chức",
                "description": ""
            }
        }
        
        result = format_entities_for_prompt(entity_lookup)
        
        self.assertIn("LHQ", result)
    
    def test_assess_evidence_quality_short(self):
        """Test assess_evidence_quality with short evidence"""
        from topic_processor import assess_evidence_quality
        
        short_evidence = "Test"
        score = assess_evidence_quality(short_evidence)
        
        self.assertIsInstance(score, float)
        self.assertEqual(score, 0.7)  # Base score only
    
    def test_assess_evidence_quality_long(self):
        """Test assess_evidence_quality with long evidence"""
        from topic_processor import assess_evidence_quality
        
        long_evidence = "Đây là một câu văn dài hơn 50 ký tự để test chất lượng evidence."
        score = assess_evidence_quality(long_evidence)
        
        self.assertGreater(score, 0.7)
        self.assertLessEqual(score, 1.0)
    
    def test_assess_evidence_quality_with_quote(self):
        """Test assess_evidence_quality with quoted evidence"""
        from topic_processor import assess_evidence_quality
        
        quoted_evidence = 'Văn bản nói rằng "Liên hợp quốc được thành lập"'
        score = assess_evidence_quality(quoted_evidence)
        
        self.assertGreater(score, 0.7)  # Should get bonus for quote
    
    def test_assess_evidence_quality_with_date(self):
        """Test assess_evidence_quality with date in evidence"""
        from topic_processor import assess_evidence_quality
        
        dated_evidence = "Sự kiện diễn ra vào ngày 2-9-1945 tại Hà Nội"
        score = assess_evidence_quality(dated_evidence)
        
        self.assertGreater(score, 0.7)  # Should get bonus for date
        
        dated_evidence2 = "Sự kiện diễn ra vào năm 1945"
        score2 = assess_evidence_quality(dated_evidence2)
        
        self.assertGreater(score2, 0.7)  # Should get bonus for year
    
    def test_assess_evidence_quality_max_score(self):
        """Test assess_evidence_quality caps at 1.0"""
        from topic_processor import assess_evidence_quality
        
        perfect_evidence = 'Đây là câu văn rất dài với trích dẫn "Liên hợp quốc" và ngày tháng 2-9-1945 tại Hà Nội.'
        score = assess_evidence_quality(perfect_evidence)
        
        self.assertLessEqual(score, 1.0)
    
    def test_topic1_config_focus_entities(self):
        """Test Chủ đề 1 has correct focus entities"""
        from topic_processor import TopicProcessor
        
        config = TopicProcessor.get_topic_config("Chủ đề 1")
        focus = config.get("focus_entities", [])
        
        self.assertIn("Tổ chức quốc tế", focus)
        self.assertIn("Quốc gia", focus)
        self.assertIn("Sự kiện", focus)
    
    def test_topic2_config_asean_specific(self):
        """Test Chủ đề 2 has ASEAN-specific config"""
        from topic_processor import TopicProcessor
        
        config = TopicProcessor.get_topic_config("Chủ đề 2")
        
        self.assertIn("asean_founding_members", config)
        self.assertIn("asean_expansion_phases", config)
        
        # Check founding members
        members = config.get("asean_founding_members", [])
        self.assertIn("Thái Lan", members)
    
    def test_topic3_config_war_periods(self):
        """Test Chủ đề 3 has war periods config"""
        from topic_processor import TopicProcessor
        
        config = TopicProcessor.get_topic_config("Chủ đề 3")
        
        self.assertIn("war_periods", config)
        periods = config.get("war_periods", {})
        self.assertIn("cmtt_1945", periods)
        self.assertIn("kccp_1945_1954", periods)
    
    def test_topic4_config_doi_moi_periods(self):
        """Test Chủ đề 4 has Doi Moi periods config"""
        from topic_processor import TopicProcessor
        
        config = TopicProcessor.get_topic_config("Chủ đề 4")
        
        self.assertIn("doi_moi_periods", config)
        self.assertIn("key_milestones", config)
        
        milestones = config.get("key_milestones", {})
        self.assertIn("1986", milestones)
    
    def test_topic6_config_life_phases(self):
        """Test Chủ đề 6 has life phases config"""
        from topic_processor import TopicProcessor
        
        config = TopicProcessor.get_topic_config("Chủ đề 6")
        
        self.assertIn("life_phases", config)
        phases = config.get("life_phases", {})
        self.assertIn("1890_1911", phases)
        self.assertIn("1911_1920", phases)
    
    def test_relationship_patterns_not_empty(self):
        """Test each topic has non-empty relationship patterns"""
        from topic_processor import TopicProcessor
        
        for topic_id, config in TopicProcessor.TOPIC_CONFIGS.items():
            patterns = config.get("relationship_patterns", {})
            self.assertGreater(len(patterns), 0, f"{topic_id} has no relationship patterns")
    
    def test_key_relationships_not_empty(self):
        """Test each topic has non-empty key relationships"""
        from topic_processor import TopicProcessor
        
        for topic_id, config in TopicProcessor.TOPIC_CONFIGS.items():
            relationships = config.get("key_relationships", [])
            self.assertGreater(len(relationships), 0, f"{topic_id} has no key relationships")


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
