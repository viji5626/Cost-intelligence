# 08 — Implementation Roadmap

## Strategic approach

Do not build the entire application in one pass.

Run two parallel tracks:

### Track A — Business Platform

- vehicle data foundation
- plant OPEX
- Ideathon
- retrieval
- evidence
- dashboards

### Track B — Local AI Runtime

- interfaces
- llama.cpp engine
- model registry
- gateway
- tool calling
- MCP
- diagnostics

Track A must remain usable with a temporary local provider if needed. Track B progressively removes dependency on Ollama/LM Studio.

## Phase 0 — Architecture

Create:

- PRD
- architecture
- ADRs
- ERD
- data dictionary
- API boundaries
- AI interfaces
- security model
- evaluation plan
- repository
- Docker/dev environment

Do not generate large volumes of feature code yet.

## Phase 1 — Data foundation

Build:

- PostgreSQL
- migrations
- vehicle hierarchy
- plant master
- product master
- component/part master
- document metadata
- audit foundation

## Phase 2 — Excel/CSV ingestion

Build:

- upload
- temporary staging
- schema detection
- field mapping
- validation
- normalization
- ingestion report
- source deletion after success

## Phase 3 — Plant OPEX engine

Build:

- OPEX import
- KPI calculations
- normalized metrics
- benchmark types
- plant comparison
- variance
- opportunity calculation
- trend analysis

## Phase 4 — Ideathon core

Build:

- idea ingestion
- raw/original preservation
- normalized fields
- classifications
- decision taxonomy
- vehicle/component mapping

## Phase 5 — Semantic retrieval

Build:

- embedding interface
- vector index
- metadata filters
- similarity search
- search evaluation

## Phase 6 — Hybrid retrieval

Build:

- exact search
- keyword search
- metadata filters
- vector retrieval
- fusion
- reranking

## Phase 7 — Existing implementation intelligence

Build:

- implementation records
- ECN/ECR support
- project retrieval
- vehicle applicability matrix
- temporal logic
- evidence links

## Phase 8 — Vehicle cost opportunity

Build deterministic:

- current cost
- proposed cost
- saving/vehicle
- annual opportunity
- implementation investment
- net opportunity
- ROI/payback where data exists

## Phase 9 — Local SLM

Add:

- Local AI Gateway
- OllamaProvider only if needed for development
- local Qwen-class reasoning model
- structured outputs
- evidence-grounded prompts

## Phase 10 — Agentic retrieval

Build:

- retrieval planner
- approved tool registry
- tool policy
- tool execution loop
- bounded agent workflows

## Phase 11 — Evidence & confidence

Build:

- evidence objects
- source citations within application
- confidence levels
- escalation rules
- “insufficient evidence” behavior

## Phase 12 — Human review

Build:

- review queue
- accept/reject/override
- reviewer notes
- audit

## Phase 13 — Evaluation framework

Build:

- Hero Gold Dataset support
- retrieval metrics
- classification metrics
- implementation recall
- false-new rate
- calculation accuracy
- human agreement
- performance metrics

## Phase 14 — Internal Local AI Runtime

Build the custom runtime as a parallel infrastructure project:

R0 interface
R1 inference abstraction
R2 llama.cpp engine
R3 model registry
R4 model validation
R5 gateway
R6 structured output
R7 tool calling
R8 policy
R9 MCP adapter
R10 context manager
R11 hardware manager
R12 internal AI Studio
R13 business integration
R14 performance
R15 security

## Phase 15 — Executive UI / business polish

Build:

- executive dashboard
- OPEX dashboard
- Ideathon dashboard
- idea investigation
- vehicle explorer
- implementation explorer
- opportunity portfolio
- data ingestion UI
- knowledge search
- review queue

## Phase 16 — Security hardening

Validate:

- authentication
- authorization
- network isolation
- outbound block
- secrets
- file permissions
- tool permissions
- audit
- backup/restore
- model governance

## Recommended POC demonstration

The first customer POC should prove three flows:

### Flow A — OPEX
Excel -> normalize -> calculate -> benchmark -> gap -> opportunity.

### Flow B — Ideathon
Ideas -> classify -> cluster -> duplicate -> existing implementation -> model applicability -> opportunity.

### Flow C — Local AI
Question -> retrieval -> evidence -> local SLM -> structured answer.

## POC hardware starting point

Development/POC class:

- 12–16 CPU cores
- 64 GB RAM
- NVIDIA GPU around 24 GB VRAM class
- 2 TB NVMe
- Linux

This is not final production sizing.

Production depends on concurrency, throughput, model, context size, data volume, HA requirements and latency targets.

## Production class starting point

Possible initial departmental class:

- 24–32 CPU cores
- 128 GB RAM
- 24–48 GB+ VRAM depending on workload
- 4 TB+ enterprise NVMe
- redundant storage/backup

Treat this as sizing guidance, not a final specification.
