# 06 — Scope-Drift, Over-Engineering & Simplification Review

## 1. Scope-Drift & Over-Engineering Audit

| Proposed Architecture Component | Evaluation Question | Decision | Justification & Architectural Boundary |
|---|---|---|---|
| **Custom C++ Runtime in Phase 1** | Do we need to build the C++ inference engine before validating business logic? | **DEFER (Track B Parallel)** | Decouple business logic from low-level C++ compilation. Implement clean `InferenceEngine` interface; stabilize `LlamaCppEngine` in parallel Track B. |
| **Model Fine-Tuning (LoRA / QLoRA)** | Should model weights be updated with Hero vehicle parts and costs? | **REMOVE FROM POC** | Changing enterprise facts (BOM, costs, ECNs) belong in SQL and RAG. Fine-tuning on volatile facts causes hallucinations and catastrophic forgetting. |
| **Dedicated Graph Database (Neo4j)** | Is a specialized graph database necessary for vehicle hierarchies? | **REMOVE (Use PostgreSQL)** | Vehicle breakdowns (Family -> Model -> Variant -> Subsystem -> Part) are fixed-depth trees easily modeled in PostgreSQL with recursive CTEs. |
| **Recursive Language Models (RLM)** | Is multi-pass recursive LLM analysis needed for 10k ideas? | **DEFER** | Fast semantic clustering followed by single-pass grounded synthesis handles 10,000 ideas reliably at 1/10th the computational cost. |
| **Multiple AI Autonomous Agents** | Do we need an army of collaborating autonomous agents? | **REMOVE** | Multi-agent swarms introduce non-deterministic execution loops, race conditions, and debugging complexity. A single bounded retrieval agent with strict tools is superior. |
| **Distributed Microservices Mesh** | Should backend features be split across 5+ microservices? | **REMOVE (Use Modular Monolith)** | Distributed microservices add Docker overhead, serialization latency, and network failure points. A clean FastAPI modular monolith is fast, testable, and robust. |
| **Model Context Protocol (MCP)** | Should core business logic run through external MCP servers? | **OPTIONAL (Interoperability Only)** | Core business tools must be native internal Python services for reliability. MCP is maintained strictly as an optional external integration layer. |
| **Multimodal OCR / Vision Engine** | Do we need full multimodal computer vision for POC? | **OPTIONAL / DEFER** | Over 95% of Ideathon ideas and OPEX records are digital tabular data. Basic text extraction is sufficient; complex vision can be deferred. |
| **Full Enterprise SSO (SAML / OIDC)** | Is corporate LDAP / Okta SSO integration required for POC? | **DEFER** | Standalone JWT authentication with local database users satisfies all POC security and RBAC requirements. |
| **Production High-Availability (HA) Cluster** | Do we need active-active database clustering for POC? | **DEFER** | Single PostgreSQL 16 container with local persistent volumes satisfies POC workloads with zero cluster management overhead. |

---

## 2. Simplification Pass: Minimum Defensible Architecture

### Core Simplification Rule:
> *"Can the same business outcome be achieved with fewer services, fewer technologies, fewer dependencies, or less infrastructure?"*

```text
                                        BEFORE (Over-Engineered)
   [React App] -> [API Gateway] -> [Ideathon Service] -> [Neo4j Graph DB]
                                -> [OPEX Service]     -> [PostgreSQL DB]
                                -> [Vector Service]   -> [Milvus/Qdrant Vector DB]
                                -> [Agent Swarm]      -> [External MCP Daemons]
                                -> [Training Engine]  -> [LoRA Fine-Tuning Pipeline]

                                         AFTER (Optimized & Defensible)
   +-----------------------------------------------------------------------------------------------+
   |                                    REACT + VITE FRONTEND                                      |
   +-----------------------------------------------------------------------------------------------+
                                                   |  HTTPS
                                                   v
   +-----------------------------------------------------------------------------------------------+
   |                                 FASTAPI MODULAR MONOLITH                                      |
   |   - PlantOpexService       - IdeathonService       - HybridRetrievalService                   |
   |   - CalculationEngine      - AiOrchestrator        - LocalAiGateway                           |
   +-----------------------------------------------------------------------------------------------+
                           |                                               |
                           v                                               v
   +-----------------------------------------------+   +-------------------------------------------+
   |          POSTGRESQL 16 + pgvector             |   |         INTERNAL LOCAL RUNTIME            |
   |  - Authoritative Relational Master Data       |   |  - LlamaCppEngine (Qwen GGUF)             |
   |  - Hierarchical Vehicle Relationships (CTEs)  |   |  - Local Embedding Engine                 |
   |  - Semantic Vector Indexes (HNSW)             |   |  - Local Cross-Encoder Reranker           |
   |  - Trigram & Exact Identifier Indexes         |   |  - Sandboxed Deterministic Tool Registry  |
   +-----------------------------------------------+   +-------------------------------------------+
```

### Architectural Reductions Achieved:
1. **Container Count**: Reduced from 8 containers to 2 containers (`app` + `postgres`).
2. **Database Engines**: Reduced from 3 distinct engines (SQL + Graph + Vector) to 1 unified engine (`PostgreSQL + pgvector`).
3. **Inference Dependencies**: Zero dependency on external cloud APIs, zero mandatory dependency on external daemons.
4. **Maintenance Overhead**: Single unified code repository with shared Pydantic data schemas across all services.
