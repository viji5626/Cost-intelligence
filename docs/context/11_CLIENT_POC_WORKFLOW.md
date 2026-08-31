# 11 — Client POC Workflow & Demonstration Script

## Objective

Demonstrate to Hero MotoCorp that the concept can be validated safely using representative data after NDA.

The presentation/demo should be business-first. Technical internals are revealed only when requested.

## Demo 1 — Plant OPEX Benchmarking

### Input
Upload a representative Excel dataset.

### Workflow

```text
Excel
 -> schema recognition
 -> validation
 -> normalization
 -> database
 -> KPI calculation
 -> peer comparison
 -> benchmark
 -> gap
 -> opportunity
```

### Demo result

Show:

- plant actual
- benchmark
- variance
- historical trend
- top drivers
- potential opportunity

Every number must show its source/calculation basis where practical.

## Demo 2 — Ideathon Intelligence

### Input
Upload a sample historical Ideathon file.

### Workflow

```text
Raw idea
 -> normalized idea
 -> vehicle/component extraction
 -> semantic search
 -> duplicate cluster
 -> implementation search
 -> vehicle/model/variant mapping
 -> cost opportunity
 -> evidence
 -> confidence
 -> human review
```

## Demo 3 — Existing Implementation

Use an idea whose solution is known to exist on only some product configurations.

Show:

- similar ideas
- implementation project
- model
- variant
- year
- component
- implementation status
- current applicability gap

The goal is to prove that “already implemented” is treated as a WHERE/WHEN/ON-WHAT problem, not a binary flag.

## Demo 4 — Local AI question

Ask a question such as:

> Which similar vehicle cost-reduction ideas are not implemented on the selected model?

Show:

```text
Question
 -> retrieval plan
 -> evidence
 -> structured facts
 -> local SLM explanation
```

## Demo 5 — Evidence

Open the evidence panel and show:

- source
- record
- model
- date
- calculations
- confidence

## Demo 6 — Uncertainty

Use a deliberately incomplete/conflicting example.

Expected behavior:

> Insufficient evidence / Human review required.

This demonstrates reliability better than claiming perfect accuracy.

## Demo 7 — Local runtime

Show the technical admin UI:

- local model loaded
- hardware
- local endpoint
- no external API dependency
- model registry
- tool policy

## Customer POC request

The appropriate next step is:

NDA
 -> Data workshop
 -> Agree data scope
 -> Controlled sample
 -> POC
 -> Measure
 -> Pilot decision

Do not request full enterprise integration at the start.

## Suggested language

Use:

- private
- local
- evidence-grounded
- deterministic
- controlled
- auditable
- measurable
- human-in-the-loop
- POC validation

Avoid:

- magic
- autonomous engineering
- zero hallucination
- 100% accuracy
- 100% secure
