"""
Retrieval & Evidence Grounding Pipeline Orchestrator
Coordinates end-to-end execution:
Query Formulation -> Multi-Channel Hybrid Search (AI-06) -> Cross-Encoder Reranking (AI-07)
-> Context Budgeting (AI-08) -> Deterministic Evidence Evaluation -> Grounded Output.
"""

import time
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai.context.context_manager import ContextManager
from ai.context.models import ContextBuildResult, ContextItem, PlacementEnum, SourceAuthorityEnum
from ai.context.token_budgeter import TokenBudgeter
from ai.grounding.evidence_evaluator import EvidenceEvaluator
from ai.grounding.models import (
    GroundingEvaluationResult,
    GroundingEvaluationSpec,
    ImplementationDecisionEnum,
)
from ai.grounding.query_formulator import FormulatedQuery, QueryFormulator
from ai.retrieval.embedding_provider import EmbeddingProvider, get_embedding_provider
from ai.retrieval.hybrid_engine import HybridRetrievalEngine, RetrievalQuery, RetrievedDocument
from ai.retrieval.reranker_provider import RerankResult, RerankerProvider, get_reranker_provider


class RetrievalGroundingOrchestrator:
    """
    Unified execution pipeline connecting AI-06 Embeddings, AI-07 Reranker, AI-08 Context Manager,
    and AI-09 Evidence Grounding Evaluator into a deterministic, audit-traceable pipeline.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None,
        spec: Optional[GroundingEvaluationSpec] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider("native_local")
        self.reranker_provider = reranker_provider or get_reranker_provider("native_local")
        self.spec = spec or GroundingEvaluationSpec()
        self.hybrid_engine = HybridRetrievalEngine(
            embedding_provider=self.embedding_provider,
            reranker_provider=self.reranker_provider,
        )

    def execute_grounding_pipeline(
        self,
        raw_query: str,
        corpus_records: List[Dict[str, Any]],
        idea_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        target_part_number: Optional[str] = None,
        target_vehicle_model: Optional[str] = None,
        applicable_sibling_models: Optional[List[str]] = None,
        submission_date: Optional[date] = None,
        context_limit: int = 4096,
        top_k: int = 10,
    ) -> GroundingEvaluationResult:
        """
        Executes synchronous/in-memory end-to-end evidence grounding pass.
        Measures exact latencies for retrieval, reranking, context assembly, and evaluation.
        """
        t_total_start = time.perf_counter()
        latency_breakdown: Dict[str, float] = {}

        # 1. Query Formulation
        t0 = time.perf_counter()
        formulated: FormulatedQuery = QueryFormulator.formulate_query(
            raw_text=raw_query,
            title=title,
            description=description,
            target_part_number=target_part_number,
            target_vehicle_model=target_vehicle_model,
        )
        latency_breakdown["query_formulation_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 2. Multi-Channel Hybrid Retrieval & Reranking
        t1 = time.perf_counter()
        retrieval_query = RetrievalQuery(
            raw_query=formulated.primary_search_text,
            target_vehicle_model=formulated.target_vehicle_model,
            target_part_number=formulated.target_part_number,
            target_category=formulated.target_category,
            top_k=top_k,
            enable_reranking=True,
        )
        retrieved_docs: List[RetrievedDocument] = self.hybrid_engine.search_corpus(
            query=retrieval_query,
            records=corpus_records,
        )
        latency_breakdown["retrieval_and_reranking_ms"] = round((time.perf_counter() - t1) * 1000.0, 2)

        # 3. AI-08 Context Budgeting & Assembly
        t2 = time.perf_counter()
        rerank_results_for_context = [
            RerankResult(
                id=doc.id,
                text=doc.text,
                initial_score=doc.score,
                initial_rank=doc.initial_rank,
                rerank_score=doc.rerank_score or doc.score,
                final_rank=doc.final_rank or doc.initial_rank,
                matched_strategy=doc.matched_strategy,
                metadata=doc.metadata,
            )
            for doc in retrieved_docs
        ]

        from ai.context.context_manager import context_manager
        context_result: ContextBuildResult = context_manager.build_context(
            query=formulated.primary_search_text,
            reranked_results=rerank_results_for_context,
            system_prompt="Analyze automotive cost and implementation evidence.",
            override_context_limit=context_limit,
        )
        latency_breakdown["context_assembly_ms"] = round((time.perf_counter() - t2) * 1000.0, 2)

        # 4. Deterministic Evidence Evaluation
        t3 = time.perf_counter()
        eval_result = EvidenceEvaluator.evaluate_grounding_and_decision(
            query_text=raw_query,
            retrieved_docs=retrieved_docs,
            target_part_number=formulated.target_part_number,
            target_model_code=formulated.target_vehicle_model,
            target_problem=formulated.decomposed_problem,
            target_solution=formulated.decomposed_solution,
            applicable_sibling_models=applicable_sibling_models,
            submission_date=submission_date,
            spec=self.spec,
            idea_id=idea_id,
        )
        latency_breakdown["evidence_evaluation_ms"] = round((time.perf_counter() - t3) * 1000.0, 2)

        # 5. Attach Final Provenance & Latency Breakdown
        total_time_ms = round((time.perf_counter() - t_total_start) * 1000.0, 2)
        latency_breakdown["total_pipeline_latency_ms"] = total_time_ms

        eval_result.provenance.expanded_query_terms = formulated.expanded_terms
        eval_result.provenance.context_items_selected_count = len(context_result.selected_items)
        eval_result.provenance.latency_breakdown_ms = latency_breakdown

        return eval_result

    async def execute_grounding_pipeline_async(
        self,
        raw_query: str,
        session: Optional[AsyncSession],
        corpus_records: List[Dict[str, Any]],
        idea_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        target_part_number: Optional[str] = None,
        target_vehicle_model: Optional[str] = None,
        submission_date: Optional[date] = None,
    ) -> GroundingEvaluationResult:
        """
        Asynchronously executes grounding pipeline with database-backed applicability queries.
        Delegates cross-model sharing to ApplicabilityMatrixEngine when session is available.
        """
        sibling_models: List[str] = []
        if session and target_part_number:
            try:
                from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
                summary = await ApplicabilityMatrixEngine.get_cross_model_summary(
                    session=session,
                    part_number=target_part_number,
                )
                if summary and summary.sibling_models_sharing_part:
                    sibling_models = summary.sibling_models_sharing_part
            except Exception:
                pass

        return self.execute_grounding_pipeline(
            raw_query=raw_query,
            corpus_records=corpus_records,
            idea_id=idea_id,
            title=title,
            description=description,
            target_part_number=target_part_number,
            target_vehicle_model=target_vehicle_model,
            applicable_sibling_models=sibling_models,
            submission_date=submission_date,
        )


# Global singleton instance
grounding_orchestrator = RetrievalGroundingOrchestrator()
