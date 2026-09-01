/**
 * Comprehensive Industrial Engineering User Manual & Knowledge Base
 * Hero Cost Intelligence Platform — Air-Gapped Workstation Manual
 * Formatted for plant analytics engineers, vehicle cost engineers, and VAVE teams.
 */

export interface HelpChapter {
  id: string;
  chapterNumber: number;
  title: string;
  category: 'CORE' | 'OPERATIONS' | 'VEHICLE_ENGINEERING' | 'DATA_GOVERNANCE' | 'AI_SYSTEM' | 'REFERENCE';
  summary: string;
  whatItIs: string;
  whyItMatters: string;
  howToUse: string[];
  pipeline?: {
    inputs: string[];
    process: string[];
    outputs: string[];
  };
  interpretationRules: string[];
  commonMistakes: string[];
  troubleshootingAction: string;
}

export interface GlossaryTerm {
  term: string;
  category: string;
  definition: string;
  exampleOrContext: string;
}

export interface TroubleshootingEntry {
  id: string;
  symptom: string;
  likelyCause: string;
  check: string[];
  action: string;
  workspaceId: string;
}

export const HELP_CHAPTERS: HelpChapter[] = [
  {
    id: 'getting-started',
    chapterNumber: 1,
    title: 'Getting Started & 10-Step Operational Flow',
    category: 'CORE',
    summary: 'Standard operating procedure for new cost engineers and plant managers navigating the platform.',
    whatItIs: 'A sequential operational workflow guiding users from system readiness check to final opportunity sign-off.',
    whyItMatters: 'Ensures consistent, auditable analysis without skipping safety reviews, baseline validations, or provenance verification.',
    howToUse: [
      'Step 1: Check System Baseline in the top bar to verify Air-Gap integrity and local GPU/VRAM hardware health.',
      'Step 2: Navigate to Plant OPEX to review target manufacturing plant utility metrics against peer group benchmarks.',
      'Step 3: Identify addressable cost drivers in Electricity, Water, Compressed Air, or Natural Gas.',
      'Step 4: Switch to Vehicle Ideathon (10K+) to explore component cost reduction proposals.',
      'Step 5: Apply filters for Target Model, Part Number, and Evidence State to locate high-impact ideas.',
      'Step 6: Open Idea Detail View to verify engineering decomposition, CAD drawing extractions, and PLM BOM lineage.',
      'Step 7: Check the Sibling Model Applicability Matrix to evaluate portfolio-wide volume scaling.',
      'Step 8: Run the Opportunity Simulator to calculate deterministic gross savings, CAPEX tooling amortization, and net opportunity.',
      'Step 9: For safety-critical parts (brakes, steering, suspension, frame), route to Human Review Queue.',
      'Step 10: Inspect the Security & Audit Log to verify SHA-256 cryptographic provenance of all decisions.',
    ],
    interpretationRules: [
      'Air-gap status must display "Air-Gap Active" indicating zero outbound internet telemetry.',
      'Financial numbers are strictly computed via Python Decimal arithmetic with zero AI arithmetic hallucinations.',
    ],
    commonMistakes: [
      'Assuming AI confidence score equals business truth without verifying canonical PLM documents.',
      'Bypassing the Human Review Queue for safety-critical components (P0).',
    ],
    troubleshootingAction: 'If any workspace fails to load, verify local backend server on port 8000.',
  },
  {
    id: 'system-overview',
    chapterNumber: 2,
    title: 'System Architecture & Air-Gap Compliance',
    category: 'CORE',
    summary: 'Comprehensive guide to the 3-tier local architecture and strict air-gapped security model.',
    whatItIs: 'The platform architecture consists of a React Web Workstation, a FastAPI platform controller, and the AI-12 Central Local AI Orchestrator.',
    whyItMatters: 'Protects proprietary Hero MotoCorp vehicle CAD designs, supplier BOM prices, and plant utility tariffs from cloud exposure.',
    howToUse: [
      'Inspect the top banner for current runtime tier (e.g. TIER1_LOW, RTX 4060 8GB).',
      'Verify that all AI model inference runs on local GGUF quantizations or local sidecars (Ollama/LM Studio).',
      'Check that external network requests are blocked by local socket egress filtering.',
    ],
    interpretationRules: [
      'Air-gap compliance is absolute: no cloud API keys, external CDNs, or remote telemetry servers are used.',
    ],
    commonMistakes: [
      'Attempting to configure cloud API endpoints (e.g. OpenAI cloud, Anthropic API) which are blocked by platform policy.',
    ],
    troubleshootingAction: 'Review Security & Audit Log for any blocked egress attempts.',
  },
  {
    id: 'executive-dashboard',
    chapterNumber: 3,
    title: 'Executive Dashboard & Dual-Domain KPI Interpretation',
    category: 'CORE',
    summary: 'How to interpret portfolio-level vehicle ideathon valuations and plant OPEX benchmark gaps.',
    whatItIs: 'An executive synthesis bridging plant-level utility efficiencies with vehicle-level component cost savings.',
    whyItMatters: 'Provides senior engineering leadership with a single unified view of addressable enterprise cost opportunities.',
    howToUse: [
      'Examine the Net Addressable Opportunity card to gauge total portfolio value across 10K+ ideas.',
      'Review Plant OPEX Addressable Gap to locate cross-plant benchmark variances.',
      'Inspect Pending Human Reviews count to prioritize safety-critical P0 gate decisions.',
      'Click on any summary card to navigate directly to its underlying detailed engineering workspace.',
    ],
    pipeline: {
      inputs: ['Raw Ideathon CSV submissions', 'Plant Utility Metering Logs', 'PLM BOM masters'],
      process: ['Magnitude Guard Validation', '5-Factor Comparability Scoring', 'Deterministic Decimal Valuation'],
      outputs: ['Net Addressable Portfolio Valuation', 'Plant Addressable Gap', 'P0-P3 Review Queue'],
    },
    interpretationRules: [
      'Addressable Gap excludes structural non-controllable factors such as regional climatic heating or fixed municipal tax rates.',
      'Ideathon pipeline numbers distinguish Confirmed, Partially Confirmed, and Unconfirmed proposals.',
    ],
    commonMistakes: [
      'Confusing gross savings with net opportunity (net opportunity deducts tooling and validation CAPEX).',
    ],
    troubleshootingAction: 'Click "Recalculate" in the Opportunity Simulator if financial parameters were recently updated.',
  },
  {
    id: 'plant-opex',
    chapterNumber: 4,
    title: 'Plant OPEX & Deterministic Benchmarking',
    category: 'OPERATIONS',
    summary: 'Methodology for decomposing plant electricity, water, compressed air, and gas costs into controllable vs structural variances.',
    whatItIs: 'A production-normalized analytics engine that compares manufacturing plants across identical manufacturing scopes.',
    whyItMatters: 'Prevents unfair benchmarking by adjusting for shift patterns, automation levels, and climate differences.',
    howToUse: [
      'Select Target Plant (e.g., Haridwar, Neemrana, Dharuhera, Gurugram, Chittoor).',
      'Select Benchmark Mode: Automatic Best Peer, Peer Group Average, or Historical Best.',
      'Review the 5-Factor Comparability Score (Scope, Capacity, Automation, Shifts, Climate).',
      'Examine the variance decomposition table to isolate controllable tariff and efficiency deltas.',
    ],
    interpretationRules: [
      'Comparability Score > 80% indicates highly reliable benchmark alignment.',
      'Controllable Inefficiencies are directly addressable through VAVE and kaizen operational changes.',
    ],
    commonMistakes: [
      'Comparing a 3-shift die casting plant with a 1-shift assembly facility without checking comparability score.',
    ],
    troubleshootingAction: 'Verify that monthly production volumes are updated in Data Ingestion Studio.',
  },
  {
    id: 'electricity-accounting',
    chapterNumber: 5,
    title: 'Utility Accounting: Electricity Sources (Grid, DG, Solar)',
    category: 'OPERATIONS',
    summary: 'Source-wise energy aggregation and double-count protection rules.',
    whatItIs: 'A multi-source energy accounting model that tracks purchased grid power, captive solar generation, and backup diesel generator (DG) power.',
    whyItMatters: 'Provides true blended cost per kWh without double-billing captive solar amortizations or fuel costs.',
    howToUse: [
      'Inspect Grid/Discom MU, Captive Solar MU, and DG MU cards.',
      'Verify Total Usable Energy sum = Grid + Captive Solar + DG.',
      'Check Blended Energy Cost (₹/kWh) and Unit Power Cost per Vehicle (₹/veh).',
    ],
    interpretationRules: [
      'DG power reflects emergency peak tariff and is accounted on fuel consumption basis.',
      'Zero-emission solar power reduces blended cost per kWh while maintaining total physical kWh balance.',
    ],
    commonMistakes: [
      'Manually adding solar unit costs to grid tariffs without volume-weighting.',
    ],
    troubleshootingAction: 'Review source-wise aliases in Ingestion Studio if energy totals do not match Discom bills.',
  },
  {
    id: 'compressed-air',
    chapterNumber: 6,
    title: 'Compressed Air Physical Efficiency & Non-Double-Count Rule',
    category: 'OPERATIONS',
    summary: 'Physical compressor efficiency metrics and accounting classification.',
    whatItIs: 'Tracks compressed air demand (CF/veh), compressor specific energy (kWh/CF), and air yield (CF/kWh).',
    whyItMatters: 'Compressed air is typically 15-20% of plant electricity. Tracking physical efficiency reveals leakage and compressor degradation.',
    howToUse: [
      'Inspect Specific Air Demand (CF/veh) against peer benchmark target.',
      'Examine Specific Energy (kWh/CF) to measure compressor motor efficiency.',
      'Review Air Yield (CF/kWh) to assess pneumatic receiver and header health.',
    ],
    interpretationRules: [
      'Non-Double-Count Rule: Compressor electrical power is already embedded in Total Grid Electricity. Compressed air is tracked as a physical efficiency index and allocated cost, not a separate duplicate ledger entry.',
    ],
    commonMistakes: [
      'Adding compressed air cost to total plant electricity cost in financial rollups.',
    ],
    troubleshootingAction: 'If air yield drops below 40 CF/kWh, check compressor intake filter pressure drops.',
  },
  {
    id: 'water-accounting',
    chapterNumber: 7,
    title: 'Water Accounting: Groundwater Tube-Wells vs Municipal PWD',
    category: 'OPERATIONS',
    summary: 'Dual-source water metering and financial reporting rules.',
    whatItIs: 'Tracks on-premise groundwater extraction (borewell tube-wells) separately from municipal PWD piped supply.',
    whyItMatters: 'Ensures compliance with Central Ground Water Authority (CGWA) quotas and accurate blended water cost per vehicle.',
    howToUse: [
      'Check Borewell KL and PWD Municipal KL consumption cards.',
      'Review Specific Water KPI (KL/vehicle) against plant baseline.',
      'Verify Blended Rate (₹/KL) and Unit Water Cost per Vehicle (₹/veh).',
    ],
    interpretationRules: [
      'Zero-cost raw groundwater is accounted on physical volume basis; financial rate is marked as source-specific without fabricating artificial zero-cost tariffs.',
    ],
    commonMistakes: [
      'Assuming zero water utility cost when tube-well pumping energy is consumed in electricity.',
    ],
    troubleshootingAction: 'Verify flow meter calibration in plant utility ingestion logs.',
  },
  {
    id: 'thermal-utilities',
    chapterNumber: 8,
    title: 'Thermal Utilities: Piped Natural Gas (PNG Volumetric Baseline)',
    category: 'OPERATIONS',
    summary: 'Volumetric flow tracking and furnace fuel accounting.',
    whatItIs: 'Tracks Piped Natural Gas (PNG) and process fuel for paint shop ovens, die casting holding furnaces, and heat treatment lines.',
    whyItMatters: 'Process heating is a major controllable cost driver with high thermal conservation potential.',
    howToUse: [
      'Review Specific Gas Consumption (CF/veh) against peer target.',
      'Examine Volumetric Demand (Million CF) and Unit Fuel Cost per Vehicle (₹/veh).',
      'Check Volumetric Tariff (₹/CF) applied by regional gas utility (e.g. GAIL/IGL).',
    ],
    interpretationRules: [
      'Volumetric baseline is recorded on direct meter readings without arbitrary theoretical conversion factors.',
    ],
    commonMistakes: [
      'Comparing natural gas volume across plants without standardizing pressure/temperature baselines.',
    ],
    troubleshootingAction: 'Inspect furnace insulation ECN records if specific gas consumption exceeds 45 CF/veh.',
  },
  {
    id: 'ideathon-search',
    chapterNumber: 9,
    title: 'Vehicle Ideathon 10,000+ Scalable Search & Filtering',
    category: 'VEHICLE_ENGINEERING',
    summary: 'High-performance search, multi-attribute filtering, and pagination across 10K+ proposals.',
    whatItIs: 'An industrial engineering catalog containing thousands of employee and supplier cost reduction ideas.',
    whyItMatters: 'Allows VAVE engineers to rapidly locate specific part optimizations across large multi-year repositories.',
    howToUse: [
      'Use the Search input to query part numbers (e.g. 53100-KTR-900), keywords, or idea codes.',
      'Filter by Target Vehicle Model (Splendor Plus, HF Deluxe, Passion Plus, Glamour XTEC, Xpulse 200).',
      'Filter by Evidence State (Confirmed, Partially Confirmed, Conflicting Records, No Evidence).',
      'Filter by Decision State (Submitted, Under Review, Accepted for Study, Approved, Rejected).',
      'Click "Inspect" on any idea row to open the complete Idea Detail View.',
    ],
    interpretationRules: [
      'Unfiltered 10K lists are virtualized and paginated to prevent memory bloat.',
      'Claimed savings represent initial proposer estimates before deterministic BOM valuation.',
    ],
    commonMistakes: [
      'Assuming an idea with "No Evidence Found" is invalid (it simply requires VAVE study).',
    ],
    troubleshootingAction: 'Click "Clear Filters" if search results return zero matching ideas.',
  },
  {
    id: 'idea-normalization',
    chapterNumber: 10,
    title: 'Idea Normalization & Duplicate Clustering',
    category: 'VEHICLE_ENGINEERING',
    summary: 'NLP-based title normalization, part synonym matching, and deduplication.',
    whatItIs: 'Standardizes disparate employee submissions into canonical engineering problem and solution statements.',
    whyItMatters: 'Merges identical proposals from different plants, avoiding redundant engineering feasibility studies.',
    howToUse: [
      'Inspect the "↳ Normalized Scope" sub-row beneath the proposer raw title.',
      'Review Problem Statement and Proposed Engineering Solution in Idea Detail View.',
      'Verify mapped Part Number and Subsystem Classification.',
    ],
    interpretationRules: [
      'Normalized scope maps raw slang (e.g. "lever ka wazan kam karo") to standard technical terms ("Brake Lever Material Optimization").',
    ],
    commonMistakes: [
      'Creating duplicate idea submissions for parts with existing normalized records.',
    ],
    troubleshootingAction: 'Use Master Data to add missing part aliases if an idea fails to map to canonical BOM.',
  },
  {
    id: 'evidence-grounding',
    chapterNumber: 11,
    title: 'Engineering Evidence, PLM BOM Lineage & CAD Citations',
    category: 'VEHICLE_ENGINEERING',
    summary: 'Grounding axioms, ECN document matching, and drawing OCR verification.',
    whatItIs: 'Links cost proposals to canonical master BOMs, controlled Engineering Change Notices (ECNs), and CAD drawings.',
    whyItMatters: 'Enforces the foundational grounding axiom: Relevance != Authority != Grounding != Business Truth.',
    howToUse: [
      'Check the Evidence State badge (Implementation Confirmed, Partially Confirmed, Conflicting Records, No Evidence).',
      'Inspect Document Type (Canonical Master, Controlled ECN, Plant Actual).',
      'Review Temporal Validity to ensure ECN notices are currently effective.',
      'Examine extracted drawing title blocks and tolerance callouts.',
    ],
    interpretationRules: [
      'Canonical Master PLM BOM has highest authority level (Weight = 1.0).',
      'Controlled ECN documents override historical drawings when effective dates match.',
    ],
    commonMistakes: [
      'Relying on unverified supplier brochures over canonical Hero engineering drawings.',
    ],
    troubleshootingAction: 'Upload missing ECN notice in Data Ingestion Studio if status is unverified.',
  },
  {
    id: 'sibling-applicability',
    chapterNumber: 12,
    title: 'Sibling Model Applicability Matrix (10-Tier Hierarchy)',
    category: 'VEHICLE_ENGINEERING',
    summary: 'Multi-model platform sharing and combined volume calculation.',
    whatItIs: 'Evaluates whether a part optimization for one vehicle model applies to sibling models (e.g. Splendor Plus $\\to$ HF Deluxe).',
    whyItMatters: 'Multiplies cost savings by scaling across shared platform vehicle volumes (from 1.2M to 2.4M units).',
    howToUse: [
      'Review the Sibling Model Applicability Matrix table in Idea Detail View.',
      'Check Compatibility score (100% Direct Fit, Sibling Fit with Minor Tooling, Incompatible).',
      'Verify Combined Annual Volume across all applicable vehicle variants.',
    ],
    interpretationRules: [
      'CONFIRMED_DIRECT_FIT: Part shares identical mounting geometry and electrical pinouts.',
      'SIBLING_FIT: Requires minor bracket or harness adaptation.',
    ],
    commonMistakes: [
      'Applying cosmetic part savings across different styling families without engineering review.',
    ],
    troubleshootingAction: 'Check vehicle platform hierarchy in Master Data if sibling mapping is missing.',
  },
  {
    id: 'opportunity-valuation',
    chapterNumber: 13,
    title: 'Vehicle Cost Opportunity & Deterministic Valuation',
    category: 'VEHICLE_ENGINEERING',
    summary: 'Exact financial math formulas: Direct Saving, Gross Opportunity, CAPEX Amortization, Net Opportunity, Payback.',
    whatItIs: 'A deterministic financial valuation engine using Python Decimal arithmetic with zero LLM estimation.',
    whyItMatters: 'Delivers audited, board-ready cost reduction valuations that match SAP financial ledgers exactly.',
    howToUse: [
      'Review Direct Saving per Vehicle = Current Piece Cost - Proposed Piece Cost.',
      'Review Gross Annual Opportunity = Direct Saving $\\times$ Applicable Annual Volume.',
      'Account for Tooling Investment + Homologation/Testing Validation Costs.',
      'Check Estimated Payback Period (Months) = Total Investment / Monthly Gross Saving.',
      'Verify Net Annual Opportunity = Gross Annual Opportunity - Total First-Year Investment.',
    ],
    interpretationRules: [
      'Payback periods under 6 months are classified as HIGH PRIORITY VAVE projects.',
      'Tooling amortizations are tracked over 12-month standard fiscal cycles.',
    ],
    commonMistakes: [
      'Omitting regulatory homologation testing costs for safety or emission-related parts.',
    ],
    troubleshootingAction: 'Adjust investment sliders in Opportunity Simulator to model different tooling scenarios.',
  },
  {
    id: 'human-review-queue',
    chapterNumber: 14,
    title: 'Human-in-the-Loop Governance & Safety Gates',
    category: 'DATA_GOVERNANCE',
    summary: 'Mandatory human approval gates for safety systems (P0) and high-value proposals (P1).',
    whatItIs: 'An automated safety gating mechanism that intercepts and blocks autonomous approval of critical ideas.',
    whyItMatters: 'Guarantees that no AI system can autonomously approve changes to vehicle brakes, steering, suspension, or frame.',
    howToUse: [
      'Navigate to Human Review & Safety Queue.',
      'Filter by Priority: P0 (Critical/Safety), P1 (High Value/Low Conf), P2 (Cross-Model), P3 (Routine).',
      'Click "Review" on any item to open the decision drawer.',
      'Examine the Safety Gate Reason and Evidence Rationale.',
      'Select Action: Approve with Engineering Sign-off, Reject with Rationale, or Human Override.',
    ],
    interpretationRules: [
      'P0 Critical: Mandatory human sign-off required by Chief Engineer. Autonomous approval is hard-blocked.',
      'P1 High Value: Requires Senior Finance Controller validation for ideas $\\ge$ ₹1 Crore.',
    ],
    commonMistakes: [
      'Attempting to auto-approve ideas flagged with P0 Safety Critical status.',
    ],
    troubleshootingAction: 'Check that reviewer credentials and digital signatures are recorded in Audit Log.',
  },
  {
    id: 'data-ingestion',
    chapterNumber: 15,
    title: 'Data Ingestion Studio & Magnitude Guards',
    category: 'DATA_GOVERNANCE',
    summary: 'Air-gapped file uploading, dry-run schema validation, and unit magnitude guards.',
    whatItIs: 'A secure ingestion pipeline for monthly plant utility logs and employee ideathon submission spreadsheets.',
    whyItMatters: 'Protects the platform database against corrupt headers, invalid formats, and 100,000x magnitude errors (Lakhs vs Rupees).',
    howToUse: [
      'Select Ingestion Pipeline: Plant OPEX Time-Series or Vehicle Ideathon Submissions.',
      'Select or drop a .CSV or .XLSX file.',
      'Review the automated Dry-Run Validation report.',
      'Inspect Column Alias Matching and Magnitude Guard checks.',
      'Click "Commit Ingestion" to persist records with an immutable SHA-256 audit entry.',
    ],
    interpretationRules: [
      'Magnitude Guard flags any unit cost $> ₹50,000$ on component BOMs to prevent Lakhs/Rupees scale confusion.',
    ],
    commonMistakes: [
      'Uploading files with unmapped custom column headers without configuring aliases.',
    ],
    troubleshootingAction: 'Download the template file from Ingestion Studio to ensure correct column header format.',
  },
  {
    id: 'master-data',
    chapterNumber: 16,
    title: 'Master Data Management & Column Aliasing',
    category: 'DATA_GOVERNANCE',
    summary: 'Managing plant metadata, vehicle hierarchy models, and part catalog mappings.',
    whatItIs: 'The foundational reference master data governing plants, vehicle models, parts, and supplier catalogs.',
    whyItMatters: 'Ensures uniform naming conventions across disparate plant ERP systems and legacy ideathon records.',
    howToUse: [
      'Review the Plant Master list (Plant A Haridwar, Plant B Dharuhera, Plant C Neemrana, etc.).',
      'Verify Vehicle Hierarchy (Platform $\\to$ Model Family $\\to$ Variant $\\to$ Subsystem).',
      'Inspect mapped Column Aliases for supplier spreadsheet ingestion.',
    ],
    interpretationRules: [
      'All vehicle models belong to defined platform families (100cc Commuter, 125cc Executive, 200cc Premium).',
    ],
    commonMistakes: [
      'Modifying plant capacity numbers without updating the benchmark comparability baseline.',
    ],
    troubleshootingAction: 'Contact System Administrator to update canonical plant capacity baselines.',
  },
  {
    id: 'ai-studio-overview',
    chapterNumber: 17,
    title: 'AI Studio Industrial Workstation Overview',
    category: 'AI_SYSTEM',
    summary: 'Engineering control center for local SLMs, task routing, and deterministic inference.',
    whatItIs: 'The local AI operations interface providing model selection, preflight hardware checks, chat playground, and provider switching.',
    whyItMatters: 'Empowers cost engineers to interact with local AI models running completely on-premise without cloud latency or egress fees.',
    howToUse: [
      'Review the top Active Runtime Bar for current active model, profile, context length, and VRAM.',
      'Use the Inference & Chat Playground for grounded reasoning queries.',
      'Use AI Orchestration & Sidecars to test local providers (Native GGUF, Ollama, LM Studio).',
      'Use Model Registry & Hardware Monitor to inspect GGUF files and admission headroom.',
      'Use Visual Document & CAD Inspector for drawing title block and tolerance extraction.',
    ],
    interpretationRules: [
      'Inference responses display cryptographic Provenance hashes and grounding scores.',
    ],
    commonMistakes: [
      'Assuming the chat playground can perform arithmetic (all math is routed to Python Decimal engine).',
    ],
    troubleshootingAction: 'Click "Preflight Check" before loading large models to verify VRAM fit.',
  },
  {
    id: 'model-selection',
    chapterNumber: 18,
    title: 'Model Selection & GGUF Format Validation (AI-02)',
    category: 'AI_SYSTEM',
    summary: 'Model registry lifecycle states, SHA-256 verification, and quarantine policies.',
    whatItIs: 'Governs local AI model manifests, ensuring only verified, uncorrupted GGUF models are loaded into GPU memory.',
    whyItMatters: 'Protects the workstation against corrupt model files, malicious weights, and incompatible tensor architectures.',
    howToUse: [
      'Navigate to Model Registry Monitor or click "Browse Models".',
      'Filter models by Format (GGUF, SafeTensors), Quantization (Q4_K_M, Q5_K_M, Q8_0), and Size.',
      'Inspect SHA-256 checksum and quarantine status.',
      'Select a verified model and click "Load Model" to initialize.',
    ],
    interpretationRules: [
      'ACTIVE_REGISTERED: Verified SHA-256 checksum, valid tensor headers, admitted by hardware profiler.',
      'QUARANTINED: Corrupted file or unsafe format. Strictly blocked from execution.',
    ],
    commonMistakes: [
      'Attempting to load unquantized 70B models on 8GB VRAM workstations.',
    ],
    troubleshootingAction: 'Re-scan model directory if a newly downloaded GGUF file is not listed.',
  },
  {
    id: 'provider-orchestration',
    chapterNumber: 19,
    title: 'Provider Orchestration (Built-in GGUF, Ollama, LM Studio)',
    category: 'AI_SYSTEM',
    summary: 'Managing optional local provider backends with strict offline reporting and non-silent fallback.',
    whatItIs: 'The platform control plane managing built-in native GGUF engine and optional local sidecars (Ollama, LM Studio).',
    whyItMatters: 'Provides execution flexibility while preserving the platform as the sole master orchestrator.',
    howToUse: [
      'Open AI Orchestration tab in AI Studio.',
      'Inspect Providers List: Built-in Native GGUF, Ollama (Port 11434), LM Studio (Port 1234), Local OpenAI API.',
      'Click "Test Connection" to perform real-time health and latency probes.',
      'Configure custom endpoint URLs and fallback policies.',
      'Select a provider and click "Set as Active".',
    ],
    interpretationRules: [
      'Built-in Native GGUF is the primary independent engine. Operates without any external daemons.',
      'If an external provider is OFFLINE and fallback is DISABLED, the system returns a strict error without silently switching.',
    ],
    commonMistakes: [
      'Expecting live VRAM telemetry from Ollama/LM Studio over standard HTTP APIs (marked as NOT EXPOSED BY PROVIDER).',
    ],
    troubleshootingAction: 'Start Ollama daemon (`ollama serve`) or LM Studio local server if provider shows OFFLINE.',
  },
  {
    id: 'hardware-profiles',
    chapterNumber: 20,
    title: 'Hardware Admission & VRAM Headroom Gating (AI-03)',
    category: 'AI_SYSTEM',
    summary: 'Hardware tiers, KV cache calculation, and CUDA layer offload strategies.',
    whatItIs: 'Calculates exact memory footprints (Model Weights + KV Cache + CUDA Context) before admitting models.',
    whyItMatters: 'Prevents Out-Of-Memory (OOM) GPU crashes and host system freezes during intensive multi-turn inference.',
    howToUse: [
      'Review Hardware Profile options: PROFILE-BALANCED, PROFILE-SPEED, PROFILE-ACCURACY, PROFILE-LOW-MEMORY.',
      'Inspect Usable VRAM and Safety Headroom metrics.',
      'Verify Recommended CUDA Layers (e.g. 33/33 layers on RTX 4060).',
    ],
    interpretationRules: [
      'SAFE: Model fits in VRAM with $> 1.0$ GB safety headroom.',
      'CONSTRAINED: Fits with limited context ($< 1.0$ GB headroom).',
      'UNSAFE: Exceeds VRAM; routed to CPU fallback or blocked.',
    ],
    commonMistakes: [
      'Increasing context length to 32K on 8GB GPU without checking KV cache growth.',
    ],
    troubleshootingAction: 'Select PROFILE-BALANCED or PROFILE-LOW-MEMORY to reduce VRAM pressure.',
  },
  {
    id: 'runtime-loading',
    chapterNumber: 21,
    title: 'Runtime Lifecycle & Dynamic Layer Offloading',
    category: 'AI_SYSTEM',
    summary: 'Sequential model swapping, memory garbage collection, and live token telemetry.',
    whatItIs: 'Controls the 5-stage progressive model loading sequence and cleans GPU memory between task switches.',
    whyItMatters: 'Enables smooth switching between embedding models, reranker cross-encoders, and generation SLMs on a single laptop GPU.',
    howToUse: [
      'Observe the 5-stage loading bar during model acquisition.',
      'Monitor live generation metrics: Time To First Token (TTFT in ms) and Generation Speed (tokens/sec).',
      'Use the Cancel button to abort long-running streaming inference.',
    ],
    interpretationRules: [
      'TTFT $< 200$ ms and speed $> 30$ tok/s represent optimal RTX 4060 hardware performance.',
    ],
    commonMistakes: [
      'Triggering multiple simultaneous model loads before the active model has finished unloading.',
    ],
    troubleshootingAction: 'Click "Unload Model" in Model Registry to force immediate GPU garbage collection.',
  },
  {
    id: 'vision-cad-parser',
    chapterNumber: 22,
    title: 'Vision & Engineering Drawing CAD Parser (AI-15)',
    category: 'AI_SYSTEM',
    summary: 'Digital PDF stream extraction, raster OCR probing, and drawing title block parsing.',
    whatItIs: 'Extracts engineering metadata, part numbers, material grades (e.g. ADC12), dimensions, and tolerances from vehicle 2D drawings.',
    whyItMatters: 'Automates verification of drawing revisions against claimed ideathon weight reductions.',
    howToUse: [
      'Navigate to Visual Document & CAD Inspector tab in AI Studio.',
      'Select a drawing sample or upload an engineering drawing PDF.',
      'Inspect Extracted Title Block: Part Number, Drawing Number, Revision, Material Grade, Drawn By, Approved By.',
      'Review Dimension callouts, critical notes, and geometric tolerances.',
    ],
    interpretationRules: [
      'Digital PDF Stream extraction provides $> 98\\%$ text fidelity in $< 5$ ms.',
      'Raster OCR probe verifies scanned legacy blueprints.',
    ],
    commonMistakes: [
      'Uploading low-resolution scans with illegible title block text.',
    ],
    troubleshootingAction: 'Verify that drawing PDFs have embedded vector text streams for fastest extraction.',
  },
  {
    id: 'audit-provenance',
    chapterNumber: 23,
    title: 'Cryptographic Provenance & Audit Ledger (AI-17)',
    category: 'DATA_GOVERNANCE',
    summary: 'SHA-256 provenance hashes, immutable audit logging, and decision traceability.',
    whatItIs: 'A tamper-evident audit ledger recording every calculation, human review override, and data ingestion event.',
    whyItMatters: 'Guarantees that every cost figure presented to executive management can be traced back to its raw input sources and reviewer IDs.',
    howToUse: [
      'Navigate to Security & Audit Log workspace.',
      'Inspect timestamped audit rows: Actor User, Action Type, Entity ID, and Details.',
      'Click on any SHA-256 hash badge in OPEX, Ideathon, or Simulator to verify decision lineage.',
    ],
    interpretationRules: [
      'SHA-256 hashes are deterministically generated from input data + formula version + timestamp.',
    ],
    commonMistakes: [
      'Attempting to edit historical audit records (records are append-only and cryptographically sealed).',
    ],
    troubleshootingAction: 'Search by Entity ID (e.g. IDEA-2024-0042) to inspect the complete history of an idea.',
  },
  {
    id: 'security-airgap',
    chapterNumber: 24,
    title: 'Security, Air-Gap Enforcement & RBAC Roles',
    category: 'DATA_GOVERNANCE',
    summary: 'Role-based access control, socket egress blocking, and password hashing.',
    whatItIs: 'Enterprise security architecture enforcing user roles (Viewer, Cost Engineer, Plant Reviewer, Chief Engineer, Administrator).',
    whyItMatters: 'Ensures strict separation of duties and prevents unauthorized modification of plant tariffs or approved BOM pieces.',
    howToUse: [
      'Verify active role badge in the top navigation header.',
      'Review permission gates for approving safety-critical ideas.',
      'Confirm that socket egress filters permit only localhost (`127.0.0.1`) communication.',
    ],
    interpretationRules: [
      'Chief Engineer role is required to override P0 Safety Critical review gates.',
      'Cost Engineer role can simulate opportunities and submit proposals for review.',
    ],
    commonMistakes: [
      'Sharing administrator credentials across multiple plant review teams.',
    ],
    troubleshootingAction: 'Contact Administrator to request elevated reviewer privileges.',
  },
  {
    id: 'troubleshooting-glossary',
    chapterNumber: 25,
    title: 'Comprehensive Troubleshooting Guide & Engineering Glossary',
    category: 'REFERENCE',
    summary: 'Quick-reference matrix for resolving operational errors and definitions for 30+ cost intelligence terms.',
    whatItIs: 'A searchable reference section explaining technical abbreviations, financial terms, and error remediation steps.',
    whyItMatters: 'Enables self-service problem resolution without waiting for IT developer assistance.',
    howToUse: [
      'Use the Troubleshooting search box to find matching error symptoms.',
      'Follow the Symptom $\\to$ Likely Cause $\\to$ Action remediation steps.',
      'Search the Glossary for technical acronyms (RRF, ECN, BOM Lineage, GBNF, TTFT, GGUF).',
    ],
    interpretationRules: [
      'All troubleshooting steps are validated for local Windows and air-gapped workstation environments.',
    ],
    commonMistakes: [
      'Restarting the entire application when only a single provider connection needed refreshing.',
    ],
    troubleshootingAction: 'Review the troubleshooting table below for step-by-step diagnostic actions.',
  },
];

export const GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    term: 'Addressable Gap',
    category: 'Plant OPEX',
    definition: 'The portion of manufacturing cost variance that can be eliminated through operational, efficiency, or commercial improvements, excluding non-controllable structural differences (e.g. ambient climate).',
    exampleOrContext: 'Haridwar vs Dharuhera addressable electricity gap of ₹28.00 / vehicle.',
  },
  {
    term: 'Air-Gap Architecture',
    category: 'Security',
    definition: 'A security design where software executes entirely on local infrastructure with zero outbound network communication to external internet servers or cloud APIs.',
    exampleOrContext: 'Platform blocks all remote egress, ensuring vehicle CAD and BOM data never leave the plant workstation.',
  },
  {
    term: 'Applicability Matrix',
    category: 'Vehicle Engineering',
    definition: 'A multi-tier vehicle compatibility mapping determining which sibling models can adopt a component optimization.',
    exampleOrContext: 'Splendor Plus brake lever optimization mapped 100% to HF Deluxe and Passion Plus.',
  },
  {
    term: 'Blended Energy Cost',
    category: 'Plant OPEX',
    definition: 'The volume-weighted cost per kWh combining purchased grid power, zero-emission captive solar generation, and backup diesel generator (DG) power.',
    exampleOrContext: 'Haridwar blended tariff: ₹7.56 / kWh across 102.0 MU total usable energy.',
  },
  {
    term: 'BOM Lineage',
    category: 'Vehicle Engineering',
    definition: 'The hierarchical structural trace connecting a part number to its parent assembly, subsystem, vehicle model family, and revision history in the PLM system.',
    exampleOrContext: 'Part 53100-KTR-900 traced to Brake System on Splendor Plus Platform.',
  },
  {
    term: 'CAD Drawing Parser',
    category: 'AI System',
    definition: 'A local vision and PDF stream analysis engine that extracts title blocks, revision letters, material grades, and tolerance callouts from 2D drawings.',
    exampleOrContext: 'Extracted ADC12 material grade and ISO 2768-mK tolerance from cylinder head drawing.',
  },
  {
    term: 'Comparability Index',
    category: 'Plant OPEX',
    definition: 'A multi-factor score (0-100%) evaluating manufacturing scope, volume scale, shift schedules, automation, and climate alignment between benchmarked plants.',
    exampleOrContext: '88% comparability score between Haridwar and Dharuhera.',
  },
  {
    term: 'Compressed Air Yield',
    category: 'Plant OPEX',
    definition: 'The volume of compressed air produced per unit of electrical energy consumed by the compressor station, measured in Cubic Feet per kWh (CF/kWh).',
    exampleOrContext: 'Plant yield of 46.5 CF/kWh compared against peer benchmark target of 51.3 CF/kWh.',
  },
  {
    term: 'Deterministic Valuation',
    category: 'Vehicle Engineering',
    definition: 'Financial opportunity calculation computed strictly via exact Decimal arithmetic, completely isolated from generative AI model estimation.',
    exampleOrContext: 'Gross Saving = Direct Saving × Annual Volume; Net = Gross - Investment.',
  },
  {
    term: 'ECN (Engineering Change Notice)',
    category: 'Vehicle Engineering',
    definition: 'A formal engineering release document authorizing modifications to part dimensions, material compositions, supplier tooling, or BOM assembly structures.',
    exampleOrContext: 'ECN-2025-042 authorizing furnace insulation retrofit.',
  },
  {
    term: 'GBNF Grammar',
    category: 'AI System',
    definition: 'A formal BNF grammar constraint engine that restricts SLM token sampling to strictly valid JSON structures matching a predefined Pydantic schema.',
    exampleOrContext: 'Guarantees 100% parseable JSON extraction from unstructured text without syntax errors.',
  },
  {
    term: 'GGUF Format',
    category: 'AI System',
    definition: 'A high-performance binary file format designed for fast local CPU/GPU model loading, quantized weights, and rapid mmap memory access.',
    exampleOrContext: 'Qwen2.5-3B-Instruct.Q4_K_M.gguf loaded into RTX 4060 VRAM.',
  },
  {
    term: 'Grounding Score',
    category: 'AI System',
    definition: 'A quantitative metric (0.0 to 1.0) assessing whether an AI generation is strictly substantiated by canonical PLM documents and plant tariff records.',
    exampleOrContext: 'Grounding score of 0.98 indicating high evidence support from ECN records.',
  },
  {
    term: 'HNSW Vector Index',
    category: 'AI System',
    definition: 'Hierarchical Navigable Small World graph index used for high-speed dense vector similarity retrieval over 10,000+ engineering documents.',
    exampleOrContext: 'Retrieves relevant ECN notices in < 2ms.',
  },
  {
    term: 'Human Review Gate (P0-P3)',
    category: 'Data Governance',
    definition: 'An automated routing policy that intercepts ideas affecting safety-critical systems or exceeding financial thresholds for mandatory human sign-off.',
    exampleOrContext: 'P0 Critical gate triggered for brake lever alloy change.',
  },
  {
    term: 'KV Cache',
    category: 'AI System',
    definition: 'Key-Value attention tensor cache stored in GPU memory during multi-turn LLM inference, proportional to sequence context length.',
    exampleOrContext: '512MB allocated for 4096-token context window.',
  },
  {
    term: 'Magnitude Guard',
    category: 'Data Governance',
    definition: 'A validation rule that catches scale confusion errors (e.g. user entering ₹2.5 Lakhs instead of ₹2.50 per vehicle unit).',
    exampleOrContext: 'Flags any unit piece cost delta > ₹50,000 as suspicious.',
  },
  {
    term: 'Non-Double-Count Rule',
    category: 'Plant OPEX',
    definition: 'An accounting principle ensuring that secondary utility demands (like compressor electricity) are not billed twice in both utility and electrical ledgers.',
    exampleOrContext: 'Compressor power is tracked as physical efficiency while accounted under grid electricity.',
  },
  {
    term: 'Payback Period',
    category: 'Vehicle Engineering',
    definition: 'The time required for cumulative component piece cost savings to fully recover initial CAPEX tooling and homologation validation investments.',
    exampleOrContext: '2.0-month payback period on ₹10 Lakh tooling investment.',
  },
  {
    term: 'Provenance Hash',
    category: 'Security',
    definition: 'A SHA-256 cryptographic digest uniquely identifying the input dataset, formula version, and timestamp of a generated cost valuation.',
    exampleOrContext: 'sha256:8b9a1c2d3e4f... displayed on opportunity ledger.',
  },
  {
    term: 'Reciprocal Rank Fusion (RRF)',
    category: 'AI System',
    definition: 'A hybrid search algorithm that merges dense vector semantic results with sparse BM25 keyword matching for optimal retrieval accuracy.',
    exampleOrContext: 'Combines part number keyword matches with conceptual NLP query matches.',
  },
  {
    term: 'Reranker Cross-Encoder',
    category: 'AI System',
    definition: 'A deep learning model that performs joint attention over query-document pairs to accurately re-score candidate citations.',
    exampleOrContext: 'BGE-Reranker model filtering top 3 authoritative ECNs.',
  },
  {
    term: 'Runtime Profile',
    category: 'AI System',
    definition: 'A pre-configured hardware execution setting (Balanced, Speed, Accuracy, Low-Memory) balancing VRAM offload layers against context size.',
    exampleOrContext: 'PROFILE-BALANCED offloading 33/33 layers to RTX 4060.',
  },
  {
    term: 'Specific Power (kWh/veh)',
    category: 'Plant OPEX',
    definition: 'Total manufacturing electricity consumed divided by total vehicle production units produced during the accounting period.',
    exampleOrContext: 'Haridwar: 42.5 kWh/veh vs Dharuhera benchmark of 38.0 kWh/veh.',
  },
  {
    term: 'Specific Water (KL/veh)',
    category: 'Plant OPEX',
    definition: 'Total plant water extraction (groundwater + municipal) divided by total vehicle production units.',
    exampleOrContext: 'Plant baseline: 0.35 KL / vehicle.',
  },
  {
    term: 'Time To First Token (TTFT)',
    category: 'AI System',
    definition: 'The latency in milliseconds between submitting a prompt and receiving the very first streaming token from the local SLM engine.',
    exampleOrContext: 'TTFT of 119.5 ms on local native GGUF CUDA runtime.',
  },
  {
    term: 'VAVE (Value Analysis & Value Engineering)',
    category: 'Vehicle Engineering',
    definition: 'A systematic method to improve the value of goods by examining function and reducing component manufacturing costs.',
    exampleOrContext: 'VAVE engineering review evaluating ADC12 die casting substitution.',
  },
  {
    term: 'VRAM Safety Headroom',
    category: 'AI System',
    definition: 'The remaining unallocated GPU dedicated memory after loading model weights and allocating KV cache.',
    exampleOrContext: '5.2 GB headroom remaining on 8GB RTX 4060.',
  },
];

export const TROUBLESHOOTING_GUIDE: TroubleshootingEntry[] = [
  {
    id: 'ts-backend-offline',
    symptom: 'Application displays "Backend Connection Error" or fails to load data tables.',
    likelyCause: 'FastAPI backend server on port 8000 is stopped or unreachable.',
    check: [
      'Check if uvicorn process is running on port 8000.',
      'Check local firewall or antivirus blocking 127.0.0.1:8000.',
    ],
    action: 'Run command: .\\.venv\\Scripts\\uvicorn.exe backend.app.main:app --port 8000',
    workspaceId: 'overview',
  },
  {
    id: 'ts-ollama-offline',
    symptom: 'Ollama shows "OFFLINE" in AI Studio Orchestration tab.',
    likelyCause: 'Ollama local daemon is not running or listening on port 11434.',
    check: [
      'Run `netstat -ano | findstr 11434` in terminal.',
      'Check if custom port (e.g. 11437) was configured without updating the endpoint URL.',
    ],
    action: 'Launch Ollama application or start daemon via `ollama serve`. Use built-in Native GGUF as immediate fallback.',
    workspaceId: 'aistudio',
  },
  {
    id: 'ts-lmstudio-offline',
    symptom: 'LM Studio shows "OFFLINE: <urlopen error timed out>" on port 1234.',
    likelyCause: 'LM Studio local server feature is toggled off in LM Studio application.',
    check: [
      'Open LM Studio -> Developer tab -> Start Local Server on port 1234.',
      'Verify base URL is http://127.0.0.1:1234 (do not append /v1 manually).',
    ],
    action: 'Toggle "Start Server" in LM Studio or use platform Built-in Native GGUF.',
    workspaceId: 'aistudio',
  },
  {
    id: 'ts-hardware-unsafe',
    symptom: 'Preflight check reports "Hardware Fit UNSAFE: Model footprint exceeds available VRAM".',
    likelyCause: 'Selected model parameter size (e.g. 14B or 70B) is too large for workstation GPU VRAM (8GB).',
    check: [
      'Check current VRAM usage in Hardware & AI Runtime workspace.',
      'Check active context window length.',
    ],
    action: 'Select a 3B or 7B Q4_K_M quantized model, or switch Hardware Profile to PROFILE-LOW-MEMORY for CPU offloading.',
    workspaceId: 'hardware',
  },
  {
    id: 'ts-magnitude-guard',
    symptom: 'Ingestion Studio displays "Magnitude Guard Rejection: Unit Cost exceeds ₹50,000".',
    likelyCause: 'Spreadsheet column has figures entered in Total Lakhs instead of Unit Rupees.',
    check: [
      'Inspect raw CSV file column "Claimed Saving" or "Piece Cost".',
      'Verify whether figures represent unit delta (e.g. ₹2.50) or annualized lakhs (e.g. ₹2.50 Lakhs).',
    ],
    action: 'Normalize column to Unit INR before re-uploading, or use Ingestion column alias transformer.',
    workspaceId: 'ingestion',
  },
  {
    id: 'ts-p0-review-blocked',
    symptom: 'Approve button is disabled on Idea Detail View for IDEA-2024-0042.',
    likelyCause: 'Idea is classified as P0 Safety Critical (Brakes/Steering/Suspension/Frame) requiring mandatory human sign-off.',
    check: [
      'Check Subsystem Classification in Idea Detail.',
      'Verify active user permissions in top bar.',
    ],
    action: 'Navigate to Human Review Queue, log in with Chief Engineer role, and record a mandatory safety review rationale.',
    workspaceId: 'governance',
  },
  {
    id: 'ts-vision-ocr-empty',
    symptom: 'Visual Document Parser returns low extraction confidence or missing title block.',
    likelyCause: 'Uploaded drawing is a low-contrast bitmap scan lacking vector text streams.',
    check: [
      'Verify PDF has embedded selectable text.',
      'Check drawing orientation (ensure drawing is not rotated 90 degrees).',
    ],
    action: 'Upload original vector PDF exported from CAD/PLM, or enable Tesseract raster OCR probe.',
    workspaceId: 'aistudio',
  },
  {
    id: 'ts-zero-evidence',
    symptom: 'Ideathon proposal displays "NO EVIDENCE FOUND" status.',
    likelyCause: 'Part number has no corresponding historical ECN release or implementation notice in the local database.',
    check: [
      'Check part number format (e.g. 53100-KTR-900).',
      'Verify whether this is a newly submitted concept proposal.',
    ],
    action: 'This is an expected status for novel proposals. Route to VAVE engineering feasibility study.',
    workspaceId: 'ideathon',
  },
];
