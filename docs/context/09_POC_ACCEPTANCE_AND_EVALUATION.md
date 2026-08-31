# 09 — POC Acceptance, Evaluation & Success Criteria

## Purpose

The POC exists to prove technical feasibility and measurable business value using representative Hero data after NDA.

Do not ask for full enterprise integration as the first step.

## Suggested POC data scope

- historical Ideathon sample
- limited vehicle master
- limited existing implementation/project records
- limited BOM/component cost if permitted
- limited plant OPEX sample
- representative supporting documents

## POC success categories

### Business

- reduction in manual idea screening
- improved identification of duplicate ideas
- improved identification of existing implementations
- better visibility of model/variant applicability
- useful cost-opportunity ranking
- useful OPEX benchmarking

### AI

- classification precision/recall
- duplicate detection precision/recall
- existing implementation recall
- false-new rate
- model/variant mapping accuracy
- retrieval Recall@K
- human agreement

### Numerical

- KPI calculation correctness
- vehicle cost calculation correctness
- benchmark arithmetic correctness
- annual opportunity arithmetic correctness

### Operational

- ingestion latency
- search latency
- inference latency
- end-to-end response time
- resource utilization

### Security

- no mandatory cloud calls during runtime
- network egress validation
- access-control validation
- audit validation
- file retention/deletion verification

## Hero Gold Dataset

Create a representative historical dataset where experts label:

- valid/invalid
- duplicate/near duplicate
- existing implementation
- model applicability
- cost relevance
- final disposition

This becomes the benchmark for POC evaluation.

## Critical metrics

### Missed Implementation Rate

False “new” decisions / actual implemented ideas.

This metric should be aggressively minimized.

### Human Review Reduction

Compare:

manual ideas requiring review before POC
vs
ideas requiring manual review after AI-assisted filtering.

Do not fabricate a target percentage before measuring baseline.

## Evaluation procedure

1. Freeze a validation set.
2. Run the current system without manual intervention.
3. Compare with human ground truth.
4. Review false positives and false negatives.
5. Identify retrieval misses.
6. Identify model reasoning errors.
7. Identify data quality problems separately from AI problems.
8. Tune retrieval/logic/prompts.
9. Re-run on a held-out set.
10. Report results transparently.

## Confidence validation

Validate whether High/Medium/Low evidence confidence correlates with actual correctness.

Do not treat model-generated probability as a formal statistical confidence unless properly calibrated.

## POC exit criteria

A POC is successful when:

- end-to-end workflows operate reliably;
- evidence can be traced;
- numeric results match deterministic expected results;
- existing-implementation detection is useful on historical cases;
- reviewers find the prioritized output operationally useful;
- local runtime operates without cloud AI dependency;
- security posture meets agreed POC controls;
- performance is acceptable for intended POC workload;
- a clear Pilot/No-Pilot decision can be made from evidence.

## POC deliverables

1. Working application.
2. Local AI runtime capability demonstration.
3. OPEX benchmarking demonstration.
4. Ideathon evaluation demonstration.
5. Data ingestion pipeline.
6. Evaluation report.
7. Accuracy and error analysis.
8. Security validation note.
9. Recommended pilot architecture.
10. Production sizing assumptions.
