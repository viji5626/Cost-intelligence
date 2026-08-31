# 04 — Vehicle Ideathon Intelligence Engine

## Objective

Process 10,000+ vehicle/product-focused Ideathon ideas and transform them into an actionable opportunity pipeline.

## End-to-end workflow

```text
10,000+ Ideas
   -> Ingestion
   -> Understanding
   -> Normalization
   -> Classification
   -> Semantic Clustering
   -> Duplicate / Near-Duplicate Detection
   -> Existing Implementation Search
   -> Vehicle / Model / Variant Mapping
   -> Component / Part Mapping
   -> Cost Impact
   -> Engineering / Quality / Safety Gates
   -> Priority Ranking
   -> Human Review
```

## Idea understanding

Extract:

- problem
- proposed solution
- product family
- vehicle/model/variant/year if present
- subsystem
- assembly
- component
- part
- material
- BOM/non-BOM
- cost reduction type
- weight impact
- quality impact
- safety impact
- reliability impact

## Semantic normalization

Normalize different wording to canonical concepts.

Example:

“bike”, “motorcycle”, “2-wheeler” -> controlled product vocabulary.

Do not destroy the original text.

## Duplicate detection

A duplicate/near-duplicate pipeline should use:

1. embedding similarity
2. exact/keyword matching where useful
3. metadata filtering
4. reranking
5. structured comparison / SLM reasoning

Do not rely on one similarity threshold for final business decisions.

## Cluster-level processing

Instead of evaluating every identical idea independently:

```text
10,000 ideas
   -> semantic clusters
   -> canonical opportunity groups
```

Maintain traceability from cluster to member ideas.

## Existing implementation detection

Search multiple evidence sources:

- previous Ideathon ideas
- engineering projects
- ECN/ECR records
- implementation records
- current vehicle master
- BOM/component records
- technical documents
- model configuration data

The system should answer:

- Was it implemented?
- Where?
- When?
- On which model?
- Which variant?
- Which generation/model year?
- On which component/part?
- Which project/ECN supports the claim?

## Model-specific applicability

Maintain an implementation matrix.

Example:

| Vehicle/Model | Variant | Model Year | Status |
|---|---|---:|---|
| Model X | Premium | 2025 | Implemented |
| Model X | Standard | 2025 | Not implemented |
| Model Y | Standard | 2026 | Not implemented |
| Model Z | Premium | 2026 | Implemented |

The recommendation may therefore be:

“Existing implementation detected on Model X Premium; evaluate applicability to Model X Standard and Model Y.”

## Vehicle cost opportunity

Use deterministic calculations.

Example:

Current component cost = ₹480
Proposed cost = ₹390
Saving/vehicle = ₹90
Annual applicable volume = 400,000
Gross annual saving = ₹3.6 Cr

Subtract implementation investment where available:

- tooling
- development
- validation
- testing
- supplier development
- certification
- implementation

Never fabricate missing values.

## Priority score

Make weights configurable.

Possible dimensions:

- financial impact
- technical feasibility
- applicability
- implementation effort
- scalability
- quality impact
- reliability
- strategic relevance
- data confidence

Do not allow the LLM to invent opaque scores.

## Engineering gates

Flag but do not autonomously approve:

- safety concerns
- reliability concerns
- durability concerns
- quality concerns
- regulatory concerns

Engineering experts retain decision authority.

## Human review

Actions:

- accept
- reject
- override
- merge
- request engineering review
- mark evidence correction

Store reviewer and decision history for audit/evaluation.

## Critical metrics

Track:

- classification accuracy
- duplicate precision/recall
- existing implementation recall
- model/variant mapping accuracy
- false-new rate
- review reduction
- human agreement

## Most important failure metric

### Missed Implementation Rate

False “new” decisions / actual implemented ideas.

This is particularly important because false “new” classification creates unnecessary engineering workload and weakens trust.
