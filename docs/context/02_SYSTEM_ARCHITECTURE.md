# 02 — System Architecture

## Architecture principle

The system is a business intelligence platform with a local AI layer, not an AI chatbot with data attached.

## High-level architecture

```text
                       HERO DATA SOURCES
                              |
              +---------------+----------------+
              |               |                |
            Excel            CSV           Documents/Images
              |               |                |
              +---------------+----------------+
                              |
                      DATA INGESTION
                              |
                  VALIDATION + NORMALIZATION
                              |
          +-------------------+------------------+
          |                   |                  |
          v                   v                  v
       SQL DB             Vector DB        Relationship Model
       /Truth              /Semantic        /Vehicle Graph
          |                   |                  |
          +-------------------+------------------+
                              |
                       RETRIEVAL LAYER
                              |
                HYBRID SEARCH + RERANKING
                              |
                     AGENTIC RETRIEVAL
                              |
                      EVIDENCE ASSEMBLY
                              |
                     DETERMINISTIC TOOLS
                              |
                          LOCAL SLM
                              |
                     DECISION SUPPORT UI
```

## Business engines

```text
                      HERO INTELLIGENCE PLATFORM
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
   VEHICLE IDEATHON ENGINE                 PLANT OPEX ENGINE
             |                                     |
    idea understanding                     data normalization
    semantic clustering                     KPI calculation
    duplicate detection                     benchmarking
    implementation search                   gap analysis
    vehicle mapping                          opportunity calculation
    cost opportunity                         trend/driver analysis
             |                                     |
             +------------------+------------------+
                                |
                         COMMON PLATFORM
```

## Technology boundaries

### SQL
Authoritative structured facts:

- vehicle master
- model/variant/year
- component/part
- BOM
- costs
- production
- project
- implementation
- engineering changes
- OPEX
- benchmark records

### Vector database
Semantic retrieval only. Do not treat vectors as the authoritative database.

### Relationship model
Represent relationships such as:

- vehicle -> model
- model -> variant
- variant -> generation
- model -> subsystem
- subsystem -> assembly
- assembly -> component
- component -> part
- idea -> component
- idea -> project
- project -> implementation
- implementation -> vehicle/model/variant/year

Start with relational relationship tables if adequate. Introduce a dedicated graph database only if business value is proven.

### Calculation engine
All financial/KPI calculations must be deterministic and independently testable.

### Local AI
The SLM reasons over retrieved evidence and structured tool outputs. It is not the source of numerical or product truth.

## Application architecture

Recommended layers:

```text
Frontend
   |
Application API
   |
Domain/Business Services
   |
AI Orchestrator ---- Data Services ---- Calculation Services
   |                       |                    |
Local AI Gateway       SQL/Vector/Docs      Deterministic logic
   |
Model Orchestrator
   |
InferenceEngine
   |
LlamaCppEngine / future engine
```

## Repository architecture

```text
hero-cost-intelligence/
├── frontend/
├── backend/
├── ai/
├── data/
├── retrieval/
├── calculations/
├── database/
├── evaluation/
├── tests/
├── docs/
└── docker/
```

Keep modules separated and testable.

## Recommended POC stack

- Frontend: React / Next.js
- Backend: Python + FastAPI
- Database: PostgreSQL
- Vector: pgvector
- Relationship model: PostgreSQL initially
- Local reasoning model: Qwen3.5-9B-class candidate
- Embedding: Qwen3-Embedding-0.6B-class candidate
- Reranker: Qwen3-Reranker-0.6B-class candidate
- Temporary development runtime: Ollama if useful
- Target internal runtime: local inference engine built around llama.cpp / llama-cpp-python initially
- Calculation: Python deterministic services
- Local document/image processing

Models are POC candidates, not irreversible technology commitments.

## AI abstraction

The business application MUST NOT call Ollama or llama.cpp directly.

Create interfaces such as:

```text
AIProvider
InferenceEngine
EmbeddingProvider
RerankerProvider
VisionProvider
```

Initial implementations may be:

- OllamaProvider (development only)
- LlamaCppEngine (target local runtime)
- local embedding implementation
- local reranker implementation

## Model capability abstraction

Do not assume every model supports:

- text
- vision
- tool calling
- structured output
- embeddings
- reranking

Represent capabilities explicitly and route by capability, not vendor name.
