# 08 — Revised Master Implementation Plan V2

## 1. Executive Summary & Evolution from Plan V1
Revised Master Implementation Plan V2 represents the hardened, defensible execution plan for the **Hero Vehicle Cost & Plant OPEX Intelligence Platform**. It incorporates all findings from the Red-Team Critique (`04_RED_TEAM_CRITIQUE.md`), FMEA & Bottlenecks (`05_FAILURE_AND_BOTTLENECK_ANALYSIS.md`), and Simplification Review (`06_SIMPLIFICATION_REVIEW.md`).

---

## 2. Key Plan Changes: V1 to V2 Evolution

| Area | Plan V1 Decision | Red-Team Critique / Flaw | Revised Plan V2 Change | Architectural Rationale & Benefit |
|---|---|---|---|---|
| **Retrieval Architecture** | Separated Vector Indexing (Phase 5) from Hybrid Search (Phase 6). | Vector search alone fails on exact 10-digit part numbers; separate phases delayed exact search validation. | **Merged into Phase 5: Unified Hybrid Retrieval & Cross-Encoder Reranking.** | Guarantees exact identifier recall and semantic discovery simultaneously from the very first search test. |
| **Local AI Runtime** | Deferred full Local AI Runtime to Phase 14 (late in sequence). | Risked late-stage C++ binding, compilation, or VRAM offload surprises on client host hardware. | **Promoted Track B (Local AI Runtime) to run in parallel from Day 1.** | Ensures `LlamaCppEngine` is stabilized, benchmarked, and proven before business workflows integrate with it. |
| **Data Ingestion** | Standard schema parsing without statistical magnitude checks. | Allowed dirty inputs with wrong units (Lakhs vs Rupees) to corrupt OPEX math. | **Added Mandatory Unit Normalization Guard & Magnitude Sanity Checks in Phase 2.** | Prevents 100,000x calculation skew before data ever reaches database tables. |
| **Security & Egress** | Security hardening placed at the final phase (Phase 16). | External network calls or telemetry could inadvertently be introduced by third-party packages early. | **Container-Level Air-Gap Isolation Enforced in Phase 0.** | Guarantees zero cloud leakage and zero telemetry throughout the entire development lifecycle. |
| **Ideathon State Machine** | Ideas without BOM costs stalled pipeline. | Over 40% of early-stage employee ideas lack BOM part costs. | **Added `UNQUANTIFIED_OPPORTUNITY` Non-Blocking Pipeline State in Phase 4.** | Allows technical screening, duplicate clustering, and implementation checks to proceed while cost data is investigated. |

---

## 3. Revised Dual-Track Implementation Architecture

```text
===================================================================================================
TRACK A: BUSINESS PLATFORM WORKSTREAM
===================================================================================================
Phase 0: Environment & Foundation Architecture
   |
Phase 1: Relational Master Data & Vehicle Hierarchy Schema
   |
Phase 2: Robust Ingestion, Unit Normalization & Validation Pipeline
   |
   +---------------------------------------+---------------------------------------+
   |                                                                               |
   v                                                                               v
Phase 3: Plant OPEX & Benchmarking Engine       Phase 4: Ideathon Core & Entity Normalization
(Deterministic KPIs, Gap, Opportunity)         (Taxonomy, Hierarchy Mapping, Clustering)
   |                                               |
   |                                            Phase 5: Unified Hybrid Retrieval & Reranking
   |                                            (pgvector + Trigram Exact + Cross-Encoder)
   |                                               |
   |                                            Phase 6: Existing Implementation Engine
   |                                            (Portfolio Applicability Matrix, ECN Match)
   |                                               |
   |                                            Phase 7: Deterministic Cost Engine
   |                                            (BOM Savings, Volume, Investment, ROI)
   |                                               |
   +---------------------------------------+-------+
                                           |
                                           v
Phase 8: Evidence-Grounded SLM Decisioning & Tool Policy   <--- [Feeds from Track B Engine]
   |
Phase 9: Evidence Confidence & Escalation Router
   |
Phase 10: Human-in-the-Loop Review & Governance Queue
   |
Phase 11: Gold Dataset Evaluation & Metrics Benchmark
   |
Phase 12: Executive UI & High-Density Dashboards
   |
Phase 13: Security Hardening & Air-Gap Compliance

===================================================================================================
TRACK B: LOCAL AI RUNTIME WORKSTREAM (Parallel Infrastructure Track)
===================================================================================================
Track B.0: AI Provider Protocols & Inference Interfaces (Runs with Phase 0)
Track B.1: Dev Ollama Provider Adapter (For rapid Phase 4-5 test fixtures)
Track B.2: Internal LlamaCppEngine Implementation (Direct GGUF, CUDA/CPU offload)
Track B.3: Local Model Registry, Validation & Checksum Verification
Track B.4: GBNF Grammar & JSON Schema Constrained Decoding
Track B.5: Sandboxed Tool Registry & Policy Enforcement Engine
Track B.6: Internal AI Studio & VRAM Hardware Monitor (Integrated in Phase 8)
```

---

## 4. Phase-by-Phase Technical Specifications (Plan V2)

### Phase 0: Environment, Scaffolding & Air-Gap Baseline
- **Phase ID**: `PHASE-00`
- **Objective**: Initialize repository, Docker environment, database migrations, security baseline, and core interface abstractions.
- **Business Value**: Guarantees zero external network dependencies, strict type safety, and reproducibility.
- **Technical Scope**:
  - FastAPI application scaffolding, configuration management via Pydantic settings.
  - PostgreSQL 16 + `pgvector` container with persistent local volume storage.
  - Alembic database migration harness.
  - Air-gap baseline: Docker container network isolation (`internal: true`), zero external telemetry flags.
  - Base protocol abstractions: `AIProvider`, `InferenceEngine`, `EmbeddingProvider`, `RerankerProvider`, `CalculationEngine`.
- **Context Files Required**: `00_CONTEXT_INDEX.md`, `02_SYSTEM_ARCHITECTURE.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`, `10_ANTIGRAVITY_EXECUTION_RULES.md`.
- **Dependencies**: None.
- **Parallel Work**: Track B.0 (AI Interface protocols), Frontend scaffolding.
- **Deliverables**: Docker environment, base test harness, passing container health checks.
- **Testing**: DB connectivity tests, air-gap packet sniffing test, migration dry-run tests.
- **Exit Criteria**: `docker compose up` initializes DB and API with zero external internet traffic.
- **Risks**: Developer workstation OS disparities.
- **Mitigation**: Standardized containerized runtime with pinned dependency lockfiles.
- **Decision Gate**: `Architecture & Security Baseline Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 1: Relational Master Data & Vehicle Hierarchy Schema
- **Phase ID**: `PHASE-01`
- **Objective**: Create the authoritative relational database schema for vehicle hierarchies, plant masters, components, parts, BOM, costs, and audit logs.
- **Business Value**: Establishes the indestructible structured source of truth for all enterprise assets and historical records.
- **Technical Scope**:
  - Vehicle Hierarchy: `PRODUCT_FAMILY` -> `VEHICLE` -> `VEHICLE_MODEL` -> `VEHICLE_VARIANT` -> `MODEL_GENERATION` -> `MODEL_YEAR`.
  - Component Hierarchy: `SUBSYSTEM` -> `ASSEMBLY` -> `COMPONENT` -> `PART` -> `MATERIAL` -> `SUPPLIER`.
  - Business Masters: `PLANT`, `PRODUCTION_RECORD`, `BOM_RECORD`, `COMPONENT_COST`, `PROJECT`, `ENGINEERING_CHANGE`, `IMPLEMENTATION`.
  - Governance: `AUDIT_LOG`, `USER`, `ROLE`.
  - Recursive CTE helper views for rapid vehicle-part tree traversal.
- **Context Files Required**: `02_SYSTEM_ARCHITECTURE.md`, `03_DATA_MODEL_AND_OPEX.md`.
- **Dependencies**: `PHASE-00`.
- **Parallel Work**: Track B.1 (Dev adapter), Synthetic data generator.
- **Deliverables**: Alembic DDL migrations, SQLAlchemy / SQLModel ORM models, synthetic master seed dataset (5 vehicle families, 8 plants, 25 models, 150 parts).
- **Testing**: Schema constraint tests, foreign key cascade tests, recursive CTE traversal performance tests (< 10ms).
- **Exit Criteria**: 100% schema migrations pass; seed data loaded and verified.
- **Risks**: Schema rigidity impeding future business attributes.
- **Mitigation**: Strategic use of typed JSONB columns for flexible custom metadata.
- **Decision Gate**: `Data Foundation Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 2: Ingestion Pipeline & Unit Normalization Guard
- **Phase ID**: `PHASE-02`
- **Objective**: Build a fault-tolerant Excel / CSV ingestion pipeline with automated schema detection, unit normalization, and data validation.
- **Business Value**: Protects system calculations from dirty data, wrong units, and corrupted spreadsheets.
- **Technical Scope**:
  - Secure multipart file upload with streaming parser (`calamine` / `openpyxl`).
  - Automated column matching with fuzzy alias dictionary.
  - Deterministic Unit Normalization Guard (kWh, MWh, KL, Litres, ₹, Lakhs, Crores).
  - Outlier magnitude sanity checks (e.g. ₹/vehicle bounded between ₹500 and ₹10,000).
  - Transactional commit with automated staging file purge upon success.
- **Context Files Required**: `03_DATA_MODEL_AND_OPEX.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-01`.
- **Parallel Work**: Phase 3 (OPEX logic), Phase 4 (Ideathon normalization).
- **Deliverables**: `DataIngestionService`, `UnitConversionGuard`, validation report API.
- **Testing**: Unit conversion tests, dirty data injection tests, corrupted Excel recovery tests.
- **Exit Criteria**: Successful ingestion of dirty multi-plant spreadsheets with 0% data corruption; full audit logs.
- **Risks**: Non-standard user spreadsheets with merged cells or missing headers.
- **Mitigation**: Pre-flight validation endpoint returning interactive column reconciliation prompts.
- **Decision Gate**: `Ingestion Reliability Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 3: Plant OPEX & Expenditure Benchmarking Engine
- **Phase ID**: `PHASE-03`
- **Objective**: Build the deterministic calculation and benchmarking engine for multi-plant operational expenditures.
- **Business Value**: Delivers exact, auditable cost-gap quantification and savings opportunities for plant operations.
- **Technical Scope**:
  - Deterministic KPI engine: kWh/veh, KL/veh, ₹ electricity/veh, ₹ water/veh, ₹ gas/veh, ₹ compressed air/veh, maintenance/veh, manpower/veh, total OPEX/veh, controllable OPEX/veh.
  - Multi-benchmark support: Best comparable plant, peer group average, historical baseline, management target.
  - Normalization weighting: Production volume, operating days, shifts, capacity utilization, power tariffs.
  - Variance decomposition: Volume variance vs Rate variance vs Efficiency gap.
  - Annual opportunity quantification ($Opportunity = Gap \times Production\ Volume$).
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `03_DATA_MODEL_AND_OPEX.md`.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 4 (Ideathon core).
- **Deliverables**: `PlantOpexService`, `CalculationEngine.opex`, OPEX summary APIs.
- **Testing**: Exact mathematical verification against pre-calculated Excel master models; zero floating-point error.
- **Exit Criteria**: 100% mathematical precision across all plant benchmark scenarios.
- **Risks**: Skewed comparison between plants with dissimilar manufacturing scopes.
- **Mitigation**: Peer group tagging and capacity/mix comparability weighting factors.
- **Decision Gate**: `OPEX Engine Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 4: Ideathon Core & Vehicle Hierarchy Mapping
- **Phase ID**: `PHASE-04`
- **Objective**: Implement idea ingestion, raw text preservation, entity extraction, canonical normalization, and decision state machine.
- **Business Value**: Normalizes 10,000+ unstandardized employee ideas into structured product improvement records.
- **Technical Scope**:
  - Tables: `IDEA`, `IDEA_CLUSTER`, `IDEA_EVALUATION`.
  - Raw submission preservation with normalized problem/solution decomposition.
  - Regex & dictionary entity extractor for part numbers, model names, and assemblies.
  - Decision state machine (`INVALID`, `DUPLICATE`, `ALREADY_IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `POTENTIAL_OPPORTUNITY`, `UNQUANTIFIED_OPPORTUNITY`, `SAFETY_HOLD`).
  - BOM vs Non-BOM deterministic classification.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 5 (Retrieval engine).
- **Deliverables**: `IdeathonService`, entity normalization engine, idea management APIs.
- **Testing**: Entity extraction precision tests, state machine transition tests, raw text immutability checks.
- **Exit Criteria**: Ingestion and structuring of 1,000+ synthetic ideas with correct hierarchy linkage.
- **Risks**: Colloquial or ambiguous employee terminology.
- **Mitigation**: Controlled product synonym dictionary and automated canonical concept mapping.
- **Decision Gate**: `Ideathon Core Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 5: Unified Hybrid Retrieval & Cross-Encoder Reranking
- **Phase ID**: `PHASE-05`
- **Objective**: Implement multi-tier hybrid search combining exact part/ECN matching, pgvector semantic search, and local cross-encoder reranking.
- **Business Value**: Eliminates both semantic false negatives (differing words) and keyword misses (part numbers).
- **Technical Scope**:
  - Exact & Trigram fuzzy matching via PostgreSQL `pg_trgm` for part numbers, ECNs, and project IDs.
  - Dense vector embedding pipeline via `EmbeddingProvider` (Qwen3-Embedding / FastEmbed) into `pgvector` HNSW indexes.
  - Partitioned vector tables with strict metadata filtering (subsystem, vehicle family, model year).
  - Reciprocal Rank Fusion (RRF) combining exact and vector search scores.
  - Local cross-encoder reranking (`RerankerProvider`) for top-25 candidate pool.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`.
- **Dependencies**: `PHASE-04`.
- **Parallel Work**: Track B.2 / B.3 (LlamaCppEngine).
- **Deliverables**: `HybridRetrievalService`, `RerankerService`, unified multi-modal search endpoint.
- **Testing**: 100% recall test on exact 10-digit part numbers; Recall@K on semantic query variations; reranker latency benchmark (< 150ms).
- **Exit Criteria**: Combined Recall@5 > 92% on test query set; sub-200ms hybrid search response time.
- **Risks**: Vector drift on model updates.
- **Mitigation**: Model version tagging on vector rows with automated reindexing scripts.
- **Decision Gate**: `Hybrid Retrieval Gate`.
- **Expected Effort**: 5 Days.
- **Can Be Deferred?**: No.

---

### Phase 6: Existing Implementation & Portfolio Applicability Engine
- **Phase ID**: `PHASE-06`
- **Objective**: Detect existing implementations across historical projects, ECNs, and BOM records; construct model/variant applicability matrix.
- **Business Value**: Directly solves the "Missed Implementation" problem, preventing duplicate engineering expenditure.
- **Technical Scope**:
  - Multi-tier implementation discovery: Part -> Assembly -> Subsystem -> Hybrid project search.
  - Temporal validity engine: `valid_from`, `valid_to`, active model year verification (current vs historical).
  - Dynamic Portfolio Applicability Matrix:
    - Model X (Implemented) | Model Y (Open Opportunity) | Variant Z (Partial Implementation).
  - Identification of cross-model standardization opportunities.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-04`, `PHASE-05`.
- **Parallel Work**: Phase 7 (Cost engine).
- **Deliverables**: `ImplementationDiscoveryService`, `ApplicabilityMatrixBuilder`, implementation inspection APIs.
- **Testing**: Benchmark suite of historical implemented ideas; variant-specific implementation test cases.
- **Exit Criteria**: Zero false "new" decisions on test benchmark of known implemented engineering changes.
- **Risks**: Discrepancy between CAD/PLM release dates and physical plant adoption.
- **Mitigation**: Ingest and verify against active BOM and plant production effective dates.
- **Decision Gate**: `Implementation Intelligence Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: No.

---

### Phase 7: Deterministic Vehicle Cost Opportunity Engine
- **Phase ID**: `PHASE-07`
- **Objective**: Implement pure mathematical calculation of vehicle cost savings, annual opportunity, and net ROI.
- **Business Value**: Delivers verified financial savings figures for executive investment decisions with zero AI hallucination.
- **Technical Scope**:
  - Pure Python deterministic calculation engine:
    - $Saving/Vehicle = Current\ Cost - Proposed\ Cost$
    - $Gross\ Annual\ Opportunity = Saving/Vehicle \times Applicable\ Annual\ Production\ Volume$
    - $Net\ Opportunity = Gross\ Opportunity - Implementation\ Investment\ (Tooling + Validation)$
    - $Payback\ Period\ (Years) = Total\ Investment / Gross\ Annual\ Opportunity$
  - Explicit handling of data gaps: Flag `MISSING_BOM_COST` or `UNQUANTIFIED` without blocking screening.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `04_IDEATHON_ENGINE.md`.
- **Dependencies**: `PHASE-01`, `PHASE-06`.
- **Parallel Work**: Phase 8 (SLM integration).
- **Deliverables**: `CalculationEngine.vehicle_cost`, cost valuation services, financial audit recorder.
- **Testing**: Deterministic mathematical unit tests, edge cases (zero volume, negative delta, zero tooling).
- **Exit Criteria**: 100% exact mathematical match against reference spreadsheets; zero LLM arithmetic.
- **Risks**: Unrealistic volume projections.
- **Mitigation**: Pull approved annual volume figures directly from authoritative `PRODUCTION_RECORD` table.
- **Decision Gate**: `Cost Engine Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 8: Evidence-Grounded SLM Decisioning & Local AI Gateway
- **Phase ID**: `PHASE-08`
- **Objective**: Integrate local reasoning SLM (Qwen3.5-9B GGUF via `LlamaCppEngine`) to synthesize retrieved evidence, explain decisions, and output typed Pydantic schemas.
- **Business Value**: Delivers human-readable rationales, evidence summaries, and automated classification assistance.
- **Technical Scope**:
  - `LocalAiGateway` routing via `AIProvider` and `LlamaCppEngine`.
  - Prompt construction with strict in-context evidence grounding and lost-in-the-middle safeguards.
  - Constrained JSON decoding via GBNF grammars / Pydantic v2 schemas.
  - Controlled Tool Registry: `search_ideas()`, `search_implementations()`, `search_bom()`, `get_component_cost()`, `check_safety_gate()`.
  - Bounded tool execution: `max_iterations = 4`, timeout = 10s, sandboxed execution.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `06_LOCAL_AI_RUNTIME.md`.
- **Dependencies**: `PHASE-05`, `PHASE-06`, `PHASE-07`, `TRACK-B`.
- **Parallel Work**: Phase 9 (Confidence engine).
- **Deliverables**: `AiOrchestratorService`, `LocalAiGateway`, structured decision synthesis endpoints.
- **Testing**: JSON schema compliance tests, prompt injection resilience, citation verification tests.
- **Exit Criteria**: 100% schema-compliant JSON output; zero ungrounded part number or cost hallucinations.
- **Risks**: Inference latency on complex prompts.
- **Mitigation**: Quantized Q4_K_M GGUF model with 100% layers offloaded to 24GB GPU VRAM.
- **Decision Gate**: `Local AI Decision Gate`.
- **Expected Effort**: 5 Days.
- **Can Be Deferred?**: No.

---

### Phase 9: Evidence Confidence & Escalation Router
- **Phase ID**: `PHASE-09`
- **Objective**: Derive objective evidence-grounded confidence scores (`HIGH`, `MEDIUM`, `LOW`) and route uncertain or conflicting cases to humans.
- **Business Value**: Establishes executive credibility by making uncertainty transparent and escalating edge cases.
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
  - Confidence Routing: `HIGH` (Auto-advance), `MEDIUM` (Standard review queue), `LOW` / `CONFLICT` (Escalate to engineering investigation).
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-08`.
- **Parallel Work**: Phase 10 (Review UI).
- **Deliverables**: `ConfidenceEngine`, escalation router, audit trail recorder.
- **Testing**: Conflicting evidence detection tests, edge case validation, routing rule verification.
- **Exit Criteria**: 100% of conflicting or low-evidence records correctly flagged for mandatory human review.
- **Risks**: Over-escalation causing reviewer fatigue.
- **Mitigation**: Calibrated factor weighting based on historical labeled data.
- **Decision Gate**: `Evidence Confidence Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 10: Human-in-the-Loop Review & Engineering Gate Queue
- **Phase ID**: `PHASE-10`
- **Objective**: Build governance workflows, decision capture, and audit trails for engineering, quality, and safety stakeholders.
- **Business Value**: Enforces regulatory compliance and keeps human experts in ultimate control.
- **Technical Scope**:
  - Review queue management with multi-criteria filtering (confidence, savings, subsystem, vehicle).
  - Decision capture: `ACCEPT`, `REJECT`, `OVERRIDE`, `REQUEST_ENGINEERING_REVIEW`, `SAFETY_HOLD`.
  - Reviewer notes, override justification capture, and immutable audit logging.
  - Non-bypassable safety gates: Automated flags for critical components (brakes, steering, suspension, frame).
- **Context Files Required**: `04_IDEATHON_ENGINE.md`, `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-09`.
- **Parallel Work**: Phase 12 (Frontend UI).
- **Deliverables**: `ReviewWorkflowService`, review queue APIs, decision audit logger.
- **Testing**: Workflow transition tests, audit log immutability verification, safety flag enforcement.
- **Exit Criteria**: Complete end-to-end review lifecycle with full provenance logging.
- **Risks**: Review backlog on large submission batches.
- **Mitigation**: Batch review and bulk disposition for verified duplicate clusters.
- **Decision Gate**: `Human Governance Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 11: Gold Dataset Evaluation & Benchmark Framework
- **Phase ID**: `PHASE-11`
- **Objective**: Implement continuous evaluation harness against a curated Hero Gold Dataset to measure accuracy and error rates.
- **Business Value**: Delivers quantifiable proof of system accuracy and business value for POC sign-off.
- **Technical Scope**:
  - Evaluation harness measuring:
    - Classification Precision, Recall, F1.
    - Duplicate Detection Recall@K and Precision.
    - **Missed Implementation Rate** (Target: < 2.0%).
    - Model / Variant Mapping Accuracy.
    - Deterministic Calculation Error Rate (Target: 0.00%).
    - Human Agreement Rate.
    - Inference latency and throughput.
  - Automated evaluation reporting and regression tracking.
- **Context Files Required**: `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md`, `09_POC_ACCEPTANCE_AND_EVALUATION.md`.
- **Dependencies**: `PHASE-08`, `PHASE-09`.
- **Parallel Work**: Phase 12 (Frontend UI).
- **Deliverables**: `EvaluationHarness`, Gold Dataset loader, automated evaluation report generator.
- **Testing**: Synthetic gold dataset evaluation run, metric computation verification.
- **Exit Criteria**: Automated evaluation report generated with all metrics calculated against baseline.
- **Risks**: Overfitting prompts to a small test dataset.
- **Mitigation**: 70/30 train/test split on historical labeled ideas.
- **Decision Gate**: `POC Evaluation Gate`.
- **Expected Effort**: 3 Days.
- **Can Be Deferred?**: No.

---

### Phase 12: Executive UI, OPEX & Ideathon Dashboards
- **Phase ID**: `PHASE-12`
- **Objective**: Build a high-density, responsive, industrial enterprise web application in React / Vite.
- **Business Value**: Delivers the executive and operational user experience that wows stakeholders and accelerates decision-making.
- **Technical Scope**:
  - Executive Overview: Portfolio savings summary, top plant opportunities, Ideathon pipeline funnel.
  - OPEX Module: Interactive peer benchmark charts, variance waterfall, plant comparison matrices.
  - Ideathon Module: Cluster visualizer, duplicate inspector, implementation matrix table, idea detail panel.
  - Evidence & Audit Inspector: Full transparency panel with clickable source links, calculation proofs, and confidence badges.
  - Review Queue: Actionable decision drawer (Accept/Reject/Override) with note capture.
  - Ingestion UI: Drag-and-drop Excel/CSV upload with live validation feedback and error breakdown.
  - Internal AI Studio: Technical admin view for model status, hardware VRAM monitor, latency metrics.
- **Context Files Required**: `01_BUSINESS_VISION_AND_REQUIREMENTS.md`, `10_ANTIGRAVITY_EXECUTION_RULES.md`, `11_CLIENT_POC_WORKFLOW.md`.
- **Dependencies**: `PHASE-03`, `PHASE-06`, `PHASE-07`, `PHASE-10`.
- **Parallel Work**: Phase 13 (Security hardening).
- **Deliverables**: Complete React/Vite SPA bundle, responsive design system, component test suite.
- **Testing**: End-to-end browser user flows, responsive layout tests, accessibility and contrast checks.
- **Exit Criteria**: All 7 client demo scenarios executable in UI smoothly without layout errors or latency lag.
- **Risks**: UI performance degradation when rendering large idea tables.
- **Mitigation**: Virtualized tables (`tanstack-virtual`) and server-side pagination.
- **Decision Gate**: `Executive UI Gate`.
- **Expected Effort**: 6 Days.
- **Can Be Deferred?**: No.

---

### Phase 13: Security Hardening & Air-Gap Compliance
- **Phase ID**: `PHASE-13`
- **Objective**: Harden the complete application for air-gapped on-premise enterprise deployment.
- **Business Value**: Ensures compliance with Hero IT / InfoSec standards, zero data leakage, and system resilience.
- **Technical Scope**:
  - Network isolation: Block all outbound HTTP/HTTPS egress at container and network levels; zero telemetry verification.
  - Security controls: JWT authentication, role-based authorization guards on all API endpoints.
  - Local storage & secrets: Encrypted environment variables, secure local file permissions (`0600`).
  - Penetration testing: SQL injection prevention (parameterized ORM), path traversal defense on upload/model paths.
  - Backup & recovery scripts: Automated PostgreSQL dump and restore verification.
- **Context Files Required**: `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md`.
- **Dependencies**: `PHASE-11`, `PHASE-12`.
- **Parallel Work**: POC acceptance documentation.
- **Deliverables**: Hardened Docker deployment bundle, security audit checklist, air-gap verification script.
- **Testing**: Egress packet capture tests, security vulnerability scans, RBAC permission tests.
- **Exit Criteria**: Zero external network packets detected during full system execution; all security gates pass.
- **Risks**: Undiscovered external dependency in a third-party npm or pip package.
- **Mitigation**: Pinned offline dependency mirrors and strict firewall egress DROP rules.
- **Decision Gate**: `Production Readiness Gate`.
- **Expected Effort**: 4 Days.
- **Can Be Deferred?**: Core security is built from Phase 0; hardening completes the POC envelope.
