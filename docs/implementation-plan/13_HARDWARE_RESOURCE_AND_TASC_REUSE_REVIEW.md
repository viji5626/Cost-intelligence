# 13 — Hardware Resource Management & TASC IIoT Studio Reuse Review

## 1. Executive Summary
This document provides the technical hardware resource engineering and code-level asset reuse evaluation for **Master Implementation Plan V3.1**. It specifically addresses:
1. Grounding the platform's execution architecture on the real-world POC development machine (**AMD Ryzen AI 9 HX 370, 16 GB System RAM, NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM**).
2. Establishing dynamic RAM, VRAM, and CPU resource management with hardware-aware model tiers and multi-model lifecycle swapping.
3. Conducting a structured capability-level and code-level reuse assessment of **TASC IIoT Studio V3** (https://github.com/viji5626/TASC_IIoT_Studio_V3), distinguishing clean extractable infrastructure from domain-specific industrial automation logic.

---

## 2. Hardware Resource Profiling & Sizing Analysis

### 2.1 Reference Machine Sizing Profile (POC Development Machine)

```text
+---------------------------------------------------------------------------------------------------+
|                                  POC REFERENCE HARDWARE PROFILE                                   |
+---------------------+---------------------------------------------+-------------------------------+
| SUBSYSTEM           | SPECIFICATION                               | SYSTEM RESERVATION / LIMIT    |
+---------------------+---------------------------------------------+-------------------------------+
| **Processor (CPU)** | AMD Ryzen AI 9 HX 370 (12 Cores / 24 Threads)| Reserve 4 cores for OS/DB/API |
| **System RAM**      | 16 GB LPDDR5x / DDR5                        | 4 GB OS/Apps + 3 GB DB/App    |
|                     |                                             | Max Available for AI: ~9 GB   |
| **Dedicated GPU**   | NVIDIA GeForce RTX 4060 Laptop GPU          | 1.0 GB Windows Desktop/DWM    |
| **Dedicated VRAM**  | 8 GB GDDR6 (128-bit bus)                    | Usable VRAM for AI: ~6.8 GB   |
| **Storage**         | High-Speed NVMe SSD                         | Configurable model directory  |
+---------------------+---------------------------------------------+-------------------------------+
```

---

### 2.2 First-Class System RAM Budgeting
System RAM is a hard constraint on a 16 GB machine. Memory must be statically and dynamically partitioned to prevent host swapping, out-of-memory (OOM) kernel kills, and application crashes:

```text
+---------------------------------------------------------------------------------------------------+
|                                 16 GB SYSTEM RAM BUDGET PARTITION                                 |
+------------------------------------+------------------+-------------------------------------------+
| WORKLOAD / SUBSYSTEM               | RAM ALLOCATION   | OPERATIONAL DESCRIPTION                   |
+------------------------------------+------------------+-------------------------------------------+
| **Host OS & Background Services**  | 3.5 GB – 4.0 GB  | Windows 11 kernel, desktop DWM, drivers.   |
| **PostgreSQL 16 Database**         | 1.0 GB – 1.5 GB  | `shared_buffers = 512MB`, `work_mem = 64MB`|
| **FastAPI Backend & Python App**   | 1.0 GB – 1.5 GB  | Uvicorn workers, Pydantic schemas, ORM.   |
| **Data Ingestion Buffer**          | 0.5 GB – 1.0 GB  | Excel streaming parser (`calamine`), temp.|
| **React / Browser Client (Local)** | 1.0 GB – 1.5 GB  | Local Chromium tab memory footprint.      |
| **Safety Reserve / Margin**        | 1.0 GB           | Unallocated headroom to prevent OOM panic.|
| **TOTAL NON-AI HOST OVERHEAD**     | **~8.0 GB**      | **Mandatory baseline before AI loading.** |
| **MAX SAFE RAM FOR LOCAL AI / KV** | **~8.0 GB**      | **Available for model weights & context.**|
+------------------------------------+------------------+-------------------------------------------+
```

---

### 2.3 Dynamic VRAM Management & Tiered Execution Modes
On an 8 GB VRAM GPU, usable VRAM is $\approx 6.8\text{ GB}$ after Windows Desktop Window Manager (DWM) allocation. The runtime cannot naively execute `n_gpu_layers = -1` on a 9B model without overflowing into slow system shared memory.

```text
                                  +---------------------------------------+
                                  |        HARDWARE PROFILER AT BOOT      |
                                  | - Detect Total & Free VRAM            |
                                  | - Detect Total & Free System RAM      |
                                  | - Detect CPU Architecture & Cores     |
                                  +---------------------------------------+
                                                      |
                                                      v
                             +-------------------------------------------------+
                             |             EXECUTION MODE SELECTION            |
                             +-------------------------------------------------+
                             |                                                 |
            +----------------+----------------+---------------+----------------+
            |                                 |               |                |
            v                                 v               v                v
+-----------------------+ +-----------------------+ +---------------+ +---------------+
|   GPU_FULL_OFFLOAD    | |  GPU_PARTIAL_OFFLOAD  | | CPU_FALLBACK  | | DEGRADED_MODE |
| - Model weights < 5GB | | - 7B/8B/9B Q4 models  | | - Zero GPU or | | - RAM < 2GB   |
| - 100% layers in VRAM | | - Offload 20-28 layers| |   CUDA OOM    | | - Minimal 1k  |
| - Fast inference      | | - Balance in host RAM | | - AVX2/AVX-512| |   context     |
+-----------------------+ +-----------------------+ +---------------+ +---------------+
```

---

### 2.4 Hardware-Aware Model Resource Tiers

| Resource Tier | Target Hardware Profile | Candidate Reasoning SLM | Candidate Embedding Model | Candidate Cross-Encoder | Default Context Window | Execution Strategy |
|---|---|---|---|---|---|---|
| **Tier 1: Low Resource (Entry/Laptop)** | **16 GB RAM / 8 GB VRAM** *(Current POC Machine)* | **Qwen2.5-3B-Instruct (Q4_K_M, ~2.2GB)** or **Qwen2.5-7B (Q3_K_M, ~3.8GB)** | **Qwen3-Embedding-0.6B (FP16, ~1.1GB)** or FastEmbed (CPU) | **Qwen3-Reranker-0.6B (~1.2GB)** | **2,048 – 4,096 tokens** | **Sequential Model Swapping** or Hybrid Partial Offload. |
| **Tier 2: Medium Resource (Standard Workstation)** | **32 GB RAM / 16 GB VRAM** | **Qwen2.5-7B / Qwen3.5-9B (Q4_K_M, ~5.5GB)** | Qwen3-Embedding-0.6B (GPU resident) | Qwen3-Reranker-0.6B (GPU resident) | **4,096 – 8,192 tokens** | Full GPU Offload; Concurrent Resident Models. |
| **Tier 3: High Resource (Enterprise Server)** | **64 GB+ RAM / 24 GB – 48 GB+ VRAM** | **Qwen2.5-14B / Qwen3.5-9B (Q5_K_M / Q8_0)** | BGE-M3 / Qwen3-Embedding (GPU resident) | BGE-Reranker-Large (GPU resident) | **8,192 – 16,384 tokens** | Full GPU Offload with High-Throughput Batching. |

---

### 2.5 Multi-Model Resource Lifecycle Management (8 GB GPU Profile)
On an 8 GB GPU, attempting to concurrently hold a 9B SLM ($\sim 5.5\text{ GB}$), an embedding model ($\sim 1.2\text{ GB}$), a cross-encoder reranker ($\sim 1.4\text{ GB}$), and a 4k context KV-cache ($\sim 1.0\text{ GB}$) totals $\sim 9.1\text{ GB}$, causing immediate CUDA Out-of-Memory.

```text
+---------------------------------------------------------------------------------------------------+
|                        SEQUENTIAL MULTI-MODEL LIFECYCLE (8 GB VRAM PROFILE)                       |
+---------------------------------------------------------------------------------------------------+
| STEP 1: HYBRID INGESTION & EMBEDDING                                                              |
| - Load Embedding Model (VRAM: ~1.2 GB) -> Generate Embeddings -> Persist to pgvector              |
| - Unload Embedding Model from VRAM                                                                |
|                                                                                                   |
| STEP 2: HYBRID SEARCH & RERANKING                                                                 |
| - Retrieve Top-50 candidates via exact trigram + pgvector cosine search                           |
| - Load Cross-Encoder Reranker (VRAM: ~1.4 GB) -> Re-score top candidates -> Output Top-5 evidence  |
| - Unload Reranker from VRAM                                                                       |
|                                                                                                   |
| STEP 3: SLM EVIDENCE SYNTHESIS & STRUCTURED REASONING                                             |
| - Load Reasoning SLM (VRAM: ~4.5 GB) -> Construct bounded prompt (< 2.5k tokens)                  |
| - Execute GBNF constrained structured generation -> Output validated JSON schema                  |
| - Model remains resident during interactive session with 10-minute idle TTL                       |
+---------------------------------------------------------------------------------------------------+
```

---

### 2.6 CPU Core Allocation Strategy (AMD Ryzen AI 9 HX 370)
The AMD Ryzen AI 9 HX 370 features 12 cores / 24 threads (4 Zen 5 performance cores + 8 Zen 5c dense cores). To prevent CPU starvation during local inference and database operations:
- **FastAPI / Uvicorn Web Server**: 2 Cores.
- **PostgreSQL 16 & Background Workers**: 2 Cores.
- **Data Ingestion & Excel Parsing (`calamine`)**: 2 Cores.
- **Local AI Inference (`llama-cpp` thread pool)**: Configured to `n_threads = 6` (pinned to Zen 5 performance cores).
- **Host OS & GUI Headroom**: Remaining threads.

---

## 3. TASC IIoT Studio V3 Capability-Level & Code-Level Reuse Assessment

### 3.1 Context & Architectural Boundary
- **Reference Asset**: **TASC IIoT Studio V3** (https://github.com/viji5626/TASC_IIoT_Studio_V3).
- **Boundary Rule**: TASC IIoT Studio is an existing, independent software asset. It is **NOT** a runtime dependency of the Hero Plant Cost Intelligence platform. The new platform will be 100% self-contained and independently deployable.
- **Assessment Approach**: We evaluate TASC modules for clean extraction, refactoring, or architectural pattern reuse to avoid rebuilding generic AI/data infrastructure from scratch.

---

### 3.2 Detailed TASC Capability & Code-Level Reuse Matrix

| TASC Module / Asset Category | Specific Capability | Current Purpose in TASC | External Dependencies | Reuse Decision | Required Changes for Hero Cost Platform | Target Destination in New Project | Testing Required | Risk Level | Indicative Benefit |
|---|---|---|---|---|---|---|---|---|---|
| **`ai_engine / provider`** | `AIProvider` & `InferenceEngine` base protocols | Abstract interface for chat, completion, embeddings | None (Pure Python Protocols) | **REUSE AS-IS** | None. Drop in as foundational abstraction. | `ai/providers/base.py` | Interface compliance unit tests | Low | Eliminates 3 days of interface design. |
| **`ai_engine / llama_cpp`** | `LlamaCppEngine` runtime adapter | Direct GGUF model execution via `llama-cpp-python` | `llama-cpp-python`, GGUF | **REFACTOR & REUSE** | Add Hardware Profiler, dynamic VRAM offloading, and idle memory release TTL. | `ai/runtime/llama_cpp_engine.py` | GGUF loading, VRAM allocation & release tests | Med | Saves ~6 days of C++ binding integration. |
| **`ai_engine / grammar`** | GBNF Grammar Engine & JSON schema compiler | Constrains LLM sampling logits to strict Pydantic JSON schemas | `pydantic`, `json` | **REUSE AS-IS** | Register Hero-specific Ideathon & OPEX Pydantic schemas. | `ai/grammar/gbnf_compiler.py` | Schema compliance & invalid token rejection tests | Low | Saves ~4 days of grammar compiler work. |
| **`ai_engine / rag`** | Local RAG Pipeline & Chunking Utilities | Text chunking, metadata injection, dense similarity querying | `numpy`, `pgvector` | **REFACTOR & REUSE** | Adapt chunking strategies for engineering ECNs, BOM tables, and multi-sheet plant spreadsheets. | `retrieval/rag/chunker.py`, `retrieval/rag/pipeline.py` | Chunk boundary and metadata preservation tests | Med | Saves ~4 days of RAG pipeline plumbing. |
| **`ai_engine / tools`** | Sandboxed Tool Registry & Policy Engine | Validates parameters, enforces execution timeouts, logs calls | `pydantic`, `asyncio` | **REFACTOR & REUSE** | Connect to Hero domain tools (`search_implementations`, `get_bom_cost`, `check_safety_gate`). | `ai/tools/registry.py`, `ai/tools/policy.py` | Parameter validation, timeout & loop breaker tests | Med | Saves ~4 days of tool orchestration setup. |
| **`frontend / studio`** | AI Studio Technical Admin UI | Model status, hardware monitor (RAM/VRAM), prompt playground | React, Lucide Icons | **REFACTOR & REUSE** | Rebrand with Hero industrial dark theme; connect to local API endpoints. | `frontend/src/modules/ai-studio/` | React component tests, live hardware telemetry rendering | Low | Saves ~5 days of admin UI development. |
| **`frontend / grid`** | Virtualized Data Grid Component | High-density rendering of large industrial tables (> 10k rows) | React, `tanstack-virtual` | **REUSE AS-IS** | Style table headers and cells for Ideathon and OPEX list views. | `frontend/src/components/common/VirtualGrid.tsx` | 10,000 row scroll performance (< 16ms frame) | Low | Saves ~3 days of grid virtualization work. |
| **`data / ingestion`** | Staging & Ingestion Pipeline Base | Temporary upload staging, file hash verification, atomic commit | `calamine`, `openpyxl` | **REFACTOR & REUSE** | Inject `MagnitudeAnomalyGuard` and canonical energy/currency unit converters. | `backend/services/ingestion_service.py` | Corrupt file recovery, unit scaling tests | Med | Saves ~4 days of upload plumbing. |
| **`scada / plc / mqtt`** | Industrial Protocol Drivers & Alarm Historian | Modbus, OPC-UA, MQTT, real-time alarm state machine | Paho MQTT, AsyncModbus | **DO NOT USE (EXCLUDED)** | None. SCADA protocols are entirely irrelevant to Ideathon & OPEX financial analytics. | *None (Omitted)* | N/A | High if imported | Prevents architectural contamination. |
| **`graphics / 3d_canvas`** | 3D SCADA Plant Canvas | WebGL/Three.js rendering of factory equipment | Three.js | **DEFER (POST-POC)** | Defer 3D vehicle assembly viewer to future post-POC roadmap. | *None in POC* | N/A | Med | Protects POC focus. |

*Total Indicative Acceleration from TASC Asset Reuse: **~27–30 Engineering Days (To be validated during implementation).***

---

## 4. Architectural Summary: V3.1 Hardware-Aware Execution Envelope

```text
+---------------------------------------------------------------------------------------------------+
|                            V3.1 ADAPTIVE HARDWARE RESOURCE ENVELOPE                               |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [APPLICATION BOOT]                                                                               |
|         |                                                                                         |
|         v                                                                                         |
|  [HARDWARE PROFILER] ---> Queries Host: AMD Ryzen AI 9 (12C/24T), 16GB RAM, RTX 4060 (8GB VRAM)   |
|         |                                                                                         |
|         +---> Configures System Budget: Max 8GB RAM for AI | Max 6.8GB VRAM for AI                 |
|         +---> Selects Resource Tier: TIER 1 (LOW RESOURCE / LAPTOP PROFILE)                       |
|         +---> Selects Models: Qwen2.5-7B (Q3_K_M) / Qwen2.5-3B (Q4_K_M) + Qwen3-Embedding (0.6B)  |
|         +---> Configures Context Window: 4,096 Tokens Baseline                                    |
|         +---> Selects Multi-Model Strategy: SEQUENTIAL ON-DEMAND SWAPPING                         |
|         +---> Pins CPU Worker Threads: n_threads = 6 (Zen 5 Performance Cores)                    |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```
