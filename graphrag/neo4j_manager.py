"""
GraphRAG Pipeline - Neo4j Operations with Vector Search and Full-Text Index
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from neo4j import GraphDatabase

from .core import (
    GraphRAGConfig, chunk_text, VietnameseNormalizer, 
    retry_with_backoff, logger, TTLCache
)

# ================================================================================
# Neo4j Manager with Vector and Full-Text Support
# ================================================================================

class Neo4jManager:
    """Neo4j operations with vector search and full-text indexing."""
    
    def __init__(self, config: GraphRAGConfig):
        self.config = config
        self.driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password)
        )
        self.driver.verify_connectivity()
        logger.info("✓ Neo4j connected")
        
        self.cache = TTLCache(maxsize=1000, ttl=config.cache_ttl)
        self.vector_index_exists = self._check_vector_index()
        self.fulltext_index_exists = self._check_fulltext_index()
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    # ============================================================================
    # Index Management
    # ============================================================================
    
    def _check_vector_index(self) -> bool:
        """Check if vector index exists."""
        try:
            with self.driver.session() as session:
                result = session.run("SHOW INDEXES WHERE type = 'VECTOR'")
                return len(list(result)) > 0
        except:
            return False
    
    def _check_fulltext_index(self) -> bool:
        """Check if fulltext index exists."""
        try:
            with self.driver.session() as session:
                result = session.run("SHOW INDEXES WHERE type = 'FULLTEXT'")
                return len(list(result)) > 0
        except:
            return False
    
    def create_indexes(self):
        """Create all required indexes."""
        with self.driver.session() as session:
            # Basic indexes
            try:
                session.run("CREATE INDEX entity_id_idx IF NOT EXISTS FOR (e:Entity) ON (e.id)")
                logger.info("✓ Created entity ID index")
            except Exception as e:
                logger.warning(f"Entity ID index: {e}")
            
            try:
                session.run("CREATE INDEX passage_chunk_idx IF NOT EXISTS FOR (p:Passage) ON (p.chunk_id)")
                logger.info("✓ Created passage chunk_id index")
            except Exception as e:
                logger.warning(f"Passage index: {e}")
            
            # Full-text index
            try:
                session.run("""
                    CALL db.index.fulltext.createNodeIndex(
                        'entityFullText',
                        ['Entity'],
                        ['name', 'description']
                    )
                """)
                logger.info("✓ Created fulltext index on Entity")
                self.fulltext_index_exists = True
            except Exception as e:
                logger.warning(f"Fulltext index: {e}")
            
            # Vector index (if supported)
            try:
                session.run("""
                    CALL db.index.vector.createNodeIndex(
                        'passageEmbeddingIndex',
                        'Passage',
                        'embedding',
                        1024,
                        'cosine'
                    )
                """)
                logger.info("✓ Created vector index on Passage")
                self.vector_index_exists = True
            except Exception as e:
                logger.warning(f"Vector index not supported: {e}")
    
    # ============================================================================
    # Passage/Chunk Management
    # ============================================================================
    
    def store_passages(self, chunks: List[Dict], batch_size: int = 200):
        """Store passage chunks in Neo4j."""
        with self.driver.session() as session:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                session.run("""
                    UNWIND $chunks AS chunk
                    MERGE (p:Passage {chunk_id: chunk.chunk_id})
                    SET p.text = chunk.text,
                        p.parent_id = chunk.parent_entity_id,
                        p.offset = chunk.offset
                    WITH p, chunk
                    MATCH (e:Entity {id: chunk.parent_entity_id})
                    MERGE (e)-[:HAS_PASSAGE]->(p)
                """, chunks=batch)
                
                logger.info(f"Stored passages {i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}")
    
    def store_passage_embeddings(self, chunk_id: str, embedding: List[float]):
        """Store embedding for a passage."""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Passage {chunk_id: $chunk_id})
                SET p.embedding = $embedding
            """, chunk_id=chunk_id, embedding=embedding)
    
    def store_entity_embedding(self, entity_id: str, embedding: List[float]):
        """Store embedding for an entity."""
        with self.driver.session() as session:
            session.run("""
                MATCH (e:Entity {id: $entity_id})
                SET e.embedding_label = $embedding
            """, entity_id=entity_id, embedding=embedding)
    
    # ============================================================================
    # Vector Search
    # ============================================================================
    
    @retry_with_backoff(max_retries=3)
    def vector_search(self, query_vector: List[float], k: int = 10) -> List[Dict]:
        """
        Vector search for similar entities.
        
        Returns list of {entity_id, description, original_text, score, provenance}
        """
        results = []
        
        with self.driver.session() as session:
            if self.vector_index_exists:
                # Use native vector search on Entity nodes
                result = session.run("""
                    CALL db.index.vector.queryNodes(
                        'passageEmbeddingIndex',
                        $k,
                        $vector
                    ) YIELD node, score
                    RETURN node.id AS entity_id,
                           node.description AS description,
                           node.original_text AS original_text,
                           score
                """, k=k, vector=query_vector)
            else:
                # Fallback: compute similarity in application
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE e.embedding_label IS NOT NULL
                    RETURN e.id AS entity_id,
                           e.description AS description,
                           e.original_text AS original_text,
                           e.embedding_label AS embedding
                    LIMIT 100
                """)
                
                # Compute cosine similarity
                import numpy as np
                query_arr = np.array(query_vector)
                
                candidates = []
                for record in result:
                    emb = record["embedding"]
                    if emb:
                        emb_arr = np.array(emb)
                        score = float(np.dot(query_arr, emb_arr) / 
                                     (np.linalg.norm(query_arr) * np.linalg.norm(emb_arr) + 1e-9))
                        candidates.append({
                            "entity_id": record["entity_id"],
                            "description": record["description"],
                            "original_text": record["original_text"],
                            "score": score,
                            "provenance": "vector_search"
                        })
                
                candidates.sort(key=lambda x: x["score"], reverse=True)
                return candidates[:k]
            
            for record in result:
                results.append({
                    "entity_id": record["entity_id"],
                    "description": record["description"],
                    "original_text": record["original_text"],
                    "score": record["score"],
                    "provenance": "vector_search"
                })
        
        return results
    
    # ============================================================================
    # Full-Text Search
    # ============================================================================
    
    @retry_with_backoff(max_retries=3)
    def fulltext_search(self, query: str, k: int = 10) -> List[Dict]:
        """Full-text search on entities.
        
        Note: In this schema, entities use 'id' as identifier (not 'name').
        Labels are stored in Neo4j node labels, not as a property.
        """
        results = []
        
        with self.driver.session() as session:
            if self.fulltext_index_exists:
                result = session.run("""
                    CALL db.index.fulltext.queryNodes('entityFullText', $search_text)
                    YIELD node, score
                    RETURN node.id AS entity_id,
                           node.description AS description,
                           labels(node) AS nodeLabels,
                           score
                    LIMIT $k
                """, search_text=query, k=k)
            else:
                # Fallback: CONTAINS search on id and description
                result = session.run("""
                    MATCH (e)
                    WHERE e.id IS NOT NULL AND (
                        toLower(e.id) CONTAINS toLower($search_text)
                        OR toLower(e.description) CONTAINS toLower($search_text)
                        OR ANY(label IN labels(e) WHERE toLower(label) CONTAINS toLower($search_text))
                    )
                    RETURN e.id AS entity_id,
                           e.description AS description,
                           labels(e) AS nodeLabels,
                           1.0 AS score
                    LIMIT $k
                """, search_text=query, k=k)
            
            for record in result:
                entity_id = record["entity_id"]
                results.append({
                    "entity_id": entity_id,
                    "name": entity_id,  # Use id as name for backward compatibility
                    "labels": record.get("nodeLabels", []),
                    "description": record["description"],
                    "score": record["score"],
                    "provenance": "fulltext_search"
                })
        
        return results
    
    # ============================================================================
    # Entity Search and Graph Traversal
    # ============================================================================
    
    def search_entity(self, name: str) -> List[Dict]:
        """Search for entity by name or alias."""
        cache_key = f"entity:{name}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        aliases = VietnameseNormalizer.get_aliases(name)
        results = []
        
        with self.driver.session() as session:
            for alias in aliases[:5]:
                # Search by id, in labels array, and in description
                result = session.run("""
                    MATCH (e)
                    WHERE e.id = $search_name 
                       OR toLower(e.id) CONTAINS toLower($search_name)
                       OR toLower(e.description) CONTAINS toLower($search_name)
                       OR ANY(label IN labels(e) WHERE toLower(label) CONTAINS toLower($search_name))
                    RETURN e, elementId(e) AS elementId, labels(e) AS nodeLabels
                    LIMIT 3
                """, search_name=alias)
                
                for record in result:
                    node = dict(record["e"])
                    node["elementId"] = record["elementId"]
                    node["labels"] = record.get("nodeLabels", [])
                    if node not in results:
                        results.append(node)
        
        self.cache.set(cache_key, results)
        return results
    
    def get_neighbors(self, element_id: str, depth: int = 1, limit: int = 20) -> List[Dict]:
        """Get neighbors of a node up to specified depth.
        
        Note: In this schema, entities don't have a 'name' field - they use 'id' as identifier
        and 'labels' (Neo4j node labels) may contain aliases.
        """
        with self.driver.session() as session:
            if depth == 1:
                result = session.run("""
                    MATCH (n)-[r]-(neighbor)
                    WHERE elementId(n) = $element_id
                    RETURN neighbor.id AS entity_id,
                           neighbor.description AS description,
                           type(r) AS relationship,
                           elementId(neighbor) AS elementId,
                           labels(neighbor) AS nodeLabels,
                           r.metadata AS rel_metadata
                    LIMIT $limit
                """, element_id=element_id, limit=limit)
            else:
                result = session.run("""
                    MATCH path = (n)-[*1..2]-(neighbor)
                    WHERE elementId(n) = $element_id
                    RETURN DISTINCT neighbor.id AS entity_id,
                           neighbor.description AS description,
                           length(path) AS distance,
                           elementId(neighbor) AS elementId,
                           labels(neighbor) AS nodeLabels
                    LIMIT $limit
                """, element_id=element_id, limit=limit)
            
            neighbors = []
            for record in result:
                entity_id = record["entity_id"]
                node_labels = record.get("nodeLabels", [])
                neighbors.append({
                    "entity_id": entity_id,
                    "name": entity_id,  # Use id as name (for backward compatibility)
                    "labels": node_labels,
                    "description": record["description"],
                    "elementId": record["elementId"],
                    "distance": record.get("distance", 1),
                    "relationship": record.get("relationship"),
                    "rel_metadata": record.get("rel_metadata"),
                    "provenance": "graph_traversal"
                })
            
            return neighbors
    
    def get_entity_passages(self, entity_id: str) -> List[Dict]:
        """Get original_text content for an entity (no separate Passage nodes)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {id: $entity_id})
                RETURN e.id AS entity_id,
                       e.description AS description,
                       e.original_text AS original_text
            """, entity_id=entity_id)
            
            passages = []
            for record in result:
                original_text = record["original_text"]
                # original_text is a JSON string containing exact_text
                if original_text:
                    try:
                        if isinstance(original_text, str):
                            import json
                            ot_list = json.loads(original_text)
                        else:
                            ot_list = original_text
                        
                        for i, ot in enumerate(ot_list if isinstance(ot_list, list) else [ot_list]):
                            if isinstance(ot, dict):
                                passages.append({
                                    "chunk_id": f"{entity_id}_{i}",
                                    "text": ot.get("exact_text", ""),
                                    "offset": i
                                })
                            elif isinstance(ot, str):
                                passages.append({
                                    "chunk_id": f"{entity_id}_{i}",
                                    "text": ot,
                                    "offset": i
                                })
                    except:
                        passages.append({
                            "chunk_id": f"{entity_id}_0",
                            "text": str(original_text),
                            "offset": 0
                        })
            return passages
    
    # ============================================================================
    # Graph Algorithms (GDS)
    # ============================================================================
    
    def run_community_detection(self):
        """Run Leiden/Louvain community detection using GDS."""
        with self.driver.session() as session:
            try:
                # Create graph projection
                session.run("""
                    CALL gds.graph.project(
                        'entityGraph',
                        'Entity',
                        {
                            RELATED_TO: {orientation: 'UNDIRECTED'}
                        }
                    )
                """)
                logger.info("✓ Created GDS graph projection")
                
                # Run Leiden algorithm
                session.run("""
                    CALL gds.leiden.write('entityGraph', {
                        writeProperty: 'gds_cluster'
                    })
                """)
                logger.info("✓ Ran Leiden community detection")
                
                # Clean up
                session.run("CALL gds.graph.drop('entityGraph')")
                
            except Exception as e:
                logger.warning(f"GDS not available or error: {e}")
    
    def get_cluster_members(self, cluster_id: int) -> List[Dict]:
        """Get all entities in a cluster."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e {gds_cluster: $cluster_id})
                WHERE e.id IS NOT NULL
                RETURN e.id AS entity_id, labels(e) AS nodeLabels
            """, cluster_id=cluster_id)
            
            members = []
            for record in result:
                entity_id = record["entity_id"]
                members.append({
                    "entity_id": entity_id,
                    "name": entity_id,  # Use id as name
                    "labels": record.get("nodeLabels", [])
                })
            return members
    
    # ============================================================================
    # Helper Methods for Original Text Parsing
    # ============================================================================
    
    @staticmethod
    def parse_original_text(original_text: str) -> List[Dict]:
        """Parse the original_text JSON string and extract exact_text content.
        
        The original_text field contains a JSON array of objects with structure:
        [{"topic": "...", "lesson": "...", "labels": [...], "sentence_range": [...],
          "text_count": int, "exact_text": "..."}]
        
        Returns:
            List of dicts with {topic, lesson, labels, sentence_range, text_count, exact_text}
        """
        if not original_text:
            return []
        
        try:
            if isinstance(original_text, str):
                parsed = json.loads(original_text)
            else:
                parsed = original_text
            
            if not isinstance(parsed, list):
                parsed = [parsed]
            
            return parsed
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_entity_full_context(self, entity_id: str) -> Dict:
        """Get comprehensive context for an entity including all text and metadata.
        
        Returns:
            Dict with {entity_id, description, labels, original_texts, metadata, neighbors}
        """
        with self.driver.session() as session:
            # Get entity node
            result = session.run("""
                MATCH (e {id: $entity_id})
                RETURN e, elementId(e) AS elementId, labels(e) AS nodeLabels
            """, entity_id=entity_id)
            
            record = result.single()
            if not record:
                return None
            
            node = dict(record["e"])
            element_id = record["elementId"]
            node_labels = record.get("nodeLabels", [])
            
            # Parse original_text
            original_texts = self.parse_original_text(node.get("original_text", ""))
            
            # Parse metadata
            metadata = {}
            if node.get("metadata"):
                try:
                    metadata = json.loads(node["metadata"]) if isinstance(node["metadata"], str) else node["metadata"]
                except:
                    metadata = {}
            
            # Get neighbors
            neighbors = self.get_neighbors(element_id, depth=1, limit=10)
            
            return {
                "entity_id": entity_id,
                "description": node.get("description", ""),
                "labels": node_labels,
                "original_texts": original_texts,
                "metadata": metadata,
                "neighbors": neighbors,
                "raw_properties": {k: v for k, v in node.items() 
                                  if k not in ["id", "description", "original_text", "metadata"]}
            }
    
    def get_entity_relationships(self, entity_id: str, limit: int = 20) -> List[Dict]:
        """Get detailed relationships for an entity with predicate types and object info.
        
        This is crucial for understanding entity connections and reasoning.
        
        Returns:
            List of relationship dicts with outgoing and incoming relations
        """
        with self.driver.session() as session:
            # Get outgoing relationships
            result = session.run("""
                MATCH (e {id: $entity_id})-[r]->(target)
                RETURN type(r) AS predicate,
                       target.id AS target_id,
                       target.description AS target_description,
                       r.metadata AS rel_metadata,
                       labels(target) AS target_labels,
                       'outgoing' AS direction
                LIMIT $limit
            """, entity_id=entity_id, limit=limit // 2)
            
            relationships = []
            for record in result:
                rel_text = f"{entity_id} --[{record['predicate']}]--> {record['target_id']}"
                if record['target_description']:
                    rel_text += f": {record['target_description'][:100]}"
                
                relationships.append({
                    "predicate": record["predicate"],
                    "target_id": record["target_id"],
                    "target_description": record["target_description"],
                    "target_labels": record["target_labels"],
                    "direction": "outgoing",
                    "relationship_text": rel_text,
                    "metadata": record.get("rel_metadata")
                })
            
            # Get incoming relationships
            result = session.run("""
                MATCH (source)-[r]->(e {id: $entity_id})
                RETURN type(r) AS predicate,
                       source.id AS source_id,
                       source.description AS source_description,
                       r.metadata AS rel_metadata,
                       labels(source) AS source_labels,
                       'incoming' AS direction
                LIMIT $limit
            """, entity_id=entity_id, limit=limit // 2)
            
            for record in result:
                rel_text = f"{record['source_id']} --[{record['predicate']}]--> {entity_id}"
                if record['source_description']:
                    rel_text = f"{record['source_id']}: {record['source_description'][:100]} --> {entity_id}"
                
                relationships.append({
                    "predicate": record["predicate"],
                    "source_id": record["source_id"],
                    "source_description": record["source_description"],
                    "source_labels": record["source_labels"],
                    "direction": "incoming",
                    "relationship_text": rel_text,
                    "metadata": record.get("rel_metadata")
                })
            
            return relationships
    
    def get_entity_context_with_relationships(self, entity_id: str) -> Dict:
        """Get entity context with both passages AND relationship information.
        
        Combines textual content with graph structure for comprehensive understanding.
        """
        # Get base context
        full_context = self.get_entity_full_context(entity_id)
        if not full_context:
            return None
        
        # Add detailed relationships
        relationships = self.get_entity_relationships(entity_id, limit=20)
        full_context["relationships"] = relationships
        
        # Build relationship summary text
        rel_texts = [r.get("relationship_text", "") for r in relationships if r.get("relationship_text")]
        full_context["relationship_summary"] = "\n".join(rel_texts[:10])
        
        return full_context
