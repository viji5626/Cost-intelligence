# 06 — Internal Local AI Runtime

## Strategic objective

The final product must NOT depend on Ollama or LM Studio.

Those may be used temporarily for development, comparison or experimentation.

The final platform contains its own internal Local AI Runtime.

This runtime is the internal execution layer for the business platform, not a replacement consumer product.

## Runtime responsibilities

- local model loading
- model validation
- model registry
- model lifecycle
- local inference
- text generation
- chat completion
- streaming
- structured output
- tool/function calling
- context management
- model capability discovery
- hardware/resource status
- local diagnostics
- local API gateway
- tool orchestration
- MCP interoperability

## Runtime architecture

```text
Business Application
       |
Local AI Gateway
       |
Model Orchestrator
       |
InferenceEngine interface
       |
+-----------------------+
| LlamaCppEngine        |
| FutureEngine          |
+-----------------------+
       |
GGUF / future formats
       |
CPU / GPU
```

## Inference foundation

Use llama.cpp / llama-cpp-python as the initial candidate foundation for GGUF local execution.

Do not implement neural-network kernels from scratch.

The custom runtime provides:

- lifecycle
- model registry
- gateway
- orchestration
- security
- tool policy
- context control
- diagnostics
- business integration

## InferenceEngine abstraction

Provide methods such as:

- load_model()
- unload_model()
- generate()
- chat()
- stream()
- generate_structured()
- generate_with_tools()
- health()
- model_info()
- supports_capability()

## Model registry

Track:

- model_id
- name
- family
- version
- format
- file path
- file size
- quantization
- context length
- architecture
- capabilities
- chat template
- vision support
- tool-calling support
- embedding/reranking capability where relevant
- checksum
- license metadata
- approval status

## Model validation

Before activation:

1. file exists
2. non-zero size
3. checksum if configured
4. supported format
5. metadata readable
6. supported architecture
7. runtime compatibility
8. hardware resource availability
9. valid context requirements
10. valid tokenizer/chat template configuration
11. capabilities detected

Never create empty/dummy model files.

## Chat template

Do NOT hard-code `chat_format="chatml"` for all models.

Use model metadata/configuration or explicit model-level configuration.

## Model capability routing

Capabilities may include:

- text
- vision
- tool calling
- structured output
- embedding
- reranking
- streaming

Applications request capabilities, not hard-coded model names where practical.

## Local AI Gateway

The gateway handles:

- request validation
- authorization
- model selection
- context construction
- model routing
- structured output
- tool invocation
- streaming
- timeouts
- request tracing
- audit hooks
- error handling

## OpenAI-compatible surface

Provide `/v1/models`, `/v1/chat/completions`, and other compatible endpoints where useful.

Compatibility is an interoperability layer, not the internal architecture.

## Tool policy

The model must never have unrestricted shell, filesystem, database or network access.

Use:

```text
Model
 -> Tool Policy Engine
 -> Authorized Tool Registry
 -> Tool
 -> Validated Result
 -> Model
```

Tool registry should define:

- tool ID
- name
- description
- input schema
- output schema
- permission
- risk level
- enabled state
- roles
- timeout
- audit requirement

## Tool loop

```text
Model
 -> Tool request
 -> Validate tool
 -> Authorize
 -> Validate arguments
 -> Execute
 -> Validate result
 -> Add result to context
 -> Continue model
```

Prevent:

- unbounded loops
- duplicate execution
- unauthorized tools
- malformed arguments
- excessive execution time

Provide `max_tool_calls`, timeouts and overall workflow limits.

## MCP

MCP is an interoperability layer, not the core business architecture.

Use an MCP adapter where helpful.

Core business tools should be local services and must not depend on external MCP servers.

Provide:

- MCP connection manager
- session manager
- tool registry/cache
- health/reconnect

Do not rediscover tools or spawn a fresh process for every chat request unless specifically required.

Handle structured MCP results and errors, not only plain text.

## Internal Local AI Studio

Build a technical admin/development interface separate from the Hero business UI.

Functions:

- list models
- register model
- validate model
- load/unload
- test prompts
- test structured output
- test tools
- test vision
- inspect hardware
- view local logs
- benchmark latency
- inspect capabilities

This is not the executive/business UI.

## Air-gapped operation

Production runtime should work without Internet connectivity.

No mandatory cloud dependency for:

- LLM
- embeddings
- reranking
- OCR
- vector search
- telemetry
- document processing

Installation/update transfers may occur through controlled procedures.

## Zero telemetry

Do not add:

- remote analytics
- crash reporting to external services
- hidden usage tracking
- cloud model telemetry

Diagnostics remain local.

## Local model store

Suggested:

```text
models/
  registry/
  active/
  cache/
  quarantine/
  archived/
```

Invalid/unverified models remain quarantined.

## Hardware management

Detect:

- CPU
- RAM
- GPU
- VRAM
- GPU count

Use resource information for model-load decisions.

Avoid loading every model simultaneously.

## Model lifecycle

Support:

- register
- validate
- approve
- activate
- load
- unload
- switch
- archive
- remove

## Error behavior

Never fabricate output when inference/tooling fails.

Examples:

- model unavailable
- model loading
- evidence retrieval unavailable
- tool unavailable
- insufficient evidence
- conflicting records

Return explicit machine-readable and user-friendly errors.

## Custom runtime phasing

Do not build a full Ollama/LM Studio clone first.

Implement in this order:

R0 interfaces
R1 InferenceEngine abstraction
R2 LlamaCppEngine
R3 Model registry
R4 Model validation
R5 Local AI Gateway
R6 Structured output
R7 Tool calling
R8 Tool policy
R9 MCP adapter
R10 Context manager
R11 Hardware/resource manager
R12 Local AI Studio
R13 Business platform integration
R14 Performance evaluation
R15 Security hardening

## Critical architectural guarantee

The Hero business application must continue to work if:

- Ollama disappears
- LM Studio disappears
- a specific model is replaced
- llama.cpp is replaced
- embedding provider is replaced
- reranker is replaced

Only the infrastructure adapters should change.
