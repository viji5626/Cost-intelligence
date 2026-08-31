# 10 — Antigravity Execution Rules

## Role

Act as a senior enterprise software engineering team, not a code generator.

## Standing rules

1. Read the relevant context files before implementing a feature.
2. Preserve the separation between Vehicle Ideathon and Plant OPEX business logic.
3. Never move authoritative business truth into LLM weights.
4. Never make numerical calculations depend on model-generated arithmetic.
5. Never hard-code production customer data.
6. Never hard-code secrets.
7. Never introduce cloud AI as a hidden dependency.
8. Never call Ollama/LM Studio directly from business code.
9. Keep AI provider/inference engine abstractions.
10. Use typed schemas and contracts.
11. Test every business-critical function.
12. Make errors explicit.
13. Never fabricate missing evidence.
14. Prefer “insufficient evidence” over a forced answer.
15. Require human review for uncertain or safety-critical decisions.
16. Maintain auditability.
17. Keep code modular and replaceable.
18. Avoid premature overengineering.
19. Do not implement the entire product in a single pass.
20. Commit meaningful milestones.

## Development cycle

```text
Requirement
 -> Architecture check
 -> Task breakdown
 -> Implementation
 -> Tests
 -> Run application
 -> Browser/UI verification
 -> Code review
 -> Documentation update
 -> Git commit
```

## Before coding

For each feature state:

- objective
- affected modules
- dependencies
- acceptance criteria
- tests
- data impact
- security impact
- AI impact if any

## Architecture review questions

Before accepting a change ask:

- Does this mix OPEX and Ideathon business rules?
- Does this turn the LLM into a source of truth?
- Does this introduce cloud dependency?
- Does this create vendor lock-in?
- Can this be tested deterministically?
- Is there an audit trail?
- Is the failure mode safe?
- Can the feature operate if the AI is unavailable?
- Can the model be replaced later?
- Can the database schema evolve?

## First task after reading the complete project context

DO NOT implement the full product immediately.

Create and review:

1. repository structure
2. architecture document
3. ERD
4. database schema
5. data dictionary
6. API contracts
7. AI interfaces
8. retrieval boundaries
9. security architecture
10. POC roadmap
11. testing strategy
12. local AI runtime boundary

Then identify remaining risks and only then start implementation.

## Recommended implementation order

### Foundation
- repository
- database
- migrations
- config
- logging
- API
- tests

### Data
- vehicle master
- plant master
- ingestion

### OPEX
- KPI engine
- benchmarking
- opportunity

### Ideathon
- ideas
- normalization
- duplicate clustering
- implementation search
- model applicability
- cost opportunity

### Retrieval
- embedding
- hybrid search
- reranking

### AI
- local SLM
- evidence prompts
- structured output
- agentic retrieval

### Governance
- confidence
- human review
- audit
- evaluation

### Runtime
- local inference engine
- model registry
- gateway
- tool policy
- MCP

### UI
- executive
- OPEX
- Ideathon
- review
- admin

## UI principles

Enterprise industrial software aesthetic.

Prefer:

- clean hierarchy
- benchmark charts
- comparison matrices
- evidence panels
- opportunity ranking
- model/component relationship views
- clear decision states

Avoid:

- excessive neon/futuristic styling
- robot/AI gimmicks
- unnecessary 3D effects
- decorative charts
- dense unreadable tables

## Business UI information priority

For any idea, users should quickly see:

1. What is it?
2. Which vehicle/model/variant?
3. Which component?
4. Duplicate?
5. Existing implementation?
6. Where/when implemented?
7. Cost opportunity?
8. Evidence?
9. Confidence?
10. Recommended next action?

## Synthetic data

Synthetic/demo data is allowed during development only.

Every synthetic dataset/value must be explicitly labelled:

DEMO DATA
ILLUSTRATIVE
SYNTHETIC

Never let synthetic data appear as customer information.

## Final product philosophy

The end state is:

Business Truth -> SQL
Relationship Truth -> Vehicle Knowledge Model
Semantic Retrieval -> Vector + Reranker
Numerical Truth -> Deterministic Calculation Engine
Current Knowledge -> RAG/Evidence
Reasoning -> Local SLM
Tool Execution -> Controlled Tools/MCP
Model Execution -> Internal Local AI Runtime
Human Authority -> Engineering/Management

The platform must remain useful even when AI is unavailable for parts of the workflow.
