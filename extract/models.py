"""Định nghĩa các model Pydantic."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Entity(BaseModel):
    """Represents an entity in the Knowledge Graph."""
    id: str = Field(description="Unique identifier for the entity in Vietnamese.")
    label: List[str] = Field(description="Array of entity names/aliases in Vietnamese.")
    type: str = Field(description="Entity type in Vietnamese.")
    description: str = Field(description="Brief description of the entity in Vietnamese.")
    original_text: List[Dict] = Field(description="List of occurrences with topic, lesson, label and exact_text.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Object containing important structured information.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Object containing additional information.")
    confidence: float = Field(default=1.0, description="Confidence score for this entity.")
    occurrence_count: int = Field(default=1, description="Number of times entity appeared.")
    window_indices: List[int] = Field(default_factory=list, description="Window indices where entity was found.")


class RequestDetail(BaseModel):
    """Chi tiết về một request API."""
    request_number: int
    file_path: str
    topic: str
    lesson: str
    window_index: int
    start_time: str
    end_time: str
    processing_time_seconds: float
    status: str  # 'success', 'error'
    text_length: int
    sentences_count: int
    entities_extracted: int = 0
    entities_processed: int = 0
    response_valid: bool = False
    error_message: Optional[str] = None
    response_length: int = 0
    topic_specific: bool = False
    acronyms_expanded: int = 0