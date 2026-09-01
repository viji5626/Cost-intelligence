# 09 — Master Implementation Plan V3.1 (Resource-Hardened & TASC-Integrated Edition)

## 1. Executive Summary
Master Implementation Plan V3.1 is the production-ready, resource-hardened blueprint for the **Hero Vehicle Cost & Plant OPEX Intelligence Platform**. It builds upon V3 by:
1. **Grounding Hardware Architecture**: Explicitly engineering dynamic RAM, VRAM, and CPU resource management for the real-world POC development machine (**AMD Ryzen AI 9 HX 370, 16 GB System RAM, NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM**).
2. **Dynamic Multi-Model Resource Lifecycle**: Implementing hardware-aware model tiers (Tier 1: 3B/7B quantized with sequential on-demand swapping; Tier 2/3: 9B/14B with full GPU residency) to guarantee zero CUDA OOM crashes.
3. **Deep TASC IIoT Studio Asset Reuse**: Extracting and refactoring proven generic infrastructure modules (AI Provider protocols, `LlamaCppEngine` core, GBNF grammar engine, local RAG chunking, virtualized data grids, and AI Studio UI) from **TASC IIoT Studio V3** (https://github.com/viji5626/TASC_IIoT_Studio_V3), saving an indicative **~27–30 engineering days**.
4. **Preserving Core Truth Boundaries**: Retaining the separation between **Vehicle Ideathon Intelligence** and **Plant OPEX Benchmarking**, pure Python deterministic financial math, the **Evidence & Policy Layer**, **`BenchmarkMethodology`**, and **`SourceAuthorityPolicy`**.

---

## 2. Final System Architecture (V3.1)

```text
+---------------------------------------------------------------------------------------------------+
|                                      FRONTEND (React 18 + Vite)                                   |
|  - Executive Command Center  - Plant OPEX Dashboards        - Ideathon Review Queue               |
|  - Evidence & Audit Panel    - Ingestion & Validation UI    - Internal AI Studio (TASC Reused)    |
|  - Virtualized Data Grid Component (TASC Reused: 10k+ rows rendered fluidly < 16ms frame)         |
+---------------------------------------------------------------------------------------------------+
                                                  |  HTTPS / REST
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 APPLICATION GATEWAY & SECURITY                                    |
|  - JWT Authentication        - Role-Based Access Control    - Audit Logger & Redaction Engine     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
                         v                                                 v
+-------------------------------------------------+   +---------------------------------------------+
|             VEHICLE IDEATHON ENGINE             |   |              PLANT OPEX ENGINE              |
| - Idea Normalization & Extraction               |   | - Plant Operational Data Ingestion          |
| - Semantic Clustering & Deduplication           |   | - MagnitudeAnomalyGuard & Unit Conversion   |
| - Hierarchy Traversal (Family->Model->Part)     |   | - BenchmarkMethodology Domain Service       |
| - Multi-tier Implementation Search              |   | - Deterministic KPI Engine (kWh/veh, ₹/veh) |
| - Deterministic Cost Opportunity Engine         |   | - Variance Decomposition & Opportunity Calc |
+-------------------------------------------------+   +---------------------------------------------+
                         |                                                 |
                         +------------------------+------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                     EVIDENCE & POLICY LAYER                                       |
|  - Evidence Aggregation      - SourceAuthorityPolicy        - Multi-Source Conflict Detection     |
|  - Freshness & Completeness  - Deterministic Confidence     - Engineering & Safety Gate Policy    |
+---------------------------------------------------------------------------------------------------+
                               |                                                 |
                               v                                                 v
+-------------------------------------------------+   +---------------------------------------------+
|                   DATA LAYER                    |   |         INTERNAL LOCAL AI RUNTIME           |
|                                                 |   |                                             |
| [PostgreSQL 16 + pgvector]                      |   | [Hardware-Aware Resource Manager]           |
| - Relational Master Data (Vehicles, Plants, BOM)|   | - System RAM Budgeter (Max 8GB for AI)      |
| - Recursive CTE Tree Views                      |   | - VRAM Offload Manager (8GB Profile Safe)   |
| - Trigram & Exact Identifier Indexes            |   | - Dynamic Sequential Model Swapper          |
| - Dense Vector Indexes (HNSW Cosine Distance)   |   |                                             |
|                                                 |   | [Inference Engine (TASC Refactored)]        |
| [Local Document Store]                          |   | - LlamaCppEngine (Qwen GGUF Direct Native)  |
| - Encrypted Local Storage with Auto-Purge       |   | - GBNF Grammar Engine (TASC Reused)         |
+-------------------------------------------------+   +---------------------------------------------+
```

---

## 3. Hardware Resource Sizing & Memory Management

### 3.1 16 GB System RAM Allocation Profile
To guarantee that the host OS (Windows 11), PostgreSQL database, and backend web workers never experience memory starvation or disk swapping on a 16 GB RAM development machine:
- **Host OS & Background Headroom**: 4.0 GB.
- **PostgreSQL 16 Database**: 1.5 GB (`shared_buffers = 512MB`, `work_mem = 64MB`).
- **FastAPI Backend & Ingestion Engine**: 2.0 GB.
- **Local Browser / Frontend Tab**: 1.5 GB.
- **Host Safety Margin**: 1.0 GB.
- **Max Safe RAM Budget for AI Runtime / KV Cache**: **~6.0 GB – 8.0 GB**.

### 3.2 Dynamic VRAM Profiling & Model Tiers

```text
+---------------------------------------------------------------------------------------------------+
|                                  HARDWARE-AWARE MODEL RESOURCE TIERS                              |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| TIER   | HARDWARE PROFILE      | CANDIDATE REASONING SLM     | CONTEXT WINDOW  | VRAM STRATEGY    |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 1 | 16GB RAM / 8GB VRAM   | Qwen2.5-3B (Q4_K_M, ~2.2GB) | 2,048 – 4,096   | Sequential Model |
| (Entry)| *(POC Laptop Profile)*| Qwen2.5-7B (Q3_K_M, ~3.8GB) | tokens          | Swapping (Safe)  |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 2 | 32GB RAM / 16GB VRAM  | Qwen2.5-7B (Q4_K_M, ~4.8GB) | 4,096 – 8,192   | Full GPU Offload |
| (Work) |                       | Qwen3.5-9B (Q4_K_M, ~5.5GB) | tokens          | Concurrent Models|
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 3 | 64GB+ RAM / 24GB+ VRAM| Qwen2.5-14B (Q4_K_M, ~8.5GB)| 8,192 – 16,384  | Full GPU Offload |
| (Server)|                      | Qwen3.5-9B (Q8_0, ~10.0GB)  | tokens          | High Concurrency |
+--------+-----------------------+-----------------------------+-----------------+------------------+
```

### 3.3 Sequential Multi-Model Lifecycle (8 GB VRAM Mode)
When running on the 8 GB VRAM laptop GPU, models are loaded and released sequentially to avoid exceeding available memory:
1. **Embedding Phase**: Load `Qwen3-Embedding-0.6B` (~1.1 GB VRAM) $\rightarrow$ vectorize text batches $\rightarrow$ unload.
2. **Hybrid Reranking Phase**: Load `Qwen3-Reranker-0.6B` (~1.2 GB VRAM) $\rightarrow$ re-score top-25 candidates $\rightarrow$ unload.
3. **SLM Synthesis Phase**: Load `Qwen2.5-7B` / `Qwen2.5-3B` (~2.2–3.8 GB VRAM) $\rightarrow$ execute GBNF constrained structured generation $\rightarrow$ output verified JSON. Model stays resident during interactive sessions with a 10-minute idle release timer.

### 3.4 CPU Core Pinning
On the AMD Ryzen AI 9 HX 370 (12 cores / 24 threads):
- **AI Inference (`llama-cpp`)**: `n_threads = 6` (pinned to Zen 5 performance cores).
- **PostgreSQL & Background Tasks**: 2 Cores.
- **FastAPI / Uvicorn Server**: 2 Cores.
- **Ingestion & Data Parsing**: 2 Cores.

---

## 4. TASC IIoT Studio V3 Code-Level Reuse Strategy

```text
                                  +---------------------------------------+
                                  |         TASC IIoT Studio V3           |
                                  |   (Proven Engineering Asset)          |
                                  +---------------------------------------+
                                                      |
                                                      v
                             +-------------------------------------------------+
                             |          SELECTIVE EXTRACTION & REFACTORING     |
                             +-------------------------------------------------+
                             |                                                 |
            +----------------+----------------+---------------+----------------+
            |                                 |               |                |
            v                                 v               v                v
+-----------------------+ +-----------------------+ +---------------+ +---------------+
|     REUSE AS-IS       | |   REFACTOR & REUSE    | |    REBUILD    | |  DO NOT USE   |
| - AIProvider Protocol | | - LlamaCppEngine Core | | - Ideathon    | | - PLC Drivers |
| - GBNF Grammar Engine | | - Local RAG Pipeline  | |   Engine      | | - MQTT Broker |
| - Virtual Data Grid UI| | - AI Studio Admin UI  | | - OPEX KPI &  | | - SCADA Alarm |
|                       | | - Ingestion Staging   | |   Benchmark   | |   Historian   |
+-----------------------+ +-----------------------+ +---------------+ +---------------+
```

### 4.1 Reused TASC Modules & Target Integration
1. **`ai/providers/base.py`** $\leftarrow$ Reused As-Is from TASC `ai_engine/provider/base.py` (Protocol definitions for chat, structured output, and embeddings).
2. **`ai/runtime/llama_cpp_engine.py`** $\leftarrow$ Refactored from TASC `ai_engine/llama_cpp/engine.py` (Added Hardware Profiler, dynamic VRAM offloading, and idle release timer).
3. **`ai/grammar/gbnf_compiler.py`** $\leftarrow$ Reused As-Is from TASC `ai_engine/grammar/compiler.py` (Compiles Pydantic schemas into GBNF grammars).
4. **`retrieval/rag/chunker.py`** $\leftarrow$ Refactored from TASC `ai_engine/rag/chunker.py` (Adapted for engineering ECNs and BOM tables).
5. **`frontend/src/modules/ai-studio/`** $\leftarrow$ Refactored from TASC `frontend/studio/` (Rebranded with Hero industrial dark theme for hardware/model monitoring).
6. **`frontend/src/components/common/VirtualGrid.tsx`** $\leftarrow$ Reused As-Is from TASC `frontend/grid/` (Renders 10k+ rows fluidly).

*Total Indicative Development Effort Saved: **~27–30 Engineering Days (To be validated during implementation).***

---

## 5. Master Implementation Phases (V3.1)

```text
===================================================================================================
TRACK A: BUSINESS PLATFORM WORKSTREAM
===================================================================================================
Phase 0: Environment, Scaffolding & Air-Gap Baseline (GATE-00)
Phase 1: Relational Master Data & Vehicle Hierarchy Schema (GATE-01)
Phase 2: Ingestion Pipeline & MagnitudeAnomalyGuard (GATE-02)
Phase 3: Plant OPEX & BenchmarkMethodology Engine (GATE-03)
Phase 4: Ideathon Core, Normalization & Hierarchy Mapping (GATE-04)
Phase 5: Unified Hybrid Retrieval & Cross-Encoder Reranking (GATE-05)
Phase 6: Implementation Discovery & Applicability Engine (GATE-06)
Phase 7: Deterministic Vehicle Cost Opportunity Engine (GATE-07)
Phase 8: Evidence & Policy Layer Integration (GATE-08)
Phase 9: Local SLM Decisioning & Local AI Gateway (GATE-09)
Phase 10: Human-in-the-Loop Review & Engineering Gate Queue (GATE-10)
Phase 11: Gold Dataset Evaluation & Benchmark Framework (GATE-11)
Phase 12: Executive UI, OPEX & Ideathon Dashboards (GATE-12)
Phase 13: Security Hardening & Air-Gap Compliance (GATE-13)

===================================================================================================
TRACK B: LOCAL AI RUNTIME WORKSTREAM (Parallel Infrastructure Track Reusing TASC Assets)
===================================================================================================
Track B.0: AI Provider Protocols & Interface Drop-in (Reused As-Is from TASC)
Track B.1: Dev Ollama Provider Adapter (For early test fixtures)
Track B.2: Internal LlamaCppEngine Implementation (Refactored from TASC with VRAM profiler)
Track B.3: Dynamic Hardware Profiler & Multi-Model Memory Swapper (8GB Profile Safe)
Track B.4: GBNF Grammar & JSON Schema Constrained Decoding (Reused As-Is from TASC)
Track B.5: Sandboxed Tool Registry & Policy Enforcement Engine (Refactored from TASC)
Track B.6: Internal AI Studio Admin UI (Reused & Rebranded from TASC)
```

---

## 6. Phase-by-Phase Technical Specifications (Plan V3.1)

### Phase 0: Environment, Scaffolding & Air-Gap Baseline
- **Phase ID**: `PHASE-00`
- **Objective**: Scaffolding, Docker configuration, database migrations, security baseline, and core interface protocol drop-ins from TASC.
- **Business Value**: Guarantees zero external network dependencies, strict type safety, and reproducibility.
- **Technical Scope**:
  - FastAPI modular monolith scaffolding, configuration management via Pydantic settings.
  - PostgreSQL 16 + `pgvector` container with persistent local volume storage.
  - Alembic database migration harness.
  - Air-gap baseline: Docker container network isolation (`internal: true`), zero external telemetry flags.
  - Drop-in `AIProvider` and `InferenceEngine` base protocols from TASC asset library.
- **Dependencies**: None.
- **Parallel Work**: Track B.0, Frontend scaffolding.
- **Deliverables**: Working Docker Compose environment, baseline test suite, interface protocol definitions.
- **Testing**: Container health checks, DB connectivity tests, air-gap packet capture validation.
- **Exit Criteria**: `docker compose up` starts cleanly with zero external internet traffic.
- **Decision Gate**: `GATE-00: Architecture & Baseline Gate`.
- **Expected Effort**: 3 Days.

---

### Phase 1: Relational Master Data & Vehicle Hierarchy Schema
- **Phase ID**: `PHASE-01`
- **Objective**: Create authoritative relational schema for vehicle hierarchies, plant masters, components, parts, BOM, costs, and audit logs.
- **Business Value**: Establishes the indestructible structured source of truth for all enterprise assets and historical records.
- **Technical Scope**:
  - Vehicle Hierarchy: `PRODUCT_FAMILY` $\rightarrow$ `VEHICLE` $\rightarrow$ `VEHICLE_MODEL` $\rightarrow$ `VEHICLE_VARIANT` $\rightarrow$ `MODEL_GENERATION` $\rightarrow$ `MODEL_YEAR`.
  - Component Hierarchy: `SUBSYSTEM` $\rightarrow$ `ASSEMBLY` $\rightarrow$ `COMPONENT` $\rightarrow$ `PART` $\rightarrow$ `MATERIAL` $\rightarrow$ `SUPPLIER`.
  - Business Masters: `PLANT`, `PRODUCTION_RECORD`, `BOM_RECORD`, `COMPONENT_COST`, `PROJECT`, `ENGINEERING_CHANGE`, `IMPLEMENTATION`.
  - Governance: `AUDIT_LOG`, `USER`, `ROLE`, `EVIDENCE_RECORD`.
  - Recursive CTE helper views for rapid vehicle-part tree traversal (< 10ms).
- **Dependencies**: `PHASE-00`.
- **Parallel Work**: Track B.1 (Dev adapter), Synthetic data generator.
- **Deliverables**: Alembic DDL migrations, SQLAlchemy models, synthetic master seed dataset (5 vehicle families, 8 plants, 25 models, 150 parts).
- **Testing**: Schema constraint tests, foreign key cascade tests, recursive CTE traversal tests.
- **Exit Criteria**: 100% schema migrations pass; seed data loaded and verified.
- **Decision Gate**: `GATE-01: Data Foundation Gate`.
- **Expected Effort**: 4 Days.

---

### Phase 2: Ingestion Pipeline & MagnitudeAnomalyGuard
- **Phase ID**: `PHASE-02`
- **Objective**: Build a fault-tolerant Excel/CSV ingestion pipeline with automated schema detection, unit normalization, and data validation (refactored from TASC staging module).
- **Business Value**: Protects calculations from dirty data, wrong units (Lakhs vs Rupees), and corrupted spreadsheets.
- **Technical Scope**:
  - Secure multipart file upload with streaming parser (`calamine` / `openpyxl`).
  - Automated column matching with fuzzy alias dictionary.
  - `MagnitudeAnomalyGuard`: Detects statistical magnitude anomalies and distinguishes `INVALID_DATA` from `UNUSUAL_VALID_DATA`.
  - Canonical Unit Conversion: kWh, MWh, KL, Litres, ₹, Lakhs, Crores.
  - Transactional commit with automated staging file purge upon success.
- **Dependencies**: `PHASE-01`.
- **Parallel Work**: Phase 3 (OPEX logic), Phase 4 (Ideathon normalization).
- **Deliverables**: `DataIngestionService`, `MagnitudeAnomalyGuard`, validation report API.
- **Testing**: Unit conversion tests, dirty data injection tests, corrupted Excel recovery tests.
- **Exit Criteria**: Successful ingestion of dirty multi-plant spreadsheets with 0% data corruption.
- **Decision Gate**: `GATE-02: Ingestion Reliability Gate`.
- **Expected Effort**: 4 Days (1 day saved via TASC staging module reuse).

---

### Phase 3: Plant OPEX & BenchmarkMethodology Engine
- **Phase ID**: `PHASE-03`
- **Objective**: Build the deterministic calculation and benchmarking engine for multi-plant operational expenditures.
- **Business Value**: Delivers exact, auditable cost-gap quantification and savings opportunities for plant operations.
- **Technical Scope**:
  - Deterministic KPI engine: kWh/veh, KL/veh, ₹ electricity/veh, ₹ water/veh, ₹ gas/veh, maintenance/veh, manpower/veh, total OPEX/veh, controllable OPEX/veh.
  - `BenchmarkMethodology` Domain Engine: Supports Best Comparable Plant, Peer Group Average, Historical Baseline, and Management Target modes.
  - Comparability Scoring: Multi-factor weighted index evaluating Manufacturing Scope, Production Volume, Mix, Operating Days, Shifts, Capacity, and Tariffs.
  - Variance Decomposition: Volume Variance vs Rate Variance vs Addressable Efficiency Gap.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 4 (Ideathon core).
- **Deliverables**: `PlantOpexService`, `BenchmarkMethodology`, `CalculationEngine.opex`, OPEX summary APIs.
- **Testing**: Exact mathematical verification against pre-calculated Excel master models; zero floating-point error.
- **Exit Criteria**: 100% mathematical precision across all plant benchmark scenarios.
- **Decision Gate**: `GATE-03: OPEX Engine Gate`.
- **Expected Effort**: 4 Days.

---

### Phase 4: Ideathon Core, Normalization & Hierarchy Mapping
- **Phase ID**: `PHASE-04`
- **Objective**: Implement idea ingestion, raw text preservation, entity extraction, canonical normalization, and decision state machine.
- **Business Value**: Normalizes 10,000+ unstandardized employee ideas into structured product improvement records.
- **Technical Scope**:
  - Tables: `IDEA`, `IDEA_CLUSTER`, `IDEA_EVALUATION`.
  - Raw submission preservation with normalized problem/solution decomposition.
  - Regex & dictionary entity extractor for part numbers, model names, and assemblies.
  - Decision state machine (`INVALID`, `DUPLICATE`, `ALREADY_IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `POTENTIAL_OPPORTUNITY`, `UNQUANTIFIED_OPPORTUNITY`, `SAFETY_HOLD`).
  - BOM vs Non-BOM deterministic classification.
- **Dependencies**: `PHASE-01`, `PHASE-02`.
- **Parallel Work**: Phase 5 (Retrieval engine).
- **Deliverables**: `IdeathonService`, entity normalization engine, idea management APIs.
- **Testing**: Entity extraction precision tests, state machine transition tests, raw text immutability checks.
- **Exit Criteria**: Ingestion and structuring of 1,000+ synthetic ideas with correct hierarchy linkage.
- **Decision Gate**: `GATE-04: Ideathon Core Gate`.
- **Expected Effort**: 4 Days.

---

### Phase 5: Unified Hybrid Retrieval & Cross-Encoder Reranking
- **Phase ID**: `PHASE-05`
- **Objective**: Implement multi-tier hybrid search combining exact part/ECN matching, pgvector semantic search, and local cross-encoder reranking (refactoring TASC RAG pipeline).
- **Business Value**: Eliminates both semantic false negatives (differing words) and keyword misses (part numbers).
- **Technical Scope**:
  - Exact & Trigram fuzzy matching via PostgreSQL `pg_trgm` for part numbers, ECNs, and project IDs.
  - Dense vector embedding pipeline via `EmbeddingProvider` (Qwen3-Embedding-0.6B / FastEmbed) into `pgvector` HNSW indexes.
  - Partitioned vector tables with strict metadata filtering (subsystem, vehicle family, model year).
  - Reciprocal Rank Fusion (RRF) combining exact and vector search scores.
  - Local cross-encoder reranking (`Qwen3-Reranker-0.6B`) for top-25 candidate pool.
- **Dependencies**: `PHASE-04`.
- **Parallel Work**: Track B.2 / B.3 (Hardware Profiler & LlamaCppEngine).
- **Deliverables**: `HybridRetrievalService`, `RerankerService`, unified multi-modal search endpoint.
- **Testing**: Recall testing on exact part numbers and semantic query variations; reranker latency benchmark.
- **Exit Criteria**: Combined Recall@5 > 90% on benchmark query set; sub-200ms hybrid search response time.
- **Decision Gate**: `GATE-05: Hybrid Retrieval Gate`.
- **Expected Effort**: 4 Days (1 day saved via TASC RAG plumbing reuse).

---

### Phase 6: Implementation Discovery & Applicability Engine
- **Phase ID**: `PHASE-06`
- **Objective**: Detect existing implementations across historical projects, ECNs, and BOM records; construct model/variant applicability matrix.
- **Business Value**: Directly solves the "Missed Implementation" problem, preventing duplicate engineering expenditure.
- **Technical Scope**:
  - Multi-tier implementation discovery: Part $\rightarrow$ Assembly $\rightarrow$ Subsystem $\rightarrow$ Sibling Models.
  - Implementation state taxonomy: Distinguishes `IMPLEMENTATION_CONFIRMED`, `PARTIALLY_CONFIRMED`, `HISTORICAL_IMPLEMENTATION`, `POTENTIAL_IMPLEMENTATION_EVIDENCE`, `NO_IMPLEMENTATION_EVIDENCE_FOUND`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`.
  - Dynamic Portfolio Applicability Matrix across Models, Variants, and Model Years.
- **Dependencies**: `PHASE-04`, `PHASE-05`.
- **Parallel Work**: Phase 7 (Cost engine).
- **Deliverables**: `ImplementationDiscoveryService`, `ApplicabilityMatrixBuilder`, implementation inspection APIs.
- **Testing**: Benchmark suite of historical implemented ideas; variant-specific implementation test cases.
- **Exit Criteria**: Zero false "new" decisions on test benchmark of known implemented engineering changes.
- **Decision Gate**: `GATE-06: Implementation Intelligence Gate`.
- **Expected Effort**: 4 Days.

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
- **Dependencies**: `PHASE-01`, `PHASE-06`.
- **Parallel Work**: Phase 8 (Evidence & Policy Layer).
- **Deliverables**: `CalculationEngine.vehicle_cost`, cost valuation services, financial audit recorder.
- **Testing**: Deterministic mathematical unit tests, edge cases (zero volume, negative delta, zero tooling).
- **Exit Criteria**: 100% exact mathematical match against reference spreadsheets; zero LLM arithmetic.
- **Decision Gate**: `GATE-07: Cost Engine Gate`.
- **Expected Effort**: 3 Days.

---

### Phase 8: Evidence & Policy Layer Integration
- **Phase ID**: `PHASE-08`
- **Objective**: Establish the formal Evidence & Policy Layer between retrieval and AI reasoning.
- **Business Value**: Enforces data governance, source precedence, conflict detection, and safety gate triggers.
- **Technical Scope**:
  - `SourceAuthorityPolicy`: Configurable precedence hierarchy (ERP > MES > Sheet; PLM > ERP > Plant).
  - Multi-source conflict detector: Flags discrepancies as `DATA_CONFLICT` and logs dual-source audit.
  - Deterministic 8-factor confidence scoring (`HIGH`, `MEDIUM`, `LOW`).
  - Safety & Quality gate triggers: Mandatory review holds for critical components (brakes, steering, frame).
- **Dependencies**: `PHASE-05`, `PHASE-06`, `PHASE-07`.
- **Parallel Work**: Track B.3 / B.4 (GBNF Grammar compiler).
- **Deliverables**: `EvidencePolicyService`, `SourceAuthorityPolicy`, `ConfidenceEngine`.
- **Testing**: Conflict detection tests, source precedence override tests, safety gate trigger tests.
- **Exit Criteria**: 100% of conflicting records flagged with mandatory human review queue routing.
- **Decision Gate**: `GATE-08: Evidence & Policy Gate`.
- **Expected Effort**: 3 Days.

---

### Phase 9: Local SLM Decisioning & Local AI Gateway
- **Phase ID**: `PHASE-09`
- **Objective**: Integrate local reasoning SLM (Qwen GGUF via refactored `LlamaCppEngine`) with GBNF grammar constraints (reused from TASC).
- **Business Value**: Delivers human-readable rationales, evidence summaries, and automated classification assistance.
- **Technical Scope**:
  - `LocalAiGateway` routing via `AIProvider` and `LlamaCppEngine`.
  - Hardware Profiler & Multi-Model Memory Swapper (safe 8GB VRAM execution).
  - In-context evidence grounding with lost-in-the-middle safeguards.
  - GBNF grammar constrained decoding for typed Pydantic JSON schemas.
  - Sandboxed tool registry (`max_iterations = 4`, timeout = 10s).
- **Dependencies**: `PHASE-08`, `TRACK-B`.
- **Parallel Work**: Phase 10 (Review queue).
- **Deliverables**: `AiOrchestratorService`, `LocalAiGateway`, structured decision synthesis endpoints.
- **Testing**: JSON schema compliance tests, prompt injection resilience, VRAM allocation/release tests.
- **Exit Criteria**: 100% schema-compliant JSON output; zero ungrounded part number or cost hallucinations; zero CUDA OOM errors on 8GB GPU.
- **Decision Gate**: `GATE-09: Local AI Decision Gate`.
- **Expected Effort**: 4 Days (2 days saved via TASC GBNF and LlamaCppEngine core reuse).

---

### Phase 10: Human-in-the-Loop Review & Engineering Gate Queue
- **Phase ID**: `PHASE-10`
- **Objective**: Build governance workflows, decision capture, and audit trails for engineering, quality, and safety stakeholders.
- **Business Value**: Enforces regulatory compliance and keeps human experts in ultimate control.
- **Technical Scope**:
  - Review queue management with multi-criteria filtering (confidence, savings, subsystem, vehicle).
  - Decision capture: `ACCEPT`, `REJECT`, `OVERRIDE`, `REQUEST_ENGINEERING_REVIEW`, `SAFETY_HOLD`.
  - Reviewer notes, override justification capture, and immutable audit logging with data minimization.
  - Non-bypassable safety gates: Automated flags for critical components.
- **Dependencies**: `PHASE-09`.
- **Parallel Work**: Phase 12 (Frontend UI).
- **Deliverables**: `ReviewWorkflowService`, review queue APIs, decision audit logger.
- **Testing**: Workflow transition tests, audit log immutability verification, safety flag enforcement.
- **Exit Criteria**: Complete end-to-end review lifecycle with full provenance logging.
- **Decision Gate**: `GATE-10: Human Governance Gate`.
- **Expected Effort**: 3 Days.

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
    - Inference latency, VRAM, and RAM utilization.
  - Automated evaluation reporting and regression tracking.
- **Dependencies**: `PHASE-08`, `PHASE-09`.
- **Parallel Work**: Phase 12 (Frontend UI).
- **Deliverables**: `EvaluationHarness`, Gold Dataset loader, automated evaluation report generator.
- **Testing**: Synthetic gold dataset evaluation run, metric computation verification.
- **Exit Criteria**: Automated evaluation report generated with all metrics calculated against baseline.
- **Decision Gate**: `GATE-11: POC Evaluation Gate`.
- **Expected Effort**: 3 Days.

---

### Phase 12: Executive UI, OPEX & Ideathon Dashboards
- **Phase ID**: `PHASE-12`
- **Objective**: Build a high-density, responsive, industrial enterprise web application in React / Vite (incorporating TASC virtualized grid & AI Studio).
- **Business Value**: Delivers the executive and operational user experience that wows stakeholders and accelerates decision-making.
- **Technical Scope**:
  - Executive Overview: Portfolio savings summary, top plant opportunities, Ideathon pipeline funnel.
  - OPEX Module: Interactive peer benchmark charts, variance waterfall, plant comparison matrices.
  - Ideathon Module: Cluster visualizer, duplicate inspector, implementation matrix table, idea detail panel.
  - Evidence & Audit Inspector: Full transparency panel with clickable source links, calculation proofs, and confidence badges.
  - Review Queue: Actionable decision drawer (Accept/Reject/Override) with note capture.
  - Internal AI Studio: Rebranded TASC AI Studio showing live hardware monitoring (RAM/VRAM), model status, and prompt playground.
  - Virtualized Data Grid: Reused from TASC for fluid scrolling on 10,000+ ideas (< 16ms frame time).
- **Dependencies**: `PHASE-03`, `PHASE-06`, `PHASE-07`, `PHASE-10`.
- **Parallel Work**: Phase 13 (Security hardening).
- **Deliverables**: Complete React/Vite SPA bundle, responsive design system, component test suite.
- **Testing**: End-to-end browser user flows, responsive layout tests, accessibility and contrast checks.
- **Exit Criteria**: All 7 client demo scenarios executable in UI smoothly without layout errors or latency lag.
- **Decision Gate**: `GATE-12: Executive UI Gate`.
- **Expected Effort**: 4 Days (2 days saved via TASC grid and AI Studio reuse).

---

### Phase 13: Security Hardening & Air-Gap Compliance
- **Phase ID**: `PHASE-13`
- **Objective**: Harden the complete application for air-gapped on-premise enterprise deployment.
- **Business Value**: Ensures compliance with Hero IT / InfoSec standards, zero data leakage, and system resilience.
- **Technical Scope**:
  - Network isolation: Block all outbound HTTP/HTTPS egress at container and network levels; zero telemetry verification.
  - Security controls: JWT authentication, role-based authorization guards on all API endpoints.
  - Audit Data Minimization: Verification that raw sensitive prompt/document content is retention-controlled and redacted.
  - Penetration testing: SQL injection prevention (parameterized ORM), path traversal defense on upload/model paths.
  - Backup & recovery scripts: Automated PostgreSQL dump and restore verification.
- **Dependencies**: `PHASE-11`, `PHASE-12`.
- **Parallel Work**: POC acceptance documentation.
- **Deliverables**: Hardened Docker deployment bundle, security audit checklist, air-gap verification script.
- **Testing**: Egress packet capture tests, security vulnerability scans, RBAC permission tests.
- **Exit Criteria**: Zero external network packets detected during full system execution; all security gates pass.
- **Decision Gate**: `GATE-13: Production Readiness Gate`.
- **Expected Effort**: 3 Days.

---

## 7. Indicative Effort & Acceleration Summary

```text
+---------------------------------------------------------------------------------------------------+
|                              EFFORT SUMMARY (PLAN V3 vs PLAN V3.1)                                |
+------------------------------------+-----------------------+------------------+-------------------+
| IMPLEMENTATION WORKSTREAM          | BASELINE EFFORT (V3)  | TASC REUSE SAVED | V3.1 NET EFFORT   |
+------------------------------------+-----------------------+------------------+-------------------+
| Track A: Data & Core Business      | 26 Days               | 5 Days           | 21 Days           |
| Track A: AI, Evidence & Governance | 16 Days               | 4 Days           | 12 Days           |
| Track A: Frontend & Dashboards     | 10 Days               | 4 Days           | 6 Days            |
| Track B: Local AI Runtime Core     | 18 Days               | 14 Days          | 4 Days            |
| Hardening, Evaluation & Security   | 10 Days               | 2 Days           | 8 Days            |
| **TOTAL PROJECT EFFORT**           | **80 Days**           | **~29 Days**     | **51 Days (~40% Accel.)** |
+------------------------------------+-----------------------+------------------+-------------------+
```
*Note: Effort estimates and acceleration figures are indicative and will be validated during Phase 0–1 implementation.*

---

## 8. Decision Gates & Milestones
- `GATE-00`: Architecture & Baseline Sign-off.
- `GATE-01`: Data Foundation & Relational Schema Verified.
- `GATE-02`: Ingestion Reliability & `MagnitudeAnomalyGuard` Verified.
- `GATE-03`: OPEX `BenchmarkMethodology` & KPI Math Verified.
- `GATE-04`: Ideathon Ingestion & Entity Normalization Verified.
- `GATE-05`: Hybrid Retrieval Recall Benchmark Verified.
- `GATE-06`: Implementation Applicability Matrix Verified.
- `GATE-07`: Deterministic Cost Opportunity Math Verified.
- `GATE-08`: Evidence & Policy Layer Sign-off.
- `GATE-09`: Local SLM Structured Output & Grammar Verified (8GB VRAM Safe).
- `GATE-10`: Human Review Queue & Safety Gates Verified.
- `GATE-11`: Gold Dataset Evaluation Report Signed Off.
- `GATE-12`: Executive UI Client Demo Scenarios Verified.
- `GATE-13`: Air-Gap Compliance & Production Readiness Verified.

---

## 9. Risk Register & Key Mitigations (V3.1)
1. **Missed Implementation** $\rightarrow$ Traversal across Part, Assembly, and Sibling Models with mandatory review on low confidence.
2. **Calculation Unit Skew** $\rightarrow$ `MagnitudeAnomalyGuard` statistical distribution validation.
3. **AI Hallucination** $\rightarrow$ Database-validated source citations and pure Python calculation services.
4. **VRAM Exhaustion on 8GB GPU** $\rightarrow$ Dynamic hardware profiler, Qwen2.5-3B/7B model selection, and sequential on-demand swapping.
5. **Air-Gap Egress Leak** $\rightarrow$ Container-level network isolation (`internal: true`) and zero telemetry flags.

---

## 10. Technology Decisions Matrix (V3.1)
- **Core Database**: PostgreSQL 16 with `pgvector` (HNSW) and `pg_trgm`.
- **Backend API**: Python 3.11+ / FastAPI with Pydantic v2.
- **Frontend SPA**: React 18+ / Vite with Vanilla CSS industrial design tokens.
- **Inference Foundation**: Internal `LlamaCppEngine` (GGUF direct execution, refactored from TASC).
- **Candidate Models**: Qwen2.5-3B / Qwen2.5-7B (SLM for Tier 1 8GB VRAM profile), Qwen3-Embedding-0.6B (Embeddings), Qwen3-Reranker-0.6B (Reranker).

---

## 11. Future Post-POC Roadmap
- **Phase 14**: Enterprise SSO Integration (SAML 2.0 / OIDC / Azure AD).
- **Phase 15**: Live ERP & PLM Connectors (SAP S/4HANA & Teamcenter read-only adapters).
- **Phase 16**: Domain-Specific LoRA Fine-Tuning (Hero engineering jargon and classification styles).
- **Phase 17**: High-Availability Multi-Node Database Clustering.
