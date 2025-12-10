"""
GraphRAG Pipeline - Embedding Generation and Vector Operations
Uses Qwen3-Embedding-0.6B for embeddings and Qwen3-Reranker-0.6B for reranking
"""

import torch
import numpy as np
from typing import List, Dict, Optional, Tuple
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoModel
import logging

from .core import GraphRAGConfig, TTLCache, MetricsCollector, retry_with_backoff, logger

# ================================================================================
# Embedding Generator using Qwen3-Embedding
# ================================================================================

class EmbeddingGenerator:
    """Generate embeddings using Qwen3-Embedding-0.6B (dedicated embedding model)."""
    
    def __init__(self, config: GraphRAGConfig, device: str = "cuda"):
        self.config = config
        self.device = device if torch.cuda.is_available() else "cpu"
        self.cache = TTLCache(maxsize=5000, ttl=config.cache_ttl)
        self.metrics = MetricsCollector()
        
        # Use dedicated embedding model
        model_name = config.embedding_model
        logger.info(f"Loading embedding model: {model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Set pad_token if not defined (required for batch > 1)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        # Use AutoModel for embedding extraction (not classification)
        self.model = AutoModel.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True
        )
        
        # Set pad_token_id in model config
        if self.model.config.pad_token_id is None:
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
        
        self.model = self.model.to(self.device)
        self.model.eval()
        logger.info(f"Embedding model loaded on {self.device}")
    
    def _get_embedding_from_model(self, text: str) -> List[float]:
        """Get embedding from model for a single text using mean pooling."""
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True,
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # AutoModel returns last_hidden_state directly
            # Use mean pooling over tokens (excluding padding)
            last_hidden = outputs.last_hidden_state
            attention_mask = inputs['attention_mask'].unsqueeze(-1).float()
            masked_hidden = last_hidden * attention_mask
            sum_hidden = masked_hidden.sum(dim=1)
            sum_mask = attention_mask.sum(dim=1).clamp(min=1e-9)
            embedding = sum_hidden / sum_mask
            
        return embedding.squeeze().cpu().numpy().tolist()
    
    def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for a single text."""
        if use_cache:
            cached = self.cache.get(text)
            if cached is not None:
                self.metrics.record_cache_hit()
                return cached
            self.metrics.record_cache_miss()
        
        import time
        start = time.time()
        
        embedding = self._get_embedding_from_model(text)
        
        # L2 normalize
        embedding = self._normalize_l2(embedding)
        
        self.cache.set(text, embedding)
        self.metrics.record_embedding()
        self.metrics.record_query(time.time() - start)
        
        return embedding
    
    def generate_embeddings_batch(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if use_cache:
                cached = self.cache.get(text)
                if cached is not None:
                    results[i] = cached
                    self.metrics.record_cache_hit()
                    continue
                self.metrics.record_cache_miss()
            texts_to_embed.append(text)
            indices_to_embed.append(i)
        
        if not texts_to_embed:
            return results
        
        # Batch inference
        import time
        start = time.time()
        
        batch_size = self.config.batch_size
        for batch_start in range(0, len(texts_to_embed), batch_size):
            batch_end = min(batch_start + batch_size, len(texts_to_embed))
            batch_texts = texts_to_embed[batch_start:batch_end]
            
            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs, output_hidden_states=True)
                hidden_states = outputs.hidden_states[-1]
                attention_mask = inputs['attention_mask'].unsqueeze(-1)
                masked_hidden = hidden_states * attention_mask
                embeddings = masked_hidden.sum(dim=1) / attention_mask.sum(dim=1)
            
            embeddings = embeddings.cpu().numpy()
            
            for j, emb in enumerate(embeddings):
                idx = indices_to_embed[batch_start + j]
                normalized = self._normalize_l2(emb.tolist())
                results[idx] = normalized
                self.cache.set(texts_to_embed[batch_start + j], normalized)
        
        self.metrics.record_embedding(len(texts_to_embed))
        self.metrics.record_query(time.time() - start)
        
        return results
    
    @staticmethod
    def _normalize_l2(vector: List[float]) -> List[float]:
        """L2 normalize a vector."""
        arr = np.array(vector)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()
    
    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(v1)
        b = np.array(v2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ================================================================================
# Reranker using Qwen3-Reranker-0.6B
# ================================================================================

class Reranker:
    """Rerank passages using Qwen3-Reranker-0.6B."""
    
    def __init__(self, config: GraphRAGConfig, device: str = "cuda"):
        self.config = config
        self.device = device if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading reranker model: {config.reranker_model}")
        self.tokenizer = AutoTokenizer.from_pretrained(config.reranker_model)
        
        # Set pad_token if not defined (required for Qwen3 with batch > 1)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        self.model = AutoModelForSequenceClassification.from_pretrained(
            config.reranker_model,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True
        )
        
        # Also set pad_token_id in model config
        if self.model.config.pad_token_id is None:
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
        
        self.model = self.model.to(self.device)
        self.model.eval()
        logger.info(f"✓ Reranker model loaded on {self.device}")
    
    def rerank(self, question: str, candidates: List[Dict], 
               text_key: str = "text", top_k: int = None) -> List[Dict]:
        """
        Rerank candidate passages based on relevance to question.
        
        Args:
            question: The query text
            candidates: List of candidate dicts with 'text' field
            text_key: Key to access text in candidate dict
            top_k: Number of top results to return (None = all)
        
        Returns:
            Reranked list with added 'rerank_score' field
        """
        if not candidates:
            return []
        
        top_k = top_k or self.config.top_k_rerank
        
        # Create query-passage pairs
        pairs = []
        for cand in candidates:
            text = cand.get(text_key, "")
            if text:
                pairs.append([question, text])
        
        if not pairs:
            return candidates[:top_k]
        
        # Batch scoring
        scores = []
        batch_size = self.config.batch_size
        
        for batch_start in range(0, len(pairs), batch_size):
            batch_end = min(batch_start + batch_size, len(pairs))
            batch_pairs = pairs[batch_start:batch_end]
            
            inputs = self.tokenizer(
                batch_pairs,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                
                # Handle different output shapes from reranker model
                # Could be: (batch, num_labels), (batch, 1), (batch,), or scalar
                
                # First, flatten to 1D if needed
                if logits.dim() > 1:
                    # If (batch, num_labels), take first column or mean
                    if logits.size(-1) > 1:
                        # For multi-label, take the first label (relevant score)
                        batch_scores = logits[:, 0]
                    else:
                        batch_scores = logits.squeeze(-1)
                else:
                    batch_scores = logits
                
                # Ensure 1D tensor (not 0D scalar)
                if batch_scores.dim() == 0:
                    batch_scores = batch_scores.unsqueeze(0)
                
                # Apply sigmoid for probability
                batch_scores = torch.sigmoid(batch_scores)
                
                # Convert to list of floats
                batch_scores_list = batch_scores.cpu().tolist()
                
                # Ensure each item is a float
                for score in batch_scores_list:
                    if isinstance(score, (list, tuple)):
                        scores.append(float(score[0]) if score else 0.0)
                    else:
                        scores.append(float(score))
        
        # Add scores to candidates - ensure each score is a float
        for i, cand in enumerate(candidates):
            if i < len(scores):
                score = scores[i]
                # Double-check score is a float
                if isinstance(score, (list, tuple)):
                    score = float(score[0]) if score else 0.0
                cand["rerank_score"] = float(score)
            else:
                cand["rerank_score"] = 0.0
        
        # Sort by rerank score
        reranked = sorted(candidates, key=lambda x: float(x.get("rerank_score", 0)), reverse=True)
        
        return reranked[:top_k]
    
    def compute_relevance_score(self, question: str, passage: str) -> float:
        """Compute relevance score for a single question-passage pair."""
        inputs = self.tokenizer(
            [[question, passage]],
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            score = torch.sigmoid(outputs.logits.squeeze()).item()
        
        return score
