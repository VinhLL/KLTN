"""
GraphRAG Pipeline - Core Configuration and Utilities
"""

import os
import re
import json
import time
import hashlib
import logging
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from functools import lru_cache
from collections import OrderedDict

# ================================================================================
# Logging Setup
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GraphRAG")

try:
    from kaggle_secrets import UserSecretsClient
    _KAGGLE_SECRETS_AVAILABLE = True
except Exception:
    _KAGGLE_SECRETS_AVAILABLE = False

def get_secret(key: str, default: str = None) -> str:
    if _KAGGLE_SECRETS_AVAILABLE:
        try:
            user_secrets = UserSecretsClient()
            val = user_secrets.get_secret(key)
            if val is not None and val != "":
                return val
        except Exception:
            pass
    val = os.getenv(key)
    if val:
        return val
    return default

# ================================================================================
# Configuration
# ================================================================================

@dataclass
class GraphRAGConfig:
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "neo4j+s://5f398723.databases.neo4j.io")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = get_secret("NEO4J_PASSWORD", "password")
    
    # DeepSeek API Configuration
    # Note: For dual-mode (Qwen + DeepSeek), use DualAnswerGenerator instead
    use_deepseek_api: bool = False  # If True, AnswerGenerator uses DeepSeek API; if False, uses local Qwen
    deepseek_api_key: str = get_secret("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"  # Options: deepseek-chat, deepseek-reasoner
    
    # Models (used when use_deepseek_api = False)
    qwen_model: str = "Qwen/Qwen3-4B"  # For MCQ questions
    tf_model: str = "Qwen/Qwen3-4B"  # For T/F questions - set to "deepseek-ai/deepseek-llm-7b-chat" for 93.1% T/F accuracy
    tf_direct_mode: bool = False  # If True, T/F uses direct prompt without KG (faster, simpler)
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"  # Separate embedding model
    reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"    # Separate reranker model
    embedding_dim: int = 1024
    
    # Retrieval - significantly increased for better coverage
    chunk_size: int = 1200
    chunk_overlap: int = 250
    top_k_retrieval: int = 40  # Increased from 20 for more candidates
    top_k_rerank: int = 25     # Increased from 10 for more evidence
    
    # Scoring weights - adjusted to favor relationship context
    entity_weight: float = 0.35  # Reduced from 0.35 to diversify
    vector_weight: float = 0.30  # Slightly reduced
    text_weight: float = 0.30
    graph_weight: float = 0.25 # Increased from 0.15 for relationship context
    
    # Thresholds - lowered for better recall
    confidence_threshold: float = 0.4  # Lowered from 0.6
    entity_linking_threshold: float = 0.5  # Lowered from 0.65
    
    # Performance
    batch_size: int = 16
    cache_ttl: int = 3600
    max_retries: int = 3
    timeout: int = 30
    
    # Files
    questions_file: str = "/kaggle/input/historical/question_1000.json"
    entities_file: str = "/kaggle/input/historical/entities_v5.json"
    kg_file: str = "/kaggle/input/historical/knowledge_graph_historical_v5.json"
    output_file: str = "/kaggle/working/results_graphrag_neo4j.json"


# ================================================================================
# Vietnamese Text Normalization
# ================================================================================

class VietnameseNormalizer:
    """Vietnamese text normalization and alias mapping."""
    
    # Common alias mappings
    ALIASES = {
        "hồ chí minh": ["ho chi minh", "bác hồ", "nguyễn ái quốc", "nguyễn sinh cung", "chủ tịch hồ chí minh"],
        "liên hợp quốc": ["liên hiệp quốc", "un", "united nations"],
        "asean": ["hiệp hội các quốc gia đông nam á", "association of southeast asian nations"],
        "chiến tranh thế giới thứ hai": ["thế chiến 2", "ww2", "world war 2", "đại chiến thế giới lần 2"],
        "chiến tranh lạnh": ["cold war"],
        "liên xô": ["soviet union", "ussr", "liên bang xô viết"],
    }
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Unicode to NFC form."""
        return unicodedata.normalize('NFC', text)
    
    @staticmethod
    def remove_diacritics(text: str) -> str:
        """Remove Vietnamese diacritics."""
        s = unicodedata.normalize('NFD', text)
        return ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace and punctuation."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"['']", "'", text)
        return text.strip()
    
    @classmethod
    def normalize(cls, text: str) -> str:
        """Full normalization pipeline."""
        text = cls.normalize_unicode(text)
        text = cls.normalize_whitespace(text)
        return text.lower()
    
    @classmethod
    def get_aliases(cls, text: str) -> List[str]:
        """Get all aliases for a text."""
        normalized = cls.normalize(text)
        aliases = [text, normalized]
        
        if normalized in cls.ALIASES:
            aliases.extend(cls.ALIASES[normalized])
        
        # Check if text matches any alias
        for canonical, alias_list in cls.ALIASES.items():
            if normalized in alias_list or normalized == canonical:
                aliases.append(canonical)
                aliases.extend(alias_list)
        
        return list(set(aliases))


# ================================================================================
# LRU Cache with TTL
# ================================================================================

class TTLCache:
    """LRU Cache with Time-To-Live."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
    
    def _hash_key(self, key: Any) -> str:
        if isinstance(key, str):
            return hashlib.md5(key.encode()).hexdigest()
        return hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()
    
    def get(self, key: Any) -> Optional[Any]:
        hashed = self._hash_key(key)
        if hashed in self.cache:
            if time.time() - self.timestamps[hashed] < self.ttl:
                self.cache.move_to_end(hashed)
                return self.cache[hashed]
            else:
                del self.cache[hashed]
                del self.timestamps[hashed]
        return None
    
    def set(self, key: Any, value: Any):
        hashed = self._hash_key(key)
        if hashed in self.cache:
            del self.cache[hashed]
        elif len(self.cache) >= self.maxsize:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
            del self.timestamps[oldest]
        
        self.cache[hashed] = value
        self.timestamps[hashed] = time.time()


# ================================================================================
# Retry Decorator with Exponential Backoff
# ================================================================================

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for exponential backoff retry."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay = min(delay * 2, max_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator


# ================================================================================
# Text Chunking
# ================================================================================

def chunk_text(text: str, max_chars: int = 800, overlap: int = 100, 
               parent_entity_id: str = None) -> List[Dict]:
    """
    Chunk text into overlapping segments.
    
    Returns list of chunk dictionaries with:
    - chunk_id, text, parent_entity_id, offset
    """
    if not text or len(text) <= max_chars:
        return [{
            "chunk_id": f"{parent_entity_id}_0" if parent_entity_id else "chunk_0",
            "text": text,
            "parent_entity_id": parent_entity_id,
            "offset": 0
        }]
    
    chunks = []
    offset = 0
    chunk_idx = 0
    
    while offset < len(text):
        # Find end position
        end = min(offset + max_chars, len(text))
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in ['. ', '.\n', '! ', '? ', '\n\n']:
                last_sep = text[offset:end].rfind(sep)
                if last_sep > max_chars // 2:
                    end = offset + last_sep + len(sep)
                    break
        
        chunk_text_content = text[offset:end].strip()
        
        if chunk_text_content:
            chunk_id = f"{parent_entity_id}_{chunk_idx}" if parent_entity_id else f"chunk_{chunk_idx}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text_content,
                "parent_entity_id": parent_entity_id,
                "offset": offset
            })
            chunk_idx += 1
        
        # Move to next position with overlap
        offset = end - overlap if end < len(text) else len(text)
    
    return chunks


# ================================================================================
# Metrics Collector
# ================================================================================

class MetricsCollector:
    """Collect and report performance metrics."""
    
    def __init__(self):
        self.metrics = {
            "queries": 0,
            "total_latency": 0.0,
            "errors": 0,
            "embeddings_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = time.time()
    
    def record_query(self, latency: float):
        self.metrics["queries"] += 1
        self.metrics["total_latency"] += latency
    
    def record_error(self):
        self.metrics["errors"] += 1
    
    def record_embedding(self, count: int = 1):
        self.metrics["embeddings_generated"] += count
    
    def record_cache_hit(self):
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        self.metrics["cache_misses"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time
        queries = self.metrics["queries"]
        
        return {
            "elapsed_seconds": elapsed,
            "qps": queries / elapsed if elapsed > 0 else 0,
            "avg_latency_ms": (self.metrics["total_latency"] / queries * 1000) if queries > 0 else 0,
            "error_rate": self.metrics["errors"] / queries if queries > 0 else 0,
            "embeddings_per_minute": self.metrics["embeddings_generated"] / elapsed * 60 if elapsed > 0 else 0,
            "cache_hit_rate": self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"]) 
                             if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0,
            **self.metrics
        }
    
    def print_stats(self):
        stats = self.get_stats()
        logger.info("=" * 50)
        logger.info("PERFORMANCE METRICS")
        logger.info(f"  QPS: {stats['qps']:.2f}")
        logger.info(f"  Avg Latency: {stats['avg_latency_ms']:.2f}ms")
        logger.info(f"  Error Rate: {stats['error_rate']:.2%}")
        logger.info(f"  Embeddings/min: {stats['embeddings_per_minute']:.2f}")
        logger.info(f"  Cache Hit Rate: {stats['cache_hit_rate']:.2%}")
        logger.info("=" * 50)
