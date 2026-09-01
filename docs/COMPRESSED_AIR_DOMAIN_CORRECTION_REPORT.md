# Critical OPEX Domain Correction Report: Compressed Air Utility & Double-Counting Safeguards

**Authoritative Baseline:** `docs/implementation-plan/09_REVISED_IMPLEMENTATION_PLAN_V3_1_1.md`  
**Execution Standard:** `docs/context/10_ANTIGRAVITY_EXECUTION_RULES.md`  
**Verification Level:** `LIVE BROWSER VERIFIED` | `AUTOMATED TEST VERIFIED (132/132 Backend, 9/9 Frontend)`  
**Status:** COMPLETED & VERIFIED (DO NOT START PHASE 10 — AWAITING MANUAL REVIEW)

---

## 1. Summary of Changes

Compressed Air is a critical plant-benchmarking utility in automotive and two-wheeler manufacturing plants. It has now been implemented across the **complete end-to-end data path**: Database Schema $\rightarrow$ Deterministic Calculation Models $\rightarrow$ Ingestion Stream Parsers $\rightarrow$ Service Layer $\rightarrow$ Multi-Plant Benchmarking Engine $\rightarrow$ REST API Schemas $\rightarrow$ Front-End UX/UI.

---

## 2. Detailed Breakdown by Architectural Layer

### 1. Database Schema (`database/models/plant_opex.py`)
- **`OpexRecord` Table**: Added nullable, Decimal-precision columns:
  - `compressed_air_cf_total`: `Numeric(16, 4)` (Total compressed-air cubic feet generated/consumed).
  - `compressor_kwh_total`: `Numeric(16, 4)` (Total compressor electrical energy consumed).
  - `compressed_air_cost_allocated`: `Numeric(16, 4)` (Separately allocated cost if separately billed/contracted).
  - `is_compressor_power_embedded`: `Boolean` (Default `True`, enforcing strict double-counting prevention).
- **`BenchmarkRecord` Table**: Added benchmarkable utility targets:
  - `compressed_air_cf_per_vehicle`: `Numeric(14, 4)`.
  - `compressor_kwh_per_cf`: `Numeric(14, 6)` (Specific energy efficiency).
  - `compressor_cf_per_kwh`: `Numeric(14, 4)` (Air generation yield).

### 2. Deterministic Calculation Engine (`calculations/opex/engine.py` & `models.py`)
- **Pure Decimal Mathematical Derivations**:
  1. $\text{Specific Demand (CF / veh)} = \frac{\text{Total Compressed Air CF}}{\text{Production Volume}}$
  2. $\text{Specific Energy (kWh / CF)} = \frac{\text{Compressor Electricity kWh}}{\text{Compressed Air CF}}$
  3. $\text{Air Yield (CF / kWh)} = \frac{\text{Compressed Air CF}}{\text{Compressor Electricity kWh}}$
  4. $\text{Allocated Unit Cost (₹ / veh)} = \frac{\text{Allocated Compressed Air Cost}}{\text{Production Volume}}$
- **Zero Hallucination / Zero Hardcoding**:
  - No physical conversion factors are hardcoded (actual physical measurements determine efficiency).
  - Missing compressor energy or volume returns an explicit `None` (missing data state) rather than fabricating values.
  - Zero division protection guards against `production_quantity = 0` or `compressed_air_cf_total = 0`.

### 3. Double-Counting Protection Architecture
- **Problem**: In manufacturing plants, shopfloor compressors are powered via the main factory electrical substation. Adding compressor electricity cost on top of total plant OPEX would double-count electricity already billed under grid power.
- **Enforcement**:
  - `is_compressor_power_embedded = True` (Default): Compressor electrical energy is tracked as a physical utility efficiency dimension (`kWh/CF`, `CF/kWh`) and its financial cost remains embedded in total plant electricity OPEX (`₹28.00/veh`).
  - Total OPEX summation strictly checks `is_compressor_power_embedded` to avoid duplicate billing lines.

### 4. Data Ingestion & Alias Normalization (`backend/app/services/ingestion/`)
- Extended `COLUMN_ALIASES[IngestionTarget.PLANT_OPEX]` in `models.py` and `parser.py` to handle customer column variations:
  - `compressed_air_cf_total`: `["compressed_air_cf_total", "compressed_air", "compressed_air_consumption", "compressed_air_volume", "compressed_air_cf", "air_consumption_cf", "air_volume_cf", "compressed_air_nm3", "air_nm3", "total_air_cf", "air_cf"]`
  - `compressor_kwh_total`: `["compressor_kwh_total", "compressor_energy", "compressor_kwh", "compressed_air_kwh", "compressor_power_kwh", "air_compressor_kwh", "compressor_electricity_kwh"]`
  - `compressed_air_cost_inr`: `["compressed_air_cost_inr", "compressed_air_cost", "air_cost", "air_inr", "compressed_air_rs", "compressor_cost"]`
  - `compressed_air_cf_per_vehicle`: `["compressed_air_cf_per_vehicle", "cf_per_vehicle", "cf_per_veh", "air_cf_per_vehicle"]`
  - `compressor_kwh_per_cf`: `["compressor_kwh_per_cf", "kwh_per_cf", "kwh_cf"]`
  - `compressor_cf_per_kwh`: `["compressor_cf_per_kwh", "cf_per_kwh", "cf_kwh"]`

### 5. Multi-Plant Benchmarking Methodology (`calculations/opex/benchmark_methodology.py`)
- Propagates candidate peer's compressed air metrics (`benchmark_compressed_air_cf_per_vehicle`, `benchmark_compressor_kwh_per_cf`, `benchmark_compressor_cf_per_kwh`) into `BenchmarkOpportunityResult`.
- Enables side-by-side shopfloor efficiency comparison without distorting total OPEX variance decomposition.

### 6. Front-End User Experience (`frontend/src/`)
- **TypeScript Interfaces (`types/index.ts`)**: Added compressed air fields to `PlantKPIs` and `BenchmarkComparisonResult`.
- **Plant OPEX Workspace (`components/opex/OpexWorkspace.tsx`)**:
  - Added dedicated **Compressed Air Utility & Compressor Efficiency** section.
  - Displays:
    - *Specific Consumption*: `3.45 CF/veh` (Target: `2.90 CF/veh`).
    - *Specific Energy*: `0.0215 kWh/CF` (Target: `0.0195`).
    - *Air Yield*: `46.5 CF/kWh` (Target: `51.3`).
    - *Unit Cost Allocation*: `₹15.20 / veh` or `Embedded in Grid Power`.
  - Explanatory banner highlighting double-counting safeguards.
  - Zero decorative emojis, pure Lucide icons (`Gauge`, `Info`), tabular numerals.

---

## 3. Verification & Test Evidence

### 1. Dedicated Unit Test Suite (`tests/unit/test_compressed_air_opex.py`)
All 12 specific validation criteria passed:
1. `test_1_cf_per_vehicle_calculation`: Passed.
2. `test_2_kwh_per_cf_calculation`: Passed.
3. `test_3_cf_per_kwh_calculation`: Passed.
4. `test_4_zero_production_handling`: Passed.
5. `test_5_zero_compressed_air_volume`: Passed.
6. `test_6_missing_compressor_kwh`: Passed.
7. `test_7_missing_compressed_air_cf`: Passed.
8. `test_8_double_counting_protection`: Passed.
9. `test_9_ingestion_aliases`: Passed.
10. `test_10_api_serialization`: Passed.
11. `test_11_benchmark_comparison`: Passed.
12. `test_12_decimal_precision_rounding`: Passed.

### 2. Full Regression Execution Results
- **Backend Test Suite (`pytest tests/`)**: **132 passed out of 132 tests in 11.37s** (0 failures, 0 regressions).
- **Frontend Test Suite (`npm test`)**: **9 passed out of 9 tests in 80ms** across 6 suites.
- **Frontend Production Build (`npm run build`)**: Compiled cleanly in **1.11s** (0 TypeScript errors).
- **Live Chrome DevTools MCP Browser Inspection**: Verified live snapshot on `http://127.0.0.1:5173/` showing all 4 compressed-air metric cards, double-counting notice, and benchmark comparisons.

---

## 4. Remaining Data Limitations & Plant Accounting Boundary

1. **Sub-Metering Availability**: In plants without dedicated sub-meters on compressor house switchgears, `compressor_kwh_total` will be unavailable and will display `N/A (No Sub-meter)` while still reporting total shopfloor air demand (`CF/veh`).
2. **Pressure Standardization**: Cubic feet (CF) are assumed to be at standard plant distribution pressure (typically 6.5 to 7.0 bar gauge). If mass flow or Normalised Cubic Metres ($\text{Nm}^3$) are ingested, existing unit conversion normalization applies.
