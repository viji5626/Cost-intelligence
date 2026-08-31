# 01 — Business Vision & Requirements

## Objective

Create a private enterprise intelligence platform for Hero MotoCorp that:

1. Benchmarks plant OPEX and expenditure across plants.
2. Processes 10,000+ vehicle-focused Ideathon ideas.
3. Identifies duplicates and near-duplicates.
4. Detects existing implementations.
5. Identifies exactly where an idea is implemented: vehicle family, model, variant, generation, model year, subsystem, assembly, component and/or part.
6. Detects partial implementation across product variants.
7. Estimates vehicle cost-reduction opportunities using verified structured data.
8. Provides evidence-backed prioritization.
9. Keeps AI/data processing local for privacy-sensitive deployments.
10. Produces measurable POC evidence before production commitment.

## Business split

### A. Vehicle Ideathon Intelligence

Ideathon ideas are about the VEHICLE / PRODUCT being produced. They are not primarily plant-OPEX ideas.

The system should determine:

- Is this a valid idea?
- Is it meaningful/actionable?
- Is it a duplicate or near-duplicate?
- What is the normalized problem and proposed solution?
- Which product family / vehicle / model / variant / generation / model year is affected?
- Which subsystem / assembly / component / part is affected?
- Is the opportunity BOM or non-BOM?
- Has a similar idea already been submitted?
- Has the underlying solution already been implemented?
- On which vehicle/model/variant/year?
- Is the implementation current or historical?
- Is the implementation partial across the portfolio?
- Could it still be applicable to another model?
- What is the potential cost saving per vehicle?
- What is the annual opportunity?
- What implementation investment may be needed?
- Are there safety, quality, reliability or regulatory constraints?
- Should it be prioritized for engineering review?

### B. Plant OPEX & Expenditure Benchmarking

The objective is:

> Which plant is spending more than its comparable benchmark, on what, why, and what opportunity exists to close the gap?

Potential KPIs:

- kWh / vehicle
- electricity ₹ / vehicle
- KL water / vehicle
- water ₹ / vehicle
- gas / vehicle
- compressed air / vehicle
- maintenance OPEX / vehicle
- manpower cost / vehicle
- total OPEX / vehicle
- controllable OPEX / vehicle
- resource / sustainability intensity metrics where applicable

Support:

- best comparable plant benchmark
- peer benchmark
- historical benchmark
- management target benchmark
- variance
- trend
- benchmark gap
- driver decomposition
- savings opportunity

Do not compare raw expenditure as the sole basis of plant performance.

## Duplicate vs implemented

### Duplicate
Two or more submitted ideas are substantially the same.

### Already implemented
The idea may be unique to Ideathon, but its underlying solution already exists in Hero's engineering/product ecosystem.

### Partially implemented
The solution exists only on some model/variant/year combinations.

Example:

- Model X Premium: Implemented
- Model X Standard: Not implemented
- Model Y: Not implemented
- Model Z: Implemented

The system should report the scope, not simply “already implemented”.

## Temporal requirement

Track:

- effective_from
- effective_to
- model year
- generation
- variant
- implementation status
- project
- ECN/ECR where available

Historical implementation must not automatically be considered current implementation.

## Cost opportunity

Vehicle cost examples:

- material cost
- part cost
- component cost
- BOM cost
- assembly cost
- manufacturing cost
- tooling cost
- supplier cost
- logistics-related product cost
- warranty/lifecycle cost where applicable
- weight-related cost
- process cost

Separate BOM from non-BOM opportunities.

## Example decision taxonomy

- INVALID
- DUPLICATE
- NEAR_DUPLICATE
- ALREADY_IMPLEMENTED
- PARTIALLY_IMPLEMENTED
- IMPLEMENTED_ON_DIFFERENT_MODEL
- NOT_APPLICABLE
- POTENTIAL_OPPORTUNITY
- HIGH_VALUE_OPPORTUNITY
- ENGINEERING_REVIEW_REQUIRED
- QUALITY_REVIEW_REQUIRED
- SAFETY_OR_REGULATORY_HOLD
- INSUFFICIENT_DATA
- CONFLICTING_EVIDENCE

## Strategic outcome

The platform should move Hero from:

> 10,000+ raw ideas

to:

> a smaller, higher-quality, evidence-backed set of vehicle cost-reduction opportunities.

For OPEX, move from:

> “Which plant spends more?”

to:

> “Where is the normalized benchmark gap, why does it exist, and what is the realistic opportunity to close it?”
