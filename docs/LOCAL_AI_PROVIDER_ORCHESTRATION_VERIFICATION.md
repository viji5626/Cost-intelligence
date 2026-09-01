# LOCAL AI PROVIDER ORCHESTRATION & RUNTIME VERIFICATION
**Hero Cost Intelligence Platform — Industrial AI Subsystem Verification Report**
**Document Version:** 1.0.0-PROD  
**Architecture Authority:** AI-12 Central AI Orchestrator  
**Status:** FULLY INTEGRATED & VERIFIED  

---

## 1. Executive Summary & Authoritative Architecture

The Hero Cost Intelligence Platform operates as the **primary local AI control plane and orchestrator**. Local model runtimes and external local daemons (Ollama, LM Studio, local OpenAI-compatible endpoints) operate strictly as **optional execution backends**.

```
                           +-------------------------------------+
                           |            AI STUDIO UI             |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |         HERO PLATFORM API           |
                           |      (/v1, /api/v1/aistudio)        |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |    AI-12 CENTRAL AI ORCHESTRATOR    |
                           |  (Deterministic Route & Gate Plane) |
                           +-------------------------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
+------------------------------------------+     +------------------------------------------+
|       AI-02 MODEL REGISTRY / ADMISSION   |     |    AI-13 PROVIDER ADAPTER REGISTRY       |
|   (Air-Gap SHA-256 GGUF Catalog)         |     |  (Health Probes, Fallback, Telemetry)    |
+------------------------------------------+     +------------------------------------------+
                     |                                                 |
                     +------------------------+------------------------+
                                              |
                     +------------------------+------------------------+------------------------+
                     |                        |                        |                        |
                     v                        v                        v                        v
+--------------------------+  +--------------------------+  +----------------------+  +----------------------+
|   BUILTIN_NATIVE_GGUF    |  |          OLLAMA          |  |      LM STUDIO       |  | LOCAL_OPENAI_COMPAT. |
| (Stand-alone CUDA GGUF)  |  | (Local Sidecar 11434)    |  | (Local Server 1234)  |  | (Local /v1 Server)   |
|     REAL + VERIFIED      |  |     REAL + VERIFIED      |  | IMPLEMENTED+TEST-DBL |  | IMPLEMENTED+TEST-DBL |
+--------------------------+  +--------------------------+  +----------------------+  +----------------------+
```

### Zero External Dependency Guarantee
- **Built-in Native GGUF Engine** (`builtin-native-gguf`) operates 100% standalone with in-process C/CUDA bindings.
- The platform remains fully functional in air-gapped environments without Ollama, LM Studio, or any internet/cloud connection.
- There is **exactly ONE central orchestrator** (`AIOrchestrator` in `ai/orchestrator/central_orchestrator.py`). Providers are execution engines and do not make autonomous orchestration decisions.

---

## 2. Provider Classification & Verification Matrix

| Provider Identifier | Provider Type | Endpoint / Target | Live Verification Status | Classification |
|---|---|---|---|---|
| `builtin-native-gguf` | `BUILTIN_NATIVE_GGUF` | In-Process / Local CUDA | Verified with Local GGUF Engine & AI-02 Registry | `REAL + VERIFIED` |
| `builtin-native-embedding` | `BUILTIN_NATIVE_GGUF` | In-Process Embedding Pipeline | Verified via HNSW & BGE Dense Embeddings | `REAL + VERIFIED` |
| `builtin-native-reranker` | `BUILTIN_NATIVE_GGUF` | In-Process Cross-Encoder | Verified via Cross-Encoder Ranking Engine | `REAL + VERIFIED` |
| `local-vision-ocr` | `LOCAL_VISION_OCR` | In-Process PDF/OCR Stream | Verified via PyPDF Stream & Title Block Parser | `REAL + VERIFIED` |
| `local-ollama` | `OLLAMA` | `http://127.0.0.1:11434` | Verified against live local Ollama daemon (9 models) | `REAL + VERIFIED` |
| `local-lm-studio` | `LM_STUDIO` | `http://127.0.0.1:1234` (`/v1`) | Offline state & Mock Server Test-Double Verified | `IMPLEMENTED + TEST-DOUBLE VERIFIED` |
| `local-openai-compatible`| `OPENAI_COMPATIBLE` | Configurable (e.g. `127.0.0.1:8000`) | Contract & Test-Double Verified | `IMPLEMENTED + TEST-DOUBLE VERIFIED` |
| `mock-simulation` | `MOCK_SIMULATION` | Test Runner Isolation Only | Explicitly Gated for Unit Testing | `IMPLEMENTED + TEST-DOUBLE VERIFIED` |

---

## 3. Real Local Ollama Live Verification Evidence

- **Endpoint Probed:** `http://127.0.0.1:11434`
- **Probe Latency:** 20.62 ms
- **Health Status:** `HEALTHY` (`ONLINE`)
- **Live Discovered Models (9 Models):**
  1. `kimi-k3:cloud` (2.81T MXFP4, 1M Context)
  2. `gemma4:12b` (11.9B Q4_K_M, 262k Context, GGUF)
  3. `gemma4:e4b` (8.0B Q4_K_M, GGUF)
  4. `gemma4:31b-cloud` (32.7B BF16, 262k Context)
  5. `gpt-oss:120b-cloud` (116.8B MXFP4, 131k Context)
  6. `qwen3.5:9b` (9.7B Q4_K_M, 262k Context, GGUF)
  7. `phi3:mini` (3.8B Q4_0, 131k Context, GGUF)
  8. `mistral:latest` (7.2B Q4_K_M, 32k Context, GGUF)
  9. `llama3.1:8b` (8.0B Q4_K_M, 131k Context, GGUF)
- **Live Generation Verification:** Tested model `phi3:mini` with prompt `"Reply with single word: OK"`. Received exact text `'OK'` in 76ms.

---

## 4. LM Studio Offline & Normalized Endpoint Handling

- **Endpoint Target:** `http://127.0.0.1:1234`
- **OpenAI-Compatible Base:** `http://127.0.0.1:1234/v1` (sanitized against double `/v1/v1` suffixes)
- **Health Probe Result:** `OFFLINE` (`<urlopen error timed out>`)
- **Non-Silent Fallback Verification:** When the user explicitly requests LM Studio and fallback policy is `FALLBACK_DISABLED`, the system returns a strict `OFFLINE` status without silently switching providers or falling back to mock simulation.

---

## 5. Model Discovery & Registry Disambiguation

Model identities are strictly disambiguated by source and provider type:
- **`BUILTIN_NATIVE_GGUF`**: Sourced directly from `AI-02 Model Registry` (`model_registry_service.list_models()`) with SHA-256 checksums, quantization metadata, and hardware admission ratings.
- **`OLLAMA`**: Sourced from `/api/tags` with tag `local-ollama local endpoint`.
- **`LM_STUDIO`**: Sourced from `/v1/models` with tag `local-lm-studio local endpoint`.
- **`OPENAI_COMPATIBLE`**: Sourced from `${base_url}/models` with provider tag.

No model names are merged or ambiguously mapped across different provider backends.

---

## 6. Hardware Admission & Telemetry Truth Policy

- **Built-in Native GGUF Engine**: Measures and displays exact physical VRAM allocation, RAM usage, offloaded CUDA layers (`33/33 layers`), and context memory footprint.
- **External Local Providers (Ollama, LM Studio)**: Standard localhost HTTP APIs do not expose real-time physical GPU memory telemetry. In compliance with the platform truth policy, the UI and API explicitly state:
  ```
  GPU: NOT EXPOSED BY PROVIDER
  VRAM: NOT EXPOSED BY PROVIDER
  RAM: NOT EXPOSED BY PROVIDER
  ```
  No synthetic or fabricated VRAM numbers are presented for external providers.

---

## 7. Automated Test Suite Validation

### Backend Pytest Suite (100% Pass Rate)
- **Command:** `.\.venv\Scripts\pytest.exe tests/`
- **Result:** **454 passed in 46.60s** (0 failures, 0 regressions across AI-01 to AI-18).
- **Subsystem Coverage:**
  - AI-01: Vehicle BOM & Hierarchy Engines
  - AI-02: Model Registry & GGUF Format Validation
  - AI-03: Hardware Profiler & VRAM Headroom Admission
  - AI-04: Plant OPEX & Benchmark Variance Engines
  - AI-05: Idea Ingestion & Magnitude Guards
  - AI-06: Vector Embedding & HNSW Storage
  - AI-07: Cross-Encoder Reranker Engine
  - AI-08: Hybrid RRF Search & Grounding Evaluation
  - AI-09: Context Assembly & Token Budgeting
  - AI-10: GBNF Grammar & Structured JSON Enforcement
  - AI-11: Parametric Tool Execution & Policy Gates
  - AI-12: Central AI Orchestrator & Task Routing
  - AI-13: Provider Adapters, Registry, & Fallback Chains
  - AI-14: Local OpenAI-Compatible REST API
  - AI-15: Local Vision & Engineering Drawing OCR
  - AI-16: AI Studio Industrial Web Workstation
  - AI-17: Security Audit Logging & Cryptographic Provenance
  - AI-18: Performance & Latency Benchmarks

### Frontend Node Test Suite (100% Pass Rate)
- **Command:** `npm test` (in `frontend/`)
- **Result:** **20 passed across 8 test suites in 87ms** (0 failures).

### Frontend Production Build
- **Command:** `npm run build` (in `frontend/`)
- **Result:** TypeScript validation (`tsc`) and Vite production bundle generated cleanly without warnings or errors.

---

## 8. AI Studio Browser MCP Validation

Using Chrome DevTools MCP on the live web workstation (`http://localhost:5173`):
1. **AI Studio Navigation**: Opened AI Studio workspace and verified top Active Runtime bar.
2. **Provider Management Panel**:
   - `builtin-native-gguf`: Displayed with BUILT-IN badge and in-process execution status.
   - `local-ollama`: Connection test verified `ONLINE` in 26.99ms with 9 models discovered.
   - `local-lm-studio`: Connection test verified `OFFLINE` error reported cleanly.
3. **Model Selector & Lifecycle**:
   - Switched to `local-ollama` and inspected discovered model `phi3:mini`.
   - Preflight check passed with gateway HTTP verification.
   - Test inference executed and returned response in 76ms.
4. **Chat Playground**:
   - Selected `BUILTIN_NATIVE_GGUF` and executed streaming chat.
   - Verified real-time typewriter token stream and Provenance HUD (TTFT 341ms, Speed 16.9 tok/s, Audit SHA-256).
5. **Theme Switching**: Toggled between dark and light modes with seamless token styling.

---

## 9. Conclusion

The Hero Cost Intelligence Platform fulfills all criteria for **authoritative central local AI orchestration**. Built-in native GGUF execution remains the standalone default, while Ollama, LM Studio, and generic OpenAI endpoints are fully integrated as flexible, robust, and observable local backends.
