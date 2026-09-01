# 01 — Architecture Synthesis & Architectural Challenge

## 1. Executive Architectural Synthesis
The **Hero Vehicle Cost & Plant OPEX Intelligence Platform** is architected as an evidence-grounded, private enterprise intelligence platform. It maintains strict separation between **Vehicle Ideathon Intelligence** and **Plant OPEX Benchmarking**, and rigorously isolates **Authoritative Data & Deterministic Calculations** from **Probabilistic AI Reasoning**.

```text
                                  +-------------------------------------------------------------+
                                  |                     HERO ENTERPRISE USER                    |
                                  |              (Leadership / Engineers / Plant Heads)         |
                                  +-------------------------------------------------------------+
                                                                 |
                                                                 v
                                  +-------------------------------------------------------------+
                                  |                    FRONTEND (React / Vite)                  |
                                  |  - Plant OPEX Dashboards        - Ideathon Review Queue     |
                                  |  - Vehicle Hierarchy Explorer   - Evidence & Audit Explorer |
                                  |  - Ingestion & Validation UI    - Local AI Admin Studio     |
                                  +-------------------------------------------------------------+
                                                                 |  HTTPS / REST / JSON
                                                                 v
                                  +-------------------------------------------------------------+
                                  |                 APPLICATION API & GATEWAY                   |
                                  |                     (FastAPI / Python)                      |
                                  |  - Auth & RBAC                  - Request Validation        |
                                  |  - Rate Limiting & Egress Block - Audit Logger & Tracing    |
                                  +-------------------------------------------------------------+
                                                                 |
                           +-------------------------------------+-------------------------------------+
                           |                                                                           |
                           v                                                                           v
+-------------------------------------------------------+   +-------------------------------------------------------+
|             VEHICLE IDEATHON ENGINE                   |   |                 PLANT OPEX ENGINE                     |
| - Idea Ingestion, Normalization & Cleansing           |   | - Plant Operational Ingestion (Excel/CSV)             |
| - Semantic Clustering & Duplicate Detection           |   | - Canonical Unit Conversion (kWh, KL, ₹)              |
| - Multi-source Implementation Discovery (ECN/ECR/BOM) |   | - Deterministic KPI Engine (kWh/veh, ₹/veh)           |
| - Model/Variant Applicability Matrix (Where/When/What)|   | - Comparable Peer Selection & Benchmarking            |
| - Opportunity Valuation & Engineering Gates           |   | - Variance Decomposition & Savings Quantification     |
+-------------------------------------------------------+   +-------------------------------------------------------+
                           |                                                                           |
                           +-------------------------------------+-------------------------------------+
                                                                 |
                                                                 v
+-------------------------------------------------------------------------------------------------------------------+
|                                          DOMAIN ORCHESTRATION & SERVICES                                          |
|  - Workflow Orchestration     - Evidence Aggregator     - Priority Scorer     - Deterministic Calculation Engine  |
+-------------------------------------------------------------------------------------------------------------------+
                           |                                                                 |
                           v                                                                 v
+-------------------------------------------------------+   +-------------------------------------------------------+
|                    DATA LAYER                         |   |              AI ORCHESTRATION & RUNTIME               |
|                                                       |   |                                                       |
|  [PostgreSQL 16 + pgvector]                           |   |  [Local AI Gateway]                                   |
|  - Structured Truth: Vehicle Master, Plant Master,    |   |  - Capability Router (Text, Tool, Embed, Rerank)      |
|    BOM, Parts, Costs, ECNs, Implementations, OPEX     |   |  - Tool Policy & Authorization Engine                 |
|  - Relationship Model: Subsystems, Assemblies, Parts  |   |  - Context Assembler & Lost-in-the-Middle Guard       |
|  - Vector Store: Idea embeddings, Project embeddings  |   |                                                       |
|  - Exact & Trigram Search: Part Nos, ECNs, Codes      |   |  [Inference Engine Abstraction]                       |
|                                                       |   |  - LlamaCppEngine (Production GGUF, Zero Telemetry)   |
|  [Local Document Store]                               |   |  - OllamaProvider (Dev/Benchmarking Only)             |
|  - Encrypted local filesystem for verified artifacts  |   |  - Local Embedding & Reranker Engines                 |
+-------------------------------------------------------+   +-------------------------------------------------------+
```

---

## 2. Core Architectural Boundaries & Truth Guarantees

| Architecture Layer | Technology / Implementation | Source of Truth / Operational Boundary |
|---|---|---|
| **Structured Business Truth** | PostgreSQL Relational Tables | Authoritative master data (Vehicles, Models, Variants, Components, Parts, Plants, Production, ECNs). |
| **Relationship Model** | PostgreSQL Relational Hierarchy + CTEs | Product breakdown structure, component linkages, and implementation applicability matrices. |
| **Financial / Numerical Truth** | Python Deterministic Calculation Engine | All unit conversions, savings calculations, ROI, KPI ratios, and plant variance math. Zero LLM arithmetic. |
| **Semantic Retrieval** | Local Embedding Model + pgvector (HNSW) | Conceptual search for ideas, historical project notes, and unstandardized problem statements. |
| **Exact Engineering Lookup** | PostgreSQL Trigram / Exact B-Tree Indexes | Part numbers, supplier IDs, ECN/ECR codes, model year codes, and CAD drawing identifiers. |
| **Retrieval Precision** | Local Cross-Encoder Reranker | Re-scoring top-K candidates from vector and keyword search to eliminate retrieval noise. |
| **Reasoning & Explanation** | Local SLM (Qwen-class GGUF via llama.cpp) | Synthesizes retrieved evidence, classifies idea intent, explains plant variances, and outputs JSON schemas. |
| **Tool Execution** | Controlled Python Tool Registry | Parameter-validated, authorization-checked deterministic functions exposed to the AI gateway. |
| **Engineering / Safety Authority** | Human-in-the-Loop Review Queue | Final authority to approve, reject, or mark ideas for physical validation and safety compliance. |

---

## 3. Challenging the Architecture (Critical Self-Review)

| # | Current Assumption | Problem / Fragility | Recommendation | Rationale | Impact |
|---|---|---|---|---|---|
| 1 | **Dedicated Graph Database** (Neo4j / GraphDB) for vehicle-part relationships. | Adds operational overhead, extra container, network latency, and synchronization lag with SQL master. | **Use PostgreSQL Relational Tables with recursive CTEs and closure tables.** | Vehicle hierarchies (Family -> Model -> Variant -> Subsystem -> Assembly -> Part) are tree-structured with predictable depth (< 8 levels). | Eliminates graph DB license/operational complexity; maintains ACID transactions with master data. |
| 2 | **Full Custom C++ Runtime in Phase 1**. | Blocks business validation, delays POC delivery, and risks building infrastructure before understanding model requirements. | **Dual-Track: Build Business Engine with `InferenceEngine` interface; implement `LlamaCppEngine` in parallel Track B.** | Decouples business logic from low-level C++ bindings while ensuring complete model and provider agnosticism. | Accelerates POC readiness by weeks without incurring vendor lock-in. |
| 3 | **Agentic Autonomous Multi-Step Reasoning for all queries.** | Increases latency (10-30s), risks unbounded tool loops, high GPU resource consumption, and non-deterministic execution. | **Hybrid Deterministic Pipelines with Agentic Fallback.** Standard screening follows a fixed deterministic pipeline; agentic search is triggered only for exploratory queries. | 90% of Ideathon screening and OPEX benchmarking follows deterministic pipeline stages. | Cuts inference latency by 75% and guarantees predictable screening throughput. |
| 4 | **Model Fine-Tuning (LoRA/QLoRA) during initial POC.** | Baking rapidly changing vehicle parts, costs, and ECNs into model weights causes catastrophic forgetting and stale data. | **RAG + Strict In-Context Schema Grounding for POC.** Restrict fine-tuning to Hero-specific taxonomy and reasoning style in production. | Enterprise data changes daily; RAG over structured SQL and vector indexes guarantees real-time accuracy. | Eliminates training pipeline overhead and prevents hallucinated historical data. |
| 5 | **Microservices Architecture with multiple independent services.** | Unnecessary network hops, serialization overhead, complex local deployment, and container sprawl for on-premise air-gapped POC. | **Modular Monolith with clean internal domain boundaries (FastAPI).** | A modular monolith provides strict internal isolation, shared database connections, easy debugging, and simple single-node container deployment. | Dramatically simplifies development, testing, deployment, and on-premise maintenance. |

---

## 4. Subsystem Architectural Specifications

### 4.1 Frontend Layer (Web Application)
- **Framework**: React 18+ with Vite, TypeScript, and modern enterprise dashboard component architecture.
- **Styling & Theme**: Vanilla CSS design system tailored for industrial enterprise platforms (Hero dark/slate theme, high data density, clear visual hierarchy).
- **Key Modules**:
  - *OPEX Intelligence Dashboard*: Peer benchmarking charts, variance waterfall decomposition, plant scorecard.
  - *Ideathon Command Center*: Pipeline overview, cluster visualizer, duplicate inspector, implementation matrix viewer.
  - *Idea Detail & Evidence Panel*: Side-by-side evidence inspection, exact source citation, confidence breakdown, deterministic calculation audit.
  - *Review & Escalation Queue*: Human-in-the-loop decision logging (Accept, Reject, Override, Flag Safety).
  - *Internal AI Studio*: Model status, hardware monitor (VRAM/RAM), latency metrics, tool execution logs.

### 4.2 Application Gateway & Business Services (Backend)
- **Framework**: Python 3.11+ / FastAPI with Pydantic v2 schemas.
- **Service Segregation**:
  - `PlantOpexService`: Data ingestion, KPI calculations, comparable peer matching, benchmark calculation, gap decomposition.
  - `IdeathonService`: Idea normalization, clustering, duplicate screening, implementation discovery, cost evaluation.
  - `RetrievalService`: Hybrid search coordination (exact, trigram, vector, reranking), metadata filtering, evidence assembly.
  - `CalculationEngine`: Pure deterministic financial and physical unit calculations (zero AI involvement).
  - `AuditService`: Immutable event logging, decision recording, prompt/response telemetry.

### 4.3 AI Orchestration & Local AI Runtime
- **AI Gateway & Provider Abstraction**:
  - `AIProvider` (Protocol): `chat()`, `generate_structured()`, `embed()`, `rerank()`.
  - `LlamaCppEngine`: Direct GGUF execution via `llama-cpp-python` with CUDA/Metal/CPU backends, support for structured JSON schemas (Grammar/GBNF/JSON Schema).
  - `OllamaProvider`: Optional development/benchmarking adapter; zero business logic dependency.
- **Tool Execution Engine**:
  - Allowlisted registry of Pydantic-validated tools.
  - Execution bounds: `max_iterations = 4`, `timeout_seconds = 10`, strict sandboxed parameters.
- **Context Manager**:
  - Token budget allocator, lost-in-the-middle mitigation (placing key query constraints and structured facts at optimal context positions), prompt compression.

### 4.4 Data & Storage Layer
- **PostgreSQL 16**:
  - Relational tables for core master data and business records.
  - `pgvector` extension for vector indexing (HNSW indexes with cosine distance).
  - `pg_trgm` extension for fuzzy part number and text matching.
- **Local Document Storage**:
  - Encrypted local filesystem for staging uploaded Excel/CSV/PDF files, with automated purge upon verified ingestion.

### 4.5 Security & Air-Gapped Governance
- **Zero Cloud Egress**: Hardened network configuration with complete offline capability. Zero telemetry.
- **Authentication & RBAC**: JWT-based session tokens with role-based access (`ADMIN`, `ENGINEER`, `PLANT_MANAGER`, `EXECUTIVE`, `AUDITOR`).
- **Audit Logging**: Comprehensive logging of user actions, data modifications, AI prompt/response traces, and calculation inputs.
