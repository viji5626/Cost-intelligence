import React, { useState } from 'react';
import { Cpu, ShieldCheck, Zap, Folder, Server, Globe, Boxes, Activity } from 'lucide-react';
import { ActiveRuntimeState, AIModelManifest, ProviderType } from '../../types/aistudio';
import { ModelLoadingBar } from './ModelLoadingBar';
import { ModelBrowserModal } from './ModelBrowserModal';

interface ActiveRuntimeBarProps {
  runtime: ActiveRuntimeState;
  models?: AIModelManifest[];
  onSelectModelTab?: () => void;
  onOpenModelBrowser?: () => void;
  onSelectAndLoadModel?: (model: AIModelManifest) => void;
  onSelectOrchestrationTab?: () => void;
}

export const ActiveRuntimeBar: React.FC<ActiveRuntimeBarProps> = ({
  runtime,
  models = [],
  onSelectModelTab,
  onOpenModelBrowser,
  onSelectAndLoadModel,
  onSelectOrchestrationTab,
}) => {
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);

  const getProviderIcon = (type: ProviderType) => {
    switch (type) {
      case 'BUILTIN_NATIVE_GGUF':
        return <Zap size={13} color="var(--hero-red)" />;
      case 'OLLAMA':
        return <Server size={13} color="#10b981" />;
      case 'LM_STUDIO':
        return <Cpu size={13} color="#3b82f6" />;
      case 'NVIDIA_NIM':
        return <Boxes size={13} color="#76b900" />;
      case 'OPENAI_COMPATIBLE':
      default:
        return <Globe size={13} color="#8b5cf6" />;
    }
  };

  const handleOpenBrowser = () => {
    if (onOpenModelBrowser) {
      onOpenModelBrowser();
    } else {
      setIsBrowserOpen(true);
    }
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      {/* Model Loading Bar (Visible during and right after load) */}
      {runtime.loading_progress && (
        <ModelLoadingBar progress={runtime.loading_progress} />
      )}

      {/* Active Runtime Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          backgroundColor: 'var(--bg-tertiary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        {/* Left: Active Provider, Model, & Browse Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Provider Selection */}
          <div
            onClick={onSelectOrchestrationTab}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: onSelectOrchestrationTab ? 'pointer' : 'default',
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
            }}
            title="Click to configure AI Orchestration Providers"
          >
            {getProviderIcon(runtime.provider_type)}
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              Provider:
            </span>
            <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
              {runtime.provider}
            </span>
          </div>

          {/* Active Model & Browse Trigger Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              Active Model:
            </span>
            <span
              onClick={onSelectModelTab}
              style={{
                fontWeight: '700',
                color: 'var(--text-primary)',
                cursor: onSelectModelTab ? 'pointer' : 'default',
                textDecoration: onSelectModelTab ? 'underline' : 'none',
              }}
            >
              {runtime.model_name || runtime.model_id}
            </span>
            <span
              style={{
                color: 'var(--text-muted)',
                fontSize: '10px',
                backgroundColor: 'var(--bg-card)',
                padding: '1px 5px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
              title={runtime.model_hash}
            >
              {runtime.model_hash ? `${runtime.model_hash.slice(0, 10)}...` : 'GGUF'}
            </span>

            {/* Browse Models Button */}
            <button
              onClick={handleOpenBrowser}
              style={{
                padding: '3px 8px',
                backgroundColor: 'var(--hero-red)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                color: '#ffffff',
                fontSize: '10px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                boxShadow: '0 1px 3px rgba(227, 27, 35, 0.25)',
              }}
            >
              <Folder size={11} /> Browse Models
            </button>
          </div>

          {/* Profile & Context */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              Profile:
            </span>
            <span style={{ color: 'var(--status-info)', fontWeight: '600' }}>
              {runtime.runtime_profile}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              Ctx:
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {runtime.context_length}
            </span>
          </div>

          {/* GPU Offload, VRAM, and RAM */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={12} color="var(--text-muted)" />
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              GPU:
            </span>
            <span style={{ color: runtime.provider_type === 'BUILTIN_NATIVE_GGUF' ? 'var(--text-secondary)' : 'var(--text-muted)', fontSize: '10px' }}>
              {runtime.provider_type === 'BUILTIN_NATIVE_GGUF'
                ? `${runtime.gpu_layers}/${runtime.total_gpu_layers} layers`
                : 'NOT EXPOSED BY PROVIDER'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              VRAM:
            </span>
            <span style={{ color: runtime.provider_type === 'BUILTIN_NATIVE_GGUF' ? 'var(--status-healthy)' : 'var(--text-muted)', fontWeight: '600', fontSize: '10px' }}>
              {runtime.provider_type === 'BUILTIN_NATIVE_GGUF' ? `${runtime.vram_used_mb} MB` : 'NOT EXPOSED BY PROVIDER'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              RAM:
            </span>
            <span style={{ color: runtime.provider_type === 'BUILTIN_NATIVE_GGUF' ? 'var(--text-secondary)' : 'var(--text-muted)', fontWeight: '600', fontSize: '10px' }}>
              {runtime.provider_type === 'BUILTIN_NATIVE_GGUF' ? `${runtime.ram_used_mb} MB` : 'NOT EXPOSED BY PROVIDER'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>
              Status:
            </span>
            <span
              style={{
                fontSize: '9px',
                fontWeight: '700',
                padding: '1px 5px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: runtime.status === 'READY' || runtime.status === 'ACTIVE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                color: runtime.status === 'READY' || runtime.status === 'ACTIVE' ? 'var(--status-healthy)' : 'var(--status-warning)',
                border: `1px solid ${runtime.status === 'READY' || runtime.status === 'ACTIVE' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              }}
            >
              {runtime.status}
            </span>
          </div>
        </div>

        {/* Right: LM Studio Live Telemetry Badge (Speed & TTFT) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {runtime.tokens_per_sec !== undefined && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '2px 7px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--status-healthy)',
                fontWeight: '700',
              }}
              title="Live Token Generation Speed (LM Studio Telemetry)"
            >
              <Activity size={12} />
              <span>{runtime.tokens_per_sec.toFixed(1)} tok/s</span>
            </div>
          )}

          {runtime.ttft_ms !== undefined && (
            <div
              style={{
                fontSize: '10px',
                color: 'var(--text-muted)',
              }}
              title="Time to First Token"
            >
              TTFT: <strong style={{ color: 'var(--text-primary)' }}>{runtime.ttft_ms.toFixed(1)}ms</strong>
            </div>
          )}

          {runtime.grounding_score !== undefined && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--status-healthy)',
                fontWeight: '600',
              }}
              title="Canonical Grounding Verification"
            >
              <ShieldCheck size={13} />
              <span>{(runtime.grounding_score * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      </div>

      {/* Model Browser Modal (if triggered directly) */}
      <ModelBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        models={models}
        activeRuntime={runtime}
        onSelectAndLoadModel={(m) => {
          if (onSelectAndLoadModel) onSelectAndLoadModel(m);
          setIsBrowserOpen(false);
        }}
      />
    </div>
  );
};
