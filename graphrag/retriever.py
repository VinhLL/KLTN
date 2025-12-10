"""
GraphRAG Pipeline - Hybrid Retriever and Entity Linking
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .core import GraphRAGConfig, VietnameseNormalizer, logger, TTLCache
from .embeddings import EmbeddingGenerator, Reranker
from .neo4j_manager import Neo4jManager

# ================================================================================
# Entity Linker
# ================================================================================

class EntityLinker:
    """Link mentions to canonical entities using embeddings and surface matching."""
    
    def __init__(self, config: GraphRAGConfig, embedding_gen: EmbeddingGenerator, 
                 neo4j_mgr: Neo4jManager):
        self.config = config
        self.embedding_gen = embedding_gen
        self.neo4j = neo4j_mgr
        self.cache = TTLCache(maxsize=1000, ttl=config.cache_ttl)
        
        # Precomputed entity embeddings
        self.entity_embeddings = {}
    
    def compute_surface_match_score(self, mention: str, entity_name: str) -> float:
        """Compute surface-level matching score."""
        mention_lower = mention.lower().strip()
        entity_lower = entity_name.lower().strip()
        
        # Exact match
        if mention_lower == entity_lower:
            return 1.0
        
        # Alias match
        aliases = VietnameseNormalizer.get_aliases(entity_name)
        if mention_lower in [a.lower() for a in aliases]:
            return 0.95
        
        # Substring match
        if mention_lower in entity_lower or entity_lower in mention_lower:
            return 0.8
        
        # Word overlap
        mention_words = set(mention_lower.split())
        entity_words = set(entity_lower.split())
        overlap = len(mention_words & entity_words)
        total = len(mention_words | entity_words)
        
        if total > 0:
            return 0.5 * (overlap / total)
        
        return 0.0
    
    def link_entity(self, mention: str, top_n: int = 5) -> Dict:
        """
        Link a mention to canonical entity.
        
        Returns:
            {
                "canonical_entity_id": str or None,
                "score": float,
                "candidates": List[Dict],
                "low_confidence": bool
            }
        """
        cached = self.cache.get(mention)
        if cached:
            return cached
        
        # Search for candidate entities
        candidates = self.neo4j.search_entity(mention)
        
        if not candidates:
            result = {
                "canonical_entity_id": None,
                "score": 0.0,
                "candidates": [],
                "low_confidence": True
            }
            self.cache.set(mention, result)
            return result
        
        # Generate mention embedding
        mention_embedding = self.embedding_gen.generate_embedding(mention)
        
        # Score candidates
        scored_candidates = []
        for cand in candidates[:top_n]:
            entity_id = cand.get("id", "")
            entity_name = entity_id  # In this schema, id is the name
            
            # Get or compute entity embedding
            if entity_id not in self.entity_embeddings:
                entity_text = f"{entity_id}. {cand.get('description', '')}"
                self.entity_embeddings[entity_id] = self.embedding_gen.generate_embedding(entity_text)
            
            entity_embedding = self.entity_embeddings[entity_id]
            
            # Compute cosine similarity
            cosine_sim = EmbeddingGenerator.cosine_similarity(mention_embedding, entity_embedding)
            
            # Compute surface match
            surface_score = self.compute_surface_match_score(mention, entity_name)
            
            # Combined score
            alpha = 0.6  # embedding weight
            beta = 0.4   # surface match weight
            combined_score = alpha * cosine_sim + beta * surface_score
            
            scored_candidates.append({
                "entity_id": entity_id,
                "name": entity_name,
                "score": combined_score,
                "cosine_sim": cosine_sim,
                "surface_score": surface_score
            })
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        best = scored_candidates[0] if scored_candidates else None
        low_confidence = best is None or best["score"] < self.config.entity_linking_threshold
        
        result = {
            "canonical_entity_id": best["entity_id"] if best else None,
            "score": best["score"] if best else 0.0,
            "candidates": scored_candidates,
            "low_confidence": low_confidence
        }
        
        self.cache.set(mention, result)
        return result
    
    def link_entities(self, mentions: List[str]) -> List[Dict]:
        """Link multiple mentions to canonical entities."""
        return [self.link_entity(m) for m in mentions]


# ================================================================================
# Hybrid Retriever
# ================================================================================

class HybridRetriever:
    """
    Hybrid retriever combining:
    - Entity linking
    - Graph traversal
    - Vector search
    - Full-text search
    """
    
    def __init__(self, config: GraphRAGConfig, embedding_gen: EmbeddingGenerator,
                 neo4j_mgr: Neo4jManager, reranker: Reranker):
        self.config = config
        self.embedding_gen = embedding_gen
        self.neo4j = neo4j_mgr
        self.reranker = reranker
        self.entity_linker = EntityLinker(config, embedding_gen, neo4j_mgr)
        self.cache = TTLCache(maxsize=500, ttl=config.cache_ttl)
    
    def retrieve(self, mentions: List[str], question_text: str, 
                 top_k: int = None) -> List[Dict]:
        """
        Hybrid retrieval combining multiple signals.
        
        Args:
            mentions: Extracted entity mentions
            question_text: Original question text
            top_k: Number of results to return
        
        Returns:
            List of {text, score, provenance, entity_id, ...}
        """
        top_k = top_k or self.config.top_k_retrieval
        
        # Cache check
        cache_key = f"{':'.join(sorted(mentions))}:{question_text[:100]}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        all_candidates = []
        
        # 1. Entity linking
        entity_scores = {}
        for mention in mentions:
            link_result = self.entity_linker.link_entity(mention)
            if link_result["canonical_entity_id"]:
                entity_id = link_result["canonical_entity_id"]
                entity_scores[entity_id] = max(
                    entity_scores.get(entity_id, 0),
                    link_result["score"]
                )
        
        # 2. Graph traversal for linked entities
        graph_candidates = []
        for entity_id, entity_score in entity_scores.items():
            # Get entity node
            entities = self.neo4j.search_entity(entity_id)
            if entities:
                entity = entities[0]
                entity_el_id = entity.get('id', entity_id)
                
                # Try to get full context with original_text AND relationships
                full_context = self.neo4j.get_entity_context_with_relationships(entity_el_id)
                
                if full_context:
                    # Add entity description as candidate
                    desc = full_context.get('description', '')
                    if desc:
                        graph_candidates.append({
                            "text": f"{entity_el_id}: {desc}",
                            "entity_id": entity_el_id,
                            "chunk_id": f"{entity_el_id}_desc",
                            "entity_score": entity_score,
                            "graph_proximity": 0,
                            "provenance": "entity_direct"
                        })
                    
                    # Add passages from original_text (most important!)
                    original_texts = full_context.get('original_texts', [])
                    for i, ot in enumerate(original_texts[:5]):  # Get up to 5 passages
                        exact_text = ot.get('exact_text', '') if isinstance(ot, dict) else str(ot)
                        if exact_text and len(exact_text.strip()) > 20:
                            topic = ot.get('topic', '') if isinstance(ot, dict) else ''
                            lesson = ot.get('lesson', '') if isinstance(ot, dict) else ''
                            header = f"[{topic}/{lesson}]" if topic or lesson else ""
                            
                            graph_candidates.append({
                                "text": f"{header} {exact_text}".strip(),
                                "entity_id": entity_el_id,
                                "chunk_id": f"{entity_el_id}_passage_{i}",
                                "entity_score": entity_score,
                                "graph_proximity": 0,
                                "provenance": "entity_passage"
                            })
                    
                    # NEW: Add relationship context (crucial for reasoning!)
                    relationships = full_context.get('relationships', [])
                    for i, rel in enumerate(relationships[:8]):
                        rel_text = rel.get('relationship_text', '')
                        if rel_text:
                            # Build a more informative relationship text
                            predicate = rel.get('predicate', '')
                            if rel.get('direction') == 'outgoing':
                                target_desc = rel.get('target_description', '')
                                if target_desc:
                                    rel_text = f"{entity_el_id} [{predicate}] {rel.get('target_id')}: {target_desc}"
                            else:
                                source_desc = rel.get('source_description', '')
                                if source_desc:
                                    rel_text = f"{rel.get('source_id')}: {source_desc} [{predicate}] {entity_el_id}"
                            
                            graph_candidates.append({
                                "text": rel_text,
                                "entity_id": entity_el_id,
                                "chunk_id": f"{entity_el_id}_rel_{i}",
                                "entity_score": entity_score * 0.8,
                                "graph_proximity": 0.5,
                                "provenance": "relationship_context"
                            })
                    
                    # Add relationship summary as single candidate
                    rel_summary = full_context.get('relationship_summary', '')
                    if rel_summary and len(rel_summary) > 30:
                        graph_candidates.append({
                            "text": f"[Relationships of {entity_el_id}]\n{rel_summary}",
                            "entity_id": entity_el_id,
                            "chunk_id": f"{entity_el_id}_rel_summary",
                            "entity_score": entity_score * 0.75,
                            "graph_proximity": 0.5,
                            "provenance": "relationship_summary"
                        })
                else:
                    # Fallback: Add entity info as candidate
                    graph_candidates.append({
                        "text": f"{entity.get('id', '')}: {entity.get('description', '')}",
                        "entity_id": entity_id,
                        "chunk_id": f"{entity_id}_desc",
                        "entity_score": entity_score,
                        "graph_proximity": 0,
                        "provenance": "entity_direct"
                    })
                    
                    # Get entity passages via get_entity_passages
                    passages = self.neo4j.get_entity_passages(entity_id)
                    for p in passages[:3]:
                        if p.get("text") and len(p.get("text", "")) > 20:
                            graph_candidates.append({
                                "text": p["text"],
                                "entity_id": entity_id,
                                "chunk_id": p.get("chunk_id", f"{entity_id}_p"),
                                "entity_score": entity_score,
                                "graph_proximity": 0,
                                "provenance": "entity_passage"
                            })
                
                # Get neighbors (for additional context)
                element_id = entity.get("elementId")
                if element_id:
                    neighbors = self.neo4j.get_neighbors(element_id, depth=1, limit=8)
                    for n in neighbors:
                        neighbor_id = n.get("entity_id", "")
                        neighbor_desc = n.get("description", "")
                        rel_type = n.get("relationship", "")
                        
                        if neighbor_desc:
                            # Add neighbor description with relationship type
                            rel_text = f"[{rel_type}] " if rel_type else ""
                            graph_candidates.append({
                                "text": f"{rel_text}{neighbor_id}: {neighbor_desc}",
                                "entity_id": neighbor_id,
                                "chunk_id": f"{neighbor_id}_neighbor",
                                "entity_score": entity_score * 0.7,
                                "graph_proximity": n.get("distance", 1),
                                "provenance": "graph_neighbor"
                            })
                            
                            # Also try to get passages for important neighbors
                            neighbor_passages = self.neo4j.get_entity_passages(neighbor_id)
                            for p in neighbor_passages[:2]:
                                if p.get("text") and len(p.get("text", "")) > 20:
                                    graph_candidates.append({
                                        "text": p["text"],
                                        "entity_id": neighbor_id,
                                        "chunk_id": p.get("chunk_id", f"{neighbor_id}_p"),
                                        "entity_score": entity_score * 0.6,
                                        "graph_proximity": n.get("distance", 1),
                                        "provenance": "neighbor_passage"
                                    })
        all_candidates.extend(graph_candidates)
        
        # 3. Vector search
        question_embedding = self.embedding_gen.generate_embedding(question_text)
        vector_results = self.neo4j.vector_search(question_embedding, k=top_k)
        
        for idx, vr in enumerate(vector_results):
            entity_id = vr.get("entity_id", "")
            vr["vector_score"] = vr.pop("score", 0)
            vr["provenance"] = "vector_search"
            vr["chunk_id"] = f"{entity_id}_vector_{idx}"
            
            # Build text from description and original_text
            text_parts = []
            if vr.get("description"):
                text_parts.append(f"{entity_id}: {vr['description']}")
            
            if vr.get("original_text"):
                ot = vr["original_text"]
                try:
                    if isinstance(ot, str):
                        import json
                        ot_list = json.loads(ot)
                    else:
                        ot_list = ot
                    
                    for i, item in enumerate((ot_list if isinstance(ot_list, list) else [ot_list])[:3]):
                        if isinstance(item, dict) and item.get("exact_text"):
                            exact = item["exact_text"]
                            topic = item.get("topic", "")
                            lesson = item.get("lesson", "")
                            header = f"[{topic}/{lesson}]" if topic or lesson else ""
                            text_parts.append(f"{header} {exact}".strip())
                        elif isinstance(item, str):
                            text_parts.append(item[:800])
                except:
                    text_parts.append(str(ot)[:500])
            
            vr["text"] = "\n\n".join(text_parts) if text_parts else entity_id
        all_candidates.extend(vector_results)
        
        # 4. Full-text search - also get passages for results
        key_terms = self._extract_key_terms(question_text)
        for term in key_terms[:3]:
            ft_results = self.neo4j.fulltext_search(term, k=5)
            for idx, fr in enumerate(ft_results):
                entity_id = fr.get("entity_id", "")
                
                # Add entity description
                text = f"{entity_id}: {fr.get('description', '')}"
                all_candidates.append({
                    "text": text,
                    "entity_id": entity_id,
                    "chunk_id": f"{entity_id}_ft_{idx}",
                    "text_score": fr.get("score", 0),
                    "provenance": "fulltext_search"
                })
                
                # Also get passages for this entity (important for context)
                passages = self.neo4j.get_entity_passages(entity_id)
                for pi, p in enumerate(passages[:2]):
                    if p.get("text") and len(p.get("text", "")) > 20:
                        all_candidates.append({
                            "text": p["text"],
                            "entity_id": entity_id,
                            "chunk_id": p.get("chunk_id", f"{entity_id}_ftp_{pi}"),
                            "text_score": fr.get("score", 0) * 0.9,
                            "provenance": "fulltext_passage"
                        })
        
        # 5. NEW: Search for similarity in exact_text based on question keywords
        # This is crucial for finding relevant passages that contain answer information
        exact_text_candidates = self._search_exact_text_similarity(mentions, question_text)
        all_candidates.extend(exact_text_candidates)
        
        # 5. Merge and compute combined scores
        merged = self._merge_and_score(all_candidates)
        
        # 6. Deduplicate
        deduplicated = self._deduplicate(merged)
        
        # 7. Rerank top candidates
        if len(deduplicated) > top_k:
            reranked = self.reranker.rerank(question_text, deduplicated, top_k=top_k * 2)
            # Combine rerank score with previous score
            for item in reranked:
                # Ensure scores are floats
                combined = item.get("combined_score", 0)
                rerank = item.get("rerank_score", 0)
                
                # Handle potential list/tuple values
                if isinstance(combined, (list, tuple)):
                    combined = float(combined[0]) if combined else 0.0
                if isinstance(rerank, (list, tuple)):
                    rerank = float(rerank[0]) if rerank else 0.0
                
                item["combined_score"] = 0.5 * float(combined) + 0.5 * float(rerank)
            reranked.sort(key=lambda x: float(x.get("combined_score", 0)), reverse=True)
            deduplicated = reranked[:top_k]
        
        self.cache.set(cache_key, deduplicated)
        return deduplicated
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms for full-text search."""
        # Remove common words
        stopwords = {'là', 'của', 'và', 'trong', 'có', 'được', 'cho', 'với', 'đã', 'này', 
                     'những', 'các', 'một', 'về', 'như', 'từ', 'đến', 'nào', 'sau', 'khi'}
        
        words = re.findall(r'\b[\w\-]+\b', text.lower())
        key_terms = [w for w in words if len(w) > 2 and w not in stopwords]
        
        # Also extract multi-word phrases
        phrases = re.findall(r'[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*(?:\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*)+', text)
        key_terms.extend(phrases)
        
        return list(set(key_terms))[:10]
    
    def _search_exact_text_similarity(self, mentions: List[str], question_text: str) -> List[Dict]:
        """
        Search for similarity between question and exact_text content of entities.
        This is crucial for finding relevant passages that contain the answer.
        
        Instead of just relying on entity matching, we:
        1. Get entities by mention
        2. Extract their exact_text passages
        3. Score passages by similarity to the question
        """
        candidates = []
        question_lower = question_text.lower()
        question_embedding = self.embedding_gen.generate_embedding(question_text)
        
        # Extract key phrases from question for keyword matching
        question_keywords = set(self._extract_key_terms(question_text))
        
        for mention in mentions[:10]:  # Limit to avoid too many queries
            entities = self.neo4j.search_entity(mention)
            
            for entity in entities[:3]:  # Top 3 matching entities per mention
                entity_id = entity.get("id", "")
                
                # Get all passages from this entity
                passages = self.neo4j.get_entity_passages(entity_id)
                
                for pi, passage in enumerate(passages[:8]):  # Up to 8 passages per entity
                    passage_text = passage.get("text", "")
                    if not passage_text or len(passage_text) < 30:
                        continue
                    
                    passage_lower = passage_text.lower()
                    
                    # Method 1: Keyword overlap score
                    passage_words = set(re.findall(r'\b\w+\b', passage_lower))
                    keyword_overlap = len(question_keywords & passage_words)
                    keyword_score = keyword_overlap / max(len(question_keywords), 1)
                    
                    # Method 2: Check if entity/mention appears in passage  
                    entity_in_passage = 1.0 if mention.lower() in passage_lower else 0.5
                    
                    # Method 3: Check for important keywords from question
                    important_matches = 0
                    for kw in question_keywords:
                        if len(kw) > 3 and kw in passage_lower:
                            important_matches += 1
                    important_score = min(important_matches / 3, 1.0)  # Normalize
                    
                    # Combined relevance score
                    relevance_score = (
                        0.4 * keyword_score + 
                        0.3 * entity_in_passage + 
                        0.3 * important_score
                    )
                    
                    # Only add if reasonably relevant
                    if relevance_score > 0.2:
                        candidates.append({
                            "text": passage_text,
                            "entity_id": entity_id,
                            "chunk_id": f"{entity_id}_exact_{pi}",
                            "text_score": relevance_score,
                            "entity_score": 0.3,  # Base entity score
                            "provenance": "exact_text_similarity"
                        })
        
        # Sort by relevance and limit
        candidates.sort(key=lambda x: x.get("text_score", 0), reverse=True)
        return candidates[:15]
    
    def _merge_and_score(self, candidates: List[Dict]) -> List[Dict]:
        """Merge candidates and compute combined scores."""
        w1 = self.config.entity_weight
        w2 = self.config.vector_weight
        w3 = self.config.text_weight
        w4 = self.config.graph_weight
        
        for cand in candidates:
            entity_score = cand.get("entity_score", 0)
            vector_score = cand.get("vector_score", 0)
            text_score = cand.get("text_score", 0)
            graph_proximity = cand.get("graph_proximity", 2)
            
            # Convert graph proximity to score (closer = higher)
            graph_score = 1.0 / (1 + graph_proximity)
            
            # Normalize scores
            combined = (
                w1 * entity_score +
                w2 * vector_score +
                w3 * text_score +
                w4 * graph_score
            )
            
            # Normalize to [0, 1]
            total_weight = w1 + w2 + w3 + w4
            cand["combined_score"] = combined / total_weight if total_weight > 0 else 0
        
        # Sort by combined score
        candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return candidates
    
    def _deduplicate(self, candidates: List[Dict]) -> List[Dict]:
        """Deduplicate candidates by text similarity."""
        seen_texts = set()
        unique = []
        
        for cand in candidates:
            text = cand.get("text", "")
            text_hash = hash(text[:100].lower().strip())
            
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique.append(cand)
        
        return unique


# ================================================================================
# Context Builder
# ================================================================================

class ContextBuilder:
    """Build context from retrieved candidates with token budget."""
    
    def __init__(self, config: GraphRAGConfig, tokenizer=None):
        self.config = config
        self.tokenizer = tokenizer
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Approximate: 1 token ≈ 4 chars for Vietnamese
        return len(text) // 4
    
    def summarize_if_needed(self, text: str, max_tokens: int = 200) -> str:
        """Truncate or summarize text if too long."""
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # Simple truncation with ellipsis
        ratio = max_tokens / current_tokens
        max_chars = int(len(text) * ratio)
        
        # Try to break at sentence boundary
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars // 2:
            truncated = truncated[:last_period + 1]
        else:
            truncated = truncated + "..."
        
        return truncated
    
    def build_context(self, candidates: List[Dict], token_budget: int = 2000) -> Tuple[str, List[Dict]]:
        """
        Build context from candidates within token budget.
        
        Returns:
            (context_text, provenance_list)
        """
        context_parts = []
        provenance_list = []
        current_tokens = 0
        
        for cand in candidates:
            text = cand.get("text", "")
            if not text:
                continue
            
            # Create formatted entry
            source = cand.get("entity_id") or cand.get("chunk_id") or "unknown"
            score = cand.get("combined_score", cand.get("score", 0))
            
            # Ensure score is float
            if isinstance(score, (list, tuple)):
                score = float(score[0]) if score else 0.0
            score = float(score)
            
            entry_text = text
            entry_tokens = self.count_tokens(entry_text)
            
            # Check if we can add this entry
            if current_tokens + entry_tokens > token_budget:
                # Try to summarize
                remaining_budget = token_budget - current_tokens
                if remaining_budget > 50:
                    entry_text = self.summarize_if_needed(text, remaining_budget - 20)
                    entry_tokens = self.count_tokens(entry_text)
                else:
                    break
            
            # Add formatted context
            header = f"[source: {source}, score: {score:.2f}]"
            context_parts.append(f"{header}\n{entry_text}")
            
            # Add to provenance with text preview for debugging
            provenance_list.append({
                "source": source,
                "chunk_id": cand.get("chunk_id"),
                "score": score,
                "provenance": cand.get("provenance", "unknown"),
                "text_preview": text[:300] if text else "",
                "entity_id": cand.get("entity_id")
            })
            
            current_tokens += entry_tokens + self.count_tokens(header) + 2
        
        context_text = "\n\n".join(context_parts)
        return context_text, provenance_list
