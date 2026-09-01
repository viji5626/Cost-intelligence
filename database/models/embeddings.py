"""
Embeddings and Vector Storage Model
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class RecordEmbedding(BaseModel):
    """
    Stores vector embeddings and metadata for documents/records across the system.
    Supports pgvector HNSW indexing in PostgreSQL and JSON array fallback.
    """

    __tablename__ = "record_embeddings"

    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # IDEA_SUBMISSION, ECN, PART, BOM_ITEM
    entity_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Identifiers for exact matching
    part_number: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    ecn_number: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    model_code: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)

    # Embedding vector (stored as JSON array of floats for universal compatibility, pgvector in PostgreSQL)
    embedding_vector: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=384, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="Qwen3-Embedding-0.6B", nullable=False)

    # Provenance metadata
    metadata_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_record_embeddings_lookup", "entity_type", "entity_id", "chunk_index"),
        Index("ix_record_embeddings_identifiers", "part_number", "model_code", "category"),
    )
