"""
GraphRAG Setup Script - Initialize indexes, generate embeddings, store passages
Run this once before using the pipeline.
"""

import json
import time
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphrag import (
    GraphRAGConfig, Neo4jManager, EmbeddingGenerator,
    chunk_text, logger
)


def setup_indexes(neo4j: Neo4jManager):
    """Create all required indexes."""
    logger.info("Creating indexes...")
    neo4j.create_indexes()
    logger.info("✓ Indexes created")


def load_and_chunk_entities(config: GraphRAGConfig) -> list:
    """Load entities and create passage chunks."""
    logger.info(f"Loading entities from {config.entities_file}...")
    
    with open(config.entities_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    all_chunks = []
    
    for entity in entities:
        entity_id = entity.get('id', '')
        if not entity_id:
            continue
        
        # Combine description and original_text
        texts = []
        
        description = entity.get('description', '')
        if description:
            texts.append(description)
        
        original_texts = entity.get('original_text', [])
        if isinstance(original_texts, list):
            for ot in original_texts:
                if isinstance(ot, dict):
                    exact_text = ot.get('exact_text', '')
                    if exact_text:
                        texts.append(exact_text)
                elif isinstance(ot, str):
                    texts.append(ot)
        
        # Combine and chunk
        combined_text = '\n\n'.join(texts)
        if combined_text:
            chunks = chunk_text(
                combined_text,
                max_chars=config.chunk_size,
                overlap=config.chunk_overlap,
                parent_entity_id=entity_id
            )
            all_chunks.extend(chunks)
    
    logger.info(f"✓ Created {len(all_chunks)} passage chunks from {len(entities)} entities")
    return all_chunks


def store_passages(neo4j: Neo4jManager, chunks: list):
    """Store passage chunks in Neo4j."""
    logger.info("Storing passages in Neo4j...")
    neo4j.store_passages(chunks, batch_size=200)
    logger.info("✓ Passages stored")


def generate_and_store_embeddings(config: GraphRAGConfig, neo4j: Neo4jManager, 
                                   embedding_gen: EmbeddingGenerator, chunks: list):
    """Generate embeddings for passages and store them."""
    logger.info("Generating embeddings for passages...")
    
    total = len(chunks)
    batch_size = 16
    
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c['text'] for c in batch]
        
        embeddings = embedding_gen.generate_embeddings_batch(texts)
        
        for j, emb in enumerate(embeddings):
            if emb:
                chunk_id = batch[j]['chunk_id']
                neo4j.store_passage_embeddings(chunk_id, emb)
        
        if (i + batch_size) % 100 == 0 or i + batch_size >= total:
            logger.info(f"  Processed {min(i + batch_size, total)}/{total} passages")
    
    logger.info("✓ Passage embeddings stored")


def generate_entity_embeddings(config: GraphRAGConfig, neo4j: Neo4jManager,
                                embedding_gen: EmbeddingGenerator):
    """Generate embeddings for entity labels."""
    logger.info(f"Loading entities for embedding...")
    
    with open(config.entities_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    logger.info(f"Generating embeddings for {len(entities)} entities...")
    
    batch_size = 16
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]
        
        texts = []
        entity_ids = []
        for e in batch:
            entity_id = e.get('id', '')
            name = e.get('name', entity_id)
            description = e.get('description', '')
            
            if entity_id:
                text = f"{name}. {description}" if description else name
                texts.append(text)
                entity_ids.append(entity_id)
        
        if texts:
            embeddings = embedding_gen.generate_embeddings_batch(texts)
            
            for j, emb in enumerate(embeddings):
                if emb:
                    neo4j.store_entity_embedding(entity_ids[j], emb)
        
        if (i + batch_size) % 100 == 0 or i + batch_size >= len(entities):
            logger.info(f"  Processed {min(i + batch_size, len(entities))}/{len(entities)} entities")
    
    logger.info("✓ Entity embeddings stored")


def run_community_detection(neo4j: Neo4jManager):
    """Run GDS community detection if available."""
    logger.info("Running community detection...")
    neo4j.run_community_detection()


def main():
    """Run full setup."""
    logger.info("=" * 60)
    logger.info("GraphRAG Setup")
    logger.info("=" * 60)
    
    config = GraphRAGConfig()
    start_time = time.time()
    
    # Initialize Neo4j
    neo4j = Neo4jManager(config)
    
    try:
        # Step 1: Create indexes
        setup_indexes(neo4j)
        
        # Step 2: Load and chunk entities
        chunks = load_and_chunk_entities(config)
        
        # Step 3: Store passages
        store_passages(neo4j, chunks)
        
        # Step 4: Initialize embedding generator
        embedding_gen = EmbeddingGenerator(config)
        
        # Step 5: Generate and store passage embeddings
        generate_and_store_embeddings(config, neo4j, embedding_gen, chunks)
        
        # Step 6: Generate entity embeddings
        generate_entity_embeddings(config, neo4j, embedding_gen)
        
        # Step 7: Run community detection (optional)
        run_community_detection(neo4j)
        
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"✓ Setup complete in {elapsed:.1f} seconds")
        logger.info("=" * 60)
        
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
