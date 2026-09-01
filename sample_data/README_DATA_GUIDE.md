# HERO Cost Intelligence — Data Architecture, Ingestion & Operations Guide

This document provides a comprehensive operational breakdown of how data moves through the **HERO Vehicle Cost & Plant OPEX Intelligence Platform**, how mock/demo data was originally loaded, what file formats are supported, where and how to ingest real production data, and how the entire system functions end-to-end.

---

## 1. How Mock / Demo Data Was Loaded

The platform utilizes a multi-layered design for demonstration and testing:

1. **PostgreSQL Database Seeder (`data/seed_demo_data.py`):**
   - Ingests initial baseline records directly into PostgreSQL tables (`plants`, `opex_records`, `product_families`, `vehicles`, `vehicle_models`, `parts`, `component_costs`).
   - Every seeded record is tagged with `source_system = 'SYNTHETIC_DEMO'` and suffixes like `-DEMO` to guarantee zero collision with real production data.
   - Idempotent: Uses `INSERT ... ON CONFLICT DO NOTHING` so it can be re-run safely.

2. **Frontend Fallback States:**
   - Workspaces (`IdeathonWorkspace.tsx`, `OpexWorkspace.tsx`, `ReviewQueueWorkspace.tsx`, `ExecutiveDashboard.tsx`) contain built-in sample fallbacks (e.g. `IDEA-2024-0042` brake lever, ₹142.5 Cr portfolio valuation, Haridwar vs Dharuhera OPEX variance) so that the UI can be explored immediately even before PostgreSQL is connected or populated.

3. **AI Studio Mock / Simulation Adapters (`ai/providers/mock_provider.py`):**
   - Allows testing token streaming, telemetry, and engineering chat playgrounds when local neural weights (`.gguf` / `.safetensors`) have not yet been downloaded.

---

## 2. Sample Data Directory Structure

All sample mock files are organized in the [`sample_data/`](file:///d:/MY%20APPS/hero-cost-intelligence/sample_data) folder:

```
sample_data/
├── README_DATA_GUIDE.md                  # This master operational guide
├── plant_opex/                           # Manufacturing Plant OPEX Time-Series
│   ├── plant_opex_haridwar_fy2024.csv    # Monthly Haridwar energy, gas, water, labor, OPEX
│   ├── plant_opex_dharuhera_fy2024.csv   # Monthly Dharuhera benchmark records
│   └── plant_opex_neemrana_fy2024.csv    # Monthly Neemrana greenfield records
├── vehicle_ideathon/                     # Employee Cost Reduction Proposals
│   └── ideathon_raw_submissions_batch_1.csv  # 10K+ batch sample (ideas, part numbers, savings)
├── vehicle_bom/                          # PLM Engineering Bill of Materials
│   └── vehicle_bom_splendor_plus_2024.csv    # Canonical BOM parts linked to Model Year
├── component_costs/                      # Purchasing & Cost Engineering Piece Master
│   └── component_cost_master_q4.csv      # Raw material, process, tooling, and total piece cost
└── engineering_changes/                  # ECN / ECO Grounding Evidence
    └── engineering_change_notices_2024.csv   # Released engineering change records & supersessions
```

---

## 3. Supported File Formats

| File Type | Extension | Purpose in Platform | Engine / Service Handler |
|---|---|---|---|
| **Spreadsheets (CSV)** | `.csv` | Plant OPEX logs, Ideathon proposals, BOMs, Component Costs, ECNs | `IngestionParser.parse_csv_stream` |
| **Spreadsheets (Excel)** | `.xlsx`, `.xls` | Multi-tab plant sheets, supplier cost breakdowns | `IngestionParser.parse_excel_stream` (`openpyxl`) |
| **Structured Metadata** | `.json`, `.jsonl` | REST API ingestion, system audit trails, model registries | `FastAPI`, `Pydantic v2` |
| **Engineering CAD & Drawings** | `.pdf`, `.png`, `.jpg`, `.dwg` | Visual document inspection, title block OCR, drawing dimension diffs | `ai.vision.ocr_engine` (`Tesseract` / `EasyOCR`) |
| **Local Neural SLM Weights** | `.gguf`, `.safetensors` | Air-gapped local AI inference, embeddings, and rerankers | `LlamaEngine` (CUDA) / HuggingFace Safetensors |

---

## 4. Where and How to Ingest Data (3 Methods)

### Method A: Web UI — Data Ingestion Studio (Recommended for Business Users)
1. Open the platform in your browser (`http://localhost:5173`).
2. Click **"Data Ingestion Studio"** in the left navigation sidebar.
3. Select your target domain:
   - **Plant OPEX Time-Series**
   - **Vehicle Ideathon Submissions**
   - **Vehicle BOM**
   - **Component Cost Master**
   - **Engineering Changes (ECN)**
4. Click the upload dropzone and choose any `.csv` or `.xlsx` file (e.g. from `sample_data/`).
5. The system performs a **Dry Run**:
   - Matches column headers using the built-in Intelligent Alias Dictionary.
   - Executes the **Magnitude Anomaly Guard** (checks for scale errors like Lakhs vs Rupees).
   - Shows total valid rows vs rejected rows.
6. Click **"Commit Ingestion to Database"** to write transactionally to PostgreSQL with a cryptographic SHA-256 audit log entry.

### Method B: Automated REST API (Recommended for IT & Automated ETL Pipelines)
You can POST files programmatically from internal ERP/PLM/SCADA pipelines:

```bash
# Upload Haridwar Plant OPEX CSV
curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "target=PLANT_OPEX" \
  -F "dry_run=false" \
  -F "allow_unusual_data=true" \
  -F "file=@sample_data/plant_opex/plant_opex_haridwar_fy2024.csv"
```

### Method C: Database Seeder / Python Scripts (Recommended for System Admins)
You can run automated database seeding or custom ingestion scripts:

```powershell
.\.venv\Scripts\python data\seed_demo_data.py
```

---

## 5. Column Specifications & Smart Header Aliasing

You do **not** need to rename existing plant/ERP headers manually. The ingestion engine recognizes dozens of real-world enterprise column aliases automatically:

### 1. Plant OPEX (`PLANT_OPEX`)
- **Plant Identifier:** `plant_code`, `plant_id`, `plant`, `unit`, `facility_code`, `factory`
- **Period / Month:** `period`, `month`, `date`, `month_year`, `financial_period` (Format: `YYYY-MM-DD` or `YYYY-MM`)
- **Production Volume:** `production_quantity`, `prod_qty`, `volume`, `vehicles_produced`, `units`
- **Electricity (Total):** `electricity_kwh`, `power_kwh`, `kwh`, `electricity_units`, `units_consumed`
- **Electricity Cost:** `electricity_cost`, `power_cost`, `electricity_inr`, `power_expense`
- **Source Breakdown (Optional):** `grid_kwh`, `grid_cost_inr`, `dg_kwh`, `dg_cost_inr`, `solar_kwh`, `solar_cost_inr`
- **Water Consumption & Cost:** `water_kl`, `water_cost`, `borewell_kl`, `pwd_kl`
- **Compressed Air:** `compressed_air_nm3`, `compressed_air_cost`, `compressed_air_cf_total`, `compressor_kwh_total`
- **Gas / Fuel:** `gas_consumption_nm3`, `gas_cost`, `gas_source_type` (PNG, LPG)
- **O&M Costs:** `labor_cost`, `maintenance_cost`, `waste_quantity_mt`, `waste_cost`, `other_opex`, `total_opex`

### 2. Vehicle Ideathon Submissions (`IDEATHON_RAW`)
- **Idea Code / ID:** `idea_id`, `idea_no`, `submission_id`, `sr_no`
- **Originating Plant:** `submitter_plant`, `plant`, `location`
- **Idea Title:** `original_title`, `title`, `idea_title`, `concept`
- **Description / Solution:** `original_description`, `description`, `problem_solution`, `details`
- **Target Model:** `target_model_name`, `model`, `vehicle`, `applicable_model` (e.g. `SPLENDOR_PLUS`)
- **Target Part:** `target_part_name`, `part`, `component`, `part_name`, `assembly`
- **Part Number:** `target_part_number`, `part_number`, `drawing_no` (e.g. `53100-KTR-900`)
- **Claimed Saving (₹/veh):** `claimed_saving_per_veh`, `cost_saving`, `saving_rs`, `expected_benefit`

### 3. Vehicle Engineering BOM (`VEHICLE_BOM`)
- **Model Year:** `model_year_code`, `model_year`, `my_code`, `year_code` (e.g. `SPL_2024_DEMO`)
- **Part Number:** `part_number`, `part_no`, `material_number`
- **Qty Per Vehicle:** `quantity_per_vehicle`, `qty`, `usage_qty` (e.g. `1.0`, `2.0`)
- **Validity Dates:** `effective_from`, `effective_to`

### 4. Component Cost Master (`COMPONENT_COST`)
- **Part Number:** `part_number`, `part_no`, `item_code`
- **Plant Code:** `plant_code`, `plant`
- **Period Start:** `period_start`, `valid_from`
- **Cost Breakdown:** `raw_material_cost`, `process_cost`, `overhead_cost`, `tool_amortization`, `total_cost`

### 5. Engineering Changes (`ENGINEERING_CHANGE`)
- **ECN / ECO ID:** `ecn_number`, `ecn_no`, `cr_number`
- **Subject / Title:** `title`, `change_title`, `description_summary`
- **Category:** `change_category`, `category`, `type_of_change` (VAVE, PROCESS, STANDARDIZATION)
- **Part Traceability:** `affected_part_number`, `replaced_by_part_number`
- **Verified Saving (₹/veh):** `estimated_saving_per_veh`, `saving_per_veh`, `cost_benefit_inr`

---

## 6. Magnitude Anomaly Guard (Data Quality Assurance)

Factory spreadsheets often contain manual scale errors (e.g. entering ₹ in Lakhs instead of absolute Rupees, or entering total kWh instead of per-vehicle numbers).

The **Magnitude Anomaly Guard** (`backend/app/services/ingestion/magnitude_guard.py`) automatically evaluates incoming data against domain physics:
- **Electricity Tariff Sanity:** Flagged if effective unit rate (`electricity_cost / electricity_kwh`) is outside ₹4.00 – ₹18.00 / kWh.
- **Specific Energy per Vehicle:** Flagged if specific power is outside 20 kWh – 80 kWh per vehicle.
- **Water Consumption per Vehicle:** Flagged if water per vehicle is outside 0.15 KL – 0.80 KL.
- **Component Unit Cost:** Flagged if piece cost is negative or exceeds ₹25,000 for standard parts.
- **Savings vs Part Cost:** If an employee claims ₹50 savings on a part that only costs ₹20, the system flags a severe scale anomaly for human review.

---

## 7. How the Complete Software Operates (End-to-End Workflow)

```
[ Plant SCADA / ERP / PLM / Ideathon Submissions ]
                       │
                       ▼
         [ 1. Ingestion & Normalization ]
         • Automated Column Alias Mapping
         • Unit Normalization (Lakhs ➔ INR, CF ➔ Nm³, MWh ➔ kWh)
         • Magnitude Anomaly Guard Validation
         • SHA-256 Batch Cryptographic Hashing
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
[ 2. Plant OPEX Engine ]     [ 3. Vehicle Ideathon Engine ]
• Normalizes Specific Costs  • NLP Decomposes Problem vs Solution
  (₹/veh, kWh/veh, KL/veh)   • Regex & Semantic Part Number Extraction
• Distinguishes Structural   • Embedding Similarity (BGE-Large / Qwen)
  vs Addressable Inefficiency• Near-Duplicate Submission Clustering
• Haridwar vs Dharuhera Gap  • Maps to PLM Vehicle BOM Hierarchy
        │                             │
        └──────────────┬──────────────┘
                       ▼
         [ 4. Opportunity Valuation Engine ]
         • Multiplies ₹/veh Saving by Planned Model Volumes
         • Aggregates Net Addressable Opportunity (₹ Cr)
                       │
                       ▼
         [ 5. Grounding & Safety Gate ]
         • ECN & CAD Document Matching (OCR + Vector Search)
         • Safety-Critical Part Detection (Brakes/Steering)
         • Automatic Escalation to Human Review Queue (P0 Gate)
                       │
                       ▼
         [ 6. Air-Gapped AI Studio Workspace ]
         • Local SLM Inference (CUDA / Ollama / LM Studio)
         • Live Token Generation Telemetry (tok/s, TTFT)
         • GBNF Constrained JSON Outputs for Cost Rationale
                       │
                       ▼
         [ 7. Executive Dashboard & Audit Log ]
         • Single-Pane-of-Glass Portfolio Valuation
         • Immutable Decision Ledger with Hash Verification
```

---

## 8. Transitioning from Demo Mode to Real Production Data

When you are ready to remove mock data and run live on factory data:

1. **Flush Demo Records in PostgreSQL:**
   ```sql
   DELETE FROM opex_records WHERE plant_id LIKE '%demo%';
   DELETE FROM component_costs WHERE source_system = 'SYNTHETIC_DEMO';
   DELETE FROM idea_submissions WHERE id LIKE '%syn%' OR submission_code LIKE '%DEMO%';
   DELETE FROM plants WHERE plant_code LIKE '%DEMO%';
   ```
2. **Ingest Real Master Data:**
   - Drop your plant master and monthly spreadsheets via **Data Ingestion Studio**.
   - Drop your PLM BOM exports and purchasing component cost sheets.
   - Drop historical ECN notices for automated grounding.
   - Drop raw employee ideathon spreadsheets.
3. **Load AI Studio Models:**
   - Scan your local model directory (`C:\Users\<user>\.lmstudio\models` or `D:\Models\GGUF`) to offload SLM neural weights into your dedicated GPU VRAM.
4. **Enjoy 100% Air-Gapped, Deterministic Cost Intelligence!**
