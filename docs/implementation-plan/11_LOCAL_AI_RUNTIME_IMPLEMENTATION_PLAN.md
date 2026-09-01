# Hero Cost Intelligence Platform — Master Local AI Runtime Architecture & Implementation Plan (Final Validated Baseline)

**Document ID:** `11_LOCAL_AI_RUNTIME_IMPLEMENTATION_PLAN.md`  
**Authoritative Baseline:** Master Implementation Plan V3.1.1 (`09_REVISED_IMPLEMENTATION_PLAN_V3_1_1.md`) & TASC Reuse Review (`13_HARDWARE_RESOURCE_AND_TASC_REUSE_REVIEW.md`)  
**Execution Standard:** `10_ANTIGRAVITY_EXECUTION_RULES.md`  
**Date:** 2026-09-01  
**Status:** **FINAL VALIDATED ARCHITECTURE & ROADMAP — READY FOR MANUAL CONFIRMATION (NO CODE COMMITTED)**

---

## 1. Executive Summary & Product Philosophy

### 1.1 Primary Product Philosophy
The Hero Cost Intelligence Platform **natively owns its Local AI Runtime**. The application runs 100% self-contained, air-gapped, and independent of external cloud APIs or external desktop daemons.

- **Primary Native Runtime:** Built-in local GGUF execution engine (llama.cpp / direct shared C-library DLL binding / isolated worker fallback).
- **Optional Local Adapters:** Ollama, LM Studio, OpenAI-compatible local endpoints, and NVIDIA NIM (when locally configured and explicitly enabled).
- **Zero Cloud Mandate:** The platform **never requires** OpenAI, Anthropic, NVIDIA NIM cloud, Ollama, LM Studio, or any internet connection for core operation.
- **Hardware & Model Portability:** The identical application codebase scales across any hardware (8GB, 12GB, 24GB, 48GB+ VRAM, CPU-only).
- **Zero Hard-Coding:** The architecture, code, and database are **strictly model-agnostic and hardware-agnostic**. Runtime profiles specify **resource budgets and concurrency policies**, NOT model parameter counts or model names.

---

## 2. Decoupled Task Runtime Architecture

Generation, Embedding, Reranking, Vision/OCR, and Tools are treated as **completely independent task runtimes/providers with decoupled dependency graphs**. Failure or absence of one task engine does not affect the others.

```
                                  ┌─────────────────────────────────────────┐
                                  │             [O] AI STUDIO UI            │
                                  │   (Model Library, Runtime Console,      │
                                  │    Hardware Telemetry, GBNF Playground, │
                                  │    Retrieval, Tools/MCP, Diagnostics)   │
                                  └────────────────────┬────────────────────┘
                                                       │ HTTP / SSE / WS
                                  ┌────────────────────▼────────────────────┐
                                  │       LOCAL AI API GATEWAY / ROUTER     │
                                  │  (/api/v1/ai/*, /v1/*, /mcp/tools/*)    │
                                  └────────────────────┬────────────────────┘
                                                       │
                                  ┌────────────────────▼────────────────────┐
                                  │           [F] AI ORCHESTRATOR           │
                                  │   (Deterministic Policy Engine,         │
                                  │    Context Budgeting, Execution Envelope)│
                                  └────────────────────┬────────────────────┘
                                                       │
                                  ┌────────────────────▼────────────────────┐
                                  │         [G] POLICY / TASK ROUTER        │
                                  └─┬──────────┬──────────┬──────────┬────┬─┘
                                    │          │          │          │    │
              ┌─────────────────────┘          │          │          │    └──────────────────────┐
              ▼                                ▼          ▼          ▼                           ▼
    ┌──────────────────┐             ┌──────────────┐ ┌────────┐ ┌──────────────┐      ┌───────────────────┐
    │   [1] GENERATION │             │[2] EMBEDDING │ │  [3]   │ │[4] VISION/OCR│      │    [5] TOOLS /    │
    │     (SLM / GGUF) │             │(Dense Vector)│ │RERANKER│ │ (Doc / Diary)│      │   LOCAL MCP MGR   │
    │  Dep: llama.cpp  │             │ Dep: EmbedGGUF│ │Dep:Cross│ │ Dep: OCR GGUF│      │ (Dry-Run / Allow) │
    └─────────┬────────┘             └──────┬───────┘ └───┬────┘ └──────┬───────┘      └─────────┬─────────┘
              │                             │             │             │                        │
              └─────────────────────────────┼─────────────┼─────────────┼────────────────────────┘
                                            │             │             │
                                  ┌─────────▼─────────────▼─────────────▼───┐
                                  │       [E] MODEL LIFECYCLE MANAGER       │
                                  │  (Quarantine -> Health Test -> Load ->  │
                                  │   Execute -> Release -> Purge Memory)   │
                                  └────────────────────┬────────────────────┘
                                                       │
                                  ┌────────────────────▼────────────────────┐
                                  │      [D] HARDWARE FIT ENGINE            │
                                  │  (Dynamic Headroom Math, Admission Ctrl,│
                                  │   SAFE / CAUTION / UNSAFE / INCOMPATIBLE│
                                  └────────────────────┬────────────────────┘
                                                       │
                                  ┌────────────────────▼────────────────────┐
                                  │     [B] MODEL REGISTRY & MANIFEST       │
                                  │  (Manifest Schema, SHA-256, Provenance, │
                                  │   Quarantine Pool, Offline Storage)     │
                                  └─────────────────────────────────────────┘
```

---

## 3. Dynamic Embedding Dimensions & Native pgvector / HNSW Migration

### 3.1 Model-Specific Dynamic Dimensionality
Embedding dimensionality ($D$) is stored as dynamic metadata in the Model Registry. The platform enforces vector/index compatibility checks before any vector write or query.

### 3.2 Native PostgreSQL pgvector Migration & Offline Re-Indexing Workflow

```
                               ┌─────────────────────────────────────────┐
                               │   Model Registration: Embedding Model   │
                               │   Dimension = D (e.g. 384, 768, 1024)   │
                               └────────────────────┬────────────────────┘
                                                    │
                               ┌────────────────────▼────────────────────┐
                               │ Preflight Index Compatibility Check     │
                               │ (Does target column match dimension D?) │
                               └────────────────────┬────────────────────┘
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      │ Match (Dimension == D)                                    │ Mismatch (Dimension != D)
                      ▼                                                           ▼
    ┌─────────────────────────────────────────┐                 ┌─────────────────────────────────┐
    │     IMMEDIATE INGESTION & QUERYING      │                 │  OFFLINE RE-INDEXING WORKFLOW   │
    │  - Insert into `record_embeddings`      │                 │  1. Prompt User in AI Studio UI │
    │  - Native Column: `embedding vector(D)` │                 │  2. Create staging table `v2`   │
    │  - Index: `HNSW (m=16, ef_constr=64)`   │                 │  3. Re-embed chunks in batches  │
    │  - Distance: `vector_cosine_ops`        │                 │  4. Atomic table swap & index   │
    └─────────────────────────────────────────┘                 └─────────────────────────────────┘
```

- **Alembic Migration Plan:** Migration creates native `pgvector` extension and defines schema with dynamic column typing support.
- **In-Memory Test Path:** SQLite JSON array float fallback remains strictly for headless unit tests.

---

## 4. Python & Native AI Runtime Compatibility Gate

### 4.1 Automated Preflight Compatibility Audit (AI-01 Gate)
Before compiling or executing native model runtimes in AI-04, an automated test harness verifies host capabilities:

```python
class NativeCompatibilityGate:
    """
    Automated preflight gate executed during AI-01.
    Verifies C-ABI bindings, GPU driver availability, and execution fallbacks.
    """
    @staticmethod
    def audit_environment() -> CompatibilityReport:
        # 1. Probe CPU SIMD: AVX2, AVX-512, FMA
        # 2. Probe CUDA Driver: NVIDIA Driver 610.47, nvcuda.dll presence
        # 3. Probe Direct CTypes DLL: libllama.dll / ggml.dll loading
        # 4. Probe Subprocess Worker: Isolated Python execution channel
        # 5. Select Best Native Strategy:
        #    - Strategy A: Direct in-process CTypes DLL binding
        #    - Strategy B: Isolated worker process wrapper
        #    - Strategy C: CPU-only AVX2 fallback
```

---

## 5. First-Class Runtime Profiles (Zero Model-Size Assumptions)

Runtime Profiles define **hardware resource allocations and operational policies**, completely decoupled from model sizes or model names:

```
+---------------------------------------------------------------------------------------------------+
|                            RESOURCE-DRIVEN RUNTIME PROFILES SPECIFICATION                         |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| PROFILE ID        | VRAM BUDGET       | RAM BUDGET        | CONCURRENCY POLICY| GPU OFFLOAD POLICY|
+-------------------+-------------------+-------------------+-------------------+-------------------+
| `PROFILE-CONSTRAINED`| Up to 6.5 GB VRAM| Up to 7.5 GB RAM  | Sequential Swap   | Dynamic Partial / |
| (POC 8GB Host)    |                   |                   | (1 active model)  | Full if fits VRAM |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| `PROFILE-BALANCED`| Up to 12.0 GB VRAM| Up to 14.0 GB RAM | Dual Resident     | Full Offload      |
| (12-16GB Systems) |                   |                   | (Embed + Gen)     | Primary Models    |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| `PROFILE-PERFORMANCE`| Up to 22.0 GB VRAM| Up to 28.0 GB RAM | Fully Concurrent  | Full GPU Offload  |
| (24GB Systems)    |                   |                   | (All resident)    | All Task Models   |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| `PROFILE-ENTERPRISE` | Up to 44.0 GB+ VRAM| Up to 60.0 GB+ RAM| High-Throughput   | Full GPU Offload  |
| (48GB+ Systems)   |                   |                   | Batch Resident    | Multi-Model Pool  |
+-------------------+-------------------+-------------------+-------------------+-------------------+
```

---

## 6. Model Manifest, Provenance & Quarantine Health Test

### 6.1 Model Manifest Schema (`manifest.json`)
Every registered model possesses an immutable manifest:

```python
class ModelManifest(BaseModel):
    model_id: str                      # "hero-slm-qwen2.5-3b-q4"
    model_version: str                  # "1.0.0"
    model_name: str                     # "Qwen 2.5 3B Instruct"
    file_path: str                      # "models/gguf/qwen2.5-3b-instruct-q4_k_m.gguf"
    file_size_bytes: int                # 2210000000
    sha256_checksum: str                # Cryptographic hash
    format: str                         # "GGUF" | "ONNX"
    quantization: str                   # "Q4_K_M" | "Q8_0" | "FP16"
    architecture: str                   # "qwen2"
    parameter_count: str                # "3.09B"
    supported_tasks: List[str]          # ["REASONING", "STRUCTURED_OUTPUT"]
    embedding_dimension: Optional[int]  # Dynamic (e.g. 384)
    base_context_length: int            # 32768
    status: str                         # "QUARANTINED" | "HEALTHY" | "REJECTED"
    provenance_author: str              # "Hero Engineering"
    imported_at: str
```

### 6.2 Three-Step Model Health Validation & Quarantine Pipeline

```
[MODEL FILE PLACED] ──> [STATE: QUARANTINED]
                              │
                              ├──> STEP 1: Format & Header Validation (Magic bytes, tensor sanity)
                              ├──> STEP 2: SHA-256 Streaming Checksum Verification
                              └──> STEP 3: 1-Token Smoke Test Probe (Loads temp, samples 1 token, unloads)
                                       │
                      ┌────────────────┴────────────────┐
                      │ Passed                          │ Failed
                      ▼                                 ▼
           [STATE: ACTIVE_REGISTERED]       [STATE: REJECTED_QUARANTINED]
           (Eligible for Selection)         (Diagnostic Error Logged in UI)
```

---

## 7. Capability- & Hardware-Driven Model Selector

Model selection is strictly filtered across 3 sequential gates:

$$\text{Task Capability Gate} \longrightarrow \text{Hardware Compatibility Gate} \longrightarrow \text{Runtime Profile Budget}$$

- **Task Filter:** Requesting `EMBEDDING` presents only models with `EMBEDDING` capability; `REASONING` presents only generative models.
- **Hardware Filter:** Dynamically assesses current free VRAM/RAM against model weight + KV cache formula, classifying as `SAFE`, `CAUTION`, `UNSAFE`, or `INCOMPATIBLE`.
- **Safety Rule:** Incompatible or quarantined models can never be selected as active defaults.

---

## 8. Sandboxed Tool / MCP Security & Dry-Run Mode

### 8.1 Tool Security Guardrails
1. **Zero Shell Policy:** No `subprocess`, `os.system`, `powershell.exe`, or arbitrary Python `eval()`.
2. **Strict Schema Validation:** Parameters validated against Pydantic models with input sanitization.
3. **Execution Limits:** 1.0 – 3.0s timeout per tool; hard maximum of 3 tool iterations per task.

### 8.2 MCP Dry-Run Mode
The AI Orchestrator supports an explicit `dry_run=True` mode:
- Validates tool schema, argument types, and user permissions.
- Simulates tool execution and produces synthetic mock output without mutating database or executing live operations.
- Records simulated execution in the audit log for safety review.

---

## 9. Standard AI Execution Envelope Contract

Every AI response delivered to downstream business modules is wrapped in a standard `AIExecutionEnvelope`:

```python
class AIExecutionEnvelope(BaseModel, Generic[T]):
    task_id: str
    task_type: str                      # "REASONING" | "EXTRACTION" | "EMBEDDING" | "RERANK"
    status: str                         # "SUCCESS" | "DEGRADED" | "INSUFFICIENT_EVIDENCE" | "ERROR"
    result: T                           # Structured Pydantic payload or text content
    raw_content: str
    grounding_score: Optional[float]    # 0.0 - 1.0 (evidence alignment)
    evidence_citations: List[Dict[str, Any]]
    usage: Dict[str, int]               # prompt_tokens, completion_tokens, total_tokens
    latency_seconds: float
    provenance: ModelProvenance         # model_id, file_hash, quantization, runtime_profile, seed
    audit_hash: str                     # SHA-256 digest of envelope for immutable audit trail
```

---

## 10. Expanded Failure-Injection Test Strategy

```
+---------------------------------------------------------------------------------------------------+
|                                 FAILURE-INJECTION TEST MATRIX                                     |
+--------------------------+---------------------------------------+--------------------------------+
| FAILURE SCENARIO         | INJECTION MECHANISM                   | EXPECTED RUNTIME RECOVERY      |
+--------------------------+---------------------------------------+--------------------------------+
| **Corrupted GGUF File**  | Truncate 1MB from GGUF binary footer  | Quarantine catches error; safe |
|                          |                                       | rejection; UI alert surfaced.  |
+--------------------------+---------------------------------------+--------------------------------+
| **CUDA OOM Simulation**  | Allocate synthetic 7.5GB VRAM tensor  | Admission control blocks load; |
|                          | prior to model acquisition            | graceful fallback to CPU.      |
+--------------------------+---------------------------------------+--------------------------------+
| **Streaming Cancel**     | Trigger cancellation token at token 5 | Token generator aborts cleanly;|
|                          | of 100-token stream                   | memory released in < 50ms.     |
+--------------------------+---------------------------------------+--------------------------------+
| **Dimension Mismatch**   | Insert 768-d vector into 384-d column | Preflight validation blocks write;|
|                          |                                       | triggers re-indexing notice.   |
+--------------------------+---------------------------------------+--------------------------------+
| **Infinite Tool Loop**   | Synthetic tool returning empty missing| Loop breaker stops execution at|
|                          | evidence in iterative retrieval       | iteration 3; routes to review. |
+--------------------------+---------------------------------------+--------------------------------+
| **Malformed SLM JSON**   | Force invalid JSON syntax in output   | Pydantic retry triggered; on   |
|                          | stream                                | failure routes to P1 review.   |
+--------------------------+---------------------------------------+--------------------------------+
| **Network Isolation**    | Block all external socket connections | 100% tests pass with zero      |
|                          | in pytest fixture                     | external socket errors.        |
+--------------------------+---------------------------------------+--------------------------------+
```

---

## 11. Phased Implementation Sequencing (AI-01 to AI-18)

| Phase ID | Sub-Phase Title | Key Deliverables & Artifacts | Readiness Status |
| :--- | :--- | :--- | :--- |
| **AI-01** | **Runtime Foundation & Compatibility Gate** | Automated preflight audit, `ai/core/config.py`, thread allocation | **READY TO EXECUTE** |
| **AI-02** | **Model Registry, Manifest & Quarantine** | `ModelRegistry`, `manifest.json`, 3-step health test, SHA-256 | **BLOCKED ON AI-01** |
| **AI-03** | **Runtime Profiles & Hardware Fit Engine** | Resource profiles (`PROFILE-CONSTRAINED`, etc.), memory fit math | **BLOCKED ON AI-02** |
| **AI-04** | **Native GGUF Inference Core** | `LlamaCppEngine`, async streaming, cancellation, deterministic mode | **BLOCKED ON AI-03** |
| **AI-05** | **Model Lifecycle & Sequential Swapper** | `ModelLifecycleManager`, sequential swapping, CUDA memory purge | **BLOCKED ON AI-04** |
| **AI-06** | **Real Embedding & Native pgvector/HNSW** | Dynamic dimension dense embedding, Alembic pgvector, HNSW index | **BLOCKED ON AI-02** |
| **AI-07** | **Real Cross-Encoder Reranker** | Cross-encoder candidate reranker, latency measurement, CPU fallback | **BLOCKED ON AI-05** |
| **AI-08** | **Context Management & Token Budgeter** | Token budgeting, reserved output guard, anti-middle-loss placement | **BLOCKED ON AI-01** |
| **AI-09** | **Retrieval & Evidence Grounding** | Connect hybrid retrieval to live embedding & reranker pipelines | **BLOCKED ON AI-08** |
| **AI-10** | **Structured Output & GBNF Grammar** | Pydantic-to-GBNF compiler, logit-masked sampling, schema validator | **BLOCKED ON AI-05** |
| **AI-11** | **Local MCP, Tool Security & Dry-Run** | Sandboxed local Tool Registry, loop breaker (max 3), dry-run mode | **BLOCKED ON AI-01** |
| **AI-12** | **Central AI Orchestrator & Task Router** | Central pipeline orchestrator, `AIExecutionEnvelope`, audit trail | **BLOCKED ON AI-11** |
| **AI-13** | **Provider Adapter Layer** | Optional Ollama/LM Studio adapters, independent of native GGUF | **BLOCKED ON AI-12** |
| **AI-14** | **Local OpenAI-Compatible API** | Localhost-only `/v1/` endpoint, CORS security, policy binding | **BLOCKED ON AI-13** |
| **AI-15** | **Vision / OCR Provider Abstraction** | Extensible Vision/OCR provider interface for handwritten idea cards | **BLOCKED ON AI-12** |
| **AI-16** | **AI Studio UI Workspace** | 8-module React workspace: Library, Console, Hardware, Playground | **BLOCKED ON AI-14** |
| **AI-17** | **End-to-End Validation & Failure Suite** | 18 automated test suites, failure-injection matrix execution | **BLOCKED ON AI-16** |
| **AI-18** | **Performance & Hardware Benchmarking** | Profiling load time, first-token latency, t/s, peak VRAM/RAM | **BLOCKED ON AI-17** |

---

## 12. Final Stop & Sign-Off Request

All 10 required corrections have been incorporated into the finalized architectural blueprint.

**Sub-Phase AI-01 (Runtime Foundation & Compatibility Gate)** is ready for execution upon your explicit manual confirmation.

### 6.2 Offline Import & Registration Workflow
1. User places local GGUF/model file into `./models/` directory or provides absolute path.
2. Registry inspects binary header (GGUF magic bytes, tensor architecture, metadata keys).
3. Registry calculates SHA-256 checksum in 64KB streaming blocks.
4. Fit engine computes resource estimates for active runtime profiles.
5. Model is registered and made available for task-filtered selection.
6. **Physical File Safety Rule:** Physical model files are **never deleted** without explicit, authenticated user confirmation.

---

## 7. Model Lifecycle & Concurrency Engine

### 7.1 State Transition Protocol
The lifecycle engine manages transitions with mutual exclusion and leak prevention:

```
[UNREGISTERED] ──> [REGISTERED] ──> [PREFLIGHT_CHECK] ──> [LOADING] ──> [ACTIVE / RESIDENT]
                                                                               │
                                                                          [EXECUTING]
                                                                               │
[EVICTED] <── [GARBAGE COLLECTED] <── [VRAM PURGED] <── [UNLOADING] <──────────┘
```

### 7.2 Concurrency & Switching Safety Policy
- **Locking & Admission Control:** An `asyncio.Lock` per task runtime prevents race conditions during model swaps.
- **Model Switching Safety Protocol:**
  1. Complete or gracefully cancel active inference tasks.
  2. Unload current model instance from memory.
  3. Force garbage collection and CUDA cache flush (`torch.cuda.empty_cache()` / `ggml_free()`).
  4. Perform hardware fit preflight for candidate model.
  5. Load candidate model and execute health probe token.
  6. Atomically update active resident state in registry and UI.
- **Queueing vs. Thrashing:** Concurrent requests for the active model are queued with FIFO admission; requests requiring a model swap wait until the active task batch finishes.

---

## 8. Task-Specific Providers & Capability-Aware Selection

Selection is strictly **Task-Driven**:

```
USER TASK ──> TASK CAPABILITY FILTER ──> HARDWARE FIT FILTER ──> ELIGIBLE MODELS ──> RUNTIME PROFILE
```

### 8.1 Task Provider Specializations

```
+---------------------------------------------------------------------------------------------------+
|                                 TASK PROVIDER SPECIALIZATION MATRIX                               |
+---------------------+-------------------------+-------------------------+-------------------------+
| TASK DOMAIN         | PRIMARY NATIVE ENGINE   | SECONDARY ADAPTER       | FALLBACK ENGINE         |
+---------------------+-------------------------+-------------------------+-------------------------+
| **[1] Generation**  | Native GGUF SLM         | Ollama / LM Studio      | Deterministic Mock      |
| **[2] Embedding**   | Native GGUF Embedding   | Local FastEmbed / ONNX  | Deterministic Vector    |
| **[3] Reranking**   | Native Cross-Encoder    | Local Cross-Encoder ONNX| Deterministic Lexical   |
| **[4] Vision / OCR**| Local Vision/OCR GGUF   | Local Tesseract / EasyOCR| Extensible Stub/Review  |
| **[5] Tools / MCP** | Local Sandboxed Registry| Direct Domain Dispatch  | Read-Only Query Service |
+---------------------+-------------------------+-------------------------+-------------------------+
```

---

## 9. Structured Output, GBNF & Grounding Policy

### 9.1 GBNF / Logit-Constrained Sampling vs. Fallback

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            STRUCTURED OUTPUT CAPABILITY ROUTING                                  │
├────────────────────────────────────────┬─────────────────────────────────────────────────────────┤
│ [A] GBNF GRAMMAR PATH (Supported GGUF) │ [B] CONSTRAINED JSON / VALIDATION PATH (Fallback)       │
│ 1. Compile Pydantic schema to GBNF     │ 1. Inject schema into system prompt                     │
│ 2. Mask logits during sampling         │ 2. Execute sampling with temperature = 0.0              │
│ 3. 100% guarantee of valid JSON tokens │ 3. Post-validate output against Pydantic schema         │
│ 4. Parse and return Pydantic object    │ 4. If invalid: retry with error feedback (max 2 retries)│
│                                        │ 5. If persistent: route cleanly to Human Review Queue   │
└────────────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

### 9.2 Grounding & Anti-Hallucination Policy
- The SLM is **never authoritative** for master data, BOM costs, OPEX figures, or governance decisions.
- If retrieval yields insufficient evidence, the system prompt and grammar compel output of `INSUFFICIENT_EVIDENCE` or `NO_IMPLEMENTATION_EVIDENCE_FOUND`.
- The platform strictly enforces the 4-tier truth hierarchy:
  1. **Authoritative Truth:** Relational Database & Provenance Hash.
  2. **Deterministic Calculations:** Pure Python Decimal Engines (`Calculations/`).
  3. **Verified Evidence:** Retrieved ECNs, BOM Lineage, Historical Project Records.
  4. **Advisory SLM Output:** Summaries, hypotheses, and structured entity extractions.

---

## 10. Context Window Management & Bounded Agentic Retrieval

### 10.1 Context Budgeting & Lost-in-the-Middle Mitigation
- **Hard Configurable Limits:** Max Context Tokens (e.g. 4,096), Output Reserve (768 tokens), Max Evidence Chunks (5 chunks).
- **Chunk Placement Strategy:**
  - Priority 1 Evidence placed at the **beginning** of the context.
  - Priority 2 Evidence placed at the **end** of the context.
  - Secondary supporting material placed in the middle.

### 10.2 Bounded Agentic & Recursive Retrieval Controls
Multi-hop evidence exploration operates under strict deterministic guardrails:
- `MAX_RETRIEVAL_ITERATIONS = 3`
- `MAX_TOOL_CALLS_PER_STEP = 3`
- `MAX_TOTAL_RUNTIME_SECONDS = 15.0`
- `CIRCUIT_BREAKER`: Duplicate query detection prevents iterative retrieval loops.

---

## 11. Sandboxed Tool / Local MCP Architecture

```
AI Model ──> Tool Request ──> Allowlist Check ──> Schema Validation ──> Authorization ──> Bounded Execution ──> Audit Trail
```

- **Strict Security Policy:** Prohibits arbitrary shell, PowerShell, CMD, or unrestricted filesystem access.
- **Allowed Local Tools:** `search_ecn_records`, `get_bom_component_cost`, `get_plant_opex_kpi`, `check_safety_critical`, `calculate_opportunity`.
- **Execution Isolation:** Bounded execution timeouts (1.0 – 3.0s per tool) and cryptographic audit logging.

---

## 12. Standard AI Result & Provenance Contract

Every AI result consumed by downstream business layers follows a standard schema:

```python
class ModelProvenance(BaseModel):
    model_id: str
    model_version: str
    model_file_hash: str
    quantization: str
    runtime_engine: str
    runtime_profile: str
    context_length: int
    temperature: float
    seed: int
    embedding_model_id: Optional[str] = None
    reranker_model_id: Optional[str] = None
    prompt_template_version: str = "v1.0"
    execution_timestamp: str

class AIResult(BaseModel):
    task_type: str
    raw_content: str
    structured_output: Optional[Dict[str, Any]] = None
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    validation_status: str  # "VALIDATED" | "FALLBACK_USED" | "HUMAN_REVIEW_REQUIRED"
    latency_seconds: float
    usage: Dict[str, int]
    provenance: ModelProvenance
```

---

## 13. AI Studio UI Specification

The AI Studio is structured into 8 integrated modules within `src/components/ai-studio/`:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HERO COST INTELLIGENCE — AI RUNTIME & MODEL STUDIO                                   [STATUS: OK]│
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ [1] HARDWARE DASHBOARD ─────────────────────────────────────────────────────────────────────┐ │
│ │ Host: AMD Ryzen AI 9 HX 370 (12C/24T)   GPU: RTX 4060 Laptop (8GB)    Tier: POC_8GB          │ │
│ │ RAM: [████████░░░░░░] 6.8 / 15.1 GB   VRAM: [██████████░░░░] 4.2 / 8.0 GB   DWM Buffer: 1.1GB │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ [2] MODEL LIBRARY ─────────────────┐ ┌─ [3] RUNTIME CONSOLE ──────────────────────────────┐ │
│ │ Qwen2.5-3B-Instruct (Q4_K_M) [SAFE] │ │ Active Provider: [ Built-in Local GGUF           ▼] │ │
│ │ Qwen2.5-7B-Instruct (Q3_K_M) [CAUT] │ │ Active Model   : [ Qwen2.5-3B-Instruct-Q4_K_M.gguf▼] │ │
│ │ Qwen3-Embedding-0.6B (384d)  [SAFE] │ │ Task Mode      : [ REASONING_SLM                 ▼] │ │
│ │ Qwen3-Reranker-0.6B          [SAFE] │ │ Context Window : [ 4096 Tokens ]   GPU Layers: [ALL]│ │
│ │ [ + REGISTER LOCAL GGUF ]           │ │ [ LOAD MODEL ]   [ UNLOAD / PURGE ]   [ TEST PING ] │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────────────────────────┘ │
│ ┌─ [4] GBNF PLAYGROUND ────────────────────────────────────────────────────────────────────────┐ │
│ │ System Schema: [ IdeaExtractionSchema ▼ ]   Prompt: "Analyze brake lever polymer idea..."    │ │
│ │ [ RUN GROUNDED GENERATION ]  ──> Live SSE Token Streaming + Structured JSON Output           │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ [5] PROVIDERS ───────┐ ┌─ [6] RETRIEVAL ──────────┐ ┌─ [7] MCP TOOLS ────┐ ┌─ [8] TELEMETRY─┐│
│ │ Built-in GGUF: ONLINE │ │ Vector Index: HNSW (384d)│ │ Allowed: 5 Tools   │ │ First-Token:42ms│
│ │ Ollama (Opt) : OFFLINE│ │ Embed Model : Qwen3-0.6B │ │ Loop Breaker: 3 Max│ │ Speed: 38 t/s   │
│ └───────────────────────┘ └──────────────────────────┘ └────────────────────┘ └────────────────┘│
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Comprehensive Self-Critique & Architectural Mitigations

```
+---------------------------------------------------------------------------------------------------+
|                                 ARCHITECTURAL SELF-CRITIQUE MATRIX                                |
+----+-----------------------+---------------------------------------+------------------------------+
| #  | IDENTIFIED RISK       | OPERATIONAL IMPACT                    | ARCHITECTURAL MITIGATION     |
+----+-----------------------+---------------------------------------+------------------------------+
| 1  | **Python 3.14 C-ABI** | Compiled binary wheels may lag Python | Dual-runtime compatibility   |
|    |                       | 3.14 releases on Windows.             | gate (Ctypes direct binding  |
|    |                       |                                       | or isolated worker fallback).|
+----+-----------------------+---------------------------------------+------------------------------+
| 2  | **Vector Dimension**  | Switching embedding models causes     | Model-specific dimension meta|
|    | **Index Corruption**  | silent index dimension mismatches.    | in registry; preflight index |
|    |                       |                                       | dimension compatibility check|
+----+-----------------------+---------------------------------------+------------------------------+
| 3  | **VRAM Fragmentation**| Repeated load/unload leaves ghost     | Explicit `cudaEmptyCache`,   |
|    |                       | memory in GPU allocator.              | garbage collection, and      |
|    |                       |                                       | allocator memory purge.      |
+----+-----------------------+---------------------------------------+------------------------------+
| 4  | **Lost in the Middle**| Concatenating multiple ECNs degrades  | Context budgeting engine with|
|    |                       | model attention on key facts.         | primacy/recency placement.   |
+----+-----------------------+---------------------------------------+------------------------------+
| 5  | **Infinite Tool Loop**| Ambiguous queries cause repetitive    | Hard cap of 3 tool iterations|
|    |                       | recursive retrieval hops.             | with circuit-breaker hash.   |
+----+-----------------------+---------------------------------------+------------------------------+
| 6  | **Model Swap Race**   | Concurrent requests swap models       | Async mutex per runtime;     |
|    |                       | mid-generation on 8GB host.           | graceful active task drain.  |
+----+-----------------------+---------------------------------------+------------------------------+
| 7  | **Malformed JSON**    | Raw SLM generation breaks downstream  | Dual-path: GBNF grammar or   |
|    |                       | Pydantic schema validation.           | retry + human review routing.|
+----+-----------------------+---------------------------------------+------------------------------+
| 8  | **Accidental Cloud**  | Unintended external requests in air-  | Hardcoded zero-remote rule;  |
|    |                       | gapped industrial deployment.         | local file paths only.       |
+----+-----------------------+---------------------------------------+------------------------------+
| 9  | **Hallucinated Cost** | SLM invents unverified part savings.  | Clear truth hierarchy; SLM   |
|    |                       |                                       | is advisory; DB is sovereign.|
+----+-----------------------+---------------------------------------+------------------------------+
```

---

## 15. Phased Implementation Sequencing (AI-01 to AI-18)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               PHASED IMPLEMENTATION ROADMAP (AI-01 to AI-18)                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

  [AI-01] RUNTIME FOUNDATION & COMPATIBILITY GATE
          - Verify host hardware telemetry & Windows/CUDA/C-ABI runtime compatibility
          - Establish `ai/core/` configuration and thread-pinning baseline

  [AI-02] MODEL REGISTRY & OFFLINE IMPORT
          - Implement `ModelRegistry` service, local directory scanner, metadata extractor
          - Implement SHA-256 streaming verification and physical file preservation rules

  [AI-03] RUNTIME PROFILES & HARDWARE FIT ENGINE
          - Implement first-class Runtime Profiles (`POC-8GB`, `WORKSTATION-12GB`, `WORKSTATION-24GB`)
          - Implement dynamic VRAM/RAM fit equation and SAFE/CAUTION/UNSAFE categorization

  [AI-04] NATIVE GGUF RUNTIME CORE
          - Implement native GGUF engine wrapper supporting CPU/GPU offload
          - Implement async token streaming, cancellation tokens, and deterministic sampling

  [AI-05] MODEL LIFECYCLE & SEQUENTIAL SWAPPER
          - Implement `ModelLifecycleManager` with async acquire/release and memory purge
          - Enforce sequential model loading for 8 GB VRAM profile

  [AI-06] REAL EMBEDDING ENGINE & NATIVE PGVECTOR / HNSW
          - Implement local dense embedding provider with dynamic model dimensionality
          - Implement native PostgreSQL `vector(D)` storage and HNSW index creation

  [AI-07] REAL CROSS-ENCODER RERANKER
          - Implement local cross-encoder reranking provider
          - Implement candidate scoring, latency measurement, and CPU fallback

  [AI-08] CONTEXT MANAGEMENT & TOKEN BUDGETER
          - Implement context window budgeter, reserved token guard, and chunk placer
          - Implement primacy/recency ordering to protect against "lost in the middle"

  [AI-09] RETRIEVAL & EVIDENCE GROUNDING INTEGRATION
          - Connect live embedding and reranker to `HybridRetrievalEngine`
          - Integrate multi-horizon evidence discovery with strict grounding enforcement

  [AI-10] STRUCTURED OUTPUT & GBNF GRAMMAR ENGINE
          - Implement Pydantic-to-GBNF grammar compiler
          - Implement logit-constrained sampling and fallback validation / retry loop

  [AI-11] LOCAL MCP & TOOL SECURITY
          - Implement sandboxed local Tool Registry with domain tools (ECN, BOM, OPEX)
          - Implement parameter schemas, execution timeouts (1-3s), and loop breaker (max 3)

  [AI-12] CENTRAL AI ORCHESTRATOR & TASK ROUTER
          - Implement central `AIOrchestrator` coordinating all sub-layers
          - Implement `TaskRouter` mapping tasks to appropriate decoupled providers

  [AI-13] PROVIDER ADAPTER LAYER
          - Implement optional Ollama, LM Studio, and local provider adapters
          - Ensure built-in GGUF remains 100% operational when adapters are offline

  [AI-14] LOCAL OPENAI-COMPATIBLE API
          - Implement localhost-only `/v1/chat/completions`, `/v1/models`, `/v1/embeddings`
          - Configure strict CORS and policy-controlled local-only binding

  [AI-15] VISION / OCR PROVIDER ABSTRACTION
          - Implement extensible Vision/OCR provider interface for handwritten idea cards
          - Connect OCR output to Ideathon normalization and human review routing

  [AI-16] AI STUDIO UI WORKSPACE
          - Build React AI Studio: Model Library, Runtime Console, Hardware, Playground
          - Connect to backend `/api/v1/ai/` endpoints with live SSE streaming

  [AI-17] END-TO-END AI VALIDATION & REGRESSION
          - Implement automated unit and integration tests for all 18 AI sub-layers
          - Validate full business chain: Ingestion -> Retrieval -> SLM -> Review -> Audit

  [AI-18] PERFORMANCE & HARDWARE BENCHMARKING
          - Profile model load time, first-token latency, tokens/sec, and peak VRAM/RAM
          - Persist benchmark metadata alongside model version and runtime profile
```

---

## 16. Implementation Readiness & Dependency Checklist

| Sub-Phase ID | Sub-Phase Title | Prerequisites Required | Readiness Status |
| :--- | :--- | :--- | :--- |
| **AI-01** | Runtime Foundation & Compatibility Gate | Phase 10 Baseline Complete | **READY TO EXECUTE** |
| **AI-02** | Model Registry & Offline Import | AI-01 | **BLOCKED ON AI-01** |
| **AI-03** | Runtime Profiles & Hardware Fit | AI-01, AI-02 | **BLOCKED ON AI-02** |
| **AI-04** | Native GGUF Runtime Core | AI-01, AI-02, AI-03 | **BLOCKED ON AI-03** |
| **AI-05** | Model Lifecycle & Swapper | AI-03, AI-04 | **BLOCKED ON AI-04** |
| **AI-06** | Real Embedding & pgvector/HNSW | AI-01, AI-02 | **BLOCKED ON AI-02** |
| **AI-07** | Real Cross-Encoder Reranker | AI-01, AI-02, AI-05 | **BLOCKED ON AI-05** |
| **AI-08** | Context Management | AI-01 | **BLOCKED ON AI-01** |
| **AI-09** | Retrieval & Evidence Grounding | AI-06, AI-07, AI-08 | **BLOCKED ON AI-08** |
| **AI-10** | Structured Output & GBNF | AI-04, AI-05 | **BLOCKED ON AI-05** |
| **AI-11** | Local MCP & Tool Security | AI-01 | **BLOCKED ON AI-01** |
| **AI-12** | AI Orchestrator & Task Router | AI-04 through AI-11 | **BLOCKED ON AI-11** |
| **AI-13** | Provider Adapter Layer | AI-12 | **BLOCKED ON AI-12** |
| **AI-14** | Local OpenAI-Compatible API | AI-12, AI-13 | **BLOCKED ON AI-13** |
| **AI-15** | Vision / OCR Provider Abstraction | AI-12 | **BLOCKED ON AI-12** |
| **AI-16** | AI Studio UI Workspace | AI-12, AI-13, AI-14 | **BLOCKED ON AI-14** |
| **AI-17** | End-to-End AI Validation | AI-01 through AI-16 | **BLOCKED ON AI-16** |
| **AI-18** | Performance Benchmarking | AI-17 Complete | **BLOCKED ON AI-17** |

---

## 17. Final Stop & Sign-Off Request

This revised document represents the **authoritative, decoupled, and hardware-agnostic architecture** for unparking the complete Local AI Runtime. 

**Summary of Key Changes from Previous Draft:**
1. **Decoupled Task Providers:** Generation, Embedding, Reranking, Vision/OCR, and Tools are completely independent task runtimes.
2. **Dynamic Vector Dimensions:** Dimensionality is model-driven metadata; native `pgvector` HNSW indexing replaces JSON vector assumptions.
3. **Python / Native Compatibility Boundary:** Added explicit C-ABI compatibility gate to decouple application Python from native bindings.
4. **First-Class Runtime Profiles:** Added formal profiles (`POC-8GB`, `WORKSTATION-12GB`, `WORKSTATION-24GB`, `HIGH-END-48GB`) with live memory admission control.
5. **AI Studio UI Expansion:** Expanded to 8 integrated technical workspaces.
6. **18-Phase Roadmap:** Structured into sequential sub-phases AI-01 through AI-18 with rigorous dependency gating.

**No code has been implemented or modified.** We await your explicit manual approval to commence **AI-01: Runtime Foundation & Compatibility Gate**.
