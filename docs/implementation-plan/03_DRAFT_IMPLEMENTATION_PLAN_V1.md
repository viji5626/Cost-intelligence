# 03 — Draft Implementation Plan V1

## 1. Executive Summary
This document presents the first-pass (V1) phased implementation plan for the **Hero Vehicle Cost & Plant OPEX Intelligence Platform**. It establishes a logical sequence from foundational data modeling to executive UI delivery, integrating both the Plant OPEX engine and the Vehicle Ideathon intelligence engine.

---

## 2. Phase-by-Phase Implementation Specifications

### Phase 0: Architecture, Tooling & Environment Initialization
- **Phase ID**: `PHASE-00`
- **Objective**: Establish the repository infrastructure, development standards, Docker containers, database migrations framework, and core interface abstractions.
- **Business Value**: Guarantees architectural integrity, security baselines, and development reproducibility across teams.
- **Technical Scope**:
  - FastAPI application scaffolding and dependency configuration.
  - PostgreSQL 16 + pgvector container configuration.
  - Database migration harness (Alembic).
  - Pydantic v2 domain schemas and `AIProvider` / `InferenceEngine` abstractions.
  - Centralized logging, error handling, and test fixtures.
- **Context Files Required**: `00_CONTEXT_INDEX.md`, `02_SYSTEM_ARCHITECTURE.md`, `10_ANTIGRAVITY_EXECUTION_RULES.md`.
- **Dependencies**: None.
- **Parallel Work**: Frontend scaffolding, initial UI design tokens.
- **Deliverables**: Working Docker Compose environment, passing baseline test suite, interface protocol definitions.
- **Testing**: Container health checks, database connectivity unit tests, configuration validation tests.
- **Exit Criteria**: `docker compose up` starts API and DB with clean migrations; baseline tests pass at 100%.
- **Risks**: Environment inconsistencies across developer workstations.
- **Mitigation**: Pinned dependency versions in lockfiles and deterministic Docker recipes.
- **Decision Gate**: `Architecture & Environment Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No (Hard Foundation).

---

### Phase 1: Relational Data Foundation & Master Entities
- **Phase ID**: `PHASE-01`
- **Objective**: Implement the authoritative relational schema for vehicle hierarchies, plant master data, components, parts, BOM, costs, and audit logs.
- **Business Value**: Creates the single source of truth for all enterprise assets and historical engineering records.
- **Technical Scope**:
  - Tables: `PLANT`, `PRODUCT_FAMILY`, `VEHICLE`, `VEHICLE_MODEL`, `VEHICLE_VARIANT`, `MODEL_GENERATION`, `MODEL_YEAR`.
  - Tables: `SUBSYSTEM`, `ASSEMBLY`, `COMPONENT`, `PART`, `MATERIAL`, `SUPPLIER`.
  - Tables: `BOM_RECORD`, `COMPONENT_COST`, `PRODUCTION_RECORD`, `PROJECT`, `ENGINEERING_CHANGE`, `IMPLEMENTATION`.
  - Tables: `AUDIT_LOG`, `USER`, `ROLE`.
  - Foreign key constraints, cascade rules, and B-Tree indexes for all natural keys (part numbers, model codes).
- **Context Files Required**: `02_SYSTEM_ARCHITECTURE.md`, `03_DATA_MODEL_AND_OPEX.md`.
- **Dependencies**: `PHASE-00`.
- **Parallel Work**: Track B (AI Runtime interfaces).
- **Deliverables**: Migration scripts, SQLAlchemy / SQLModel ORM models, synthetic seed script with 5 vehicle families and 8 plants.
- **Testing**: Schema constraint tests, foreign key integrity tests, seed data verification tests.
- **Exit Criteria**: All relational tables created with verified indices; seed data loads without error.
- **Risks**: Over-normalization leading to complex joins.
- **Mitigation**: Strategic denormalization of frequently searched codes (e.g. `part_number` in implementation records).
- **Decision Gate**: `Data Foundation Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 2: Ingestion & Validation Pipeline (Excel / CSV)
- **Phase ID**: `PHASE-02`
- **Objective**: Build a robust, failure-resistant ingestion pipeline for plant operational data and Ideathon spreadsheets.
- **Business Value**: Eliminates manual data entry errors, validates formats, and enforces data quality before business processing.
- **Technical Scope**:
  - Multi-part file upload with temporary staging in local workspace.
  - Automated schema detection, column mapping, and datatype validation.
  - Business rules validation: missing values, duplicate rows, invalid model references, cost range sanity checks.
  - Deterministic unit normalization (kWh, KL, ₹).
  - Transactional insertion: rollback on critical errors; quarantine invalid rows with detailed error reports.
  - Secure cleanup: temporary source file deletion only after verified database commit.
- **Context Files Required**: `03_DATA_MODEL_AND_OPEX.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-01`.
- **Parallel Work**: Phase 3 (OPEX calculation logic).
- **Deliverables**: `DataIngestionService`, validation rules engine, ingestion report API.
- **Testing**: Malformed file tests, dirty data tests (missing columns, bad units), transactional rollback tests.
- **Exit Criteria**: Successful ingestion and validation of representative dirty Excel files; 100% audit logging.
- **Risks**: Malformed Excel formats and inconsistent headers from different plant sources.
- **Mitigation**: Dynamic header alias mapping and interactive column reconciliation API.
- **Decision Gate**: `Ingestion Reliability Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 3: Plant OPEX & Expenditure Benchmarking Engine
- **Phase ID**: `PHASE-03`
- **Objective**: Build the deterministic calculation and benchmarking engine for multi-plant operational expenditures.
- **Business Value**: Provides plant heads and leadership with exact, auditable cost-gap analysis and savings opportunities.
- **Technical Scope**:
  - Deterministic KPI calculation engine: kWh/veh, KL/veh, ₹ electricity/veh, ₹ water/veh, ₹ gas/veh, ₹ compressed air/veh, maintenance/veh, manpower/veh, total OPEX/veh, controllable OPEX/veh.
  - Benchmarking logic: Best comparable plant, peer group average, historical baseline, management target.
  - Normalization adjustments: production volume, shift patterns, operating days, capacity utilization.
  - Variance decomposition: Volume variance vs. Rate variance vs. Efficiency gap.
  - Opportunity quantification ($Annual\ Opportunity = Gap \times Projected\ Volume$).
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `03_DATA_MODEL_AND_OPEX.md`.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 4 (Ideathon core).
- **Deliverables**: `PlantOpexService`, `CalculationEngine.opex`, OPEX summary APIs.
- **Testing**: Mathematical unit tests against pre-calculated Excel benchmarks, edge case tests (zero production, leap year).
- **Exit Criteria**: 100% mathematical accuracy on test cases; zero floating-point rounding errors in currency outputs.
- **Risks**: Comparing non-comparable plants (e.g. EV assembly vs. foundry).
- **Mitigation**: Explicit peer group tags and capacity/mix comparability weighting factors.
- **Decision Gate**: `OPEX Engine Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 4: Ideathon Core & Vehicle Hierarchy Mapping
- **Phase ID**: `PHASE-04`
- **Objective**: Implement the data ingestion, text preservation, entity extraction, and classification engine for 10,000+ ideas.
- **Business Value**: Transforms unstructured idea submissions into structured, queryable product-improvement candidates.
- **Technical Scope**:
  - Tables: `IDEA`, `IDEA_CLUSTER`, `IDEA_EVALUATION`.
  - Raw submission text preservation alongside normalized fields (problem, proposed solution).
  - Rule-based & regex entity extraction (part numbers, vehicle models, assemblies).
  - Decision taxonomy enum implementation (`INVALID`, `DUPLICATE`, `ALREADY_IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, etc.).
  - Deterministic BOM vs. Non-BOM classification.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `03_DATA_MODEL_AND_OPEX.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 5 (Vector indexing).
- **Deliverables**: `IdeathonService`, entity normalization engine, idea management APIs.
- **Testing**: Entity extraction precision tests, taxonomy state machine tests, text preservation verification.
- **Exit Criteria**: Ingestion of 1,000+ synthetic ideas with correct entity linkage and taxonomy validation.
- **Risks**: Unstandardized colloquial terminology in raw submissions.
- **Mitigation**: Controlled vocabulary mapping table and synonym normalization dictionary.
- **Decision Gate**: `Ideathon Core Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 5: Semantic Retrieval & Vector Indexing (pgvector)
- **Phase ID**: `PHASE-05`
- **Objective**: Implement vector embeddings and similarity search for ideas, historical projects, and engineering notes.
- **Business Value**: Enables finding semantically similar ideas regardless of differing keyword terminology.
- **Technical Scope**:
  - Embedding pipeline using `EmbeddingProvider` interface (local Qwen3-Embedding / FastEmbed candidate).
  - Vector storage in PostgreSQL using `pgvector` with HNSW cosine distance indexing.
  - Partitioned vector tables for ideas, project summaries, and technical documents.
  - Metadata filtering by vehicle family, subsystem, and submission year.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`.
- **Dependencies**: `PHASE-04`.
- **Parallel Work**: Track B (Local AI Runtime).
- **Deliverables**: `VectorSearchService`, embedding batch generator, similarity query APIs.
- **Testing**: Vector Recall@K benchmarks, index generation speed tests, metadata filter validation.
- **Exit Criteria**: Sub-50ms vector query latency for 10,000 embeddings with metadata filtering.
- **Risks**: Embedding drift when model versions change.
- **Mitigation**: Store embedding model identifier and version metadata on every vector record; versioned reindexing script.
- **Decision Gate**: `Vector Retrieval Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 6: Hybrid Search & Cross-Encoder Reranking
- **Phase ID**: `PHASE-06`
- **Objective**: Combine exact keyword/trigram search with vector similarity and apply cross-encoder reranking.
- **Business Value**: Guarantees exact part number recall while eliminating irrelevant semantic false positives.
- **Technical Scope**:
  - Exact & Trigram fuzzy matching via PostgreSQL `pg_trgm` for part numbers, ECNs, and model codes.
  - Reciprocal Rank Fusion (RRF) / weighted score fusion combining exact and vector search scores.
  - Local cross-encoder reranking pipeline using `RerankerProvider` interface.
  - Context truncation and deduplication filter.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`.
- **Dependencies**: `PHASE-05`.
- **Parallel Work**: Phase 7 (Implementation intelligence).
- **Deliverables**: `HybridSearchService`, `RerankerService`, unified search API.
- **Testing**: Exact identifier recall tests (part numbers, ECNs), comparative Recall@K before/after reranking.
- **Exit Criteria**: 100% recall on exact part numbers; top-5 candidate precision improvement > 30% via reranker.
- **Risks**: High latency added by cross-encoder on large candidate sets.
- **Mitigation**: Restrict reranking to top-25 candidate pool; use lightweight 0.6B reranker model.
- **Decision Gate**: `Hybrid Search Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 7: Existing Implementation & Portfolio Applicability Engine
- **Phase ID**: `PHASE-07`
- **Objective**: Detect if an idea's solution is already implemented across Hero's product portfolio and build the model applicability matrix.
- **Business Value**: Directly solves the "Missed Implementation" problem, preventing redundant engineering spend.
- **Technical Scope**:
  - Implementation matching across historical projects, ECN/ECR records, and active BOM components.
  - Temporal validation: `valid_from`, `valid_to`, model year, generation verification (historical vs. current).
  - Applicability matrix builder: Model X (Implemented) vs. Model Y (Not Implemented) vs. Variant Z (Partial).
  - Cross-model applicability gap identification.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-04`, `PHASE-06`.
- **Parallel Work**: Phase 8 (Cost calculation).
- **Deliverables**: `ImplementationDiscoveryService`, `ApplicabilityMatrixBuilder`, implementation inspection APIs.
- **Testing**: Test against known historical implemented ideas, variant-specific implementation test cases.
- **Exit Criteria**: Correct identification of implementation status and model matrix on 100% of benchmark test cases.
- **Risks**: Different terminology used in historical ECN records vs. raw idea submissions.
- **Mitigation**: Multi-tier search: match on part numbers, then component hierarchy, then hybrid semantic description.
- **Decision Gate**: `Implementation Intelligence Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 8: Deterministic Vehicle Cost Opportunity Engine
- **Phase ID**: `PHASE-08`
- **Objective**: Implement pure mathematical calculation of vehicle cost savings, annual opportunity, and net ROI.
- **Business Value**: Provides CFO and engineering leaders with defensible, auditable financial figures.
- **Technical Scope**:
  - Deterministic calculations:
    - $Saving\ per\ Vehicle = Current\ Component\ Cost - Proposed\ Cost$
    - $Gross\ Annual\ Opportunity = Saving\ per\ Vehicle \times Applicable\ Production\ Volume$
    - $Net\ Opportunity = Gross\ Opportunity - Implementation\ Investment\ (Tooling + Validation)$
    - $Payback\ Period\ (Years) = Total\ Investment / Gross\ Annual\ Opportunity$
  - Handling of missing data: explicit `MISSING_BOM_COST` or `UNQUANTIFIED` flags (zero AI arithmetic).
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-01`, `PHASE-07`.
- **Parallel Work**: Track B / Phase 9 (Local AI Gateway).
- **Deliverables**: `CalculationEngine.vehicle_cost`, cost valuation services, financial audit log.
- **Testing**: Deterministic mathematical unit tests, edge case tests (zero volume, negative savings, null tooling).
- **Exit Criteria**: Exact match against reference spreadsheets; absolute zero reliance on LLM for calculations.
- **Risks**: Incomplete BOM cost data in early submissions.
- **Mitigation**: Output structured `DATA_GAP` flag with exact missing fields clearly identified.
- **Decision Gate**: `Cost Engine Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 9: Local SLM Integration & Structured Decisioning
- **Phase ID**: `PHASE-09`
- **Objective**: Integrate local reasoning SLM (Qwen-class GGUF) to synthesize retrieved evidence, explain decisions, and output typed Pydantic schemas.
- **Business Value**: Delivers human-readable rationales, evidence summaries, and automated classification assistance.
- **Technical Scope**:
  - `LocalAiGateway` routing via `AIProvider` interface.
  - Prompt construction with strict in-context evidence grounding and lost-in-the-middle safeguards.
  - Typed structured JSON output enforcement (JSON Schema / GBNF grammar).
  - Decision synthesis: Taxonomy classification, problem/solution summary, risk flags.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `06_LOCAL_AI_RUNTIME.md`.
- **Dependencies**: `PHASE-06`, `PHASE-07`, `PHASE-08`.
- **Parallel Work**: Track B (llama-cpp engine hardening).
- **Deliverables**: `AiOrchestratorService`, structured prompt templates, decision synthesis endpoint.
- **Testing**: JSON schema compliance tests, prompt injection resilience, evidence grounding validation.
- **Exit Criteria**: 100% valid JSON schema output; zero hallucination of part numbers or costs outside provided context.
- **Risks**: SLM output formatting instability.
- **Mitigation**: GBNF grammar-based constrained decoding in local runtime; Pydantic retry/repair wrapper.
- **Decision Gate**: `Local AI Decision Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 10: Agentic Retrieval & Controlled Tool Registry
- **Phase ID**: `PHASE-10`
- **Objective**: Implement bounded multi-step agentic retrieval for complex queries with an authorized tool registry.
- **Business Value**: Enables dynamic discovery across multiple enterprise databases for multi-faceted user investigations.
- **Technical Scope**:
  - Authorized tool registry: `search_ideas()`, `search_implementations()`, `search_bom()`, `get_component_cost()`, `get_production_volume()`, `check_safety_gate()`.
  - Tool policy engine: RBAC checks, parameter validation, rate limits, execution timeouts.
  - Bounded agent execution loop: `max_tool_calls = 4`, zero loop guarantee, graceful timeout handling.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `06_LOCAL_AI_RUNTIME.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-09`.
- **Parallel Work**: Phase 11 (Confidence engine).
- **Deliverables**: `AgenticRetrievalPlanner`, `ToolRegistry`, sandboxed tool execution engine.
- **Testing**: Tool policy enforcement tests, loop termination tests, malformed tool parameter handling.
- **Exit Criteria**: Agent resolves complex 3-step investigation queries within 15 seconds; zero unhandled tool crashes.
- **Risks**: Model enters recursive search loop on ambiguous queries.
- **Mitigation**: Hard iteration counter and deterministic circuit breaker.
- **Decision Gate**: `Agentic Tool Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: Optional for basic POC; recommended for interactive search.

---

### Phase 11: Evidence Confidence & Escalation Engine
- **Phase ID**: `PHASE-11`
- **Objective**: Derive evidence-grounded confidence scores (`HIGH`, `MEDIUM`, `LOW`) and route uncertain or conflicting cases to humans.
- **Business Value**: Builds executive trust by making certainty transparent and flagging edge cases for expert review.
- **Technical Scope**:
  - Deterministic Confidence Scoring Engine based on 8 objective factors:
    1. Exact entity / part number match.
    2. Exact vehicle / model / variant match.
    3. Freshness / current model year validation.
    4. Verified ECN / Project implementation record.
    5. Authoritative BOM cost availability.
    6. Multi-source evidence agreement.
    7. Semantic similarity score threshold.
    8. Source document provenance.
  - Confidence Routing: `HIGH` (Auto-advance to pipeline), `MEDIUM` (Flag for standard review), `LOW` / `CONFLICT` (Escalate to engineering investigation).
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-09`, `PHASE-10`.
- **Parallel Work**: Phase 12 (Review UI).
- **Deliverables**: `ConfidenceEngine`, escalation router, audit trail recorder.
- **Testing**: Factor weighting tests, conflicting record escalation tests, edge case validation.
- **Exit Criteria**: 100% of conflicting records flagged as `LOW/CONFLICT` with mandatory human review.
- **Risks**: Miscalibrated confidence weights causing false confidence.
- **Mitigation**: Conservative threshold tuning against historical human-labeled benchmarks.
- **Decision Gate**: `Evidence Confidence Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 12: Human-in-the-Loop Review & Engineering Gate Queue
- **Phase ID**: `PHASE-12`
- **Objective**: Build the review workflows, decision capture, and audit trails for engineering, quality, and safety stakeholders.
- **Business Value**: Enforces governance and ensures AI serves strictly as decision support, keeping humans in full control.
- **Technical Scope**:
  - Review queue management: Filter by category, confidence, estimated savings, vehicle family.
  - Decision capture: `ACCEPT`, `REJECT`, `OVERRIDE`, `REQUEST_ENGINEERING_REVIEW`, `SAFETY_HOLD`.
  - Reviewer notes, override justification capture, and immutable audit logging.
  - Safety & Quality gate flags: Non-bypassable warning triggers for critical components (brakes, steering, suspension, frame).
- **Context Files Required**: `04_IDEATHON_ENGINE.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-11`.
- **Parallel Work**: Phase 15 (Frontend UI).
- **Deliverables**: `ReviewWorkflowService`, review queue APIs, decision audit logger.
- **Testing**: Workflow transition tests, audit log immutability verification, safety flag enforcement.
- **Exit Criteria**: Complete end-to-end review lifecycle with full provenance logging.
- **Risks**: Review bottleneck if too many low-confidence ideas are queued.
- **Mitigation**: Batch review capabilities for verified duplicate clusters.
- **Decision Gate**: `Human Governance Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 13: Gold Dataset Evaluation & Benchmark Framework
- **Phase ID**: `PHASE-13`
- **Objective**: Implement continuous evaluation harness against a curated Hero Gold Dataset to measure accuracy and error rates.
- **Business Value**: Provides quantifiable evidence of system efficacy for POC sign-off.
- **Technical Scope**:
  - Evaluation harness measuring:
    - Classification Precision, Recall, F1.
    - Duplicate Detection Recall@K and Precision.
    - **Missed Implementation Rate** (False New / Actual Implemented).
    - Model / Variant Mapping Accuracy.
    - Deterministic Calculation Error Rate (Target: 0.00%).
    - Human Agreement Rate.
    - Inference latency and throughput.
  - Automated evaluation reporting and regression tracking.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `09_POC_ACCEPTANCE_AND_EVALUATION.md`.
- **Dependencies**: `PHASE-09`, `PHASE-11`.
- **Parallel Work**: Phase 14 / Track B (Runtime optimization).
- **Deliverables**: `EvaluationHarness`, Gold Dataset loader, automated evaluation report generator.
- **Testing**: Synthetic gold dataset evaluation run, metric computation verification.
- **Exit Criteria**: Automated evaluation report generated with all metrics calculated against baseline.
- **Risks**: Overfitting prompts to a small test dataset.
- **Mitigation**: 70/30 train/test split on historical labeled ideas.
- **Decision Gate**: `POC Evaluation Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 14: Internal Local AI Runtime & Gateway (Track B Hardening)
- **Phase ID**: `PHASE-14`
- **Objective**: Finalize the internal, self-contained Local AI Runtime using `llama-cpp-python` / GGUF, removing all external dependencies.
- **Business Value**: Guarantees on-premise air-gapped deployment capability with zero vendor lock-in to Ollama or cloud APIs.
- **Technical Scope**:
  - `LlamaCppEngine` implementation with full GGUF model lifecycle (load, unload, context reset).
  - Local Model Registry: Checksum validation, capability discovery (text, tool, grammar), quarantine folder.
  - Hardware resource manager: VRAM / RAM detection and dynamic GPU layer offloading (`n_gpu_layers`).
  - Internal AI Admin Studio: Model health, resource utilization, latency benchmarking.
- **Context Files Required**: `06_LOCAL_AI_RUNTIME.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: Track B foundation (`PHASE-00`).
- **Parallel Work**: Phase 15 (Frontend Polish).
- **Deliverables**: Standalone `LocalAiRuntime` package, Model Registry manager, AI Studio endpoints.
- **Testing**: GGUF loading tests, VRAM allocation tests, zero-network air-gap validation tests.
- **Exit Criteria**: Full business platform executes end-to-end against `LlamaCppEngine` with zero internet connection.
- **Risks**: C++ library compilation issues across diverse host OS environments.
- **Mitigation**: Pre-built wheel binaries inside standard Linux Docker containers with CUDA / CPU fallbacks.
- **Decision Gate**: `Local AI Independence Gate`.
- **Expected Effort**: 5 Days.
- **Can Be Deferred?**: Track B runs in parallel; must be completed before production deployment.

---

### Phase 15: Executive UI, OPEX & Ideathon Dashboards
- **Phase ID**: `PHASE-15`
- **Objective**: Build a high-density, responsive, industrial enterprise web application in React / Vite.
- **Business Value**: Delivers the executive and operational user experience that wows stakeholders and accelerates decision-making.
- **Technical Scope**:
  - Executive Overview: Portfolio savings summary, top plant opportunities, Ideathon pipeline funnel.
  - OPEX Module: Interactive peer benchmark charts, variance waterfall, plant comparison matrices.
  - Ideathon Module: Cluster visualizer, duplicate inspector, implementation matrix table, idea detail panel.
  - Evidence & Audit Inspector: Full transparency panel with clickable source links, calculation proofs, and confidence badges.
  - Review Queue: Actionable decision drawer (Accept/Reject/Override) with note capture.
  - Ingestion UI: Drag-and-drop Excel/CSV upload with live validation feedback and error breakdown.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `10_ANTIGRAVITY_EXECUTION_RULES.md`, `11_CLIENT_POC_WORKFLOW.md`.
- **Dependencies**: `PHASE-03`, `PHASE-07`, `PHASE-08`, `PHASE-12`.
- **Parallel Work**: Phase 16 (Security hardening).
- **Deliverables**: Complete React/Vite SPA bundle, responsive design system, component test suite.
- **Testing**: End-to-end browser user flows, responsive layout tests, accessibility and contrast checks.
- **Exit Criteria**: All 7 client demo scenarios executable in UI smoothly without layout errors or latency lag.
- **Risks**: UI performance degradation when rendering large idea tables.
- **Mitigation**: Virtualized tables (`tanstack-virtual`) and server-side pagination.
- **Decision Gate**: `Executive UI Gate`.
- **Expected Effort**: 6 Days.
- **Can Be Deferred?**: No.

---

### Phase 16: Security Hardening & Air-Gap Validation
- **Phase ID**: `PHASE-16`
- **Objective**: Harden the complete application for air-gapped on-premise enterprise deployment.
- **Business Value**: Ensures compliance with Hero IT / InfoSec standards, zero data leakage, and system resilience.
- **Technical Scope**:
  - Network isolation: Block all outbound HTTP/HTTPS egress at container and network levels; zero telemetry verification.
  - Security controls: JWT authentication, role-based authorization guards on all API endpoints.
  - Local storage & secrets: Encrypted environment variables, secure local file permissions (`0600`).
  - Penetration testing: SQL injection prevention (parameterized ORM), path traversal defense on upload/model paths.
  - Backup & recovery scripts: Automated PostgreSQL dump and restore verification.
- **Context Files Required**: `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-14`, `PHASE-15`.
- **Parallel Work**: POC acceptance documentation.
- **Deliverables**: Hardened Docker deployment bundle, security audit checklist, air-gap verification script.
- **Testing**: Egress packet capture tests, security vulnerability scans, RBAC permission tests.
- **Exit Criteria**: Zero external network packets detected during full system execution; all security gates pass.
- **Risks**: Undiscovered external dependency in a third-party npm or pip package.
- **Mitigation**: Pinned offline dependency mirrors and strict firewall egress DROP rules.
- **Decision Gate**: `Production Readiness Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: Core security is built from Phase 0; hardening completes the POC envelope.
