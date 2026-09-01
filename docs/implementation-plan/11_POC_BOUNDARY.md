# 11 — POC Scope Boundary & Feature Prioritization

## 1. Executive Summary of POC Scope Boundary
To maximize business impact, minimize engineering risk, and deliver a defensible, evidence-grounded demonstration to Hero MotoCorp leadership, this document formally categorizes all system capabilities into explicit scope tiers.

```text
+---------------------------------------------------------------------------------------------------+
|                                        POC SCOPE PYRAMID                                          |
+---------------------------------------------------------------------------------------------------+
| [1] MUST HAVE FOR POC (Hard Core Deliverable - Zero Compromise)                                    |
|     - Relational Vehicle Hierarchy & Master Data (PostgreSQL)                                     |
|     - Multi-Plant OPEX Benchmarking & Deterministic KPI Engine (kWh/veh, ₹/veh, Gap Analysis)     |
|     - Ideathon 10k Ingestion, Entity Extraction & Canonical Normalization                         |
|     - Unified Hybrid Retrieval (Exact Part + pgvector Semantic + Cross-Encoder Reranker)          |
|     - Multi-tier Implementation Detection & Portfolio Applicability Matrix (Where/When/What)      |
|     - Deterministic Vehicle Cost Opportunity Engine (Unit Savings, Annual Opportunity, ROI)       |
|     - Local SLM Reasoning & Structured Output via LlamaCppEngine (Qwen GGUF, Zero Telemetry)       |
|     - Evidence-Grounded Confidence Engine (High/Med/Low) & Human Review Queue                     |
|     - Industrial Enterprise Web UI (React/Vite) & Air-Gapped Container Setup                      |
+---------------------------------------------------------------------------------------------------+
| [2] SHOULD HAVE FOR POC (High Value Additions)                                                    |
|     - Sandboxed Bounded Agentic Multi-Step Search Tool Loop                                       |
|     - Interactive Ingestion Column Reconciliation & Unit Error Alerting                           |
|     - Synthetic Gold Dataset Continuous Evaluation Harness & Automated Accuracy Reporter          |
|     - Internal AI Studio for Model Health, VRAM Monitoring & Latency Diagnostics                  |
+---------------------------------------------------------------------------------------------------+
| [3] NICE TO HAVE (If Time Permits)                                                                |
|     - Exportable Executive PDF Reports for Plant OPEX and Ideathon Portfolios                     |
|     - Batch Review & Bulk Disposition for Verified Duplicate Clusters                             |
|     - Basic Scanned Document Text Extraction (Clean Typed PDF OCR)                                |
+---------------------------------------------------------------------------------------------------+
| [4] FUTURE PRODUCTION (Post-POC Phase)                                                            |
|     - Enterprise Single Sign-On (SAML / OIDC / Corporate Active Directory)                        |
|     - Multi-Plant Distributed Architecture with High-Availability Database Replication            |
|     - Automated Integration Adapters for SAP / Teamcenter PLM / MES Connectors                    |
|     - Domain-Specific Model Fine-Tuning (LoRA on Hero Engineering Taxonomy & Jargon)              |
+---------------------------------------------------------------------------------------------------+
| [5] ADVANCED / EXPERIMENTAL (Research & Long-Term Roadmap)                                        |
|     - Multimodal Handwritten Idea Card Vision Extraction & Complex Engineering Drawing OCR        |
|     - Recursive Language Model (RLM) for Multi-Decade Cross-Portfolio Reconciliation              |
|     - Dedicated Neo4j Knowledge Graph Migration (Triggered only if SQL CTE depth > 10)           |
+---------------------------------------------------------------------------------------------------+
| [6] REMOVE / DO NOT BUILD YET (Explicit Anti-Patterns)                                            |
|     - Unrestricted LLM Natural Language SQL or Database Query Access                              |
|     - LLM-Based Financial Arithmetic or KPI Calculations                                         |
|     - Autonomous Engineering Change Approvals without Human-in-the-Loop Sign-Off                  |
|     - External Cloud AI APIs (OpenAI, Anthropic, Gemini, Cloud Vector Services)                   |
|     - Microservice Swarm Sprawl for Single-Node Deployment                                        |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Scope Tier Breakdown

### 2.1 MUST HAVE FOR POC (Phase 0 to Phase 13 Core)
- **Authoritative SQL Data Foundation**: Complete vehicle breakdown (Family -> Model -> Variant -> Subsystem -> Assembly -> Part) and plant master.
- **Deterministic Plant OPEX Engine**: Normalization, KPI calculations (kWh/veh, KL/veh, ₹/veh), peer comparisons, and gap quantification.
- **Ideathon Ingestion & Cleansing**: Processing 10,000+ ideas with raw text preservation, entity extraction, and canonical normalization.
- **Unified Hybrid Retrieval**: Exact part number search (`pg_trgm`) + dense vector search (`pgvector`) + cross-encoder reranker.
- **Implementation Intelligence**: Detecting where and when a solution exists (Model, Variant, Model Year, ECN, BOM status).
- **Deterministic Vehicle Cost Engine**: Financial savings, volume calculations, and net ROI computed exclusively in Python.
- **Local AI Runtime (Track B)**: `LlamaCppEngine` running local Qwen GGUF model in GPU VRAM with zero internet connection.
- **Evidence-Grounded Confidence Model**: Objective factor scoring (High/Medium/Low) with automatic human escalation for conflicts.
- **Human-in-the-Loop Review Queue**: Decision capture (Accept/Reject/Override/Safety Hold) and immutable audit logging.
- **Executive & Operational UI**: High-density React/Vite dashboard demonstrating all 7 client presentation scenarios.

### 2.2 SHOULD HAVE FOR POC
- **Bounded Agentic Tool Execution**: Multi-step query planning with strict 4-iteration limit and circuit breaker.
- **Interactive Column Mapping UI**: Feedback interface for dirty spreadsheet uploads with unrecognized headers.
- **Automated Evaluation Harness**: Automated scoring against the Hero Gold Dataset (Missed Implementation Rate, Recall@K).
- **Internal AI Studio**: Technical admin view for hardware monitoring (GPU VRAM, RAM) and prompt testing.

### 2.3 NICE TO HAVE
- **Executive PDF Export**: Generating printable summary decks for leadership meetings.
- **Batch Cluster Disposition**: Approving or rejecting 20 near-duplicate ideas in one action.
- **Basic Clean PDF Text Extraction**: Reading digital specification sheets attached to idea submissions.

### 2.4 FUTURE PRODUCTION (Post-POC)
- **Enterprise IAM**: SSO integration with Hero Active Directory / Okta.
- **Live ERP / PLM Connectors**: Real-time read-only sync with SAP S/4HANA and Siemens Teamcenter PLM.
- **Domain LoRA Fine-Tuning**: Tuning model reasoning style and Hero-specific acronyms.
- **High-Availability Clustering**: Multi-node PostgreSQL streaming replication.

### 2.5 ADVANCED / EXPERIMENTAL
- **Multimodal Handwriting OCR**: Advanced vision models for deciphering handwritten paper Ideathon cards.
- **Recursive Language Model (RLM)**: Multi-pass recursive analysis for reconciling 100,000+ ideas across 15 years.
- **Dedicated Graph Database**: Neo4j migration if relationship traversal depth exceeds relational performance limits.

### 2.6 REMOVE / DO NOT BUILD YET
- **Unrestricted SQL Agent**: Never let the LLM generate and execute raw ad-hoc SQL queries on the database.
- **Probabilistic LLM Arithmetic**: Never allow the LLM to compute financial savings or OPEX ratios.
- **Autonomous Engineering Sign-off**: Never permit AI to autonomously approve safety-critical engineering changes.
- **External Cloud Dependencies**: Never call cloud LLM APIs, cloud vector databases, or remote telemetry endpoints.
- **Container / Microservice Sprawl**: Never fragment the architecture into 10+ microservices for a single-node on-premise installation.
