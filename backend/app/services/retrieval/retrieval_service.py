"""
Retrieval Database Service
Connects PostgreSQL/SQLite RecordEmbedding storage with HybridRetrievalEngine.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ai.retrieval.chunker import DomainChunker
from ai.retrieval.embedding_provider import get_embedding_provider
from ai.retrieval.hybrid_engine import HybridRetrievalEngine, RetrievalQuery, RetrievedDocument
from ai.retrieval.reranker_provider import get_reranker_provider
from database.models.embeddings import RecordEmbedding
from database.models.engineering_change import EngineeringChange
from database.models.ideathon import IdeaSubmission
from database.models.part_bom import Part


class RetrievalService:
    """
    Service for indexing records into vector storage and executing hybrid multi-strategy retrieval.
    """

    def __init__(self):
        self.embedding_provider = get_embedding_provider("deterministic")
        self.reranker_provider = get_reranker_provider("deterministic")
        self.engine = HybridRetrievalEngine(
            embedding_provider=self.embedding_provider,
            reranker_provider=self.reranker_provider,
        )

    async def index_idea_submission(self, session: AsyncSession, idea: IdeaSubmission) -> List[RecordEmbedding]:
        """Chunks, embeds, and indexes an IdeaSubmission record."""
        chunks = DomainChunker.chunk_idea_submission(
            idea_id=idea.id,
            title=idea.raw_title,
            description=idea.raw_description,
            part_number=idea.extracted_part_number,
            model_code=idea.target_model_id,
            category=idea.cost_reduction_category,
            metadata={"submission_code": idea.submission_code, "decision_state": idea.decision_state},
        )

        embeddings: List[RecordEmbedding] = []
        for chk in chunks:
            vec = self.embedding_provider.embed_text(chk.text)
            rec = RecordEmbedding(
                entity_type=chk.entity_type,
                entity_id=chk.entity_id,
                chunk_index=chk.chunk_index,
                chunk_text=chk.text,
                part_number=chk.part_number,
                ecn_number=chk.ecn_number,
                model_code=chk.model_code,
                category=chk.category,
                embedding_vector=vec,
                dimension=self.embedding_provider.dimension,
                model_name=self.embedding_provider.model_name,
                metadata_payload=chk.metadata_payload,
            )
            session.add(rec)
            embeddings.append(rec)

        await session.commit()
        return embeddings

    async def index_ecn(self, session: AsyncSession, ecn: EngineeringChange) -> List[RecordEmbedding]:
        """Chunks, embeds, and indexes an EngineeringChange record."""
        chunks = DomainChunker.chunk_ecn_record(
            ecn_id=ecn.id,
            ecn_number=ecn.ecn_number,
            title=ecn.title,
            description=ecn.description or "",
            reason=ecn.change_category,
            part_number=None,
            model_code=None,
            metadata={"change_category": ecn.change_category, "status": ecn.status},
        )

        embeddings: List[RecordEmbedding] = []
        for chk in chunks:
            vec = self.embedding_provider.embed_text(chk.text)
            rec = RecordEmbedding(
                entity_type=chk.entity_type,
                entity_id=chk.entity_id,
                chunk_index=chk.chunk_index,
                chunk_text=chk.text,
                part_number=chk.part_number,
                ecn_number=chk.ecn_number,
                model_code=chk.model_code,
                category=chk.category,
                embedding_vector=vec,
                dimension=self.embedding_provider.dimension,
                model_name=self.embedding_provider.model_name,
                metadata_payload=chk.metadata_payload,
            )
            session.add(rec)
            embeddings.append(rec)

        await session.commit()
        return embeddings

    async def search(
        self,
        session: AsyncSession,
        raw_query: str,
        target_vehicle_model: Optional[str] = None,
        target_part_number: Optional[str] = None,
        target_category: Optional[str] = None,
        entity_type_filter: Optional[str] = None,
        top_k: int = 10,
        enable_reranking: bool = True,
    ) -> List[RetrievedDocument]:
        """Performs hybrid retrieval over indexed database records."""
        # Query indexed records from database
        stmt = select(RecordEmbedding)
        if entity_type_filter:
            stmt = stmt.where(RecordEmbedding.entity_type == entity_type_filter)
        if target_category:
            stmt = stmt.where(RecordEmbedding.category == target_category)

        db_records = (await session.execute(stmt)).scalars().all()

        records_payload: List[Dict[str, Any]] = []
        for r in db_records:
            records_payload.append(
                {
                    "id": r.id,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "text": r.chunk_text,
                    "part_number": r.part_number,
                    "ecn_number": r.ecn_number,
                    "model_code": r.model_code,
                    "category": r.category,
                    "embedding_vector": r.embedding_vector,
                    "metadata": r.metadata_payload or {},
                }
            )

        query_obj = RetrievalQuery(
            raw_query=raw_query,
            target_vehicle_model=target_vehicle_model,
            target_part_number=target_part_number,
            target_category=target_category,
            entity_type_filter=entity_type_filter,
            top_k=top_k,
            enable_reranking=enable_reranking,
        )

        return self.engine.search_corpus(query_obj, records_payload)
