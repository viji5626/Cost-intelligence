# 14 — V3 to V3.1 Architecture Hardening & Resource Change Log

## 1. Executive Overview
This change log documents the precise architectural hardening and resource management refinements made during the transition from **Implementation Plan V3** (`08_REVISED_IMPLEMENTATION_PLAN_V3.md`) to **Master Implementation Plan V3.1** (`09_REVISED_IMPLEMENTATION_PLAN_V3_1.md`).

All changes ground the execution architecture in the real-world POC development machine (**AMD Ryzen AI 9 HX 370, 16 GB RAM, NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM**), establish dynamic RAM/VRAM memory budgets, formalize sequential multi-model lifecycle swapping, and detail code-level asset reuse from **TASC IIoT Studio V3**.

---

## 2. Detailed Change Matrix (V3 $\rightarrow$ V3.1)

| ID | Architectural Area | V3 Baseline | Identified Vulnerability / Defect | V3.1 Hardened Change | Architectural Rationale & Benefit | POC Impact |
|---|---|---|---|---|---|---|
| **V3.1-01** | **GPU VRAM & Model Sizing** | Assumed 9B model running concurrently with Embedding & Reranker in VRAM. | Concurrently loading 9B SLM + Embedding + Reranker + KV cache exceeds 8 GB VRAM, causing CUDA OOM crash. | **Introduced Hardware Resource Tiers & Sequential Multi-Model Lifecycle.** Tier 1 (16GB RAM/8GB VRAM) uses Qwen2.5-3B (Q4_K_M) or Qwen2.5-7B (Q3_K_M) with sequential on-demand swapping (`LOAD -> PROCESS -> RELEASE`). Tier 2/3 scale to 9B/14B on 24GB+ hardware. | Guarantees stable, crash-free execution on 8GB laptop GPUs while preserving scaling capability for servers. | High (Fixes GPU crash risk). |
| **V3.1-02** | **System RAM Budgeting** | Treated VRAM as the primary memory constraint; lacked explicit host RAM partition. | On a 16 GB host, OS (4GB) + DB (1.5GB) + Backend (1.5GB) + Browser (1.5GB) leaves $\approx 7.5\text{ GB}$ for AI. Unbounded RAM allocations cause OS paging and system freeze. | **Formally Partitioned 16 GB System RAM.** Allocated explicit budgets: OS (4.0GB), PostgreSQL (1.5GB), FastAPI (1.5GB), Ingestion (1.0GB), Browser (1.0GB), AI Safety Reserve (1.0GB), leaving $\approx 6.0\text{ GB}$ maximum safe RAM for AI process. | Protects host OS and PostgreSQL database from memory starvation. | Medium (Adds memory budget enforcement). |
| **V3.1-03** | **CPU Core Allocation** | Unconstrained multi-threaded inference on host CPU. | AMD Ryzen AI 9 HX 370 has 12 cores (4 Zen 5 + 8 Zen 5c). Uncontrolled thread pools starve web server and database workers. | **Implemented Explicit CPU Core Pinning Strategy.** Pinned `llama-cpp` inference to 6 threads on Zen 5 performance cores; dedicated 2 cores for DB and 2 cores for web workers. | Eliminates CPU contention and keeps API responsive during heavy AI generation. | Low (Performance tuning). |
| **V3.1-04** | **TASC IIoT Studio Code-Level Reuse** | High-level conceptual reuse mentioned in V3. | Needed explicit module-level classification, dependency mapping, and integration boundary. | **Completed Detailed Code-Level Reuse Matrix.** Classified exact TASC assets: `AIProvider` (Reuse As-Is), `LlamaCppEngine` (Refactor & Reuse), `GBNF Grammar` (Reuse As-Is), `Local RAG` (Refactor & Reuse), `AI Studio UI` (Refactor & Rebrand), `Virtualized Data Grid` (Reuse As-Is), `SCADA/PLC/MQTT` (Excluded). | Accelerates development by an indicative ~27 engineering days without architectural contamination. | High (Reduces implementation effort). |
| **V3.1-05** | **Context Window Sizing** | V3 allowed context windows up to 8k tokens. | 8k context on 7B/9B models inflates KV-cache VRAM usage by over 2.0 GB. | **Set Dynamic Context Window Sizing by Hardware Tier.** Low-Resource Tier (8GB VRAM) defaults to 2,048 – 4,096 tokens; relies on strict hybrid retrieval and reranking to fit evidence into compact prompts (< 2.5k tokens). | Reduces KV-cache footprint while maintaining high retrieval precision. | Medium (Optimizes context efficiency). |
| **V3.1-06** | **Performance & Latency Claims** | Converted SLAs to measurement targets in V3. | Kept from V3. Re-emphasized that all latency/throughput claims are subject to local benchmarking. | **NO CHANGE (Preserved from V3).** | Maintains rigorous engineering baseline methodology. | None. |
| **V3.1-07** | **Evidence & Policy Layer** | Introduced in V3. | Core architecture sound; preserved intact. | **NO CHANGE (Preserved from V3).** | Ensures clean separation between retrieval, policy rules, and SLM synthesis. | None. |
| **V3.1-08** | **BenchmarkMethodology & SourceAuthorityPolicy** | Introduced in V3. | Formally validated as robust; preserved intact. | **NO CHANGE (Preserved from V3).** | Preserves transparent, auditable multi-plant benchmarking and data precedence. | None. |
| **V3.1-09** | **Implementation State Taxonomy** | Introduced in V3 (`NO_EVIDENCE_FOUND` $\ne$ `NOT_IMPLEMENTED`). | Preserved intact. | **NO CHANGE (Preserved from V3).** | Protects system against false "new" decisions. | None. |
| **V3.1-10** | **Modular Monolith Architecture** | Preserved from V2/V3. | Validated as the optimal architectural pattern for air-gapped on-premise deployment. | **NO CHANGE (Preserved from V3).** | Avoids microservice sprawl. | None. |

---

## 3. Preserved Sound Decisions from V3
- Strict partition between **Vehicle Ideathon Intelligence** and **Plant OPEX Benchmarking**.
- **Pure Python Deterministic Calculation Engine** for all financial, unit savings, ROI, and KPI arithmetic (Zero LLM math).
- **PostgreSQL 16 + `pgvector`** for unified relational master truth and dense vector search.
- **Dedicated Evidence & Policy Layer** for multi-source conflict resolution, freshness checks, and safety gate triggers.
- **Three-Tier Air-Gap Lifecycle** (Connected Build $\rightarrow$ Controlled Artifact Transfer $\rightarrow$ Air-Gapped Runtime).
