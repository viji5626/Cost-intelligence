# 05 — AI, RAG, Hybrid Search, Agentic Retrieval & Evaluation

## AI design principle

Do not build:

```text
Idea -> LLM -> Answer
```

Build:

```text
Idea
 -> entity extraction
 -> SQL exact search
 -> semantic retrieval
 -> relationship lookup
 -> reranking
 -> agentic retrieval
 -> evidence assembly
 -> deterministic calculations/tools
 -> local SLM
 -> structured recommendation
```

## SLM

Initial POC candidate: Qwen3.5-9B-class local SLM.

Use for:

- understanding
- classification
- normalization assistance
- semantic reasoning
- explanation
- structured decision output
- multimodal interpretation if required

Do not use as:

- authoritative database
- numerical calculator
- safety authority
- product master
- business memory store

## Embeddings

Initial candidate: Qwen3-Embedding-0.6B-class model.

Use for semantic retrieval.

Do not hard-code model-specific behavior into the application.

## Reranking

Initial candidate: Qwen3-Reranker-0.6B-class model.

Use to improve precision of retrieved candidates.

## Hybrid search

Combine:

- semantic/vector search
- exact/keyword search
- metadata filtering
- reranking

Exact search is essential for:

- part numbers
- model codes
- ECN/ECR numbers
- project IDs
- supplier codes
- document IDs

## Chunking principles

### Ideas
Keep a single idea as a semantic unit.

### Projects
Keep a project summary as a semantic unit, with metadata.

### Technical documents
Chunk structurally by sections/subsections/tables/evidence blocks.

### BOM
Keep authoritative BOM in SQL. Do not rely on row-level vectorization as the source of truth.

## Metadata on retrievable content

Include where applicable:

- document_id
- source_type
- vehicle_family
- model
- variant
- generation
- model_year
- subsystem
- component
- part_no
- supplier
- project_id
- implementation_status
- valid_from
- valid_to
- department
- confidence/evidence quality

## Agentic retrieval

An agent should decide what evidence is needed.

Example query:

“Has the lightweight battery bracket idea already been implemented and could it apply to another model?”

Potential subtasks:

1. Identify component.
2. Identify target model.
3. Search similar ideas.
4. Search projects.
5. Search implementations.
6. Search ECN/ECR.
7. Search current vehicle configuration.
8. Search cost.
9. Search model applicability.
10. Evaluate conflicting evidence.

## Controlled tool registry

Expose approved tools only:

- search_ideas()
- search_projects()
- search_implementations()
- search_vehicle()
- search_model()
- search_variant()
- search_component()
- search_part()
- search_bom()
- search_ecns()
- search_documents()
- get_component_cost()
- get_production_volume()
- get_model_applicability()
- calculate_vehicle_saving()
- calculate_annual_saving()
- calculate_roi()
- check_quality_gate()
- check_safety_gate()
- check_reliability_gate()

Never expose unrestricted database or shell access to the model.

## Lost-in-the-middle protection

Do not put 10,000 ideas plus all documents into one giant prompt.

Use:

```text
Large corpus
 -> candidate retrieval
 -> metadata filtering
 -> reranking
 -> small high-quality evidence set
 -> SLM
```

Context window is a capability, not a replacement for retrieval.

## Recursive analysis / RLM

Treat recursive language model patterns as an advanced capability for very large investigations.

Do not make RLM mandatory for the first POC.

Potential pattern:

```text
10,000 ideas
 -> partitions
 -> local analyses
 -> local clusters/summaries
 -> reconciliation
 -> global analysis
```

## RAG principle

RAG is for current enterprise knowledge.

Do not fine-tune rapidly changing information into the model weights.

Keep live information in:

- SQL
- vector index
- relationship model
- document store

## Fine-tuning principle

Fine-tune on:

- Hero terminology
- evaluation methodology
- classification behavior
- decision taxonomy
- example reasoning
- output format

Do not fine-tune continually on:

- current BOM
- current costs
- current vehicle portfolio
- current implementation status
- current production data

## Catastrophic forgetting

Use controlled LoRA/QLoRA adaptation and periodic validated retraining.

Keep changing enterprise facts outside model weights.

## Structured AI output

Use typed/Pydantic/JSON-schema outputs.

Example:

```json
{
  "decision": "PARTIALLY_IMPLEMENTED",
  "confidence_level": "HIGH",
  "affected_vehicle": "...",
  "affected_model": "...",
  "affected_component": "...",
  "similar_ideas": [],
  "implementations": [],
  "cost_opportunity": {},
  "evidence": [],
  "missing_information": [],
  "human_review_required": true
}
```

Business logic must not depend on parsing arbitrary prose.

## Evidence confidence

Do not call this “LLM confidence”.

Use evidence confidence derived from factors such as:

- exact entity match
- exact vehicle/model/variant match
- current model year
- verified implementation record
- ECN/ECR
- project evidence
- cost record
- source freshness
- agreement across sources

Possible output:

HIGH / MEDIUM / LOW

## Confidence routing

```text
HIGH -> normal downstream workflow
MEDIUM -> human review
LOW / conflict -> insufficient evidence / manual investigation
```

## Evaluation framework

Create a Hero Gold Dataset with historically reviewed and human-labelled ideas.

Evaluate:

- precision
- recall
- F1
- Recall@K
- MRR/nDCG where useful
- implementation recall
- model mapping accuracy
- human agreement
- cost calculation accuracy
- false-new rate
- review reduction
- response latency

Do not claim performance until measured on representative data.
