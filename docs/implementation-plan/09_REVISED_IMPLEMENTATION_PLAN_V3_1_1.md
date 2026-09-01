# 09 — Master Implementation Plan V3.1.1 (Targeted Final Baseline)

## 1. Executive Summary
Master Implementation Plan V3.1.1 is the authoritative implementation baseline for the **Hero Vehicle Cost & Plant OPEX Intelligence Platform**. It provides:
1. **Dynamic Hardware & Resource Governance**: Manages host system memory dynamically (tracking `total_ram`, `available_ram`, `reserved_headroom`, `db_usage`, `app_usage`, `ai_usage`) for the reference development profile (**AMD Ryzen AI 9 HX 370, 16 GB RAM, NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM**), with configurable CPU thread allocation and sequential on-demand model swapping.
2. **Stress-Envelope CUDA OOM Protection**: Enforces "no reproducible CUDA OOM under the defined POC workload and stress-test envelope" as the measurable POC acceptance criterion, while maintaining certified Zero CUDA OOM as a long-term hardening goal.
3. **Model Independence & Capability Routing**: Evaluates `Qwen2.5-3B` and `Qwen2.5-7B` as *initial candidates* for 8 GB VRAM execution while maintaining a fully model-agnostic capability router (`request_reasoning_model()`, `request_embedding_model()`, `request_reranker()`).
4. **TASC IIoT Studio Asset Reuse (Indicative Savings)**: Incorporates generic infrastructure modules (protocols, `LlamaCppEngine` core, GBNF grammar engine, local RAG chunking, virtualized data grids, and AI Studio UI) from **TASC IIoT Studio V3** (https://github.com/viji5626/TASC_IIoT_Studio_V3) with effort savings tagged as *INDICATIVE / TO BE VALIDATED DURING IMPLEMENTATION*.
5. **Linear Evidence & Policy Pipeline**: Preserves the explicit flow:
   $$\text{BUSINESS ENGINES} \longrightarrow \text{STRUCTURED DATA + RETRIEVAL} \longrightarrow \text{EVIDENCE \& POLICY} \longrightarrow \text{AI ORCHESTRATION} \longrightarrow \text{LOCAL AI RUNTIME}$$
6. **Strict Three-Tier Scope Stratification**: Classifies capabilities into **CURRENT POC**, **PARKED / FUTURE** (architecturally preserved), and **PRODUCTION SCALE**, ensuring zero feature loss while keeping the POC laser-focused.

---

## 2. Final System Architecture & Conceptual Data Flow

```text
===================================================================================================
                                      CONCEPTUAL SYSTEM DATA FLOW
===================================================================================================

[1] BUSINESS ENGINES
    +-----------------------------------------------+   +-------------------------------------------+
    |             VEHICLE IDEATHON ENGINE           |   |             PLANT OPEX ENGINE             |
    |  - 10,000+ Idea Ingestion & Normalization     |   |  - Plant Operational Ingestion            |
    |  - Semantic Clustering & Entity Extraction    |   |  - MagnitudeAnomalyGuard                  |
    |  - Implementation Discovery (Where/When/What) |   |  - BenchmarkMethodology Domain Service    |
    +-----------------------------------------------+   +-------------------------------------------+
                                            |                                   |
                                            +-----------------+-----------------+
                                                              |
                                                              v
[2] STRUCTURED DATA + RETRIEVAL
    +-----------------------------------------------------------------------------------------------+
    |  - PostgreSQL 16 Relational Truth (Vehicles, Plants, BOM, Parts, Costs, ECNs, Audit)          |
    |  - Exact Alphanumeric & Trigram Matching (pg_trgm for 10-digit Part Nos, Drawing IDs)         |
    |  - Dense Vector Search (pgvector HNSW Cosine Distance)                                        |
    |  - Cross-Encoder Candidate Reranking (Top-25 Re-scoring Pool)                                 |
    +-----------------------------------------------------------------------------------------------+
                                                              |
                                                              v
[3] EVIDENCE & POLICY LAYER
    +-----------------------------------------------------------------------------------------------+
    |  - Evidence Aggregation & Completeness Verification                                           |
    |  - SourceAuthorityPolicy (Precedence Hierarchy: ERP > MES > Sheet; PLM > ERP > Plant)         |
    |  - Multi-Source Conflict Detection & Discrepancy Logging (DATA_CONFLICT)                      |
    |  - Temporal Freshness Validation (valid_from, valid_to, active model year)                     |
    |  - Deterministic Confidence Scoring (HIGH / MEDIUM / LOW)                                     |
    |  - Non-Bypassable Engineering & Safety Gates (Brakes, Steering, Suspension, Frame)            |
    +-----------------------------------------------------------------------------------------------+
                                                              |
                                                              v
[4] AI ORCHESTRATION LAYER
    +-----------------------------------------------------------------------------------------------+
    |  - LocalAiGateway with In-Context Evidence Grounding (Lost-in-the-Middle Guards)              |
    |  - GBNF Grammar Constrained JSON Decoding (Pydantic Schema Output Enforcement)                |
    |  - Sandboxed Tool Policy Engine (Bounded Loop: max_iterations = 4, timeout = 10s)             |
    |  - Deterministic Calculation Override Guard (Zero LLM Financial Arithmetic)                   |
    +-----------------------------------------------------------------------------------------------+
                                                              |
                                                              v
[5] LOCAL AI RUNTIME (TASC Refactored)
    +-----------------------------------------------------------------------------------------------+
    |  - Hardware-Aware Profiler (Dynamic RAM/VRAM Tracking & Tier Selection)                       |
    |  - Sequential Multi-Model Lifecycle Manager (LOAD -> PROCESS -> RELEASE on 8GB VRAM)          |
    |  - LlamaCppEngine (Direct GGUF Native Execution, Configurable Thread Pool)                    |
    |  - Complete Air-Gap Compliance (Zero External Network Calls, Zero Telemetry)                  |
    +-----------------------------------------------------------------------------------------------+
```

---

## 3. Dynamic Hardware Resource Management & Profiling

### 3.1 Dynamic System RAM Budgeting (16 GB Host Machine)
Rather than assuming rigid static partitions, the runtime continuously tracks system memory metrics:
$$\text{Available for AI Runtime} = \text{Total RAM} - (\text{Host OS Reserve} + \text{PostgreSQL Usage} + \text{Backend Usage} + \text{Browser Usage} + \text{Safety Margin})$$
- **Total System RAM**: 16.0 GB.
- **Dynamic Headroom Target**: The runtime maintains a continuous safety reserve ($\ge 1.0\text{ GB}$) to prevent Windows disk swapping.
- **Tested Operating Envelope**: In practice, active host processes (OS, DB, API, Browser) consume $\approx 8.0\text{ GB} – 9.5\text{ GB}$, providing an *indicative operating envelope of 6.0 GB – 8.0 GB for the AI runtime process and KV cache*.

### 3.2 Dynamic VRAM Profiling & Sequential Swapping (8 GB GPU Profile)
- **Measurable POC Criterion**: *No reproducible CUDA OOM under the defined POC workload and stress-test envelope.* (Certified Zero CUDA OOM preserved for long-term production).
- **Sequential Model Swapping Strategy**:
  1. *Embedding Phase*: Load `Qwen3-Embedding-0.6B` (~1.1 GB VRAM) $\rightarrow$ process batch $\rightarrow$ unload.
  2. *Reranking Phase*: Load `Qwen3-Reranker-0.6B` (~1.2 GB VRAM) $\rightarrow$ score top-25 pool $\rightarrow$ unload.
  3. *Reasoning Phase*: Load Candidate SLM (`Qwen2.5-3B` / `Qwen2.5-7B`, ~2.2–3.8 GB VRAM) $\rightarrow$ execute GBNF generation $\rightarrow$ retain in memory during active session with a 10-minute idle TTL.
- **Peak VRAM Guarantee**: Peak memory stays strictly $\le 4.8\text{ GB}$, providing ample headroom below the 6.8 GB usable VRAM limit.

### 3.3 Configurable CPU Core Allocation
- **Initial POC Profile (AMD Ryzen AI 9 HX 370)**: 12 Cores / 24 Threads. Configured to `n_threads = 6` pinned to Zen 5 performance cores.
- **Configurability**: Thread counts and CPU core masks are dynamically configurable via environment settings (`LLAMA_NUM_THREADS`) to support server scaling (e.g. 16, 32, or 64 threads).

---

## 4. Hardware-Aware Model Resource Tiers & Agnosticism

```text
+---------------------------------------------------------------------------------------------------+
|                                  HARDWARE-AWARE MODEL RESOURCE TIERS                              |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| TIER   | HARDWARE PROFILE      | INITIAL CANDIDATE SLM       | CONTEXT WINDOW  | VRAM STRATEGY    |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 1 | 16GB RAM / 8GB VRAM   | Qwen2.5-3B (Q4_K_M, ~2.2GB) | 2,048 – 4,096   | Sequential Model |
| (POC)  | *(POC Laptop Profile)*| Qwen2.5-7B (Q3_K_M, ~3.8GB) | tokens          | Swapping (Safe)  |
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 2 | 32GB RAM / 16GB VRAM  | Qwen2.5-7B (Q4_K_M, ~4.8GB) | 4,096 – 8,192   | Full GPU Offload |
| (Parked)| (Workstation Profile)| Qwen3.5-9B (Q4_K_M, ~5.5GB) | tokens          | Concurrent Models|
+--------+-----------------------+-----------------------------+-----------------+------------------+
| Tier 3 | 64GB+ RAM / 24GB+ VRAM| Qwen2.5-14B (Q4_K_M, ~8.5GB)| 8,192 – 16,384  | Full GPU Offload |
| (Future)| (Enterprise Server)  | Qwen3.5-9B (Q8_0, ~10.0GB)  | tokens          | High Concurrency |
+--------+-----------------------+-----------------------------+-----------------+------------------+
```
*Model Independence: The application requests abstract capabilities (`request_reasoning_model()`, `request_embedding_model()`, `request_reranker()`). Model candidates are configurable GGUF binaries and never hardcoded into business logic.*

---

## 5. Scope Stratification: Current POC vs. Parked vs. Production

```text
+---------------------------------------------------------------------------------------------------+
|                                   THREE-TIER SCOPE STRATIFICATION                                 |
+---------------------------------------------------------------------------------------------------+
| [1] CURRENT POC (What Must Work on 16GB RAM / 8GB VRAM Laptop Baseline)                          |
|     - PostgreSQL 16 Relational Truth (Vehicles, Plants, BOM, Parts, Costs, ECNs, Audit)          |
|     - Plant OPEX Deterministic KPI Engine (kWh/veh, KL/veh, ₹/veh) & MagnitudeAnomalyGuard        |
|     - Formal BenchmarkMethodology (4 Benchmark Modes, Multi-Factor Comparability Scoring)         |
|     - Ideathon 10k Ingestion, Entity Extraction & Canonical Normalization                         |
|     - Unified Hybrid Retrieval (Exact Part Trigram + pgvector Semantic + Cross-Encoder Reranker)  |
|     - Multi-tier Implementation Detection & Applicability Matrix (Where/When/What)                |
|     - Implementation State Machine (NO_EVIDENCE_FOUND != NOT_IMPLEMENTED)                         |
|     - Deterministic Vehicle Cost Engine (Unit Savings, Annual Opportunity, Tooling ROI)           |
|     - Evidence & Policy Layer (SourceAuthorityPolicy, Conflict Detection, Safety Gates)           |
|     - Local AI Runtime (LlamaCppEngine, Hardware Profiler, Sequential Swapping, GBNF Grammar)     |
|     - Human-in-the-Loop Review Queue with Audit Data Minimization                                 |
|     - Synthetic Gold Dataset Continuous Evaluation Harness                                        |
|     - High-Density Industrial UI (React/Vite, TASC Virtual Grid, Rebranded AI Studio)             |
|     - Complete Air-Gap Compliance (Zero External Network Calls, Zero Telemetry)                   |
+---------------------------------------------------------------------------------------------------+
| [2] PARKED / FUTURE (Architecturally Preserved — Not Required for Initial POC Validation)         |
|     - Tier 2 & Tier 3 Hardware Profiles (Concurrent Resident Multi-Model VRAM Loading)            |
|     - Larger Context Windows (8k – 16k Tokens)                                                    |
|     - Certified Zero CUDA OOM Deployment Hardening                                                |
|     - Model Context Protocol (MCP) External Interoperability Adapter                              |
|     - Recursive Language Model (RLM) Multi-Pass Corpus Analysis                                    |
|     - Domain-Specific LoRA / QLoRA Adaptation (Hero Engineering Jargon & Taxonomy)                |
|     - Multimodal Handwritten Idea Card & Technical Drawing OCR                                    |
|     - 3D Vehicle Cost Assembly Explorer                                                           |
|     - Real-time SAP S/4HANA & Teamcenter PLM Connectors                                           |
|     - Enterprise Single Sign-On (SAML 2.0 / OIDC / Azure AD)                                      |
|     - Multi-Node High-Availability PostgreSQL Clustering                                          |
+---------------------------------------------------------------------------------------------------+
| [3] PRODUCTION SCALE (Future Enterprise Rollout)                                                  |
|     - High-Throughput Multi-GPU Batch Inference Clustering (vLLM / TensorRT-LLM option)           |
|     - Multi-Plant Distributed Edge-to-Cloud Sync                                                  |
|     - Full Automated Engineering Change Order (ECO) Workflow Generation                           |
+---------------------------------------------------------------------------------------------------+
```

---

## 6. TASC IIoT Studio Asset Reuse Strategy (Indicative Acceleration)

| TASC Asset Category | Specific Component | Current Purpose in TASC | Reuse Classification | Required Adaptation | Destination in Project | Indicative Effort Saved |
|---|---|---|---|---|---|---|
| **AI Abstraction** | `AIProvider` Protocol | Base protocol for chat, completions, embeddings | **REUSE AS-IS** | None. Drop-in protocol. | `ai/providers/base.py` | ~3 Days (Indicative) |
| **GGUF Runtime** | `LlamaCppEngine` Core | GGUF model execution via `llama-cpp-python` | **REFACTOR & REUSE** | Add Hardware Profiler & sequential VRAM swapper. | `ai/runtime/llama_cpp_engine.py` | ~6 Days (Indicative) |
| **Grammar Engine** | GBNF Grammar Compiler | Constrains logits to Pydantic JSON schemas | **REUSE AS-IS** | Register Hero-specific schemas. | `ai/grammar/gbnf_compiler.py` | ~4 Days (Indicative) |
| **RAG Plumbing** | Local RAG & Chunker | Document chunking and metadata injection | **REFACTOR & REUSE** | Adapt for ECNs and BOM tables. | `retrieval/rag/chunker.py` | ~4 Days (Indicative) |
| **Admin UI** | Internal AI Studio UI | Model health, VRAM monitor, prompt test | **REFACTOR & REUSE** | Rebrand with Hero dark theme. | `frontend/src/modules/ai-studio/` | ~5 Days (Indicative) |
| **Data Grid** | Virtualized Data Grid | Renders 10k+ rows fluidly (< 16ms frame) | **REUSE AS-IS** | Style for Ideathon & OPEX. | `frontend/src/components/common/VirtualGrid.tsx` | ~3 Days (Indicative) |
| **Ingestion Base** | Staging & Hash Check | Upload staging and transactional commit | **REFACTOR & REUSE** | Inject `MagnitudeAnomalyGuard`. | `backend/services/ingestion_service.py` | ~4 Days (Indicative) |

*Total Indicative Acceleration: **~27–30 Engineering Days (To be validated during implementation).***

---

## 7. Master Implementation Phases (V3.1.1)

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
- `GATE-09`: Local SLM Structured Output & Grammar Verified (No reproducible CUDA OOM).
- `GATE-10`: Human Review Queue & Safety Gates Verified.
- `GATE-11`: Gold Dataset Evaluation Report Signed Off.
- `GATE-12`: Executive UI Client Demo Scenarios Verified.
- `GATE-13`: Air-Gap Compliance & Production Readiness Verified.

---

## 9. Technology Decisions Matrix (V3.1.1)
- **Core Database**: PostgreSQL 16 with `pgvector` (HNSW) and `pg_trgm`.
- **Backend API**: Python 3.11+ / FastAPI with Pydantic v2.
- **Frontend SPA**: React 18+ / Vite with Vanilla CSS industrial design tokens.
- **Inference Foundation**: Internal `LlamaCppEngine` (GGUF direct execution, refactored from TASC).
- **Candidate Models**: Qwen2.5-3B / Qwen2.5-7B (SLM for Tier 1 8GB VRAM profile), Qwen3-Embedding-0.6B (Embeddings), Qwen3-Reranker-0.6B (Reranker).
- **Math Verification**: Pure Python `CalculationEngine` using `Decimal` representation and independently calculated reference models.
