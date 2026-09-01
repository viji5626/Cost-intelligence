# Phase 9 OPEX Utility Model Correction Report
**Authoritative Baseline**: `docs/implementation-plan/09_REVISED_IMPLEMENTATION_PLAN_V3_1_1.md`  
**Standard**: `docs/context/10_ANTIGRAVITY_EXECUTION_RULES.md`  
**Decision Gate**: `GATE-09: Plant OPEX Source-Wise Utility Correction Verified`  
**Status**: `COMPLETED & VALIDATED`

---

## 1. Executive Summary & Objective

Prior to Phase 10, a targeted architectural enhancement was executed across the full data path (**DATA → INGESTION → DATABASE → DETERMINISTIC CALCULATION → BENCHMARKING → API → FRONTEND**) to represent major plant utilities with source-wise provenance and strict financial accounting double-counting safeguards.

The 4 major plant utility domains implemented:
1. **Electricity & Energy**: Grid (Purchased), Captive Solar, Diesel Generator (DG), Other Captive Generation.
2. **Water Extraction & Municipal Supply**: Borewell / Groundwater, PWD / Municipal Supply, Recycled / Other.
3. **Compressed Air & Generation Efficiency**: Total Demand (CF), Specific Demand (CF/veh), Compressor Electricity (kWh), Specific Energy (kWh/CF), Air Yield (CF/kWh), Embedded Power Accounting.
4. **Natural Gas / Process Fuel**: Process Gas (CF & Nm³), Specific Gas (CF/veh & Nm³/veh), Volumetric Tariff (₹/CF), Source Classification (PNG/LPG).

---

## 2. Architecture & File Modifications

| Architectural Layer | File Path | Enhancements |
|---|---|---|
| **Database Schema** | `database/models/plant_opex.py` | Added columns to `OpexRecord` for source-wise Electricity (`grid_kwh`, `grid_cost_inr`, `dg_kwh`, `dg_cost_inr`, `solar_kwh`, `solar_cost_inr`, `other_generated_kwh`), Water (`borewell_kl`, `borewell_cost_inr`, `pwd_kl`, `pwd_cost_inr`, `other_water_kl`), Compressed Air (`compressed_air_cf_total`, `compressor_kwh_total`), Gas (`gas_cf_total`, `gas_source_type`). Added utility benchmark targets to `BenchmarkRecord`. |
| **Pydantic Domain Models** | `calculations/opex/models.py` | Implemented `ElectricitySourceBreakdown`, `WaterSourceBreakdown`, `CompressedAirBreakdown`, `GasFuelBreakdown`, `AccountingCostClassification`, `DataAvailabilityState`. |
| **Deterministic Engine** | `calculations/opex/engine.py` | Implemented pure Decimal arithmetic methods: `calculate_electricity_source_breakdown`, `calculate_water_source_breakdown`, `calculate_compressed_air_breakdown`, `calculate_gas_fuel_breakdown`. Enforced half-up rounding and zero double-counting. |
| **Benchmarking Methodology** | `calculations/opex/benchmark_methodology.py` | Propagated source-level utility snapshots into `BenchmarkOpportunityResult`. Evaluated 5-factor comparability and variance decomposition. |
| **Ingestion Models & Parser** | `backend/app/services/ingestion/models.py`<br>`backend/app/services/ingestion/parser.py`<br>`backend/app/services/ingestion/ingestion_service.py` | Expanded `COLUMN_ALIASES` for all source utility variants. Parsed and normalized source metrics. Persisted all columns to `OpexRecord`. |
| **API & Service Layer** | `backend/app/services/opex/opex_service.py` | Loaded source-wise utility data and passed through to `PlantKpiMetrics` and `BenchmarkOpportunityResult`. |
| **Frontend Types & UI** | `frontend/src/types/index.ts`<br>`frontend/src/styles/index.css`<br>`frontend/src/components/opex/OpexWorkspace.tsx` | Expanded top KPI row to 6 responsive cards (`.grid-6`). Added 4 dedicated source-wise analytical utility containers with double-counting safeguards. |

---

## 3. Double-Counting Safeguard & Accounting Integrity

To prevent inflation of plant OPEX:
1. **Compressor Electricity**: Embedded within total plant electricity bills; tracked as physical efficiency metric without creating duplicate cost line items.
2. **Captive Solar & DG**: Usable energy is aggregated as $\text{Total Usable Energy} = \text{Purchased Grid} + \text{Captive Generation}$ without duplicate billing.
3. **Groundwater Extraction**: Where extraction is zero-cost, costs are preserved as `None` / `Unmetered` rather than fabricating artificial zeroes.

---

## 4. Test Suite & Validation Results

### Backend Automated Test Suite:
- **30/30** dedicated unit tests passed in `tests/unit/test_source_wise_opex.py`.
- **162/162** total project backend tests passed (`pytest`).

```text
============================ 162 passed in 13.70s =============================
```

### Frontend Automated Test Suite & Build:
- **9/9** frontend test suites passed (`node --test`).
- **Production bundle build successful** (`tsc && vite build` in 1.99s).

---

## 5. Live Browser Verification

Verified on Windows workstation via Chrome DevTools MCP:
- **Top 6 KPI Cards**:
  1. Production Volume: `24.0 L units`
  2. Specific Power: `42.5 kWh/veh`
  3. Specific Water: `0.35 KL/veh`
  4. Compressed Air: `3.45 CF/veh`
  5. Natural Gas / Fuel: `42.4 CF/veh`
  6. Unit Plant OPEX: `₹595.00 / veh` (`Total: ₹142.8 Cr`)
- **4 Dedicated Analytical Containers**:
  - `A. Electricity & Energy (Grid: 90.0 MU, Solar: 8.0 MU, DG: 4.0 MU, Blended: ₹7.56/kWh)`
  - `B. Water Extraction & Supply (Borewell: 600k KL, PWD: 240k KL, Total: 840k KL, Unit: ₹8.75/veh)`
  - `C. Compressed Air Utility & Compressor Efficiency (3.45 CF/veh, 0.0215 kWh/CF, 46.5 CF/kWh, ₹15.20/veh embedded)`
  - `D. Natural Gas / Fuel (42.4 CF/veh, 101.7M CF, ₹50.00/veh, Volumetric Tariff: ₹1.18/CF, PNG)`
- **Comparability Breakdown (5 Dimensions)**: Scope (35%), Volume (25%), Shifts (15%), Capacity (15%), Tariff (10%).

---

## 6. Strict Stop Protocol

Work for Phase 9 OPEX Utility Model Correction is complete and verified.  
**STOPPED for User Review. Phase 10 has NOT been started.**
