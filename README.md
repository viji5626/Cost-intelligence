# HERO Vehicle Cost & Plant OPEX Intelligence Platform

Enterprise solution for **Vehicle Ideathon Intelligence** and **Plant Operational Expenditure (OPEX) Benchmarking**, designed for private, on-premise, air-gapped deployment for Hero MotoCorp.

---

## 1. Core Platform Mission & Truth Principles

> **AI interprets. Data proves. Calculations quantify. Evidence supports. Humans decide.**

- **Structured Business Truth** $\rightarrow$ PostgreSQL 16 Relational Tables (Vehicles, Plants, BOM, Parts, Costs, ECNs).
- **Vehicle Relationship Model** $\rightarrow$ Hierarchical Relational Structure + Recursive CTEs.
- **Financial & Numerical Truth** $\rightarrow$ Pure Python Deterministic Calculation Engine (Zero LLM arithmetic, `Decimal` precision).
- **Linear Data & Evidence Pipeline** $\rightarrow$
  $$\text{BUSINESS ENGINES} \longrightarrow \text{STRUCTURED DATA + RETRIEVAL} \longrightarrow \text{EVIDENCE \& POLICY} \longrightarrow \text{AI ORCHESTRATION} \longrightarrow \text{LOCAL AI RUNTIME}$$
- **Evidence & Policy Layer** $\rightarrow$ `SourceAuthorityPolicy`, conflict detection, freshness validation, and safety gate triggers.
- **Semantic Retrieval** $\rightarrow$ Dense Embeddings + `pgvector` HNSW Indexing.
- **Exact Identifier Lookup** $\rightarrow$ PostgreSQL Trigram / B-Tree Exact Search (Part Numbers, ECNs, Project IDs).
- **Hardware-Aware Local AI Runtime** $\rightarrow$ Dynamic RAM/VRAM resource profiling, tiered model selection, and sequential on-demand swapping.
- **Final Authority** $\rightarrow$ Human-in-the-Loop Engineering Review Queue.

---

## 2. Two Independent Business Engines

### A. Vehicle Ideathon Intelligence
Processes 10,000+ employee ideas to determine:
- **Idea Validity & Normalization**: Standardizes colloquial terminology into canonical problem/solution statements.
- **Duplicate & Near-Duplicate Detection**: Hybrid search and semantic clustering across submission batches.
- **Implementation Discovery**: Traverses Part $\rightarrow$ Assembly $\rightarrow$ ECN $\rightarrow$ BOM records to distinguish `IMPLEMENTATION CONFIRMED`, `PARTIALLY CONFIRMED`, `HISTORICAL IMPLEMENTATION`, `POTENTIAL EVIDENCE`, `NO EVIDENCE FOUND`, `INSUFFICIENT EVIDENCE`, or `CONFLICTING EVIDENCE`.
- **Portfolio Applicability Matrix**: Maps implementation status across Model, Variant, and Model Year (Where, When, On What).
- **Deterministic Cost Opportunity**: Quantifies unit savings, gross annual opportunity, and net ROI using verified BOM and production volume records.

### B. Plant OPEX & Expenditure Benchmarking
Answers: *"Which plant is spending more than its comparable benchmark, on what, why, and what opportunity exists to close the gap?"*
- **`BenchmarkMethodology` Domain Engine**: 4 distinct modes (Best Comparable Plant, Peer Group Benchmark, Historical Baseline, Management Target).
- **Multi-Factor Comparability Scoring**: Accounts for manufacturing scope, production volume, mix, operating days, shift patterns, and capacity utilization.
- **Deterministic Variance Decomposition**: Separates Volume Variance, Rate/Tariff Variance, and Addressable Operational Efficiency Gap.
- **`MagnitudeAnomalyGuard`**: Unit sanity and statistical outlier validation preventing unit-mismatch errors (e.g. Lakhs vs Rupees).

---

## 3. Hardware Resource Adaptability (POC Development Profile)
- **Reference Profile**: AMD Ryzen AI 9 HX 370 (12 Cores), 16 GB System RAM, NVIDIA RTX 4060 Laptop GPU (8 GB VRAM).
- **Dynamic RAM Management**: Continuous dynamic tracking of `total_ram`, `available_ram`, and system headroom; tested AI operating envelope of 6.0–8.0 GB.
- **Stress-Envelope CUDA OOM Protection**: Measurable POC criterion (*No reproducible CUDA OOM under the defined POC workload and stress-test envelope*).
- **VRAM Sequential Swapping**: Tier 1 (8GB VRAM) selects Qwen2.5-3B/7B candidates with sequential on-demand swapping (`LOAD -> PROCESS -> RELEASE`).
- **Configurable CPU Threading**: Thread pool dynamically adjustable via environment configuration (default `n_threads = 6` on Zen 5 cores).

---

## 4. TASC IIoT Studio Asset Reuse (Indicative ~27–30 Days Saved)
- **Reused As-Is**: `AIProvider` protocols, GBNF Grammar Engine, Virtualized Data Grid UI.
- **Refactored & Reused**: `LlamaCppEngine` Core (extended with VRAM profiler), Local RAG chunker, AI Studio Admin UI, Ingestion staging base.
- **Excluded**: PLC drivers, MQTT brokers, SCADA canvas, industrial alarm historians.
- *Status*: All effort savings classified as **INDICATIVE / TO BE VALIDATED DURING IMPLEMENTATION**.

---

## 5. Scope Stratification: Current POC vs. Parked vs. Production
- **CURRENT POC**: Relational core, OPEX engine, Ideathon ingestion, hybrid retrieval, implementation applicability, deterministic cost math, Evidence & Policy Layer, local SLM runtime, human review queue, evaluation harness, executive UI, air-gap compliance.
- **PARKED / FUTURE**: Tier 2/3 hardware, concurrent model residency, larger context (8k–16k), MCP adapter, recursive language models (RLM), domain LoRA fine-tuning, multimodal handwriting OCR, 3D explorer, SAP/PLM sync, SSO, HA clustering.
- **PRODUCTION SCALE**: Multi-GPU distributed inference clustering, multi-plant edge sync.

---

## 6. Master Implementation Roadmap (V3.1.1)

| Phase | Phase Name | Core Deliverables | Decision Gate |
|---|---|---|---|
| **Phase 0** | **Environment & Foundation** | Docker setup, FastAPI scaffolding, air-gap baseline, TASC interface protocol drop-ins. | `GATE-00: Architecture & Baseline` |
| **Phase 1** | **Relational Master Data** | Vehicle hierarchy schema, plant master, BOM, parts, costs, ECNs, audit logs. | `GATE-01: Data Foundation` |
| **Phase 2** | **Ingestion & Validation** | Streaming parser, `MagnitudeAnomalyGuard`, unit conversion rules. | `GATE-02: Ingestion Reliability` |
| **Phase 3** | **Plant OPEX Engine** | `BenchmarkMethodology`, deterministic KPI engine (kWh/veh, ₹/veh), variance decomposition. | `GATE-03: OPEX Engine` |
| **Phase 4** | **Ideathon Core** | Idea ingestion, raw text preservation, entity extraction, decision state machine. | `GATE-04: Ideathon Core` |
| **Phase 5** | **Unified Hybrid Retrieval** | `pgvector` HNSW indexes, exact trigram matching, cross-encoder reranking. | `GATE-05: Hybrid Retrieval` |
| **Phase 6** | **Implementation Intelligence** | Multi-tier implementation discovery, cross-model applicability matrix. | `GATE-06: Implementation Intelligence` |
| **Phase 7** | **Deterministic Cost Engine** | Mathematical vehicle unit savings, annual opportunity, tooling ROI calculations. | `GATE-07: Cost Engine` |
| **Phase 8** | **Evidence & Policy Layer** | `SourceAuthorityPolicy`, multi-source conflict detector, confidence scoring. | `GATE-08: Evidence & Policy` |
| **Phase 9** | **Local SLM & Gateway** | Local Qwen GGUF integration via `LlamaCppEngine`, GBNF JSON schemas, tool policy. | `GATE-09: Local AI Decision` |
| **Phase 10** | **Human Review & Governance** | Decision queue (Accept/Reject/Override), non-bypassable safety gates, audit trail. | `GATE-10: Human Governance` |
| **Phase 11** | **Gold Dataset Evaluation** | Evaluation harness measuring Missed Implementation Rate, Recall@K, latency. | `GATE-11: POC Evaluation` |
| **Phase 12** | **Executive Dashboard UI** | High-density React/Vite industrial UI (TASC virtual grid & AI Studio integrated). | `GATE-12: Executive UI` |
| **Phase 13** | **Security Hardening** | Final air-gap verification, zero egress check, RBAC audit, backup/restore. | `GATE-13: Production Readiness` |

*Note: Track B (Local AI Runtime: `LlamaCppEngine`, GGUF Registry, GBNF Grammar, AI Studio) executes in parallel with Phases 0–9, leveraging TASC assets.*

---

## 7. Specification & Implementation Documentation Library

- `docs/context/` — 12 Authoritative Specification Files.
- `docs/implementation-plan/00_PROJECT_AUDIT.md` — Repository & Specification Audit.
- `docs/implementation-plan/01_ARCHITECTURE_SYNTHESIS.md` — Architecture Synthesis & Challenges.
- `docs/implementation-plan/02_DEPENDENCY_GRAPH.md` — Dependency Graph & Workstream Breakdown.
- `docs/implementation-plan/03_DRAFT_IMPLEMENTATION_PLAN_V1.md` — Draft Plan V1.
- `docs/implementation-plan/04_RED_TEAM_CRITIQUE.md` — Red-Team Critique & 32 AI Scenarios.
- `docs/implementation-plan/05_FAILURE_AND_BOTTLENECK_ANALYSIS.md` — FMEA & Bottlenecks.
- `docs/implementation-plan/06_SIMPLIFICATION_REVIEW.md` — Scope-Drift & Simplification Review.
- `docs/implementation-plan/07_TECHNOLOGY_DECISIONS.md` — Technology Decisions & Runtime Model.
- `docs/implementation-plan/08_REVISED_IMPLEMENTATION_PLAN_V3.md` — Master Plan V3.
- `docs/implementation-plan/09_REVISED_IMPLEMENTATION_PLAN_V3_1_1.md` — **Master Implementation Plan V3.1.1 (Targeted Final Baseline)**.
- `docs/implementation-plan/10_RISK_REGISTER.md` — Top 10 Risks & Mitigation Strategy.
- `docs/implementation-plan/11_POC_BOUNDARY.md` — POC Scope Boundary & Feature Tiers.
- `docs/implementation-plan/12_V2_TO_V3_CHANGELOG.md` — V2 $\rightarrow$ V3 Architecture Hardening Change Log.
- `docs/implementation-plan/13_HARDWARE_RESOURCE_AND_TASC_REUSE_REVIEW.md` — Hardware Resource & TASC Reuse Review.
- `docs/implementation-plan/14_V3_TO_V3_1_CHANGELOG.md` — V3 $\rightarrow$ V3.1 Architecture Hardening Change Log.
- `docs/implementation-plan/16_V3_1_TO_V3_1_1_CHANGELOG.md` — **V3.1 $\rightarrow$ V3.1.1 Architecture Hardening Change Log**.
