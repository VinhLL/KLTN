# kg_builder.py
import time
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict
from models import Entity, Triplet, KnowledgeGraph
from entity_processor import identify_unconnected_entities, create_entity_lookup, filter_entities_by_topic_lesson
from text_processor import read_source_files, find_context_windows_for_entity
from relationship_processor import extract_relationships_from_window, post_process_relationships
from utils import extract_topic_and_lesson, create_overlapping_windows, split_into_sentences
from topic_processor import process_topic_1_file, process_asean_file, process_ho_chi_minh_file, process_vietnam_war_file, process_doi_moi_file, process_diplomacy_file
import json

class KnowledgeGraphBuilder:
    def __init__(self):
        self.api_request_count = 0
        self.kg = {'entities': [], 'triplets': []}
        
    def build_from_existing(self, entities: List[Dict], source_files: Dict[str, str]) -> KnowledgeGraph:
        """Build knowledge graph với xử lý theo chủ đề."""
        print("Bắt đầu xây dựng knowledge graph với xử lý theo chủ đề...")
        
        entity_lookup = create_entity_lookup(entities)
        print(f"Đã tạo lookup cho {len(entity_lookup)} thực thể")
        
        self.kg = {
            'entities': entities,
            'triplets': []
        }
        
        files_by_topic = defaultdict(list)
        for file_path in source_files.keys():
            topic, _ = extract_topic_and_lesson(file_path)
            files_by_topic[topic].append(file_path)
        
        print(f"\nPhát hiện {len(files_by_topic)} chủ đề:")
        for topic, files in files_by_topic.items():
            print(f"  {topic}: {len(files)} file")
        
        for topic, file_paths in files_by_topic.items():
            print(f"\n{'='*60}")
            print(f"XỬ LÝ CHỦ ĐỀ: {topic}")
            print(f"{'='*60}")
            
            if topic == "Chủ đề 1":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_topic_1_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ: {len(self.kg['triplets'])}")
            
            elif topic == "Chủ đề 2":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_asean_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ ASEAN: {len(self.kg['triplets'])}")
            
            elif topic == "Chủ đề 3":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_vietnam_war_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ chiến tranh: {len(self.kg['triplets'])}")
            
            elif topic == "Chủ đề 4":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_doi_moi_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ Đổi mới: {len(self.kg['triplets'])}")
            
            elif topic == "Chủ đề 5":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_diplomacy_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ Đối ngoại: {len(self.kg['triplets'])}")
            
            elif topic == "Chủ đề 6":
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = process_ho_chi_minh_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ Hồ Chí Minh: {len(self.kg['triplets'])}")
            
            else:
                for file_path in file_paths:
                    if source_files.get(file_path):
                        self.kg = self.process_general_file(file_path, entity_lookup, self.kg)
                        print(f"Tổng quan hệ: {len(self.kg['triplets'])}")
        
        self.supplement_unconnected_entities(entity_lookup, source_files)
        self.process_thematic_groups(entity_lookup, source_files)
        
        return self._create_knowledge_graph()
    
    def process_general_file(self, file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
        """Process a general file without specific topic processing."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return existing_kg
        
        topic, lesson = extract_topic_and_lesson(file_path)
        file_info = {
            'file_path': file_path,
            'topic': topic,
            'lesson': lesson
        }
        
        all_entities = existing_kg.get('entities', [])
        filtered_entity_lookup = filter_entities_by_topic_lesson(all_entities, topic, lesson)

        # # If no entities found for this topic/lesson, use all entities as fallback
        # if not filtered_entity_lookup and topic == "Unknown" or lesson == "Unknown":
        #     print(f"Warning: No entities found for {topic}/{lesson}. Using all entities as fallback.")
        #     # Create a basic lookup from all entities
        #     filtered_entity_lookup = {}
        #     for entity in all_entities[:100]:  # Limit to 100 entities to avoid too large prompts
        #         entity_copy = entity.copy()
        #         filtered_entity_lookup[entity['id']] = entity_copy
        #         for label in entity.get('label', []):
        #             if label and label not in filtered_entity_lookup:
        #                 filtered_entity_lookup[label] = entity_copy
        
        print(f"Found {len(filtered_entity_lookup)} unique entities/labels in {topic}/{lesson}")
        
        sentences = split_into_sentences(content)
        print(f"Total sentences: {len(sentences)}")
        
        windows = create_overlapping_windows(sentences, window_size=10, step=3)
        print(f"Created {len(windows)} overlapping windows")
        
        all_relationships = []
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows):
            print(f"Window {window_idx+1}/{len(windows)}: ", end="", flush=True)
            
            result = extract_relationships_from_window(
                start_idx,
                window_sentences,
                filtered_entity_lookup,
                file_info
            )
            
            if result:
                relationships = result.get('relationships', [])
                all_relationships.extend(relationships)
                print(f"{len(relationships)}R")
            else:
                print("Failed")
            
            time.sleep(2)
        
        final_relationships, diagnostics = post_process_relationships(all_relationships)
        
        triplets = []
        for rel in final_relationships:
            triplet = {
                'subject_id': rel['subject_id'],
                'predicate': rel['predicate'],
                'object_id': rel['object_id'],
                'properties': rel.get('properties', {}),
                'metadata': {
                    'extraction_method': 'gemini_window_analysis',
                    'file_info': file_info,
                    'evidence_count': len(rel.get('supporting_sentences', [])),
                    'topic_specific': True
                },
                'supporting_sentences': rel.get('supporting_sentences', []),
                'confidence': rel.get('confidence', 0.9),
                'occurrence_count': rel.get('occurrence_count', 1)
            }
            triplets.append(triplet)
        
        existing_triplets = existing_kg.get('triplets', [])
        existing_entities = existing_kg.get('entities', [])
        
        triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
        for triplet in triplets:
            key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
            if key not in triplet_keys:
                existing_triplets.append(triplet)
                triplet_keys.add(key)
        
        return {
            'entities': existing_entities,
            'triplets': existing_triplets,
            'diagnostics': diagnostics
        }
    
    def supplement_unconnected_entities(self, entity_lookup: Dict[str, Dict], source_files: Dict[str, str]):
        """Supplement relationships for entities without connections."""
        connected_entities, unconnected_entities = identify_unconnected_entities(self.kg)
        
        print(f"\n{'='*60}")
        print(f"BỔ SUNG QUAN HỆ CHO THỰC THỂ CHƯA KẾT NỐI")
        print(f"{'='*60}")
        print(f"Tổng số thực thể: {len(self.kg.get('entities', []))}")
        print(f"Thực thể đã có quan hệ: {len(connected_entities)}")
        print(f"Thực thể chưa có quan hệ: {len(unconnected_entities)}")
        
        if not unconnected_entities:
            print("Tất cả thực thể đều đã có quan hệ!")
            return
        
        entity_type_groups = defaultdict(list)
        for entity_id in unconnected_entities:
            entity = entity_lookup.get(entity_id)
            if entity:
                entity_type_groups[entity.get('type', 'Unknown')].append(entity_id)
        
        print(f"\nPhân nhóm theo loại:")
        for entity_type, entity_ids in entity_type_groups.items():
            print(f"  {entity_type}: {len(entity_ids)} thực thể")
        
        total_new_relationships = 0
        
        for entity_type, entity_ids in entity_type_groups.items():
            print(f"\nXử lý nhóm '{entity_type}' ({len(entity_ids)} thực thể):")
            
            for i, entity_id in enumerate(entity_ids, 1):
                print(f"  [{i}/{len(entity_ids)}] Tìm quan hệ cho: {entity_id}...", end="", flush=True)
                
                context_windows = find_context_windows_for_entity(entity_id, entity_lookup, source_files)
                
                if not context_windows:
                    print(" Không tìm thấy ngữ cảnh")
                    continue
                
                entity_relationships = []
                
                for window_idx, window in enumerate(context_windows[:3]):
                    try:
                        topic = window['file_info']['topic']
                        lesson = window['file_info']['lesson']
                        
                        all_entities = self.kg.get('entities', [])
                        filtered_entity_lookup = filter_entities_by_topic_lesson(all_entities, topic, lesson)
                        
                        if entity_id not in filtered_entity_lookup:
                            entity = entity_lookup.get(entity_id)
                            if entity:
                                entity_copy = entity.copy()
                                entity_copy['context_labels'] = entity.get('label', [])
                                filtered_entity_lookup[entity_id] = entity_copy
                        
                        result = extract_relationships_from_window(
                            window['start_idx'],
                            window['sentences'],
                            filtered_entity_lookup,
                            window['file_info'],
                            target_entity_id=entity_id
                        )
                        
                        if result:
                            relationships = result.get('relationships', [])
                            relevant_relationships = [
                                rel for rel in relationships 
                                if rel.get('subject_id') == entity_id or rel.get('object_id') == entity_id
                            ]
                            
                            if relevant_relationships:
                                print(f" Tìm thấy {len(relevant_relationships)} quan hệ")
                                entity_relationships.extend(relevant_relationships)
                                break
                                
                    except Exception as e:
                        print(f" Lỗi xử lý cửa sổ {window_idx+1}: {e}")
                        continue
                
                if not entity_relationships:
                    print(" Không tìm thấy quan hệ")
                
                if entity_relationships:
                    merged_new, _ = post_process_relationships(entity_relationships)
                    
                    existing_triplets = self.kg.get('triplets', [])
                    existing_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
                    
                    for rel in merged_new:
                        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
                        if key not in existing_keys:
                            triplet = {
                                'subject_id': rel['subject_id'],
                                'predicate': rel['predicate'],
                                'object_id': rel['object_id'],
                                'properties': rel.get('properties', {}),
                                'metadata': {
                                    'extraction_method': 'supplemental_context_analysis',
                                    'evidence_count': len(rel.get('supporting_sentences', [])),
                                    'targeted_entity': True,
                                    'entity_type': entity_type,
                                    'context_windows_used': len(context_windows[:3])
                                },
                                'supporting_sentences': rel.get('supporting_sentences', []),
                                'confidence': rel.get('confidence', 0.9),
                                'occurrence_count': rel.get('occurrence_count', 1)
                            }
                            existing_triplets.append(triplet)
                            existing_keys.add(key)
                            total_new_relationships += 1
                    
                    self.kg['triplets'] = existing_triplets
                    
                    for rel in merged_new:
                        connected_entities.add(rel['subject_id'])
                        connected_entities.add(rel['object_id'])
                
                time.sleep(1)
            
            print(f"  Đã xử lý xong nhóm '{entity_type}'")
        
        connected_entities, remaining_unconnected = identify_unconnected_entities(self.kg)
        
        print(f"\n{'='*60}")
        print(f"KẾT QUẢ BỔ SUNG")
        print(f"{'='*60}")
        print(f"Đã thêm: {total_new_relationships} quan hệ mới")
        print(f"Thực thể có quan hệ sau bổ sung: {len(connected_entities)}")
        print(f"Thực thể vẫn chưa có quan hệ: {len(remaining_unconnected)}")
        
        if remaining_unconnected:
            unconnected_details = []
            for entity_id in remaining_unconnected:
                entity = entity_lookup.get(entity_id)
                if entity:
                    unconnected_details.append({
                        'id': entity_id,
                        'type': entity.get('type', 'Unknown'),
                        'label': entity.get('label', []),
                        'occurrence_count': len(entity.get('original_text', [])),
                        'context_windows_found': len(find_context_windows_for_entity(entity_id, entity_lookup, source_files))
                    })
            
            with open("still_unconnected_entities.json", 'w', encoding='utf-8') as f:
                json.dump(unconnected_details, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu thông tin {len(unconnected_details)} thực thể chưa kết nối vào: still_unconnected_entities.json")
    
    def process_thematic_groups(self, entity_lookup: Dict[str, Dict], source_files: Dict[str, str]):
        """Process thematic grouping for remaining unconnected entities."""
        connected_entities, unconnected_entities = identify_unconnected_entities(self.kg)
        
        if not unconnected_entities:
            return
        
        print(f"\n{'='*60}")
        print("KẾT NỐI THEO NHÓM CHỦ ĐỀ")
        print(f"{'='*60}")
        print(f"Còn {len(unconnected_entities)} thực thể chưa kết nối")
        
        entity_type_groups = defaultdict(list)
        for entity_id in unconnected_entities:
            entity = entity_lookup.get(entity_id)
            if entity:
                entity_type_groups[entity.get('type', 'Unknown')].append(entity_id)
        
        for entity_type, entity_ids in entity_type_groups.items():
            if len(entity_ids) < 2:
                continue
                
            print(f"\nNhóm '{entity_type}': {len(entity_ids)} thực thể")
            
            for file_path, content in source_files.items():
                if not content:
                    continue
                
                topic, lesson = extract_topic_and_lesson(file_path)
                sentences = split_into_sentences(content)
                entities_in_file = []
                
                for entity_id in entity_ids[:5]:
                    entity = entity_lookup.get(entity_id)
                    if entity and any(label in content for label in entity.get('label', [])):
                        entities_in_file.append(entity_id)
                
                if len(entities_in_file) >= 2:
                    print(f"  Tìm thấy {len(entities_in_file)} thực thể trong {file_path.split('/')[-1]}")
                    
                    file_info = {
                        'file_path': file_path,
                        'topic': topic,
                        'lesson': lesson
                    }
                    
                    all_entities = self.kg.get('entities', [])
                    filtered_entity_lookup = filter_entities_by_topic_lesson(all_entities, topic, lesson)
                    
                    windows = create_overlapping_windows(sentences, window_size=15, step=5)
                    
                    for window_idx, (start_idx, window_sentences) in enumerate(windows[:3]):
                        result = extract_relationships_from_window(
                            start_idx,
                            window_sentences,
                            filtered_entity_lookup,
                            file_info
                        )
                        
                        if result:
                            relationships = result.get('relationships', [])
                            relevant_relationships = [
                                rel for rel in relationships 
                                if rel.get('subject_id') in entity_ids or rel.get('object_id') in entity_ids
                            ]
                            
                            if relevant_relationships:
                                existing_triplets = self.kg.get('triplets', [])
                                existing_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
                                
                                for rel in relevant_relationships:
                                    key = (rel['subject_id'], rel['predicate'], rel['object_id'])
                                    if key not in existing_keys:
                                        triplet = {
                                            'subject_id': rel['subject_id'],
                                            'predicate': rel['predicate'],
                                            'object_id': rel['object_id'],
                                            'properties': rel.get('properties', {}),
                                            'metadata': {
                                                'extraction_method': 'thematic_group_analysis',
                                                'evidence_count': len(rel.get('supporting_sentences', [])),
                                                'group_type': entity_type,
                                                'topic_specific': True
                                            },
                                            'supporting_sentences': rel.get('supporting_sentences', []),
                                            'confidence': rel.get('confidence', 0.9),
                                            'occurrence_count': rel.get('occurrence_count', 1)
                                        }
                                        existing_triplets.append(triplet)
                                        existing_keys.add(key)
                                
                                self.kg['triplets'] = existing_triplets
                                print(f"    Đã thêm {len(relevant_relationships)} quan hệ mới")
                                break
    
    def _create_knowledge_graph(self) -> KnowledgeGraph:
        """Convert internal dictionary to KnowledgeGraph model."""
        connected_entities, unconnected_entities = identify_unconnected_entities(self.kg)
        print(f"\n{'='*60}")
        print("KẾT QUẢ CUỐI CÙNG")
        print(f"{'='*60}")
        print(f"Tổng số thực thể: {len(self.kg['entities'])}")
        print(f"Thực thể có quan hệ: {len(connected_entities)}")
        print(f"Thực thể chưa có quan hệ: {len(unconnected_entities)}")
        print(f"Tỷ lệ bao phủ: {(len(connected_entities)/len(self.kg['entities'])*100):.1f}%")
        print(f"Tổng số API requests: {self.api_request_count}")
        
        entity_objects = []
        for entity_dict in self.kg['entities']:
            try:
                entity_obj = Entity(**entity_dict)
                entity_objects.append(entity_obj)
            except Exception as e:
                print(f"Lỗi khi tạo entity {entity_dict.get('id', 'Unknown')}: {e}")
                continue
        
        triplet_objects = []
        for triplet_dict in self.kg['triplets']:
            try:
                triplet_obj = Triplet(**triplet_dict)
                triplet_objects.append(triplet_obj)
            except Exception as e:
                print(f"Lỗi khi tạo triplet: {e}")
                continue
        
        return KnowledgeGraph(
            entities=entity_objects,
            triplets=triplet_objects
        )