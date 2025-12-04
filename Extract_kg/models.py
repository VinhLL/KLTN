# models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Entity(BaseModel):
    """Represents an entity in the Knowledge Graph."""
    id: str = Field(description="Unique identifier for the entity in Vietnamese.")
    label: List[str] = Field(description="Array of entity names/aliases in Vietnamese.")
    type: str = Field(description="Entity type in Vietnamese.")
    description: str = Field(description="Brief description of the entity in Vietnamese.")
    original_text: List[Dict[str, Any]] = Field(description="List of occurrences with topic, lesson, label and exact_text.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Object containing important structured information.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Object containing all additional available information.")
    confidence: float = Field(default=1.0, description="Confidence score for this entity.")
    occurrence_count: int = Field(default=1, description="Number of times entity appeared.")
    window_indices: List[int] = Field(default_factory=list, description="Window indices where entity was found.")

class Triplet(BaseModel):
    """Represents a relationship (triplet) in the Knowledge Graph."""
    subject_id: str = Field(description="Vietnamese ID of the subject entity.")
    predicate: str = Field(description="Relationship name, a concise phrase/verb in Vietnamese.")
    object_id: str = Field(description="Vietnamese ID of the object entity.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Structured information about the relationship.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional information for the relationship.")
    supporting_sentences: List[Dict[str, Any]] = Field(default_factory=list, description="Sentence information supporting this relationship.")
    confidence: float = Field(default=1.0, description="Confidence score for this relationship.")
    occurrence_count: int = Field(default=1, description="Number of times relationship appeared.")

class KnowledgeGraph(BaseModel):
    """Complete structure of Knowledge Graph containing entities and relationships."""
    entities: List[Entity] = Field(description="List of all extracted entities.")
    triplets: List[Triplet] = Field(description="List of all extracted relationships.")

class ExtractionResult(BaseModel):
    """Result of relationship extraction from a window."""
    relationships: List[Dict[str, Any]]
    window_index: int
    target_entity: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)