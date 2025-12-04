# output_manager.py
import json
from typing import List, Dict, Any
from models import KnowledgeGraph

def analyze_knowledge_graph(kg: KnowledgeGraph):
    """Analyze and print statistics about the knowledge graph."""
    print("\n" + "="*60)
    print("PHÂN TÍCH KNOWLEDGE GRAPH")
    print("="*60)
    
    print(f"Tổng số thực thể: {len(kg.entities)}")
    print(f"Tổng số quan hệ: {len(kg.triplets)}")
    
    entity_types = {}
    for entity in kg.entities:
        entity_type = entity.type
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    print(f"\nPhân bố loại thực thể:")
    for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {entity_type}: {count}")
    
    relationship_types = {}
    for triplet in kg.triplets:
        predicate = triplet.predicate
        relationship_types[predicate] = relationship_types.get(predicate, 0) + 1
    
    print(f"\nTop 20 loại quan hệ phổ biến:")
    for predicate, count in sorted(relationship_types.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {predicate}: {count}")
    
    entity_connections = {}
    for triplet in kg.triplets:
        entity_connections[triplet.subject_id] = entity_connections.get(triplet.subject_id, 0) + 1
        entity_connections[triplet.object_id] = entity_connections.get(triplet.object_id, 0) + 1
    
    print(f"\nTop 10 thực thể có nhiều kết nối nhất:")
    for entity_id, count in sorted(entity_connections.items(), key=lambda x: x[1], reverse=True)[:10]:
        entity = next((e for e in kg.entities if e.id == entity_id), None)
        entity_type = entity.type if entity else "Unknown"
        print(f"  {entity_id} ({entity_type}): {count} kết nối")
    
    connected_entities = set(entity_connections.keys())
    all_entities = set(entity.id for entity in kg.entities)
    unconnected_entities = all_entities - connected_entities
    
    if unconnected_entities:
        print(f"\nThực thể không có kết nối ({len(unconnected_entities)}):")
        for entity_id in list(unconnected_entities)[:20]:
            entity = next((e for e in kg.entities if e.id == entity_id), None)
            entity_type = entity.type if entity else "Unknown"
            print(f"  {entity_id} ({entity_type})")

def save_analysis_report(kg: KnowledgeGraph, output_path: str = "kg_analysis_report.json"):
    """Save detailed analysis report to JSON file."""
    report = {
        "summary": {
            "total_entities": len(kg.entities),
            "total_relationships": len(kg.triplets),
            "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "entity_statistics": {},
        "relationship_statistics": {},
        "top_connected_entities": [],
        "unconnected_entities": []
    }
    
    entity_types = {}
    for entity in kg.entities:
        entity_type = entity.type
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    report["entity_statistics"] = entity_types
    
    relationship_types = {}
    for triplet in kg.triplets:
        predicate = triplet.predicate
        relationship_types[predicate] = relationship_types.get(predicate, 0) + 1
    
    report["relationship_statistics"] = relationship_types
    
    entity_connections = {}
    for triplet in kg.triplets:
        entity_connections[triplet.subject_id] = entity_connections.get(triplet.subject_id, 0) + 1
        entity_connections[triplet.object_id] = entity_connections.get(triplet.object_id, 0) + 1
    
    top_connected = sorted(entity_connections.items(), key=lambda x: x[1], reverse=True)[:20]
    for entity_id, count in top_connected:
        entity = next((e for e in kg.entities if e.id == entity_id), None)
        report["top_connected_entities"].append({
            "id": entity_id,
            "connections": count,
            "type": entity.type if entity else "Unknown",
            "labels": entity.label if entity else []
        })
    
    connected_entities = set(entity_connections.keys())
    all_entities = set(entity.id for entity in kg.entities)
    unconnected_entities = all_entities - connected_entities
    
    for entity_id in list(unconnected_entities)[:50]:
        entity = next((e for e in kg.entities if e.id == entity_id), None)
        if entity:
            report["unconnected_entities"].append({
                "id": entity_id,
                "type": entity.type,
                "labels": entity.label,
                "description": entity.description[:100] if entity.description else ""
            })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nĐã lưu báo cáo phân tích vào: {output_path}")
    return report

def export_to_neo4j(kg: KnowledgeGraph, output_path: str = "kg_neo4j_import.csv"):
    """Export knowledge graph to Neo4j compatible format."""
    import csv
    
    nodes = []
    relationships = []
    
    for entity in kg.entities:
        nodes.append({
            "entity_id": entity.id,
            "labels": "|".join(entity.label),
            "type": entity.type,
            "description": entity.description,
            "confidence": entity.confidence
        })
    
    for triplet in kg.triplets:
        relationships.append({
            "subject_id": triplet.subject_id,
            "predicate": triplet.predicate,
            "object_id": triplet.object_id,
            "confidence": triplet.confidence,
            "occurrence_count": triplet.occurrence_count,
            "evidence_count": len(triplet.supporting_sentences)
        })
    
    with open(f"nodes_{output_path}", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["entity_id", "labels", "type", "description", "confidence"])
        writer.writeheader()
        writer.writerows(nodes)
    
    with open(f"relationships_{output_path}", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["subject_id", "predicate", "object_id", "confidence", "occurrence_count", "evidence_count"])
        writer.writeheader()
        writer.writerows(relationships)
    
    print(f"\nĐã xuất dữ liệu Neo4j:")
    print(f"  - nodes_{output_path}: {len(nodes)} nodes")
    print(f"  - relationships_{output_path}: {len(relationships)} relationships")
    
    return len(nodes), len(relationships)