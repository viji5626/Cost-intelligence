/**
 * TypeScript Definitions for AI Studio UI Workspace (Phase AI-16 & Extensions)
 * Industrial engineering workstation specifications for local AI runtime.
 */

export type AIStudioTab = 'playground' | 'vision' | 'evidence' | 'models' | 'orchestration';

export type CapabilityStatus = 'REAL_OCR' | 'REAL_VISION_MODEL' | 'CONTRACT_ONLY' | 'NOT_VERIFIED';

export type ProviderType =
  | 'BUILTIN_NATIVE_GGUF'
  | 'OLLAMA'
  | 'LM_STUDIO'
  | 'NVIDIA_NIM'
  | 'OPENAI_COMPATIBLE'
  | 'LOCAL_VISION_OCR'
  | 'MOCK_SIMULATION';

export type ModelLifecycleState = 'UNLOADED' | 'LOADING' | 'READY' | 'ACTIVE' | 'ERROR';

export interface AIModelManifest {
  model_id: string;
  display_name: string;
  version: string;
  status: 'ACTIVE_REGISTERED' | 'QUARANTINED' | 'REJECTED_INVALID' | 'REJECTED_INCOMPATIBLE' | 'ARCHIVED';
  format: 'GGUF' | 'ONNX' | 'SAFE_TENSORS' | 'PYTORCH';
  quantization: string;
  architecture: string;
  parameter_count: string;
  file_path: string;
  file_size_bytes: number;
  sha256_checksum: string;
  context_length: number;
  primary_task_type: string;
  capabilities: string[];
  supports_vision?: boolean;
  embedding_dimension?: number;
  quarantine_notes?: string;
  vram_footprint_mb?: number;
  ram_footprint_mb?: number;
  provider_type?: ProviderType;
  tags?: string[];
}

export interface OrchestrationProviderConfig {
  provider_id: ProviderType;
  display_name: string;
  icon_name: string;
  description: string;
  endpoint_url: string;
  api_key?: string;
  status: 'ONLINE' | 'STANDBY' | 'OFFLINE' | 'CONNECTING' | 'ERROR';
  latency_ms: number;
  supported_formats: string[];
  streaming_supported: boolean;
  default_models: string[];
  is_builtin?: boolean;
  telemetry_exposed?: boolean;
  fallback_policy?: 'FALLBACK_DISABLED' | 'FALLBACK_BUILTIN_LOCAL' | 'FALLBACK_ALLOWED_LIST';
  model_count?: number;
}

export interface ModelLoadingProgress {
  is_loading: boolean;
  stage_index: number;
  total_stages: number;
  stage_title: string;
  percentage: number;
  elapsed_seconds: number;
  target_model_id: string;
  target_model_name: string;
}

export interface LMStudioTelemetry {
  tokens_per_sec: number;
  ttft_ms: number;
  total_latency_seconds: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  finish_reason: string;
  gpu_vram_used_mb: number;
  gpu_vram_total_mb: number;
  gpu_layers_offloaded: number;
  gpu_total_layers: number;
  gpu_compute_device: string;
  audit_hash: string;
  grounding_score: number;
  is_streaming: boolean;
}

export interface ProviderHealthInfo {
  provider_name: string;
  provider_type: ProviderType;
  status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'ERROR';
  is_live_verified: boolean;
  latency_ms: number;
  active_model?: string;
  available_models?: string[];
  details: {
    adapter_installed: boolean;
    backend_available: boolean;
    model_available: boolean;
    runtime_healthy: boolean;
    active_ocr_engine?: string;
    pdf_text_backend_available?: boolean;
    tesseract_ocr_backend_available?: boolean;
    phase_note?: string;
    endpoint_url?: string;
  };
}

export interface ActiveRuntimeState {
  provider: string;
  provider_type: ProviderType;
  model_id: string;
  model_name: string;
  model_hash: string;
  runtime_profile: string;
  context_length: number;
  gpu_layers: number;
  total_gpu_layers: number;
  vram_used_mb: number;
  ram_used_mb: number;
  status: ModelLifecycleState;
  ttft_ms?: number;
  tokens_per_sec?: number;
  last_task_id?: string;
  last_audit_hash?: string;
  grounding_score?: number;
  loading_progress?: ModelLoadingProgress;
  live_telemetry?: LMStudioTelemetry;
}

export interface HardwareFitInfo {
  status: 'SAFE' | 'CONSTRAINED' | 'UNSAFE';
  usable_vram_mb: number;
  usable_ram_mb: number;
  estimated_model_mb: number;
  estimated_kv_cache_mb: number;
  estimated_peak_mb: number;
  recommended_layers: number;
  total_layers: number;
  recommended_context: number;
  runtime_profile: string;
  safety_headroom_mb: number;
  reasons: string[];
}

export interface DrawingTitleBlockData {
  part_number?: string;
  drawing_number?: string;
  revision?: string;
  material_grade?: string;
  surface_treatment?: string;
  drawn_by?: string;
  approved_by?: string;
  date?: string;
  general_tolerance?: string;
  extraction_confidence: number;
}

export interface DrawingExtractionResult {
  title_block: DrawingTitleBlockData;
  dimensions: string[];
  notes: string[];
  weld_symbols: string[];
  tolerance_callouts: string[];
  raw_text: string;
  ocr_confidence: number;
  extraction_confidence: number;
  capability_classification: Record<string, CapabilityStatus>;
}

export interface EvidenceCitationItem {
  citation_id: string;
  source_document: string;
  document_type: string;
  authority_level: 'CANONICAL_MASTER' | 'CONTROLLED_ECN' | 'PLANT_ACTUAL' | 'UNVERIFIED';
  dense_similarity: number;
  reranker_score: number;
  rrf_rank: number;
  temporal_validity: string;
  grounding_weight: number;
  snippet_text: string;
  applicable_models: string[];
  applicable_plants: string[];
}
