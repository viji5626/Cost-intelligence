# Hero Cost Intelligence Platform — UI/UX Refinement & Help Architecture

## Executive Summary

The **Hero Cost Intelligence Platform** has undergone a comprehensive UI/UX refinement, information architecture transformation, and integrated user manual deployment. The interface now delivers a mature, enterprise industrial engineering experience tailored for automotive VAVE engineers, plant analytics leads, and corporate cost controllers.

---

## 1. Information Architecture & Navigation Transformation

### 1.1 Collapsible Sidebar Navigation
- **Expanded State (230px)**: Displays grouped industrial navigation categories with section headers, crisp icons, badges, and collapse toggle.
- **Collapsed State (60px)**: Compact icon-only workstation mode with hover tooltips and urgent gate indicators. State is persisted in `localStorage ('hero-sidebar-collapsed')`.
- **Logical Navigation Taxonomy**:
  1. **OVERVIEW**: Executive Dashboard (`overview`)
  2. **OPERATIONS**: Plant OPEX & Benchmark (`opex`), Opportunity Simulator (`opportunity`)
  3. **ENGINEERING INTELLIGENCE**: Vehicle Ideathon 10K+ (`ideathon`), Human Review & Safety Gates (`governance`)
  4. **DATA**: Data Ingestion Studio (`ingestion`)
  5. **SYSTEM**: AI Studio Control Center (`aistudio`), Hardware & Runtime (`hardware`), Security & Audit Log (`audit`)
  6. **HELP & MANUAL**: User Manual & Knowledge Base (`help`)

### 1.2 Compact Global Header
- **Brand Identity**: Hero Red logo badge with active workspace breadcrumb (`Workstation / Executive Overview`).
- **Telemetry HUD**: Compact hardware indicator showing runtime tier (`TIER1_LOW`), active GPU (`RTX 4060 8GB`), and allocated host RAM (`7 GB`).
- **Contextual Help Trigger**: Single-click `Help` button dynamically routing to the relevant chapter of the engineering manual.
- **Air-Gap Indicator**: Persistent `Air-Gap Active` badge validating zero outbound internet egress.
- **Theme Switcher**: Instant toggle between Dark Engineering Workstation and Light Industrial Workstation.

---

## 2. Integrated 25-Chapter User Manual & Knowledge System

A first-class engineering documentation and failure remediation system is integrated directly into the platform via `HelpManualWorkspace.tsx` and `helpManualData.ts`:

### 2.1 The 25 Operational Chapters
| Chapter | Title | Category |
| :--- | :--- | :--- |
| **01** | Getting Started & 10-Step Operational Flow | Core |
| **02** | System Architecture & Air-Gap Compliance | Core |
| **03** | Executive Dashboard & Dual-Domain KPI Interpretation | Core |
| **04** | Plant OPEX & Deterministic Benchmarking | Operations |
| **05** | Utility Accounting: Electricity Sources (Grid, DG, Solar) | Operations |
| **06** | Compressed Air Physical Efficiency & Non-Double-Count Rule | Operations |
| **07** | Water Accounting: Groundwater Tube-Wells vs Municipal PWD | Operations |
| **08** | Thermal Utilities: Piped Natural Gas (PNG Volumetric Baseline) | Operations |
| **09** | Vehicle Ideathon 10,000+ Scalable Search & Filtering | Vehicle Engineering |
| **10** | Idea Normalization & Duplicate Clustering | Vehicle Engineering |
| **11** | Engineering Evidence, PLM BOM Lineage & CAD Citations | Vehicle Engineering |
| **12** | Sibling Model Applicability Matrix (10-Tier Hierarchy) | Vehicle Engineering |
| **13** | Vehicle Cost Opportunity & Deterministic Valuation | Vehicle Engineering |
| **14** | Human-in-the-Loop Governance & Safety Gates | Data Governance |
| **15** | Data Ingestion Studio & Magnitude Guards | Data Governance |
| **16** | Master Data Management & Column Aliasing | Data Governance |
| **17** | AI Studio Industrial Workstation Overview | Local AI System |
| **18** | Model Selection & GGUF Format Validation (AI-02) | Local AI System |
| **19** | Provider Orchestration (Built-in GGUF, Ollama, LM Studio) | Local AI System |
| **20** | Hardware Admission & VRAM Headroom Gating (AI-03) | Local AI System |
| **21** | Runtime Lifecycle & Dynamic Layer Offloading | Local AI System |
| **22** | Vision & Engineering Drawing CAD Parser (AI-15) | Local AI System |
| **23** | Cryptographic Provenance & Audit Ledger (AI-17) | Data Governance |
| **24** | Security, Air-Gap Enforcement & RBAC Roles | Data Governance |
| **25** | Comprehensive Troubleshooting Guide & Engineering Glossary | Reference |

### 2.2 Searchable Engineering Glossary
Contains 28+ defined industrial cost intelligence terms including:
- `Addressable Gap`, `Air-Gap Architecture`, `Applicability Matrix`, `Blended Energy Cost`, `BOM Lineage`, `CAD Drawing Parser`, `Comparability Index`, `Compressed Air Yield`, `Deterministic Valuation`, `ECN`, `GBNF Grammar`, `GGUF Format`, `Grounding Score`, `HNSW Vector Index`, `Human Review Gate (P0-P3)`, `KV Cache`, `Magnitude Guard`, `Non-Double-Count Rule`, `Payback Period`, `Provenance Hash`, `RRF`, `Reranker Cross-Encoder`, `Specific Power`, `Specific Water`, `TTFT`, `VAVE`, and `VRAM Safety Headroom`.

### 2.3 System Failure Remediation Matrix
Interactive troubleshooting guide with **Symptom $\to$ Likely Cause $\to$ Diagnostic Checks $\to$ Recommended Action** for:
1. Backend Connection Error (Port 8000)
2. Ollama Daemon Offline (Port 11434)
3. LM Studio Offline (Port 1234)
4. Hardware Fit Unsafe (VRAM Exceeded)
5. Magnitude Guard Scale Confusion (Lakhs vs Rupees)
6. P0 Safety Gate Approval Blocked
7. Visual Document OCR Low Contrast
8. Zero Evidence Proposal Routing

---

## 3. Workspace-Level Refinements & Clutter Reduction

1. **Executive Dashboard**:
   - 4 primary KPI cards (Pipeline, Net Opportunity, OPEX Gap, Pending Reviews).
   - Domain split cards (Vehicle Cost Intelligence vs Plant OPEX Benchmarking).
   - Collapsible *Methodology, Air-Gap Guarantees & Cryptographic Lineage* disclosure.
   - Direct `Manual Ch. 03` button.

2. **Plant OPEX & Benchmark**:
   - Primary: Target Plant, Benchmark Mode, Production Volume, Specific Power, Specific Water, Compressed Air, Natural Gas, Unit OPEX.
   - Secondary: Source-wise breakdown cards for Electricity (Grid/Solar/DG), Water (Borewell/Municipal), Compressed Air (yield/energy), and Natural Gas (volumetric tariff).
   - Accounting rules and physical formulas clearly separated from primary KPI surfaces.
   - Direct `Manual Ch. 04` button.

3. **Vehicle Ideathon (10K+)**:
   - High-density tabular layout with sticky header, normalized scope sub-rows, and instant "Inspect" action.
   - Direct `Manual Ch. 09` button.

4. **Idea Investigation & Lineage**:
   - Technical decomposition, 10-tier sibling applicability matrix, deterministic valuation math, and ECN document citations.
   - Direct `Manual Ch. 11` button.

5. **Human-in-the-Loop Governance**:
   - Priority indicators for P0 Critical / Safety, P1 High Value, P2 Cross-Model, P3 Routine.
   - Mandatory human gate routing explanations.
   - Direct `Manual Ch. 14` button.

6. **Opportunity Simulator**:
   - Interactive what-if parameter sliders with instant recalculation.
   - Output summary card with gross opportunity, net opportunity, tooling CAPEX, and payback period in months.
   - Direct `Manual Ch. 13` button.

7. **Data Ingestion Studio**:
   - 5-step visual pipeline indicator (`Select` $\to$ `Validate` $\to$ `Magnitude Guard` $\to$ `Preview` $\to$ `Commit`).
   - Direct `Manual Ch. 15` button.

8. **AI Studio Control Center**:
   - Active runtime bar, model browser modal, multi-provider switcher, and grounded inference playground.
   - Direct `Manual Ch. 17` button.

9. **Hardware & AI Runtime**:
   - Telemetry cards for Host RAM, Dedicated VRAM, Runtime Tier, and sequential swapping state.
   - Direct `Manual Ch. 20` button.

10. **Security & Audit Log**:
    - Tamper-evident ledger with Actor User, Action Type, Entity ID, JSON Payload, and SHA-256 Provenance Hash.
    - Direct `Manual Ch. 23` button.

---

## 4. Verification & Validation Summary

### 4.1 Automated Backend & Frontend Tests
- **Backend Test Suite (`pytest`)**: **454 / 454 Passed** (100% pass rate in 48.69s).
- **Frontend Test Suite (`vitest`)**: **20 / 20 Passed** (100% pass rate in 89.36ms).
- **TypeScript & Vite Production Bundle (`npm run build`)**: **Passed** in 1.26s.

### 4.2 Browser Verification (Chrome DevTools MCP)
- **Sidebar Collapse / Expand**: Verified toggle from 230px to 60px with persisted `localStorage` state.
- **Theme Switcher**: Verified dark and light mode transitions with optimal contrast.
- **Contextual Help Routing**: Verified deep-linking from Plant OPEX (`Manual Ch. 04`) directly to Chapter 4 of the manual.
- **Glossary & Troubleshooting Search**: Verified dynamic filtering across all 28 glossary terms and 8 troubleshooting scenarios.
