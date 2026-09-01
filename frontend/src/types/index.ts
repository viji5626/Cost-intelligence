/**
 * TypeScript Type Definitions for HERO Vehicle Cost Intelligence Platform
 * Phase 9 Front-End UX & Production Readiness
 */

// ==========================================
// 1. Core Enums & Dimension Definitions
// ==========================================

export type ImplementationEvidenceState =
  | 'IMPLEMENTED'
  | 'PARTIALLY_CONFIRMED'
  | 'HISTORICAL'
  | 'POTENTIAL_EVIDENCE'
  | 'NO_EVIDENCE_FOUND'
  | 'INSUFFICIENT'
  | 'CONFLICTING';

export type IdeaDecisionState =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'ACCEPTED_FOR_STUDY'
  | 'APPROVED_FOR_IMPLEMENTATION'
  | 'ON_HOLD'
  | 'REJECTED'
  | 'SUPERSEDED';

export type ReviewStatus =
  | 'NOT_REQUIRED'
  | 'PENDING_REVIEW'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'OVERRIDDEN'
  | 'MORE_EVIDENCE_REQUESTED'
  | 'ESCALATED';

export type ReviewPriority =
  | 'CRITICAL_P0'
  | 'HIGH_P1'
  | 'MEDIUM_P2'
  | 'LOW_P3';

export type ReviewActionType =
  | 'ASSIGN'
  | 'APPROVE'
  | 'REJECT'
  | 'OVERRIDE'
  | 'REQUEST_MORE_EVIDENCE'
  | 'ESCALATE'
  | 'REOPEN';

export type ConfidenceTier = 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW';

export type ValidationOutcome = 'VALID' | 'UNUSUAL_VALID_DATA' | 'INVALID_DATA';

// ==========================================
// 2. Plant OPEX & Benchmark Types
// ==========================================

export interface ElectricitySourceData {
  grid_kwh?: number;
  grid_cost_inr?: number;
  dg_kwh?: number;
  dg_cost_inr?: number;
  solar_kwh?: number;
  solar_cost_inr?: number;
  other_generated_kwh?: number;
  purchased_kwh?: number;
  total_generated_kwh?: number;
  total_energy_kwh: number;
  total_electricity_cost_inr: number;
  kwh_per_vehicle: number;
  cost_per_kwh_inr?: number;
  cost_per_vehicle_inr: number;
  accounting_classification?: string;
}

export interface WaterSourceData {
  borewell_kl?: number;
  borewell_cost_inr?: number;
  pwd_kl?: number;
  pwd_cost_inr?: number;
  other_water_kl?: number;
  total_water_kl: number;
  total_water_cost_inr: number;
  kl_per_vehicle: number;
  cost_per_kl_inr?: number;
  cost_per_vehicle_inr: number;
}

export interface CompressedAirData {
  compressed_air_cf_total?: number;
  compressed_air_cf_per_vehicle?: number;
  compressor_kwh_total?: number;
  compressor_kwh_per_cf?: number;
  compressor_cf_per_kwh?: number;
  compressed_air_cost_inr?: number;
  compressed_air_cost_per_cf_inr?: number;
  compressed_air_cost_per_vehicle_inr?: number;
  is_compressor_power_embedded?: boolean;
}

export interface GasFuelData {
  gas_cf_total?: number;
  gas_nm3_total?: number;
  gas_cf_per_vehicle?: number;
  gas_nm3_per_vehicle?: number;
  gas_cost_inr: number;
  gas_cost_per_cf_inr?: number;
  gas_cost_per_vehicle_inr: number;
  gas_source_type: string;
}

export interface PlantKPIs {
  plant_id: string;
  plant_name: string;
  period_start: string;
  period_end: string;
  production_volume: number;
  kwh_per_vehicle: number;
  kl_per_vehicle: number;
  gas_per_vehicle: number;
  gas_cf_per_vehicle?: number;
  cost_per_vehicle_inr: number;
  total_opex_inr: number;
  compressed_air_cf_per_vehicle?: number;
  compressor_kwh_per_cf?: number;
  compressor_cf_per_kwh?: number;
  compressed_air_cost_per_veh_inr?: number;
  is_compressor_power_embedded?: boolean;
  electricity?: ElectricitySourceData;
  water?: WaterSourceData;
  compressed_air?: CompressedAirData;
  gas_fuel?: GasFuelData;
  provenance_hash: string;
}

export interface ComparabilityBreakdown {
  scope_similarity: number;
  volume_similarity: number;
  shift_similarity: number;
  capacity_similarity: number;
  tariff_similarity: number;
}

export interface VarianceDecomposition {
  electricity_variance_inr: number;
  fuel_gas_variance_inr: number;
  water_variance_inr: number;
  maintenance_variance_inr: number;
  manpower_variance_inr: number;
  fixed_overhead_variance_inr: number;
  total_variance_inr: number;
}

export interface BenchmarkComparisonResult {
  target_plant_id: string;
  target_plant_name: string;
  benchmark_plant_id?: string;
  benchmark_plant_name?: string;
  benchmark_source_name?: string;
  comparison_mode?: 'BEST_COMPARABLE' | 'PEER_GROUP' | 'HISTORICAL_BASELINE' | 'MANAGEMENT_TARGET' | string;
  comparability_score: number;
  comparability_tier: 'HIGH' | 'MEDIUM' | 'LOW';
  comparability_breakdown: ComparabilityBreakdown;
  comparison_explanation: string;
  target_cost_per_veh: number;
  benchmark_cost_per_veh: number;
  gross_gap_per_veh: number;
  addressable_efficiency_gap_per_veh: number;
  structural_gap_per_veh: number;
  target_annual_production: number;
  annual_addressable_opportunity_inr: number;
  variance_breakdown: VarianceDecomposition;
  benchmark_compressed_air_cf_per_vehicle?: number;
  benchmark_compressor_kwh_per_cf?: number;
  benchmark_compressor_cf_per_kwh?: number;
  benchmark_gas_cf_per_vehicle?: number;
  benchmark_electricity?: ElectricitySourceData;
  benchmark_water?: WaterSourceData;
  benchmark_compressed_air?: CompressedAirData;
  benchmark_gas_fuel?: GasFuelData;
  provenance_hash: string;
}

// ==========================================
// 3. Vehicle Hierarchy & BOM Types
// ==========================================

export interface ProductFamily {
  id: string;
  family_code: string;
  name: string;
  description?: string;
}

export interface VehicleModel {
  id: string;
  model_code: string;
  name: string;
  vehicle_id: string;
  segment?: string;
}

export interface PartLineage {
  part_id: string;
  part_number: string;
  part_name: string;
  is_safety_critical: boolean;
  component_id: string;
  component_name: string;
  assembly_id: string;
  assembly_name: string;
  subsystem_id: string;
  subsystem_name: string;
  current_piece_cost_inr?: number;
}

// ==========================================
// 4. Ideathon & Discovery Types
// ==========================================

export interface IdeaSubmission {
  id: string;
  submission_code: string;
  raw_title: string;
  raw_description: string;
  raw_claimed_saving_per_veh?: number;
  normalized_title?: string;
  problem_statement?: string;
  proposed_solution?: string;
  target_vehicle_id?: string;
  target_model_id?: string;
  target_part_id?: string;
  extracted_part_number?: string;
  decision_state: IdeaDecisionState;
  evidence_state: ImplementationEvidenceState;
  duplicate_cluster_id?: string;
  created_at: string;
}

export interface SiblingModelApplicability {
  model_id: string;
  model_name: string;
  variant_id: string;
  variant_name: string;
  annual_volume_planned: number;
  applicability_status: string;
  compatibility_score: number;
  notes?: string;
}

export interface EvidenceRecord {
  id: string;
  source_id: string;
  source_type: string;
  source_authority: string;
  evidence_state: ImplementationEvidenceState;
  effective_date?: string;
  vehicle_model?: string;
  part_number?: string;
  ecn_number?: string;
  relevance_score: number;
  notes?: string;
}

export interface IdeaEvidenceEvaluation {
  idea_id: string;
  submission_code: string;
  evidence_state: ImplementationEvidenceState;
  confidence_score: number;
  confidence_tier: ConfidenceTier;
  target_part_lineage?: PartLineage;
  applicable_models: SiblingModelApplicability[];
  supporting_evidence: EvidenceRecord[];
  conflicting_evidence: EvidenceRecord[];
  total_applicable_annual_volume: number;
  has_conflicting_evidence: boolean;
  is_safety_critical: boolean;
}

// ==========================================
// 5. Deterministic Opportunity Types
// ==========================================

export interface OpportunityEvaluation {
  id: string;
  idea_id: string;
  current_piece_cost_inr: number;
  proposed_piece_cost_inr: number;
  saving_per_vehicle_inr: number;
  applicable_annual_volume: number;
  gross_annual_opportunity_inr: number;
  tooling_investment_inr: number;
  validation_investment_inr: number;
  net_opportunity_inr: number;
  payback_period_months?: number;
  provenance_hash: string;
  calculation_metadata?: Record<string, any>;
  created_at: string;
}

// ==========================================
// 6. Governance & Review Types
// ==========================================

export interface ReviewAction {
  id: string;
  review_record_id: string;
  actor_user_id: string;
  actor_username?: string;
  action_type: ReviewActionType;
  previous_status: string;
  new_status: string;
  comments?: string;
  override_rationale?: string;
  created_at: string;
}

export interface ReviewRecord {
  id: string;
  idea_id: string;
  submission_code: string;
  idea_title: string;
  review_status: ReviewStatus;
  review_priority: ReviewPriority;
  routing_reasons: string[];
  is_safety_critical: boolean;
  is_escalated: boolean;
  calibrated_confidence_score: number;
  confidence_tier: ConfidenceTier;
  confidence_breakdown?: Record<string, number>;
  original_automated_decision: string;
  original_evidence_state: string;
  assigned_reviewer_id?: string;
  assigned_reviewer_name?: string;
  final_decision?: string;
  final_decision_by?: string;
  final_decision_at?: string;
  final_decision_reason?: string;
  created_at: string;
  updated_at: string;
  actions?: ReviewAction[];
}

export interface ReviewCaseDetail {
  idea_id: string;
  submission_code: string;
  title: string;
  description: string;
  problem_statement?: string;
  proposed_solution?: string;
  target_part?: PartLineage;
  dimensions: {
    calibrated_confidence_score: number;
    confidence_tier: ConfidenceTier;
    implementation_evidence_state: ImplementationEvidenceState;
    idea_decision_state: IdeaDecisionState;
    human_review_status: ReviewStatus;
    review_priority: ReviewPriority;
  };
  safety_governance: {
    is_safety_critical: boolean;
    is_escalated: boolean;
    routing_reasons: string[];
  };
  financial_opportunity?: {
    current_piece_cost_inr: number;
    proposed_piece_cost_inr: number;
    saving_per_vehicle_inr: number;
    applicable_annual_volume: number;
    gross_annual_opportunity_inr: number;
    net_opportunity_inr: number;
    provenance_hash: string;
  };
  review_record?: ReviewRecord;
  review_actions_history: ReviewAction[];
}

// ==========================================
// 7. Hardware & System Status Types
// ==========================================

export interface HardwareProfile {
  cpu_model: string;
  cpu_cores: number;
  cpu_threads: number;
  total_ram_gb: number;
  available_ram_gb: number;
  gpu_name?: string;
  total_vram_gb: number;
  available_vram_gb: number;
  runtime_tier: 'TIER_1_LAPTOP_POC' | 'TIER_2_WORKSTATION' | 'TIER_3_ENTERPRISE';
  slm_candidate: string;
  active_model_loaded?: string;
  sequential_swapping_active: boolean;
}

export interface AuditLogEntry {
  id: string;
  user_id?: string;
  username?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  ip_address?: string;
  payload?: Record<string, any>;
  provenance_hash?: string;
  created_at: string;
}
