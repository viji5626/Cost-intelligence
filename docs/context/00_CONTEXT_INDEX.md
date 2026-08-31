# HERO Vehicle Cost & Plant OPEX Intelligence Platform
## Antigravity Context Index

This folder contains the phase-wise project context for building the Hero MotoCorp POC and eventual enterprise platform.

## How to use these files

Do NOT paste all files into a single prompt.

Use them progressively in Antigravity:

1. Read `01_BUSINESS_VISION_AND_REQUIREMENTS.md` first.
2. Then read `02_SYSTEM_ARCHITECTURE.md`.
3. Then read the relevant data/business files for the feature being implemented.
4. Read `05_AI_RAG_AND_AGENTIC_RETRIEVAL.md` before implementing AI retrieval.
5. Read `06_LOCAL_AI_RUNTIME.md` before implementing the internal model runtime.
6. Read `07_SECURITY_RELIABILITY_AND_GOVERNANCE.md` before security hardening.
7. Read `08_IMPLEMENTATION_ROADMAP.md` before coding each phase.
8. Use `09_POC_ACCEPTANCE_AND_EVALUATION.md` for validation.
9. Use `10_ANTIGRAVITY_EXECUTION_RULES.md` as the standing development instruction.

## Core product statement

Build a private, evidence-grounded vehicle cost and plant OPEX intelligence platform using deterministic analytics, structured enterprise data, semantic retrieval, agentic retrieval and local SLM reasoning.

## Two independent business engines

### 1. Vehicle Ideathon Intelligence
10,000+ vehicle/product-focused ideas are evaluated for validity, duplication, existing implementation, model/variant applicability, vehicle cost impact, engineering implications and prioritization.

### 2. Plant OPEX & Expenditure Benchmarking
Plant operational data is normalized and benchmarked across comparable plants using KPIs such as kWh/vehicle, KL/vehicle and ₹/vehicle, with gap analysis and savings opportunity calculation.

These engines share infrastructure but MUST retain separate business logic.

## Core design principle

**AI interprets. Data proves. Calculations quantify. Evidence supports. Humans decide.**

## Core truth boundaries

- SQL / structured data = authoritative facts and numeric values.
- Relationship model / knowledge graph = vehicle/model/component relationships.
- Vector search + reranking = semantic retrieval.
- Deterministic calculation engine = financial and KPI calculations.
- RAG = current enterprise knowledge.
- Local SLM = reasoning, classification and explanation.
- Human experts = final engineering/management authority.
- Local AI Runtime = model execution infrastructure, not business memory.

## Local-first principle

The final product must NOT depend on Ollama or LM Studio. They may be used temporarily during development. The production platform must contain its own local AI runtime abstraction built over a mature inference foundation such as llama.cpp/llama-cpp-python.

## Important non-goals

Do not build a generic chatbot, autonomous engineering approval system, or a monolithic LLM application.

Do not claim “zero hallucination”, “100% accuracy” or “100% secure”. Use “evidence-grounded”, “hallucination-controlled”, “human-in-the-loop”, and “designed for on-premise/private deployment”.
