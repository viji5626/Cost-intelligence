"""
Document and Record Chunking Engine for Cost Intelligence RAG
Adapted from TASC AI infrastructure for Hero engineering records.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DocumentChunk:
    """Represents a chunked text unit with rich engineering metadata injection."""

    chunk_index: int
    text: str
    token_estimate: int
    entity_type: str
    entity_id: str
    part_number: Optional[str] = None
    ecn_number: Optional[str] = None
    model_code: Optional[str] = None
    category: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None


class DomainChunker:
    """
    Engineering Domain Chunker that splits text into semantic blocks while preserving
    part numbers, model names, and metadata context in every chunk header.
    """

    DEFAULT_MAX_TOKENS = 256
    DEFAULT_OVERLAP = 32

    @classmethod
    def chunk_idea_submission(
        cls,
        idea_id: str,
        title: str,
        description: str,
        part_number: Optional[str] = None,
        model_code: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Chunks an Idea Submission. Injects contextual header containing vehicle,
        part number, and category into the chunk text for dense semantic retrieval.
        """
        meta_header = []
        if model_code:
            meta_header.append(f"[VEHICLE: {model_code}]")
        if part_number:
            meta_header.append(f"[PART: {part_number}]")
        if category:
            meta_header.append(f"[CATEGORY: {category}]")

        header_str = " ".join(meta_header)
        full_content = f"{header_str}\nTITLE: {title.strip()}\nDESCRIPTION: {description.strip()}"

        # Standard vehicle cost ideas are concise (usually 50-200 words), single chunk is optimal
        words = full_content.split()
        if len(words) <= cls.DEFAULT_MAX_TOKENS:
            return [
                DocumentChunk(
                    chunk_index=0,
                    text=full_content,
                    token_estimate=len(words),
                    entity_type="IDEA_SUBMISSION",
                    entity_id=idea_id,
                    part_number=part_number,
                    ecn_number=None,
                    model_code=model_code,
                    category=category,
                    metadata_payload=metadata or {},
                )
            ]

        # Multi-chunk sliding window for long engineering descriptions
        chunks = []
        step = cls.DEFAULT_MAX_TOKENS - cls.DEFAULT_OVERLAP
        for idx, i in enumerate(range(0, len(words), step)):
            chunk_words = words[i : i + cls.DEFAULT_MAX_TOKENS]
            chunk_text = " ".join(chunk_words)
            chunks.append(
                DocumentChunk(
                    chunk_index=idx,
                    text=f"{header_str}\n{chunk_text}",
                    token_estimate=len(chunk_words),
                    entity_type="IDEA_SUBMISSION",
                    entity_id=idea_id,
                    part_number=part_number,
                    ecn_number=None,
                    model_code=model_code,
                    category=category,
                    metadata_payload=metadata or {},
                )
            )
            if i + cls.DEFAULT_MAX_TOKENS >= len(words):
                break

        return chunks

    @classmethod
    def chunk_ecn_record(
        cls,
        ecn_id: str,
        ecn_number: str,
        title: str,
        description: str,
        reason: Optional[str] = None,
        part_number: Optional[str] = None,
        model_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Chunks an Engineering Change Note (ECN)."""
        header = f"[ECN: {ecn_number}]"
        if model_code:
            header += f" [VEHICLE: {model_code}]"
        if part_number:
            header += f" [PART: {part_number}]"

        full_content = (
            f"{header}\nECN TITLE: {title.strip()}\nREASON: {(reason or '').strip()}\nDETAILS: {description.strip()}"
        )

        return [
            DocumentChunk(
                chunk_index=0,
                text=full_content,
                token_estimate=len(full_content.split()),
                entity_type="ECN",
                entity_id=ecn_id,
                part_number=part_number,
                ecn_number=ecn_number,
                model_code=model_code,
                category="ENGINEERING_CHANGE",
                metadata_payload=metadata or {},
            )
        ]
