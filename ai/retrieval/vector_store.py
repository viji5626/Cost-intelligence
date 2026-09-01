"""
Native Vector Storage & HNSW Indexing Module
Implements dynamic vector dimensionality, embedding space versioning, pgvector DDL generation,
HNSW index parameter management, and safe re-indexing migrations.
"""

import math
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from ai.registry.models import ModelManifest


class EmbeddingSpaceStatusEnum(str, Enum):
    """Embedding Space Migration Status."""
    ACTIVE = "ACTIVE"
    STAGED = "STAGED"
    REINDEX_REQUIRED = "REINDEX_REQUIRED"
    DEPRECATED = "DEPRECATED"


class EmbeddingSpaceRecord(BaseModel):
    """Immutable metadata tracking an embedding vector space."""
    space_id: str
    model_id: str
    model_version: str = "1.0.0"
    model_hash: str
    dimension: int
    is_normalized: bool = True
    status: EmbeddingSpaceStatusEnum = EmbeddingSpaceStatusEnum.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HNSWIndexConfig(BaseModel):
    """Configurable parameters for HNSW (Hierarchical Navigable Small World) Index."""
    m: int = Field(default=16, ge=4, le=128, description="Max number of bi-directional links per node")
    ef_construction: int = Field(default=64, ge=8, le=512, description="Size of dynamic candidate list during build")
    ef_search: int = Field(default=64, ge=8, le=512, description="Size of dynamic candidate list during search")
    metric: str = Field(default="cosine", description="Distance metric: cosine, l2, or inner_product")

    def to_pgvector_sql(self, table_name: str, column_name: str, index_name: str = "idx_vectors_hnsw") -> str:
        """Generates native PostgreSQL pgvector HNSW index creation DDL."""
        ops = "vector_cosine_ops" if self.metric == "cosine" else "vector_l2_ops"
        return (
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON {table_name} USING hnsw ({column_name} {ops}) "
            f"WITH (m = {self.m}, ef_construction = {self.ef_construction});"
        )


class VectorStoreRecord(BaseModel):
    """Single vector entry with provenance and lineage metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str  # IDEA_SUBMISSION, ECN, PART_BOM, PLANT_OPEX
    entity_id: str
    content_text: str
    embedding: List[float]
    embedding_space_id: str
    embedding_model_id: str
    embedding_model_version: str = "1.0.0"
    embedding_dimension: int
    is_normalized: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmbeddingSpaceVersionManager:
    """Manages embedding space lifecycle, version detection, and re-indexing safety."""

    def __init__(self):
        self._spaces: Dict[str, EmbeddingSpaceRecord] = {}
        self._active_space_id: Optional[str] = None

    @property
    def active_space(self) -> Optional[EmbeddingSpaceRecord]:
        if self._active_space_id:
            return self._spaces.get(self._active_space_id)
        return None

    def register_space(
        self,
        space_id: str,
        model_id: str,
        model_hash: str,
        dimension: int,
        model_version: str = "1.0.0",
        is_normalized: bool = True,
        set_as_active: bool = True,
    ) -> EmbeddingSpaceRecord:
        """Registers a new embedding space."""
        rec = EmbeddingSpaceRecord(
            space_id=space_id,
            model_id=model_id,
            model_version=model_version,
            model_hash=model_hash,
            dimension=dimension,
            is_normalized=is_normalized,
            status=EmbeddingSpaceStatusEnum.ACTIVE if set_as_active else EmbeddingSpaceStatusEnum.STAGED,
        )
        self._spaces[space_id] = rec
        if set_as_active:
            self._active_space_id = space_id
        return rec

    def detect_reindex_needed(self, current_space_id: str, target_manifest: ModelManifest) -> bool:
        """
        Determines whether switching to target_manifest necessitates a full dataset re-indexing.
        Returns True if dimension, model hash, or embedding architecture changes.
        """
        current = self._spaces.get(current_space_id)
        if not current:
            return True

        # Check dimension mismatch
        if target_manifest.embedding_dimension and target_manifest.embedding_dimension != current.dimension:
            return True

        # Check model file hash mismatch
        if target_manifest.sha256_checksum != current.model_hash:
            return True

        # Check model ID mismatch
        if target_manifest.model_id != current.model_id:
            return True

        return False

    def stage_new_space(
        self,
        new_space_id: str,
        model_id: str,
        model_hash: str,
        dimension: int,
    ) -> EmbeddingSpaceRecord:
        """Stages a new vector space while keeping the old active space intact."""
        return self.register_space(
            space_id=new_space_id,
            model_id=model_id,
            model_hash=model_hash,
            dimension=dimension,
            set_as_active=False,
        )

    def activate_staged_space(self, staged_space_id: str) -> None:
        """Promotes a staged vector space to ACTIVE and deprecates the prior space."""
        if staged_space_id not in self._spaces:
            raise KeyError(f"Space '{staged_space_id}' not found.")

        if self._active_space_id and self._active_space_id != staged_space_id:
            old_space = self._spaces[self._active_space_id]
            old_space.status = EmbeddingSpaceStatusEnum.DEPRECATED

        new_space = self._spaces[staged_space_id]
        new_space.status = EmbeddingSpaceStatusEnum.ACTIVE
        self._active_space_id = staged_space_id


class NativeVectorStore:
    """
    High-Performance Vector Storage and Query Engine.
    Enforces strict dimension bounds, embedding space versioning, and HNSW cosine similarity.
    """

    def __init__(
        self,
        embedding_space: Optional[EmbeddingSpaceRecord] = None,
        hnsw_config: Optional[HNSWIndexConfig] = None,
    ):
        self.space_manager = EmbeddingSpaceVersionManager()
        self.hnsw_config = hnsw_config or HNSWIndexConfig()
        self._records: Dict[str, VectorStoreRecord] = {}  # id -> record
        self._space_indices: Dict[str, List[str]] = {}  # space_id -> list of record_ids

        if embedding_space:
            self.space_manager.register_space(
                space_id=embedding_space.space_id,
                model_id=embedding_space.model_id,
                model_hash=embedding_space.model_hash,
                dimension=embedding_space.dimension,
            )

    def get_pgvector_table_ddl(self, table_name: str = "vector_embeddings") -> str:
        """Generates PostgreSQL pgvector table and HNSW index DDL."""
        dim = self.space_manager.active_space.dimension if self.space_manager.active_space else 384
        table_sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            f"    id VARCHAR(64) PRIMARY KEY,\n"
            f"    entity_type VARCHAR(64) NOT NULL,\n"
            f"    entity_id VARCHAR(128) NOT NULL,\n"
            f"    content_text TEXT NOT NULL,\n"
            f"    embedding vector({dim}) NOT NULL,\n"
            f"    embedding_space_id VARCHAR(128) NOT NULL,\n"
            f"    embedding_model_id VARCHAR(128) NOT NULL,\n"
            f"    embedding_dimension INTEGER NOT NULL,\n"
            f"    is_normalized BOOLEAN DEFAULT TRUE,\n"
            f"    metadata JSONB DEFAULT '{{}}',\n"
            f"    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP\n"
            f");"
        )
        index_sql = self.hnsw_config.to_pgvector_sql(table_name=table_name, column_name="embedding")
        return f"{table_sql}\n\n{index_sql}"

    def insert_record(self, record: VectorStoreRecord) -> str:
        """
        Inserts a single vector record.
        Strictly validates embedding dimension against the registered embedding space.
        """
        active_sp = self.space_manager.active_space
        if active_sp:
            if record.embedding_dimension != active_sp.dimension:
                raise ValueError(
                    f"Vector dimension mismatch: Record has dimension {record.embedding_dimension}, "
                    f"but active embedding space '{active_sp.space_id}' expects {active_sp.dimension}."
                )
            if len(record.embedding) != active_sp.dimension:
                raise ValueError(
                    f"Vector length mismatch: Float array has length {len(record.embedding)}, "
                    f"expected {active_sp.dimension}."
                )

        self._records[record.id] = record
        if record.embedding_space_id not in self._space_indices:
            self._space_indices[record.embedding_space_id] = []
        self._space_indices[record.embedding_space_id].append(record.id)
        return record.id

    def insert_batch(self, records: List[VectorStoreRecord]) -> List[str]:
        """Batched insertion with validation."""
        ids = []
        for r in records:
            ids.append(self.insert_record(r))
        return ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_entity_type: Optional[str] = None,
        score_threshold: float = 0.0,
        space_id: Optional[str] = None,
    ) -> List[Tuple[VectorStoreRecord, float]]:
        """
        Executes HNSW-modeled cosine similarity search over resident records.
        """
        target_space = space_id or (self.space_manager.active_space.space_id if self.space_manager.active_space else None)
        if not target_space:
            return []

        active_sp = self.space_manager.active_space
        if active_sp and len(query_vector) != active_sp.dimension:
            raise ValueError(
                f"Query vector dimension mismatch: Query has length {len(query_vector)}, "
                f"expected {active_sp.dimension}."
            )

        candidate_ids = self._space_indices.get(target_space, [])
        scores: List[Tuple[VectorStoreRecord, float]] = []

        q_norm = math.sqrt(sum(x * x for x in query_vector))
        if q_norm == 0.0:
            return []

        for cid in candidate_ids:
            rec = self._records.get(cid)
            if not rec:
                continue

            if filter_entity_type and rec.entity_type != filter_entity_type:
                continue

            # Cosine similarity dot product (vectors are L2 unit-normalized)
            dot = sum(q * v for q, v in zip(query_vector, rec.embedding))
            sim = dot / (q_norm)
            sim_clamped = max(0.0, min(1.0, sim))

            if sim_clamped >= score_threshold:
                scores.append((rec, round(sim_clamped, 5)))

        # Sort descending by similarity
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def count_records(self, space_id: Optional[str] = None) -> int:
        """Returns total records in the store or for a specific space."""
        if space_id:
            return len(self._space_indices.get(space_id, []))
        return len(self._records)


# Global singleton vector store
native_vector_store = NativeVectorStore()
