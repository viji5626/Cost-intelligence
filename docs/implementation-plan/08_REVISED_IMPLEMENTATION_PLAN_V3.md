# 08 — Master Implementation Plan V3 (Hardened Edition)

## 1. Executive Summary
Master Implementation Plan V3 is the definitive, hardened architectural blueprint for the **Hero Vehicle Cost & Plant OPEX Intelligence Platform**. It incorporates the rigorous corrections identified in the V2 review, establishes an explicit **Evidence & Policy Layer**, formalizes the **`BenchmarkMethodology`** and **`SourceAuthorityPolicy`**, refactors the implementation state machine to eliminate false "new" decisions, and incorporates proven software assets from **TASC IIoT Studio** to accelerate delivery while eliminating redundant engineering.

---

## 2. Final System Architecture

```text
+---------------------------------------------------------------------------------------------------+
|                                      FRONTEND (React 18 + Vite)                                   |
|  - Executive Command Center  - Plant OPEX Dashboards        - Ideathon Review Queue               |
|  - Evidence & Audit Panel    - Ingestion & Validation UI    - Internal AI Studio (TASC Reused)    |
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
| [PostgreSQL 16 + pgvector]                      |   | [Local AI Gateway]                          |
| - Relational Master Data (Vehicles, Plants, BOM)|   | - Task-Specific Model Router (TASC Reused)  |
| - Recursive CTE Tree Views                      |   | - Sandboxed Tool Registry & Policy Engine   |
| - Trigram & Exact Identifier Indexes            |   |                                             |
| - Dense Vector Indexes (HNSW Cosine Distance)   |   | [Inference Engine Abstraction]              |
|                                                 |   | - LlamaCppEngine (Production GGUF Native)   |
| [Local Document Store]                          |   | - OllamaProvider (Dev Adapter Only)         |
| - Encrypted Local Storage with Auto-Purge       |   | - Hardware Profiler (Dynamic VRAM Offload)  |
+-------------------------------------------------+   +---------------------------------------------+
```

---

## 3. Business Engine Separation
The platform enforces a strict architectural partition between its two primary business domains:

```text
+---------------------------------------------------+   +---------------------------------------------------+
|             VEHICLE IDEATHON ENGINE               |   |                 PLANT OPEX ENGINE                 |
+---------------------------------------------------+   +---------------------------------------------------+
| Target: The Vehicle / Product Manufactured        |   | Target: The Manufacturing Plants / Operations     |
| Input: 10,000+ Employee Improvement Submissions   |   | Input: Plant Consumption & Expenditure Records    |
| Core Question: "Is this valid, duplicate, already |   | Core Question: "Which plant is spending more than |
| implemented, applicable to other models, and what |   | its comparable benchmark, on what, why, and what |
| is the verified vehicle cost saving?"             |   | is the realistic opportunity to close the gap?"   |
| Math: Component Unit Savings * Annual Production  |   | Math: KPI Delta * Period Production Volume        |
+---------------------------------------------------+   +---------------------------------------------------+
```
*Rule: While these engines share foundational infrastructure (database, hybrid retrieval, local SLM runtime, frontend design system), their business domain services, calculation models, and evaluation criteria remain strictly isolated.*

---

## 4. Data Architecture & Master Entities
The data architecture relies on PostgreSQL 16 as the single relational source of truth:
- **Vehicle Master Hierarchy**: `PRODUCT_FAMILY` $\rightarrow$ `VEHICLE` $\rightarrow$ `VEHICLE_MODEL` $\rightarrow$ `VEHICLE_VARIANT` $\rightarrow$ `MODEL_GENERATION` $\rightarrow$ `MODEL_YEAR`.
- **Engineering Component Hierarchy**: `SUBSYSTEM` $\rightarrow$ `ASSEMBLY` $\rightarrow$ `COMPONENT` $\rightarrow$ `PART` $\rightarrow$ `MATERIAL` $\rightarrow$ `SUPPLIER`.
- **Operational & Manufacturing Records**: `PLANT`, `PRODUCTION_RECORD`, `BOM_RECORD`, `COMPONENT_COST`, `OPEX_RECORD`.
- **Change & Project Records**: `PROJECT`, `ENGINEERING_CHANGE` (ECN/ECR), `IMPLEMENTATION`.
- **Idea & Clustering Entities**: `IDEA` (raw text preserved immutable), `IDEA_CLUSTER`, `IDEA_EVALUATION`.
- **Governance & Audit**: `AUDIT_LOG`, `USER`, `ROLE`, `EVIDENCE_RECORD`.

---

## 5. Formal Plant OPEX Benchmark Methodology
The system eliminates the flawed assumption that "lowest cost = best benchmark". It introduces a formal domain service, **`BenchmarkMethodology`**, with four distinct operational benchmark modes:

```text
+---------------------------------------------------------------------------------------------------+
|                                      BENCHMARK MODES                                              |
+------------------------------+------------------------------+-------------------------------------+
| 1. BEST COMPARABLE PLANT     | 2. PEER GROUP BENCHMARK      | 3. HISTORICAL BASELINE & TARGET     |
| Identifies the top-performer | Calculates the normalized    | Compares plant against its own past |
| among plants sharing similar | median across plants in the  | performance or management-defined   |
| manufacturing scope and mix. | same structural peer cluster.| target efficiency goals.            |
+------------------------------+------------------------------+-------------------------------------+
```

### 5.1 Comparability Scoring Engine
Comparability between Plant $A$ and Plant $B$ is determined via a multi-dimensional weighted index:
$$\text{Comparability Index} = w_1 S_{\text{scope}} + w_2 S_{\text{volume}} + w_3 S_{\text{mix}} + w_4 S_{\text{shifts}} + w_5 S_{\text{utilization}}$$
- **Manufacturing Scope ($S_{\text{scope}}$)**: Binary and categorical alignment of operations (e.g. Press Shop + Paint Shop + Engine Assembly vs. Final Assembly Only). Non-comparable scopes are excluded.
- **Production Mix ($S_{\text{mix}}$)**: Ratio of complex models (premium 200cc+ / EV) vs. commuter 100cc models.
- **Operating Shifts & Days ($S_{\text{shifts}}$)**: Normalizes baseline energy/baseload overhead.
- **Power & Utility Tariffs**: Separates volume/efficiency gap from regional state electricity board rate variances.

### 5.2 Deterministic Variance Decomposition
$$\text{Total Expenditure Gap} = \text{Volume Variance} + \text{Rate/Tariff Variance} + \text{Operational Efficiency Gap}$$
Only the **Operational Efficiency Gap** is reported as addressable management opportunity.

---

## 6. Vehicle Ideathon Architecture
Processes 10,000+ raw employee ideas through an automated, evidence-grounded screening pipeline:
1. **Raw Submission Ingestion**: Preserves exact original text and attachments immutable.
2. **Entity Normalization**: Uses regex, synonym dictionaries, and semantic parsing to extract target part numbers, assemblies, subsystems, and vehicle models.
3. **Semantic Clustering**: Groups semantically equivalent proposals into canonical opportunity clusters to enable bulk screening.
4. **Deterministic Classification**: Categorizes proposals into cost reduction types (Material substitution, Geometry optimization, Process streamlining, Weight reduction, Supplier re-sourcing) and BOM vs. Non-BOM opportunities.

---

## 7. Implementation Detection Architecture
### Core Architectural Axiom:
> **"No Implementation Found" $\ne$ "Not Implemented"**  
> The absence of a search hit in an unstructured database is never treated as positive proof that an idea is new.

```text
IDEA SUBMISSION
      |
      v
ENTITY RESOLUTION (Part No, Subsystem, Model, Mechanism)
      |
      v
EXACT IDENTIFIER LOOKUP (PostgreSQL Trigram / B-Tree on ECN, ECR, Part Master)
      |
      +---> [Match Found in Active BOM] --------> IMPLEMENTATION CONFIRMED (CURRENT)
      |
      +---> [Match Found in Closed ECN/Project] -> HISTORICAL IMPLEMENTATION (DISCONTINUED/SUPERSEDED)
      |
      v
HIERARCHICAL TREE TRAVERSAL (Part -> Assembly -> Subsystem across Sibling Models)
      |
      +---> [Match Found on Sibling Model] ------> PARTIALLY CONFIRMED (CROSS-MODEL OPPORTUNITY)
      |
      v
HYBRID SEMANTIC SEARCH + CROSS-ENCODER RERANKING
      |
      +---> [High-Confidence Match] ------------> POTENTIAL IMPLEMENTATION EVIDENCE
      |
      v
AUTHORITATIVE EVIDENCE COMPLETENESS CHECK
      |
      +---> [All Authoritative Sources Present & Clear] -> NO IMPLEMENTATION EVIDENCE FOUND
      |
      +---> [Key BOM / ECN Records Missing or Dirty] ------> INSUFFICIENT EVIDENCE
      |
      +---> [ERP and PLM Records Disagree] ---------------> CONFLICTING EVIDENCE
```

---

## 8. Evidence & Policy Layer
Sitting directly between retrieval services and final business/AI decisioning, the **Evidence & Policy Layer** enforces governance and data integrity:

```text
+-----------------------------------------------------------------------------------------------+
|                                   EVIDENCE & POLICY LAYER                                     |
+-----------------------------------------------------------------------------------------------+
| 1. Evidence Aggregation: Packages exact DB records, ECN documents, and vector snippets.      |
| 2. SourceAuthorityPolicy: Resolves multi-source data precedence deterministically.            |
| 3. Conflict Detection: Flags discrepancies across enterprise systems before AI synthesis.     |
| 4. Freshness Validation: Enforces temporal relevance (`valid_from`, `valid_to`, model year).   |
| 5. Deterministic Confidence Scoring: Computes objective 8-factor score (HIGH, MEDIUM, LOW).    |
| 6. Safety & Quality Gate Enforcement: Non-bypassable flags for safety-critical components.     |
+-----------------------------------------------------------------------------------------------+
```

### 8.1 Source Authority Precedence Hierarchy
When multiple enterprise systems provide conflicting data, the system evaluates precedence via configurable domain rules:
- **Production Quantities**: ERP (SAP) $\succ$ Plant MES $\succ$ Manual Spreadsheet.
- **BOM & Engineering Release**: PLM (Teamcenter) $\succ$ ERP Master $\succ$ Local Plant BOM.
- **Part Costs**: Central Cost Database $\succ$ Purchase Order $\succ$ Idea Submission Estimate.
- **Implementation Status**: Approved ECN/ECR Record $\succ$ Project Milestone $\succ$ Historical Idea Note.

---

## 9. Hybrid Retrieval Architecture
Combines dense semantic representations with exact alphanumeric indexing and cross-encoder precision re-ranking:
- **Exact & Trigram Stream**: PostgreSQL `pg_trgm` and B-Tree indexes matching exact 10-digit part numbers, drawing codes, and ECN numbers with top-rank weight.
- **Dense Vector Stream**: PostgreSQL `pgvector` with HNSW cosine distance indexing, strictly partitioned by subsystem metadata.
- **Cross-Encoder Reranking**: Re-scores the top-25 candidate pool using a local cross-encoder model to eliminate semantic false positives.
- **Performance Framework**: Evaluated via structured baseline measurement (Measure $\rightarrow$ Optimize $\rightarrow$ Acceptance Threshold) tracking Recall@K, Precision, and latency separately.

---

## 10. AI / SLM Reasoning & In-Context Grounding
- **Role of the SLM**: Synthesizes verified evidence, explains plant variance drivers, summarizes implementation applicability, and generates structured JSON output.
- **Strict In-Context Grounding**: Zero temperature ($T=0.0$), prompt templates with structured evidence blocks placed at optimal positions to prevent lost-in-the-middle degradation.
- **Constrained Decoding**: Output is forced into strict Pydantic/JSON schemas using GBNF grammar constraints in the local runtime.
- **Zero Arithmetic Rule**: Financial savings and KPI ratios generated in JSON are validated against the deterministic `CalculationEngine`. If model numbers diverge, the Python calculation service overrides them automatically.

---

## 11. Local AI Runtime Architecture
An internal, self-contained inference engine built directly on `llama-cpp-python` / GGUF:
- **Hardware-Aware Profiler**: Detects host CPU cores, RAM, and GPU VRAM at boot and automatically configures execution mode:
  - `GPU_FULL_OFFLOAD`: 100% layers offloaded to GPU VRAM (e.g. 24GB+ VRAM).
  - `GPU_PARTIAL_OFFLOAD`: Splits layers between VRAM and system RAM.
  - `CPU_FALLBACK`: Executes quantized GGUF on host CPU using AVX-512 / NEON.
  - `DEGRADED_MODE`: Throttles context window size to preserve stability.
- **Zero External Telemetry**: Zero external network calls or cloud dependencies.

---

## 12. TASC IIoT Studio Asset Reuse Strategy
To avoid reinventing existing, proven internal software components, the platform integrates proven modules from **TASC IIoT Studio**:

| TASC Software Asset | Capability Description | Reuse Classification | Adaptation Required for Hero Platform | Development Effort Saved |
|---|---|---|---|---|
| **AI Provider Abstraction** | Unified protocol for chat, completion, and embeddings. | **REUSE AS-IS** | None. Drop-in protocol layer. | 3 Days |
| **`LlamaCppEngine` Core** | Local GGUF execution via `llama-cpp-python`. | **REFACTOR & REUSE** | Add dynamic VRAM profiling and multi-model budget allocation. | 5 Days |
| **GBNF Grammar Constraints** | Grammar-based JSON schema enforcement engine. | **REUSE AS-IS** | Register Hero-specific Pydantic schemas. | 4 Days |
| **Local RAG Pipeline & Chunking** | Document chunking, metadata tagging, and vector querying. | **REFACTOR & REUSE** | Reconfigure chunking for engineering ECNs and BOM records. | 4 Days |
| **Internal AI Studio UI** | Technical admin panel for model health, VRAM, and latency. | **REFACTOR & REUSE** | Brand with Hero dark/slate industrial theme. | 4 Days |
| **Virtualized Data Grid UI** | High-density table virtualizer for large industrial datasets. | **REUSE AS-IS** | Integrate with Ideathon and OPEX list views. | 3 Days |
| **Deterministic Ingestion Validator** | Staging, transactional rollback, and schema detection. | **REFACTOR & REUSE** | Add `MagnitudeAnomalyGuard` and canonical energy/cost units. | 4 Days |
| **Total Estimated Effort Saved** | — | — | — | **27 Engineering Days** |

*Excluded TASC Assets (Do Not Use)*: PLC connectors, MQTT brokers, SCADA canvas, industrial automation alarm historians, 3D SCADA graphics engine.

---

## 13. Security Architecture & Air-Gap Lifecycle
The security framework distinguishes three lifecycle environments:
1. **Connected Build / Preparation Environment**: Development workstations and CI/CD pipelines with approved access to package mirrors (pip, npm) and official GGUF model repositories.
2. **Controlled Artifact Transfer**: Secure packaging of all wheels, node modules, GGUF binaries, and database schemas into self-contained Docker images and offline tarballs.
3. **Air-Gapped Target Runtime**: Deployed in customer on-premise infrastructure with zero network egress, `internal: true` Docker networking, zero telemetry, and strict local JWT authentication.
4. **Audit Data Minimization**: Audit logs record metadata, hashes, and decision provenance. Full raw text is stored with configurable retention and PII redaction.

---

## 14. Reliability & FMEA Controls
- **Missed Implementation Prevention**: Multi-tier hierarchy traversal (Part $\rightarrow$ Assembly $\rightarrow$ Subsystem $\rightarrow$ Sibling Models) with mandatory human review for all medium-confidence cases.
- **Unit Error Defense (`MagnitudeAnomalyGuard`)**: Detects statistical scale anomalies in uploaded data (e.g. Lakhs vs. Rupees) and triggers interactive confirmation before database commit.
- **Citation Validator**: Discards model-generated claims if cited ECN or Part IDs do not match primary keys in the PostgreSQL database.
- **Circuit Breakers**: Hard bounds on agentic tool calling (`max_iterations = 4`, `timeout = 10s`) to prevent runaway loops.

---

## 15. Evaluation Strategy & Gold Dataset
System accuracy is measured against a frozen, human-labeled **Hero Gold Dataset**:
- **Deterministic Math Accuracy**: Target $100.00\%$ ($\pm 0.00\%$ arithmetic tolerance).
- **Missed Implementation Rate**: Target $< 2.0\%$ on benchmark dataset.
- **Duplicate Detection Recall@5**: Target $> 90\%$ on semantic test variations.
- **Model / Variant Mapping Accuracy**: Target $> 95\%$ on structured test cases.

---

## 16. POC Scope Boundary & Feature Tiers
- **Must Have**: PostgreSQL relational truth, OPEX benchmarking engine, Ideathon ingestion, hybrid retrieval, implementation applicability matrix, deterministic cost engine, local SLM integration (`LlamaCppEngine`), Evidence & Policy Layer, human review queue, executive UI.
- **Should Have**: Bounded agentic tool loop, interactive column reconciliation UI, Gold Dataset evaluation harness, internal AI Studio.
- **Nice to Have**: Exportable executive PDF summaries, batch duplicate cluster review.
- **Future Production**: Enterprise SAML/OIDC SSO, live SAP/Teamcenter PLM sync connectors, domain LoRA fine-tuning.
- **Removed / Forbidden**: Unrestricted LLM database access, LLM-based arithmetic, autonomous engineering sign-offs, external cloud APIs.

---

## 17. Master Implementation Phases (V3)

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
Phase 8: Evidence & Policy Layer (GATE-08)
Phase 9: Local SLM Decisioning & Local AI Gateway (GATE-09)
Phase 10: Human-in-the-Loop Review & Engineering Gate Queue (GATE-10)
Phase 11: Gold Dataset Evaluation & Benchmark Framework (GATE-11)
Phase 12: Executive UI, OPEX & Ideathon Dashboards (GATE-12)
Phase 13: Security Hardening & Air-Gap Compliance (GATE-13)

===================================================================================================
TRACK B: LOCAL AI RUNTIME WORKSTREAM (Parallel Track Reusing TASC Assets)
===================================================================================================
Track B.0: AI Provider Protocols & Interface Drop-in (Reused from TASC)
Track B.1: Dev Ollama Provider Adapter (For early test fixtures)
Track B.2: Internal LlamaCppEngine Implementation (Reused & adapted from TASC)
Track B.3: Hardware Profiler & Dynamic VRAM Offloader
Track B.4: GBNF Grammar & JSON Schema Constrained Decoding (Reused from TASC)
Track B.5: Sandboxed Tool Registry & Policy Enforcement Engine
Track B.6: Internal AI Studio UI (Reused & rebranded from TASC)
```

---

## 18. Parallel Workstream Plan
- **Track A (Data & Core Logic)** and **Track B (Runtime & Tooling)** execute concurrently from Day 1.
- **Frontend Scaffolding** runs in parallel with backend database migrations using mock contracts.
- **Evaluation Benchmark Curation** runs in parallel with hybrid retrieval optimization.

---

## 19. Decision Gates & Milestones
- `GATE-00`: Architecture & Baseline Sign-off.
- `GATE-01`: Data Foundation & Relational Schema Verified.
- `GATE-02`: Ingestion Reliability & `MagnitudeAnomalyGuard` Verified.
- `GATE-03`: OPEX Benchmark Methodology & KPI Math Verified.
- `GATE-04`: Ideathon Ingestion & Entity Normalization Verified.
- `GATE-05`: Hybrid Retrieval Recall Benchmark Verified.
- `GATE-06`: Implementation Applicability Matrix Verified.
- `GATE-07`: Deterministic Cost Opportunity Math Verified.
- `GATE-08`: Evidence & Policy Layer Sign-off.
- `GATE-09`: Local SLM Structured Output & Grammar Verified.
- `GATE-10`: Human Review Queue & Safety Gates Verified.
- `GATE-11`: Gold Dataset Evaluation Report Signed Off.
- `GATE-12`: Executive UI Client Demo Scenarios Verified.
- `GATE-13`: Air-Gap Compliance & Production Readiness Verified.

---

## 20. Risk Register & Key Mitigations
1. **Missed Implementation** $\rightarrow$ Traversal across Part, Assembly, and Sibling Models with mandatory review on low confidence.
2. **Calculation Unit Skew** $\rightarrow$ `MagnitudeAnomalyGuard` statistical distribution validation.
3. **AI Hallucination** $\rightarrow$ Database-validated source citations and pure Python calculation services.
4. **VRAM Exhaustion** $\rightarrow$ Hardware profiler with dynamic CPU layer offloading.
5. **Air-Gap Egress Leak** $\rightarrow$ Container-level network isolation (`internal: true`) and zero telemetry flags.

---

## 21. Technology Decisions Matrix
- **Core Database**: PostgreSQL 16 with `pgvector` (HNSW) and `pg_trgm`.
- **Backend API**: Python 3.11+ / FastAPI with Pydantic v2.
- **Frontend SPA**: React 18+ / Vite with Vanilla CSS industrial design tokens.
- **Inference Foundation**: Internal `LlamaCppEngine` (GGUF Q4_K_M).
- **Candidate Models**: Qwen3.5-9B (SLM), Qwen3-Embedding-0.6B (Embeddings), Qwen3-Reranker-0.6B (Reranker).

---

## 22. Future Post-POC Roadmap
- **Phase 14**: Enterprise SSO Integration (SAML 2.0 / OIDC / Azure AD).
- **Phase 15**: Live ERP & PLM Connectors (SAP S/4HANA & Teamcenter read-only adapters).
- **Phase 16**: Domain-Specific LoRA Fine-Tuning (Hero engineering jargon and classification styles).
- **Phase 17**: High-Availability Multi-Node Database Clustering.
