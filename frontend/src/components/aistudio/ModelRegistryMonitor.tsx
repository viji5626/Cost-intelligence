import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Folder,
  Zap,
} from 'lucide-react';
import { aistudioApi } from '../../api/aistudio';
import {
  AIModelManifest,
  ActiveRuntimeState,
  HardwareFitInfo,
  ProviderHealthInfo,
} from '../../types/aistudio';
import { ModelBrowserModal } from './ModelBrowserModal';

interface ModelRegistryMonitorProps {
  models: AIModelManifest[];
  providers: ProviderHealthInfo[];
  activeRuntime: ActiveRuntimeState;
  onSetActiveModel: (model: AIModelManifest) => void;
  onSelectOrchestrationTab?: () => void;
}

export const ModelRegistryMonitor: React.FC<ModelRegistryMonitorProps> = ({
  models,
  providers,
  activeRuntime,
  onSetActiveModel,
  onSelectOrchestrationTab,
}) => {
  const [selectedModel, setSelectedModel] = useState<AIModelManifest>(
    models.find((m) => m.model_id === activeRuntime.model_id) || models[0]
  );
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);
  const activeProfile = 'PROFILE-BALANCED';

  const fitInfo: HardwareFitInfo = aistudioApi.getHardwareFit(selectedModel, activeProfile);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE_REGISTERED':
      case 'HEALTHY':
        return {
          bg: 'rgba(16, 185, 129, 0.1)',
          color: 'var(--status-healthy)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          label: status,
        };
      case 'QUARANTINED':
      case 'UNSAFE':
      case 'ERROR':
        return {
          bg: 'rgba(255, 0, 0, 0.08)',
          color: 'var(--hero-red)',
          border: '1px solid var(--hero-red-border)',
          label: status,
        };
      case 'DEGRADED':
      case 'CONSTRAINED':
        return {
          bg: 'rgba(245, 158, 11, 0.1)',
          color: 'var(--status-warning)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          label: status,
        };
      case 'OFFLINE':
      default:
        return {
          bg: 'rgba(102, 102, 117, 0.1)',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-subtle)',
          label: status,
        };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top: Provider Status Cards Grid */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Decoupled Provider Adapters & Inference Endpoints
          </div>
          {onSelectOrchestrationTab && (
            <button
              onClick={onSelectOrchestrationTab}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--hero-red)',
                fontSize: '11px',
                fontWeight: '700',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Configure Orchestration Providers &rarr;
            </button>
          )}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
          {providers.map((p) => {
            const badge = getStatusBadge(p.status);
            return (
              <div
                key={p.provider_name}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--text-primary)' }}>
                    {p.provider_name}
                  </span>
                  <span style={{ ...badge, fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                    {p.status}
                  </span>
                </div>

                <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  Latency: <strong style={{ color: 'var(--text-primary)' }}>{p.latency_ms}ms</strong>
                </div>

                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {p.details.phase_note || 'Local inference engine ready.'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Middle: Model Registry Header with Browse Models Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Registered AI Model Manifests (Local GGUF & ONNX)
        </div>
        <button
          onClick={() => setIsBrowserOpen(true)}
          style={{
            padding: '4px 10px',
            backgroundColor: 'var(--hero-red)',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            color: '#ffffff',
            fontSize: '11px',
            fontWeight: '700',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            boxShadow: '0 1px 4px rgba(227, 27, 35, 0.3)',
          }}
        >
          <Folder size={12} /> Open Full Model Browser
        </button>
      </div>

      {/* Main Two-Column Model Selector & Fit Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '14px' }}>
        {/* Left: Model Cards List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {models.map((m) => {
            const isSelected = selectedModel.model_id === m.model_id;
            const isActive = activeRuntime.model_id === m.model_id;
            const badge = getStatusBadge(m.status);

            return (
              <div
                key={m.model_id}
                onClick={() => setSelectedModel(m)}
                style={{
                  padding: '10px 14px',
                  backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                  border: `1px solid ${isActive ? 'var(--hero-red)' : isSelected ? 'var(--text-primary)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--text-primary)' }}>
                      {m.display_name}
                    </span>
                    {isActive && (
                      <span style={{ fontSize: '9px', fontWeight: '700', color: 'var(--status-healthy)', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '1px 4px', borderRadius: 'var(--radius-sm)' }}>
                        LOADED
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {m.parameter_count} &bull; {m.quantization} &bull; {m.format}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ ...badge, fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                    {badge.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Selected Model Hardware Fit & Load Action */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                {selectedModel.display_name}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Architecture: {selectedModel.architecture} &bull; Ctx: {selectedModel.context_length}
              </div>
            </div>

            <span style={{ ...getStatusBadge(fitInfo.status), fontSize: '10px', fontWeight: '700', padding: '2px 7px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
              Hardware {fitInfo.status}
            </span>
          </div>

          {/* Hardware Fit Numbers */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
              <span className="kv-key">Model Weights</span>
              <span className="kv-val">{fitInfo.estimated_model_mb} MB</span>
            </div>

            <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
              <span className="kv-key">KV Cache (4K Ctx)</span>
              <span className="kv-val">{fitInfo.estimated_kv_cache_mb} MB</span>
            </div>

            <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
              <span className="kv-key">GPU Offload</span>
              <span className="kv-val">{fitInfo.recommended_layers} / {fitInfo.total_layers} layers</span>
            </div>

            <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
              <span className="kv-key">VRAM Headroom</span>
              <span className="kv-val" style={{ color: fitInfo.safety_headroom_mb > 0 ? 'var(--status-healthy)' : 'var(--hero-red)' }}>
                {fitInfo.safety_headroom_mb > 0 ? `+${fitInfo.safety_headroom_mb} MB` : `${fitInfo.safety_headroom_mb} MB`}
              </span>
            </div>
          </div>

          {/* Admission Checklist */}
          <div style={{ padding: '10px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', fontSize: '11px' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Routing Admission Explanation
            </div>
            <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--status-healthy)' }}>
                <CheckCircle2 size={12} />
                <span>Task capability compatible ({selectedModel.primary_task_type})</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: selectedModel.status === 'ACTIVE_REGISTERED' ? 'var(--status-healthy)' : 'var(--hero-red)' }}>
                {selectedModel.status === 'ACTIVE_REGISTERED' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                <span>Status: {selectedModel.status}</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: fitInfo.status === 'SAFE' ? 'var(--status-healthy)' : 'var(--hero-red)' }}>
                {fitInfo.status === 'SAFE' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                <span>Hardware admission: {fitInfo.status}</span>
              </li>
            </ul>
          </div>

          {/* Load Model Action Button */}
          <div style={{ marginTop: 'auto', paddingTop: '8px' }}>
            {selectedModel.status === 'QUARANTINED' ? (
              <button
                disabled
                style={{
                  width: '100%',
                  padding: '9px',
                  backgroundColor: 'rgba(255, 0, 0, 0.1)',
                  border: '1px solid var(--hero-red-border)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--hero-red)',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'not-allowed',
                }}
              >
                ⛔ QUARANTINED: Safety Gate Denied
              </button>
            ) : activeRuntime.model_id === selectedModel.model_id ? (
              <button
                disabled
                style={{
                  width: '100%',
                  padding: '9px',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--status-healthy)',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'default',
                }}
              >
                ✓ Active Model Loaded in Dedicated VRAM
              </button>
            ) : (
              <button
                onClick={() => onSetActiveModel(selectedModel)}
                style={{
                  width: '100%',
                  padding: '9px',
                  backgroundColor: 'var(--hero-red)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 6px rgba(227, 27, 35, 0.3)',
                }}
              >
                <Zap size={13} /> Load Model into Dedicated VRAM
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Model Browser Modal */}
      <ModelBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        models={models}
        activeRuntime={activeRuntime}
        onSelectAndLoadModel={(m) => {
          setSelectedModel(m);
          onSetActiveModel(m);
        }}
      />
    </div>
  );
};
