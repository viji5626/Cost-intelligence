# 03 — Data Model, Ingestion & Plant OPEX Benchmarking

## Core relational entities

Recommended initial entities:

PLANT
PRODUCT_FAMILY
VEHICLE
VEHICLE_MODEL
VEHICLE_VARIANT
MODEL_GENERATION
MODEL_YEAR

SUBSYSTEM
ASSEMBLY
COMPONENT
PART
MATERIAL
SUPPLIER

IDEA
IDEA_CLUSTER
IDEA_EVALUATION

PROJECT
ENGINEERING_CHANGE
IMPLEMENTATION

BOM_RECORD
COMPONENT_COST
PRODUCTION_RECORD

OPEX_RECORD
BENCHMARK_RECORD

DOCUMENT
DOCUMENT_CHUNK
EVIDENCE
AUDIT_LOG

## Vehicle hierarchy

```text
Product Family
  -> Vehicle Type
      -> Model
          -> Variant
              -> Generation
                  -> Model Year
                      -> Subsystem
                          -> Assembly
                              -> Component
                                  -> Part
                                      -> Material
                                          -> Supplier
```

## Idea entity

Store both original and normalized content.

Suggested fields:

- idea_id
- source_id
- original_text
- normalized_title
- normalized_description
- idea_category
- cost_reduction_type
- product_family_id
- vehicle_id
- model_id
- variant_id
- generation_id
- model_year
- subsystem_id
- assembly_id
- component_id
- part_id
- problem_statement
- proposed_solution
- expected_cost_benefit
- expected_weight_benefit
- quality_impact
- safety_impact
- reliability_impact
- BOM/non-BOM classification
- status
- timestamps

## Data ingestion

Support:

- Excel
- CSV
- PDF
- Word
- scanned documents
- images / handwritten notes

Pipeline:

```text
Input
  -> Temporary staging
  -> Schema detection
  -> Mapping
  -> Validation
  -> Unit normalization
  -> Business validation
  -> Normalization
  -> SQL insertion
  -> Vector indexing if needed
  -> Verification
  -> Temporary source deletion
```

Only delete a source file after successful processing and verification.

Retain audit metadata such as ingestion ID, source identifier, timestamp, row count and validation status.

## Data quality

Check:

- required fields
- datatypes
- dates
- units
- duplicate rows
- model references
- vehicle references
- cost validity
- outliers
- missing values
- inconsistent mappings

Do not silently mutate critical customer data.

## Unit normalization

Maintain canonical units for:

- kWh
- KL
- Nm3
- kg
- ₹/vehicle
- ₹/component
- ₹/year

Use deterministic conversion tables.

## Plant OPEX model

Suggested OPEX record fields:

- plant_id
- period
- production_quantity
- electricity_kwh
- electricity_cost
- water_kl
- water_cost
- gas_consumption
- gas_cost
- compressed_air
- compressed_air_cost
- waste_quantity
- waste_cost
- labor_cost
- maintenance_cost
- other_opex
- total_opex

Derived KPIs:

- kWh/vehicle
- KL/vehicle
- ₹ electricity/vehicle
- ₹ water/vehicle
- ₹ gas/vehicle
- ₹ compressed air/vehicle
- maintenance/vehicle
- manpower/vehicle
- total OPEX/vehicle

## Benchmarking logic

Support:

1. Best comparable plant benchmark.
2. Peer benchmark.
3. Historical benchmark.
4. Management target benchmark.

Do not define “best” solely as the lowest absolute expenditure.

Consider where relevant:

- production volume
- product/vehicle mix
- operating days
- shifts
- capacity utilization
- tariff
- plant age/conditions or other justified comparability factors

## Benchmark workflow

```text
Plant Data
   -> Normalize
   -> Calculate KPI
   -> Select comparable peers
   -> Benchmark
   -> Variance
   -> Driver decomposition
   -> Potential opportunity
```

## Example

Illustrative only:

Plant A = ₹1,450/vehicle
Benchmark = ₹1,200/vehicle
Gap = ₹250/vehicle
Annual production = 500,000
Opportunity = ₹12.5 Cr/year

Do not hardcode these values.

## AI role in OPEX

The calculation engine computes:

- actuals
- benchmark
- variance
- trend
- opportunity

The SLM may explain:

- likely drivers
- anomalies
- historical changes
- comparative insights

The SLM must not be the calculator.

## Additional benchmarking

The Ideathon engine may benchmark a new cost opportunity against historical similar implemented opportunities.

Example concept:

Historical comparable saving range -> new idea estimate -> relative opportunity ranking.

Use real Hero data in POC; never invent values.
