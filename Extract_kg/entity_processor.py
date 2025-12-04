# entity_processor.py
import json
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict
from difflib import SequenceMatcher
from utils import normalize_text

def load_existing_entities(entity_file_path: str) -> List[Dict[str, Any]]:
    """Load existing entities from JSON file."""
    try:
        with open(entity_file_path, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        print(f"Đã tải {len(entities)} thực thể từ file")
        return entities
    except Exception as e:
        print(f"Lỗi khi tải thực thể: {e}")
        return []

def create_entity_lookup(entities: List[Dict]) -> Dict[str, Dict]:
    """Create lookup dictionary for entities."""
    lookup = {}
    for entity in entities:
        lookup[entity['id']] = entity
        for label in entity.get('label', []):
            clean_label = label.strip()
            if clean_label and clean_label not in lookup:
                lookup[clean_label] = entity
    return lookup

def filter_entities_by_topic_lesson(entities: List[Dict], topic: str, lesson: str) -> Dict[str, Dict]:
    """Filter entities that appear in the specific topic and lesson, and get their labels for that context."""
    filtered_entities = {}
    
    for entity in entities:
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context = occ.get('labels', entity.get('label', []))
                
                entity_copy = entity.copy()
                entity_copy['context_labels'] = labels_in_context
                
                filtered_entities[entity['id']] = entity_copy
                
                for label in labels_in_context:
                    if label not in filtered_entities:
                        filtered_entities[label] = entity_copy
                break
    
    return filtered_entities

def find_entity_occurrences_in_sentences(sentences: List[str], entity_labels: List[str]) -> List[int]:
    """Find sentence indices where entity appears."""
    occurrences = []
    entity_labels_lower = [label.lower() for label in entity_labels]
    
    for idx, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        for label in entity_labels_lower:
            if label in sentence_lower and len(label) > 2:
                occurrences.append(idx)
                break
    return occurrences

def identify_unconnected_entities(kg: Dict) -> Tuple[Set[str], Set[str]]:
    """Identify entities with and without relationships."""
    connected_entities = set()
    
    for triplet in kg.get('triplets', []):
        connected_entities.add(triplet['subject_id'])
        connected_entities.add(triplet['object_id'])
    
    all_entities = set(entity['id'] for entity in kg.get('entities', []))
    unconnected_entities = all_entities - connected_entities
    
    return connected_entities, unconnected_entities

def find_similar_entities(entity_id: str, entities: List[Dict], threshold: float = 0.7) -> List[Dict]:
    """Find entities similar to the given entity based on labels and description."""
    target_entity = next((e for e in entities if e['id'] == entity_id), None)
    if not target_entity:
        return []
    
    target_labels = set(normalize_text(label) for label in target_entity.get('label', []))
    target_desc = normalize_text(target_entity.get('description', ''))
    
    similar_entities = []
    for entity in entities:
        if entity['id'] == entity_id:
            continue
        
        entity_labels = set(normalize_text(label) for label in entity.get('label', []))
        entity_desc = normalize_text(entity.get('description', ''))
        
        # Calculate label similarity
        label_similarity = 0
        if target_labels and entity_labels:
            common = len(target_labels.intersection(entity_labels))
            total = len(target_labels.union(entity_labels))
            label_similarity = common / total if total > 0 else 0
        
        # Calculate description similarity
        desc_similarity = SequenceMatcher(None, target_desc, entity_desc).ratio()
        
        # Overall similarity
        overall_similarity = max(label_similarity, desc_similarity)
        
        if overall_similarity >= threshold:
            similar_entities.append({
                'entity': entity,
                'similarity': overall_similarity,
                'type': entity['type']
            })
    
    similar_entities.sort(key=lambda x: x['similarity'], reverse=True)
    return similar_entities

def group_entities_by_type(entities: List[Dict]) -> Dict[str, List[Dict]]:
    """Group entities by their type."""
    groups = defaultdict(list)
    for entity in entities:
        entity_type = entity.get('type', 'Unknown')
        groups[entity_type].append(entity)
    return dict(groups)