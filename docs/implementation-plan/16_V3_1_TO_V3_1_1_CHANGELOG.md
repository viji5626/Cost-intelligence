# 16 — V3.1 to V3.1.1 Targeted Architecture & Resource Change Log

## 1. Executive Overview
This change log documents the targeted final adjustments made during the transition from **Implementation Plan V3.1** (`09_REVISED_IMPLEMENTATION_PLAN_V3_1.md`) to **Master Implementation Plan V3.1.1** (`09_REVISED_IMPLEMENTATION_PLAN_V3_1_1.md`).

All changes preserve 100% of V3.1's architectural features while refining dynamic memory measurements, CPU configurability, model agnosticism, deterministic verification tolerances, indicative TASC reuse savings, and the conceptual flow of the **Evidence & Policy Layer**.

---

## 2. Targeted Change Matrix (V3.1 $\rightarrow$ V3.1.1)

| ID | Architectural Area | V3.1 Baseline | Targeted Correction in V3.1.1 | Rationale & Architectural Benefit | POC vs Parked Classification |
|---|---|---|---|---|---|
| **V3.1.1-01** | **RAM / Memory Budgeting** | Static table of fixed RAM allocations (e.g. exactly 1.5GB DB, 4GB OS). | **Converted to Dynamic Runtime Measurements**: Tracks `total_ram`, `available_ram`, `system_headroom`, `app_usage`, `db_usage`, `ai_usage`, and `safety_threshold`. The 6–8 GB figure is explicitly classified as an *indicative/tested operating envelope*, not a rigid partition. | Adapts to dynamic runtime fluctuations across operating systems and active workloads without artificial memory clamping. | **CURRENT POC** (Dynamic Runtime Feature) |
| **V3.1.1-02** | **CPU Resource Management** | Hardcoded universal `n_threads = 6`. | **Configurable & Benchmark-Driven CPU Allocation**: Initial POC profile configures `n_threads = 6` for AMD Ryzen AI 9 HX 370 Zen 5 cores, but thread allocation is dynamically configurable based on active load and benchmarking. | Prevents rigid thread locking while preserving full multi-core scalability on enterprise servers. | **CURRENT POC** (Configurable Runtime Setting) |
| **V3.1.1-03** | **Zero CUDA OOM Criteria** | Absolute universal "Zero CUDA OOM" claim. | **Refined for POC Validation**: "No reproducible CUDA OOM under the defined POC workload and stress-test envelope." Zero CUDA OOM is retained as a permanent long-term runtime certification objective. | Provides measurable, auditable test criteria for POC sign-off while preserving long-term hardening goals. | **CURRENT POC**: Test Envelope Compliance<br>**PARKED/FUTURE**: Certified Zero OOM |
| **V3.1.1-04** | **Model Candidate Agnosticism** | Qwen2.5-3B and Qwen2.5-7B listed as primary models. | **Clarified as Initial Candidates**: Explicitly stated that Qwen2.5-3B and Qwen2.5-7B are *initial candidate models* for the 16GB RAM / 8GB VRAM profile. Model selection remains fully dynamic, task-aware, and benchmark-driven. | Guarantees absolute model independence; any compliant GGUF model can be registered and selected. | **CURRENT POC**: 3B/7B Candidates<br>**PARKED/FUTURE**: 9B/14B/32B Tier 2/3 Models |
| **V3.1.1-05** | **Deterministic Mathematics & Verification** | Strict exact calculation requirement. | **Clarified Verification Tolerances**: Preserves pure Python deterministic calculation engine and zero LLM arithmetic. Clarified that validation uses independently calculated reference results with explicitly defined representation tolerances (`Decimal` exactness; float $\pm 1e-6$ where applicable). | Mathematically rigorous and verifiable against reference Excel sheets. | **CURRENT POC** (Non-Bypassable Rule) |
| **V3.1.1-06** | **TASC Effort Savings Status** | Stated savings as ~27–30 days. | **Formally Classified as Indicative**: Preserves all identified TASC reuse assets; explicitly tags all effort-saved numbers as *INDICATIVE / TO BE VALIDATED DURING IMPLEMENTATION*. | Maintains transparent project governance without contractual or unvalidated assumptions. | **CURRENT POC** (Asset Reuse Execution) |
| **V3.1.1-07** | **Conceptual Data & Evidence Flow** | General bidirectional layout. | **Formalized Linear Conceptual Pipeline**: `BUSINESS ENGINES` $\rightarrow$ `STRUCTURED DATA + RETRIEVAL` $\rightarrow$ `EVIDENCE & POLICY` $\rightarrow$ `AI ORCHESTRATION` $\rightarrow$ `LOCAL AI RUNTIME`. | Eliminates ambiguity; enforces that evidence and policy rules are validated before AI synthesis. | **CURRENT POC** (Core Pipeline Flow) |
| **V3.1.1-08** | **Preservation of Advanced Features** | Some advanced capabilities parked without explicit tiering. | **Formal Scope Stratification**: All advanced features (Tier 2/3 hardware, concurrent model residency, larger context, MCP, RLM, LoRA/QLoRA, multimodal vision, 3D explorer, SAP/PLM sync, SSO, HA clustering) are explicitly preserved and classified as **PARKED / FUTURE**. | Guarantees no architectural feature is deleted while protecting the POC focus. | **PARKED / FUTURE** (Preserved in Architecture) |

---

## 3. Preserved Sound Architecture
- Strict isolation of **Vehicle Ideathon Intelligence** and **Plant OPEX Benchmarking**.
- **Evidence & Policy Layer** enforcing `SourceAuthorityPolicy`, conflict detection, and non-bypassable safety gates.
- **`BenchmarkMethodology`** domain engine with 4 distinct benchmark modes and multi-factor comparability scoring.
- **Implementation State Taxonomy** (`NO_EVIDENCE_FOUND` $\ne$ `NOT_IMPLEMENTED`).
- **PostgreSQL 16 + `pgvector`** relational truth and hybrid search.
- **Air-Gap Lifecycle** (Connected Build $\rightarrow$ Controlled Transfer $\rightarrow$ Air-Gapped Runtime).
