# 07 — Security, Reliability, Governance & Auditability

## Security positioning

Use:

> Designed for private/on-premise deployment with no mandatory cloud AI/data dependency.

Do not claim 100% security.

Final security posture is subject to customer IT/InfoSec validation.

## Local security architecture

```text
Hero Network
  |
Application
  |
Local DB / Vector / Document Services
  |
Local AI Gateway
  |
Local Model Runtime
```

Security controls:

- network segmentation
- firewall controls
- outbound egress restrictions
- authentication
- authorization
- role-based access control
- database permissions
- encryption in transit
- encryption at rest
- secrets management
- audit logging
- backup/restore
- model/version governance

## No-cloud runtime principle

Production should not require:

- OpenAI
- Gemini
- Claude
- external LLM API
- external embedding API
- external OCR API
- cloud vector service
- cloud telemetry

## Data security

Use least privilege.

Do not expose the entire database to the model.

The model receives only task-specific evidence and approved tool outputs.

## Filesystem security

Protect against:

- path traversal
- arbitrary file access
- unauthorized model replacement
- arbitrary shell commands

Model-generated paths must be constrained to approved workspaces.

## MCP security

Treat MCP servers/tools as untrusted until allowlisted.

Every tool needs:

- permission
- scope
- risk class
- timeout
- audit requirement

High-risk tools require human confirmation.

## Reliability principle

Do not claim “zero hallucination”.

Use:

> Evidence-grounded, hallucination-controlled decision support.

Reliability is achieved through layered controls:

1. structured data truth
2. semantic retrieval
3. reranking
4. agentic cross-check
5. deterministic calculations
6. evidence validation
7. confidence routing
8. human review

## Confidence model

Confidence is evidence quality, not the LLM’s internal feeling.

Evidence factors:

- exact entity match
- model/variant match
- model year freshness
- verified implementation record
- project/ECN support
- cost record
- source freshness
- multi-source agreement

Return HIGH / MEDIUM / LOW.

## Human-in-the-loop

AI is decision support.

It does not autonomously:

- approve engineering changes
- approve safety-critical changes
- certify regulatory compliance
- approve financial projects

Workflow:

```text
AI recommendation
 -> Engineer / Expert
 -> Accept / Reject / Override / Review
 -> Audit trail
```

## Auditability

Record at minimum:

- idea ID
- model version
- provider/runtime
- retrieval timestamp
- evidence IDs
- matched project/implementation
- vehicle/model/variant
- calculation inputs
- result
- confidence
- reviewer decision
- override reason

## Logging

Separate where practical:

- application logs
- audit logs
- security logs
- AI evaluation logs

Do not log sensitive raw customer data unnecessarily.

## Reliability failure behavior

If model inference fails:

> “Local AI model unavailable.”

If retrieval fails:

> “Evidence retrieval unavailable.”

If evidence conflicts:

> “Conflicting records detected. Human review required.”

If evidence is insufficient:

> “Insufficient evidence for reliable determination.”

Never invent a fallback answer.

## Data ingestion reliability

Only delete source files after successful transaction/verification.

Handle:

- malformed files
- partial ingestion
- schema mismatch
- row-level errors
- duplicate data
- unit mismatch
- invalid models

## Business governance

Maintain versioning for:

- model
- prompt
- evaluation dataset
- calculation formulas
- scoring weights
- benchmark methodology
- taxonomy

Business logic changes require traceable versioning.
