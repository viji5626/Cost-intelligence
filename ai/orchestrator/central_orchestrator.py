"""
Central AI Master Orchestrator (AI-12)
Coordinates TaskRouter, ModelLifecycleManager, ContextManager, EvidenceEvaluator,
StructuredOutputEngine, and ToolRegistry into a unified, air-gapped, decoupled AI runtime.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Type, TypeVar

from ai.context.context_manager import ContextManager
from ai.core.contracts import (
    AIExecutionEnvelope,
    EmbeddingEngineContract,
    InferenceEngineContract,
    ModelProvenance,
    RerankerEngineContract,
    TaskType,
    VisionOCREngineContract,
)
from ai.grammar.schemas import ToolCallOutputSchema
from ai.grammar.structured_engine import StructuredOutputEngine
from ai.grounding.evidence_evaluator import EvidenceEvaluator
from ai.orchestrator.models import (
    ExecutionPlan,
    ExecutionStageTrace,
    PipelineStageEnum,
    TaskRequest,
    TaskRoutingDecision,
)
from ai.orchestrator.task_router import TaskRouter
from ai.providers.native_embedding import NativeLocalEmbeddingEngine
from ai.providers.native_gguf import NativeGGUFEngine
from ai.providers.native_reranker import NativeLocalRerankerEngine
from ai.retrieval.reranker_provider import RerankResult
from ai.runtime.lifecycle_manager import ModelLifecycleManager
from ai.tools.models import ToolExecutionRequest, ToolExecutionStatusEnum
from ai.tools.registry import ToolRegistry
from ai.vision.local_ocr_engine import LocalVisionOCREngine

T = TypeVar("T")


class AIOrchestrator:
    """
    Master AI Orchestrator coordinating all local AI runtime subsystems.
    """

    def __init__(
        self,
        router: Optional[TaskRouter] = None,
        lifecycle_manager: Optional[ModelLifecycleManager] = None,
        context_manager: Optional[ContextManager] = None,
        evidence_evaluator: Optional[EvidenceEvaluator] = None,
        structured_engine: Optional[StructuredOutputEngine] = None,
        tool_registry: Optional[ToolRegistry] = None,
        inference_engine: Optional[InferenceEngineContract] = None,
        embedding_engine: Optional[EmbeddingEngineContract] = None,
        reranker_engine: Optional[RerankerEngineContract] = None,
        vision_ocr_engine: Optional[VisionOCREngineContract] = None,
    ):
        self.router = router or TaskRouter()
        self.lifecycle_manager = lifecycle_manager or ModelLifecycleManager()
        self.context_manager = context_manager or ContextManager()
        self.evidence_evaluator = evidence_evaluator or EvidenceEvaluator()
        self.tool_registry = tool_registry or ToolRegistry()
        self.inference_engine = inference_engine or NativeGGUFEngine()
        self.embedding_engine = embedding_engine or NativeLocalEmbeddingEngine()
        self.reranker_engine = reranker_engine or NativeLocalRerankerEngine()
        self.structured_engine = structured_engine or StructuredOutputEngine(inference_engine=self.inference_engine)
        self.vision_ocr_engine = vision_ocr_engine or LocalVisionOCREngine()

        # Idempotency Cache: (task_id, req_sig) -> AIExecutionEnvelope
        self._idempotency_cache: Dict[str, AIExecutionEnvelope[Any]] = {}

    async def execute_task(self, request: TaskRequest) -> AIExecutionEnvelope[Any]:
        """
        Executes a task request using its decoupled ExecutionPlan.
        """
        t_global_start = time.perf_counter()
        traces: List[ExecutionStageTrace] = []

        # 1. Idempotency Check
        req_sig = request.compute_request_signature()
        if req_sig in self._idempotency_cache:
            cached_env = self._idempotency_cache[req_sig]
            return cached_env

        # 2. Routing Stage
        trace_routing = ExecutionStageTrace(stage_name=PipelineStageEnum.ROUTING)
        t_route_start = time.perf_counter()
        decision = self.router.resolve_routing(request)
        trace_routing.latency_seconds = round(time.perf_counter() - t_route_start, 4)
        trace_routing.completed_at = datetime.now(timezone.utc).isoformat()
        trace_routing.metadata = {
            "is_routed": decision.is_routed,
            "selected_model": decision.selected_model.model_id if decision.selected_model else None,
            "provider": decision.provider_type,
            "explanation": decision.explanation,
        }
        traces.append(trace_routing)

        if not decision.is_routed:
            trace_routing.status = "FAILED"
            trace_routing.error_message = decision.explanation
            return self._build_error_envelope(
                request=request,
                error_msg=decision.explanation,
                status="NO_CAPABLE_MODEL",
                traces=traces,
                latency=round(time.perf_counter() - t_global_start, 4),
            )

        # 3. Create Task-Specific Execution Plan
        plan = self.router.create_execution_plan(request, decision)

        # 4. Dispatch by Task Plan
        try:
            # Plan A: EMBEDDING
            if PipelineStageEnum.EMBEDDING in plan.required_stages:
                return await self._execute_embedding_plan(request, plan, decision, traces, t_global_start)

            # Plan B: RERANKING
            if PipelineStageEnum.RERANKER_ONLY in plan.required_stages:
                return await self._execute_reranking_plan(request, plan, decision, traces, t_global_start)

            # Plan C: VISION / OCR
            if PipelineStageEnum.OCR_ONLY in plan.required_stages or request.task_type == TaskType.VISION_OCR:
                return await self._execute_ocr_plan(request, plan, decision, traces, t_global_start)

            # Plan D: GENERATIVE / GROUNDED / STRUCTURED / TOOL
            return await self._execute_generative_plan(request, plan, decision, traces, t_global_start, req_sig)

        except asyncio.TimeoutError:
            return self._build_error_envelope(
                request=request,
                error_msg=f"Task execution timed out after {request.timeout_seconds}s limit.",
                status="TIMEOUT",
                traces=traces,
                latency=round(time.perf_counter() - t_global_start, 4),
            )
        except Exception as ex:
            return self._build_error_envelope(
                request=request,
                error_msg=f"Unhandled orchestrator execution exception: {str(ex)}",
                status="ERROR",
                traces=traces,
                latency=round(time.perf_counter() - t_global_start, 4),
            )

    async def _execute_embedding_plan(
        self,
        request: TaskRequest,
        plan: ExecutionPlan,
        decision: TaskRoutingDecision,
        traces: List[ExecutionStageTrace],
        t_global_start: float,
    ) -> AIExecutionEnvelope[List[List[float]]]:
        """Executes pure dense embedding task."""
        trace = ExecutionStageTrace(stage_name=PipelineStageEnum.EMBEDDING)
        t_start = time.perf_counter()
        texts = request.input_texts or ([request.prompt] if request.prompt else [])

        vectors = await self.embedding_engine.embed_texts(texts)
        trace.latency_seconds = round(time.perf_counter() - t_start, 4)
        trace.completed_at = datetime.now(timezone.utc).isoformat()
        trace.metadata = {"text_count": len(texts), "dimension": self.embedding_engine.get_dimension()}
        traces.append(trace)

        provenance = self._create_provenance(decision, plan, prompt_version="v1.0-embed")
        envelope = AIExecutionEnvelope[List[List[float]]](
            task_id=request.task_id,
            task_type=TaskType.EMBEDDING,
            status="SUCCESS",
            result=vectors,
            raw_content=f"Embedded {len(texts)} texts to {self.embedding_engine.get_dimension()}d vectors",
            latency_seconds=round(time.perf_counter() - t_global_start, 4),
            provenance=provenance,
            usage={"input_texts": len(texts), "dimension": self.embedding_engine.get_dimension()},
        )
        return envelope

    async def _execute_reranking_plan(
        self,
        request: TaskRequest,
        plan: ExecutionPlan,
        decision: TaskRoutingDecision,
        traces: List[ExecutionStageTrace],
        t_global_start: float,
    ) -> AIExecutionEnvelope[List[Dict[str, Any]]]:
        """Executes pure cross-encoder reranking task."""
        trace = ExecutionStageTrace(stage_name=PipelineStageEnum.RERANKER_ONLY)
        t_start = time.perf_counter()
        query = request.prompt or ""
        candidates = request.rerank_candidates or []

        reranked = await self.reranker_engine.rerank_async(query=query, candidates=candidates)
        trace.latency_seconds = round(time.perf_counter() - t_start, 4)
        trace.completed_at = datetime.now(timezone.utc).isoformat()
        trace.metadata = {"query": query, "candidate_count": len(candidates)}
        traces.append(trace)

        provenance = self._create_provenance(decision, plan, prompt_version="v1.0-rerank")
        envelope = AIExecutionEnvelope[List[Dict[str, Any]]](
            task_id=request.task_id,
            task_type=TaskType.RERANKING,
            status="SUCCESS",
            result=reranked,
            raw_content=f"Reranked {len(candidates)} candidates for query '{query}'",
            latency_seconds=round(time.perf_counter() - t_global_start, 4),
            provenance=provenance,
            usage={"candidate_count": len(candidates)},
        )
        return envelope

    async def _execute_ocr_plan(
        self,
        request: TaskRequest,
        plan: ExecutionPlan,
        decision: TaskRoutingDecision,
        traces: List[ExecutionStageTrace],
        t_global_start: float,
    ) -> AIExecutionEnvelope[Any]:
        """Executes Vision/OCR document processing and CAD annotation extraction."""
        trace = ExecutionStageTrace(stage_name=PipelineStageEnum.OCR_ONLY)
        try:
            doc_bytes = request.document_bytes or (request.prompt.encode("utf-8") if request.prompt else b"")
            if not doc_bytes:
                return self._build_error_envelope(
                    request=request,
                    error_msg="No document bytes provided for VISION_OCR task.",
                    status="FAILED",
                    traces=traces,
                    latency=round(time.perf_counter() - t_global_start, 4),
                )

            if request.schema_model is not None or request.json_schema is not None:
                res = await self.vision_ocr_engine.extract_structured(
                    document_bytes=doc_bytes,
                    json_schema=request.json_schema or (request.schema_model.model_json_schema() if hasattr(request.schema_model, "model_json_schema") else {}),
                    model_id=decision.selected_model.model_id if decision.selected_model else "local-vision-ocr",
                )
                result_data = res.get("data", res)
                raw_text = json.dumps(result_data)
            else:
                raw_text = await self.vision_ocr_engine.extract_text(
                    document_bytes=doc_bytes,
                    mime_type=request.mime_type,
                    model_id=decision.selected_model.model_id if decision.selected_model else "local-vision-ocr",
                )
                result_data = raw_text

            trace.status = "COMPLETED"
            trace.latency_seconds = round(time.perf_counter() - t_global_start, 4)
            traces.append(trace)

            provenance = ModelProvenance(
                model_id=decision.selected_model.model_id if decision.selected_model else "local-vision-ocr",
                model_version=decision.selected_model.model_version if decision.selected_model else "1.0.0",
                model_file_hash=decision.selected_model.sha256_checksum if decision.selected_model else "sha256-unassigned",
                quantization="N/A",
                runtime_engine="LocalVisionOCREngine",
                runtime_profile="OCR",
                context_length=0,
                temperature=0.0,
                seed=42,
            )

            return AIExecutionEnvelope(
                task_id=request.task_id,
                task_type=TaskType.VISION_OCR,
                status="SUCCESS",
                result=result_data,
                raw_content=raw_text,
                grounding_score=0.95,
                provenance=provenance,
                latency_seconds=round(time.perf_counter() - t_global_start, 4),
            )
        except Exception as e:
            trace.status = "FAILED"
            trace.error_message = str(e)
            traces.append(trace)
            return self._build_error_envelope(
                request=request,
                error_msg=f"Vision/OCR execution failed: {str(e)}",
                status="FAILED",
                traces=traces,
                latency=round(time.perf_counter() - t_global_start, 4),
            )

    async def _execute_generative_plan(
        self,
        request: TaskRequest,
        plan: ExecutionPlan,
        decision: TaskRoutingDecision,
        traces: List[ExecutionStageTrace],
        t_global_start: float,
        req_sig: str,
    ) -> AIExecutionEnvelope[Any]:
        """Executes generative SLM pipelines (Reasoning, Grounded, Structured, Tools)."""
        # 1. Acquire Model via Lifecycle
        trace_acquire = ExecutionStageTrace(stage_name=PipelineStageEnum.ACQUIRE_MODEL)
        t_acq_start = time.perf_counter()
        if decision.selected_model:
            try:
                from ai.registry.models import ModelTaskTypeEnum
                await self.lifecycle_manager.load_model(
                    model_id=decision.selected_model.model_id,
                    task_type=ModelTaskTypeEnum.GENERATION,
                )
            except Exception:
                pass
            # Also load native inference engine if needed
            if not await self.inference_engine.is_ready():
                try:
                    await self.inference_engine.load_model(decision.selected_model.model_id)
                except Exception:
                    pass

        trace_acquire.latency_seconds = round(time.perf_counter() - t_acq_start, 4)
        trace_acquire.completed_at = datetime.now(timezone.utc).isoformat()
        traces.append(trace_acquire)

        # 2. Evidence Grounding (if grounded)
        grounding_score: Optional[float] = None
        evidence_citations: List[Dict[str, Any]] = []
        grounding_status = "NOT_EVALUATED"

        if PipelineStageEnum.EVIDENCE_EVALUATION in plan.required_stages:
            trace_eval = ExecutionStageTrace(stage_name=PipelineStageEnum.EVIDENCE_EVALUATION)
            t_eval_start = time.perf_counter()
            chunks = request.retrieved_chunks or []
            if chunks:
                claim_text = request.prompt or ""
                from ai.retrieval.hybrid_engine import RetrievedDocument
                retrieved_docs: List[RetrievedDocument] = []
                for idx, c in enumerate(chunks):
                    doc_id = str(c.get("doc_id") or c.get("id") or c.get("chunk_id") or f"doc_{idx}")
                    entity_id = str(c.get("entity_id") or c.get("code_or_number") or doc_id)
                    r_val = c.get("rerank_score") if c.get("rerank_score") is not None else c.get("score", 0.9)
                    r_score = float(r_val) if r_val is not None else 0.9
                    s_val = c.get("score", 0.9)
                    s_score = float(s_val) if s_val is not None else 0.9
                    retrieved_docs.append(
                        RetrievedDocument(
                            id=doc_id,
                            entity_type=str(c.get("source_type") or c.get("entity_type") or "ECN"),
                            entity_id=entity_id,
                            text=str(c.get("text") or c.get("content") or ""),
                            matched_strategy=str(c.get("matched_strategy") or "HYBRID_FUSION"),
                            score=s_score,
                            initial_rank=idx + 1,
                            rerank_score=r_score,
                            part_number=c.get("part_number"),
                            model_code=c.get("model_code"),
                            metadata=c.get("metadata") or c,
                        )
                    )
                eval_res = self.evidence_evaluator.evaluate_grounding_and_decision(
                    query_text=claim_text,
                    retrieved_docs=retrieved_docs,
                )
                grounding_score = eval_res.grounding_score
                grounding_status = eval_res.decision.value
                evidence_citations = [
                    {
                        "doc_id": item.evidence_id,
                        "evidence_id": item.evidence_id,
                        "source_type": item.source_type,
                        "code_or_number": item.code_or_number,
                        "snippet": item.snippet,
                        "grounding_contribution": item.dim8_grounding_contribution,
                        "classification": item.classification.value,
                    }
                    for item in eval_res.classified_evidences
                ]
                trace_eval.metadata = {
                    "grounding_score": grounding_score,
                    "status": grounding_status,
                    "citations": len(evidence_citations),
                }
            else:
                grounding_status = "INSUFFICIENT_EVIDENCE"
                trace_eval.metadata = {"status": "INSUFFICIENT_EVIDENCE", "citations": 0}

            trace_eval.latency_seconds = round(time.perf_counter() - t_eval_start, 4)
            trace_eval.completed_at = datetime.now(timezone.utc).isoformat()
            traces.append(trace_eval)

            # Strict Grounding Policy: If grounding required and evidence is insufficient, mark degraded
            if plan.grounding_required and (not chunks or grounding_status in {"NO_IMPLEMENTATION_EVIDENCE_FOUND", "INSUFFICIENT_EVIDENCE", "CONTRADICTED"}):
                provenance = self._create_provenance(decision, plan)
                return AIExecutionEnvelope[str](
                    task_id=request.task_id,
                    task_type=request.task_type,
                    status="INSUFFICIENT_EVIDENCE",
                    result="Evidence grounding failed: No verified implementation records support the requested premise.",
                    raw_content="INSUFFICIENT_EVIDENCE: Grounding required but retrieved evidence was insufficient or contradictory.",
                    grounding_score=grounding_score or 0.0,
                    evidence_citations=evidence_citations,
                    latency_seconds=round(time.perf_counter() - t_global_start, 4),
                    provenance=provenance,
                )

        # 3. Context Budgeting
        trace_ctx = ExecutionStageTrace(stage_name=PipelineStageEnum.CONTEXT_BUILD)
        t_ctx_start = time.perf_counter()
        raw_prompt = request.prompt or ""
        system_prompt = request.system_prompt or "You are an expert automotive cost engineering AI assistant."
        
        reranked_results: List[RerankResult] = []
        if request.retrieved_chunks:
            for idx, chunk in enumerate(request.retrieved_chunks):
                chk_r_val = chunk.get("rerank_score") if chunk.get("rerank_score") is not None else chunk.get("score", 0.85)
                chk_r_score = float(chk_r_val) if chk_r_val is not None else 0.85
                chk_s_val = chunk.get("score", 0.8)
                chk_s_score = float(chk_s_val) if chk_s_val is not None else 0.8
                reranked_results.append(
                    RerankResult(
                        id=str(chunk.get("id", f"chunk_{idx}")),
                        text=str(chunk.get("text", chunk.get("content", ""))),
                        initial_score=chk_s_score,
                        initial_rank=idx + 1,
                        rerank_score=chk_r_score,
                        final_rank=idx + 1,
                        matched_strategy=str(chunk.get("matched_strategy", "HYBRID")),
                        metadata=chunk.get("metadata", {}),
                    )
                )

        manifest = None
        if decision.selected_model:
            manifest = self.router.registry.get_model(decision.selected_model.model_id)

        if reranked_results:
            context_res = self.context_manager.build_context(
                query=raw_prompt,
                reranked_results=reranked_results,
                system_prompt=system_prompt,
                override_context_limit=plan.context_limit,
            )
            final_prompt = context_res.assembled_prompt
            total_tokens = context_res.total_used_tokens
            truncated = (context_res.overflow_status.value == "OVERFLOW_REDUCED")
        else:
            final_prompt = raw_prompt
            total_tokens, _ = self.context_manager.budgeter.count_tokens(raw_prompt)
            truncated = False

        trace_ctx.latency_seconds = round(time.perf_counter() - t_ctx_start, 4)
        trace_ctx.completed_at = datetime.now(timezone.utc).isoformat()
        trace_ctx.metadata = {"total_tokens": total_tokens, "truncated": truncated}
        traces.append(trace_ctx)

        # 4. Generation / Structured Output / Tool Loop
        provenance = self._create_provenance(decision, plan)

        # Case 4A: Structured Output Request
        if request.schema_model is not None or request.task_type == TaskType.STRUCTURED_EXTRACTION:
            trace_gen = ExecutionStageTrace(stage_name=PipelineStageEnum.STRUCTURED_VALIDATION)
            t_gen_start = time.perf_counter()
            schema = request.schema_model or ToolCallOutputSchema
            struct_res = await self.structured_engine.generate_structured(
                prompt=final_prompt,
                response_model=schema,
                temperature=plan.temperature,
                seed=plan.seed,
                timeout_seconds=plan.timeout_seconds,
            )
            trace_gen.latency_seconds = round(time.perf_counter() - t_gen_start, 4)
            trace_gen.completed_at = datetime.now(timezone.utc).isoformat()
            traces.append(trace_gen)

            result_payload = struct_res.result
            struct_env = AIExecutionEnvelope[Any](
                task_id=request.task_id,
                task_type=request.task_type,
                status="SUCCESS" if struct_res.result is not None else "VALIDATION_FAILED",
                result=result_payload,
                raw_content=struct_res.raw_response,
                grounding_score=grounding_score,
                evidence_citations=evidence_citations,
                latency_seconds=round(time.perf_counter() - t_global_start, 4),
                provenance=provenance,
                metadata={"validation_errors": struct_res.validation_errors, "parsed_json": struct_res.parsed_json},
            )
            self._idempotency_cache[req_sig] = struct_env
            return struct_env

        # Case 4B: Tool Execution Loop
        if request.allow_tool_calls or request.task_type == TaskType.TOOL_CALL:
            return await self._execute_tool_loop(
                request=request,
                plan=plan,
                decision=decision,
                final_prompt=final_prompt,
                provenance=provenance,
                grounding_score=grounding_score,
                evidence_citations=evidence_citations,
                traces=traces,
                t_global_start=t_global_start,
                req_sig=req_sig,
            )

        # Case 4C: Standard Text Generation (Reasoning / Grounded Reasoning)
        trace_gen = ExecutionStageTrace(stage_name=PipelineStageEnum.GENERATION)
        t_gen_start = time.perf_counter()
        if decision.provider_type in ("OLLAMA", "LM_STUDIO", "OPENAI_COMPATIBLE"):
            from ai.providers.registry import provider_registry
            adapter = provider_registry.get_adapter(decision.provider_type)
            if adapter and hasattr(adapter, "generate_text"):
                raw_text = await adapter.generate_text(
                    prompt=final_prompt,
                    model_id=plan.model_id or "default",
                    max_tokens=plan.max_tokens,
                    temperature=plan.temperature,
                    timeout_seconds=plan.timeout_seconds,
                )
            else:
                raw_text = await self.inference_engine.generate_text(
                    prompt=final_prompt,
                    max_tokens=plan.max_tokens,
                    temperature=plan.temperature,
                    timeout_seconds=plan.timeout_seconds,
                )
        else:
            raw_text = await self.inference_engine.generate_text(
                prompt=final_prompt,
                max_tokens=plan.max_tokens,
                temperature=plan.temperature,
                timeout_seconds=plan.timeout_seconds,
            )
        trace_gen.latency_seconds = round(time.perf_counter() - t_gen_start, 4)
        trace_gen.completed_at = datetime.now(timezone.utc).isoformat()
        trace_gen.metadata = {"generated_chars": len(raw_text)}
        traces.append(trace_gen)

        envelope = AIExecutionEnvelope[str](
            task_id=request.task_id,
            task_type=request.task_type,
            status="SUCCESS",
            result=raw_text,
            raw_content=raw_text,
            grounding_score=grounding_score,
            evidence_citations=evidence_citations,
            latency_seconds=round(time.perf_counter() - t_global_start, 4),
            provenance=provenance,
            usage={"prompt_tokens": total_tokens, "completion_chars": len(raw_text)},
            metadata={
                "requested_provider": decision.requested_provider,
                "actual_provider": decision.actual_provider,
                "fallback_occurred": decision.fallback_occurred,
                "fallback_reason": decision.fallback_reason,
            },
        )
        self._idempotency_cache[req_sig] = envelope
        return envelope

    async def _execute_tool_loop(
        self,
        request: TaskRequest,
        plan: ExecutionPlan,
        decision: TaskRoutingDecision,
        final_prompt: str,
        provenance: ModelProvenance,
        grounding_score: Optional[float],
        evidence_citations: List[Dict[str, Any]],
        traces: List[ExecutionStageTrace],
        t_global_start: float,
        req_sig: str,
    ) -> AIExecutionEnvelope[Any]:
        """Bounded multi-step tool proposal and execution loop."""
        trace_tool = ExecutionStageTrace(stage_name=PipelineStageEnum.TOOL_PIPELINE)
        t_tool_start = time.perf_counter()
        tool_results: List[Dict[str, Any]] = []

        # 1. Propose Tool Call via Structured Engine
        tool_proposal_res = await self.structured_engine.generate_structured(
            prompt=f"{final_prompt}\n\nPropose a relevant sandboxed tool invocation for this query.",
            response_model=ToolCallOutputSchema,
            temperature=0.0,
            seed=plan.seed,
            timeout_seconds=plan.timeout_seconds,
        )

        proposal: Optional[ToolCallOutputSchema] = tool_proposal_res.result
        if proposal and proposal.tool_name:
            # 2. Execute tool through AI-11 ToolRegistry
            tool_req = ToolExecutionRequest(
                task_id=request.task_id,
                tool_name=proposal.tool_name,
                arguments=proposal.arguments,
                caller_identity=request.caller_identity,
                intent_description=proposal.intent_description,
                dry_run=request.dry_run,
            )
            tool_res = await self.tool_registry.execute_tool_secure(tool_req)
            tool_results.append(tool_res.model_dump())

            # 3. Feed tool output back to final generation
            tool_context = f"\n\n[TOOL RESULT: {proposal.tool_name}]\n{json.dumps(tool_res.data or tool_res.error_message)}"
            final_gen_prompt = f"{final_prompt}{tool_context}\n\nProvide the final grounded answer."
            final_text = await self.inference_engine.generate_text(
                prompt=final_gen_prompt,
                max_tokens=plan.max_tokens,
                temperature=0.0,
                timeout_seconds=plan.timeout_seconds,
            )
        else:
            final_text = await self.inference_engine.generate_text(
                prompt=final_prompt,
                max_tokens=plan.max_tokens,
                temperature=0.0,
                timeout_seconds=plan.timeout_seconds,
            )

        trace_tool.latency_seconds = round(time.perf_counter() - t_tool_start, 4)
        trace_tool.completed_at = datetime.now(timezone.utc).isoformat()
        trace_tool.metadata = {"tool_calls_executed": len(tool_results)}
        traces.append(trace_tool)

        envelope = AIExecutionEnvelope[Dict[str, Any]](
            task_id=request.task_id,
            task_type=TaskType.TOOL_CALL,
            status="SUCCESS",
            result={"final_answer": final_text, "tool_executions": tool_results},
            raw_content=final_text,
            grounding_score=grounding_score,
            evidence_citations=evidence_citations,
            latency_seconds=round(time.perf_counter() - t_global_start, 4),
            provenance=provenance,
            metadata={
                "tool_calls": tool_results,
                "requested_provider": decision.requested_provider,
                "actual_provider": decision.actual_provider,
                "fallback_occurred": decision.fallback_occurred,
                "fallback_reason": decision.fallback_reason,
            },
        )
        self._idempotency_cache[req_sig] = envelope
        return envelope

    async def stream_task(self, request: TaskRequest) -> AsyncIterator[str]:
        """
        Streams token generation for a reasoning or grounded task.
        """
        decision = self.router.resolve_routing(request)
        if not decision.is_routed:
            yield f"[ERROR: {decision.explanation}]"
            return

        messages = request.messages or [{"role": "user", "content": request.prompt or ""}]
        if decision.provider_type in ("OLLAMA", "LM_STUDIO", "OPENAI_COMPATIBLE"):
            from ai.providers.registry import provider_registry
            adapter = provider_registry.get_adapter(decision.provider_type)
            if adapter and hasattr(adapter, "stream_chat"):
                async for token in adapter.stream_chat(
                    messages=messages,
                    model_id=decision.selected_model.model_id if decision.selected_model else "default",
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    timeout_seconds=request.timeout_seconds,
                ):
                    yield token
                return

        if decision.selected_model:
            try:
                from ai.registry.models import ModelTaskTypeEnum
                await self.lifecycle_manager.load_model(
                    model_id=decision.selected_model.model_id,
                    task_type=ModelTaskTypeEnum.GENERATION,
                )
            except Exception:
                pass

        if not await self.inference_engine.is_ready():
            try:
                if decision.selected_model:
                    await self.inference_engine.load_model(decision.selected_model.model_id)
            except Exception:
                pass

        async for token in self.inference_engine.stream_chat(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            timeout_seconds=request.timeout_seconds,
        ):
            yield token

    def cancel_task(self) -> None:
        """Propagates cancellation to active generation and runtime lifecycle."""
        self.inference_engine.cancel_current_generation()

    def _create_provenance(
        self,
        decision: TaskRoutingDecision,
        plan: ExecutionPlan,
        prompt_version: str = "v1.0",
    ) -> ModelProvenance:
        """Constructs canonical ModelProvenance for execution auditing."""
        model = decision.selected_model
        return ModelProvenance(
            model_id=plan.model_id,
            model_version=plan.model_version,
            model_file_hash=model.sha256_checksum if model else "sha256-unassigned",
            quantization=model.quantization if model else "Q4_K_M",
            runtime_engine="llama.cpp",
            runtime_profile=plan.runtime_profile,
            context_length=model.recommended_context_length if model else 4096,
            temperature=plan.temperature,
            seed=plan.seed,
            prompt_template_version=prompt_version,
        )

    def _build_error_envelope(
        self,
        request: TaskRequest,
        error_msg: str,
        status: str,
        traces: List[ExecutionStageTrace],
        latency: float,
    ) -> AIExecutionEnvelope[str]:
        """Constructs standard error envelope."""
        provenance = ModelProvenance(
            model_id=request.model_id_override or "unrouted",
            model_version="0.0.0",
            model_file_hash="sha256-none",
            quantization="NONE",
            runtime_engine="llama.cpp",
            runtime_profile="NONE",
            context_length=0,
            temperature=request.temperature,
            seed=request.seed,
        )
        return AIExecutionEnvelope[str](
            task_id=request.task_id,
            task_type=request.task_type,
            status=status,
            result=error_msg,
            raw_content=error_msg,
            latency_seconds=latency,
            provenance=provenance,
        )
