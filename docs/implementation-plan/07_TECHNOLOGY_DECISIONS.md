# 07 — Technology Decision Matrix & Model Runtime Architecture

## 1. Comprehensive Technology Decision Matrix

| Purpose | Candidate | Alternative(s) | Recommendation | Justification (Why) | Scope | Lock-in Risk | Migration Risk | Complexity |
|---|---|---|---|---|---|---|---|---|
| **Relational Database** | PostgreSQL 16 | MySQL, Oracle, SQL Server | **PostgreSQL 16** | Robust ACID compliance, native recursive CTEs, JSONB support, and seamless `pgvector` extension integration. | POC & Prod | None (ANSI SQL) | Low | Low |
| **Vector Storage** | `pgvector` (HNSW) | Milvus, Qdrant, Pinecone | **`pgvector`** | Keeps vectors transactional with relational master data. Eliminates data sync lag and extra database container management. | POC & Prod | None | Low | Low |
| **Relationship Modeling** | PostgreSQL Relational + CTEs | Neo4j, AWS Neptune | **PostgreSQL Relational + CTEs** | Vehicle and assembly hierarchies have fixed depth (< 8 levels). Standard SQL recursive CTEs satisfy all query requirements. | POC & Prod | None | Low | Low |
| **Backend API Framework** | FastAPI (Python 3.11+) | Django, Flask, Go/Gin, Node/Express | **FastAPI** | High-performance async support, automated OpenAPI docs, native Pydantic v2 validation, and rich Python AI/data ecosystem. | POC & Prod | None | Low | Low |
| **Frontend Framework** | React 18+ (Vite) | Next.js, Vue, Angular | **React + Vite (SPA)** | Blazing fast client-side routing, instant HMR, lightweight static build, perfectly suited for air-gapped enterprise dashboard deployment. | POC & Prod | Low | Low | Low |
| **Production Local SLM Runtime** | `llama-cpp-python` / `llama.cpp` | Ollama, vLLM, TensorRT-LLM | **`llama-cpp-python` (Internal)** | Pure local GGUF execution, zero external daemon requirement, fine-grained control over GPU offloading, grammar-constrained decoding. | Production Target | None (Open GGUF) | Low | Med |
| **Dev / Benchmarking Runtime** | Ollama | LM Studio, LocalAI | **Ollama (Dev Only via Adapter)** | Accelerated initial development and benchmarking before internal `LlamaCppEngine` binary compilation is finalized. | Dev Only | Zero (Isolated Adapter) | Zero | Low |
| **Reasoning Model (SLM)** | Qwen3.5-9B (GGUF Q4_K_M) | Llama-3.1-8B, Mistral-7B | **Qwen3.5-9B Candidate** | State-of-the-art multilingual reasoning, native tool calling, strong JSON schema adherence, and fits comfortably in 24GB VRAM. | POC Candidate | None (Model Agnostic) | Low | Med |
| **Embedding Model** | Qwen3-Embedding-0.6B | bge-large-en, all-MiniLM-L6-v2 | **Qwen3-Embedding Candidate** | High semantic retrieval precision on engineering and domain-specific terminology; ultra-compact VRAM footprint (< 1GB). | POC Candidate | None | Low | Low |
| **Cross-Encoder Reranker** | Qwen3-Reranker-0.6B | bge-reranker-large, Cohere | **Qwen3-Reranker Candidate** | Substantial precision boost over raw vector similarity; low latency (< 150ms for top-25 candidate pool). | POC Candidate | None | Low | Low |
| **External Interoperability** | Model Context Protocol (MCP) | Custom REST plugins, gRPC | **Optional MCP Adapter** | Standardized protocol for external tool connectivity without hardcoding integration logic into the core business engine. | Optional / Post-POC | Low | Low | Med |

---

## 2. Model Strategy & Capabilities

```text
+---------------------------------------------------------------------------------------------------+
|                                      MODEL INFERENCE SUITE                                        |
+------------------------------------+----------------------------------+---------------------------+
| REASONING MODEL                    | EMBEDDING MODEL                  | CROSS-ENCODER RERANKER    |
| Candidate: Qwen3.5-9B (GGUF)       | Candidate: Qwen3-Embedding-0.6B  | Candidate: Qwen3-Reranker |
| VRAM Footprint: ~14 GB (Q4_K_M)    | VRAM Footprint: ~1.2 GB (FP16)   | VRAM Footprint: ~1.5 GB   |
| Purpose: Synthesis, Classification,| Purpose: Dense vector embedding  | Purpose: High-precision   |
| Explanation, Structured JSON Output| generation for hybrid search.    | re-ranking of top-K pool. |
+------------------------------------+----------------------------------+---------------------------+
```

### Critical Model-Agnostic Guarantee:
The business platform interacts with models exclusively via abstract capability protocols (`AIProvider`, `InferenceEngine`, `EmbeddingProvider`, `RerankerProvider`). If a new open-weights model supersedes Qwen (e.g. Llama-4), the model binary can be swapped in the local model registry without altering a single line of business logic.

---

## 3. Layered Model Runtime Abstraction

```text
+-----------------------------------------------------------------------------------------------+
|                                      BUSINESS APPLICATION                                     |
|                      (IdeathonService / PlantOpexService / RetrievalService)                  |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                                    AI PROVIDER INTERFACE                                      |
|  - chat(messages, tools, response_schema)         - embed(texts)                              |
|  - generate_structured(prompt, schema)            - rerank(query, candidates)                 |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                                      LOCAL AI GATEWAY                                         |
|  - Capability Routing (Text, Tool, Structured)    - Tool Policy & Authorization Engine        |
|  - Context Assembler & Lost-in-the-Middle Guard   - Request Tracing & Audit Logging           |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                                  INFERENCE ENGINE ADAPTERS                                    |
|  +-------------------------------------------------+   +------------------------------------+ |
|  | LlamaCppEngine (Production Internal Target)     |   | OllamaProvider (Dev / Benchmark)   | |
|  | - Direct GGUF loading via llama-cpp-python      |   | - HTTP client to local Ollama      | |
|  | - Hardware-aware VRAM offloading                |   | - Fast local prototyping           | |
|  | - Grammar / GBNF constrained JSON decoding      |   | - Isolated development adapter     | |
|  +-------------------------------------------------+   +------------------------------------+ |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                                    LOCAL HARDWARE LAYER                                       |
|                           (NVIDIA CUDA / Apple Metal / Host CPU)                              |
+-----------------------------------------------------------------------------------------------+
```

---

## 4. Local AI Runtime Scope Boundary

### Included in Production Scope:
- Model Registry: Checksum validation, metadata parsing, capability discovery, quarantine directory.
- Model Lifecycle: Dynamic loading, unloading, context clearing, GPU VRAM allocation.
- Structured Decoding: Strict JSON schema enforcement via GBNF grammars / constrained logits.
- Sandboxed Tool Execution: Parameter validation, execution limits (`max_iterations = 4`, `timeout = 10s`).
- Hardware Monitoring: VRAM and CPU RAM utilization reporting.
- Internal AI Studio: Technical developer interface for prompt testing, model health, and latency benchmarking.

### Excluded / Deferred from Scope:
- Cloud model synchronization or automatic internet weight downloading.
- Multi-node distributed inference clustering.
- Real-time LoRA fine-tuning GUI.
- Complex multimodal video analysis.
