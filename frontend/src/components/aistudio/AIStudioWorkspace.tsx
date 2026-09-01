import React, { useState, useEffect } from 'react';
import {
  Terminal,
  FileText,
  Search,
  Cpu,
  Server,
  BookOpen,
} from 'lucide-react';
import { aistudioApi } from '../../api/aistudio';
import {
  AIModelManifest,
  AIStudioTab,
  ActiveRuntimeState,
  ProviderHealthInfo,
  ProviderType,
} from '../../types/aistudio';
import { ActiveRuntimeBar } from './ActiveRuntimeBar';
import { ChatPlayground } from './ChatPlayground';
import { EvidenceExplorer } from './EvidenceExplorer';
import { ModelRegistryMonitor } from './ModelRegistryMonitor';
import { OrchestrationSelector } from './OrchestrationSelector';
import { VisualDocumentInspector } from './VisualDocumentInspector';
import { ModelBrowserModal } from './ModelBrowserModal';

interface AIStudioWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

export const AIStudioWorkspace: React.FC<AIStudioWorkspaceProps> = ({ onOpenHelp }) => {
  const [activeTab, setActiveTab] = useState<AIStudioTab>('playground');
  const [models, setModels] = useState<AIModelManifest[]>([]);
  const [providers, setProviders] = useState<ProviderHealthInfo[]>([]);
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);

  const [activeRuntime, setActiveRuntime] = useState<ActiveRuntimeState>({
    provider: '⚡ Native GGUF / Llama Engine',
    provider_type: 'BUILTIN_NATIVE_GGUF',
    model_id: 'qwen2.5-3b-instruct',
    model_name: 'Qwen 2.5 3B Instruct',
    model_hash: 'a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9',
    runtime_profile: 'PROFILE-BALANCED',
    context_length: 4096,
    gpu_layers: 33,
    total_gpu_layers: 33,
    vram_used_mb: 2310,
    ram_used_mb: 850,
    status: 'READY',
    ttft_ms: 119.5,
    tokens_per_sec: 91.4,
    grounding_score: 0.98,
  });

  useEffect(() => {
    const fetchData = async () => {
      const [fetchedModels, fetchedProviders] = await Promise.all([
        aistudioApi.getModels(),
        aistudioApi.getProviderHealth(),
      ]);
      setModels(fetchedModels);
      setProviders(fetchedProviders);
    };
    fetchData();
  }, []);

  const handleUpdateRuntime = (runtimeUpdates: Partial<ActiveRuntimeState>) => {
    setActiveRuntime((prev) => ({
      ...prev,
      ...runtimeUpdates,
    }));
  };

  const handleSelectAndLoadModel = async (model: AIModelManifest) => {
    if (model.status === 'QUARANTINED') {
      alert(`Model ${model.display_name} is QUARANTINED by Hero Safety Gate.`);
      return;
    }

    // Trigger progressive model loading with live stage tracking
    await aistudioApi.loadModelWithProgress(model, (progress) => {
      setActiveRuntime((prev) => ({
        ...prev,
        status: progress.is_loading ? 'LOADING' : 'READY',
        loading_progress: progress,
        model_id: model.model_id,
        model_name: model.display_name,
        model_hash: model.sha256_checksum,
        context_length: model.context_length,
        vram_used_mb: model.vram_footprint_mb || 2100,
      }));
    });
  };

  const handleSelectProvider = async (provType: ProviderType) => {
    const provConfigs = await aistudioApi.getOrchestrationProviders();
    const config = provConfigs.find((p) => p.provider_id === provType);
    if (config) {
      setActiveRuntime((prev) => ({
        ...prev,
        provider: config.display_name,
        provider_type: provType,
      }));
    }
  };

  return (
    <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Top Active Runtime Status Bar with Browse & Loading Bar */}
      <ActiveRuntimeBar
        runtime={activeRuntime}
        models={models}
        onSelectModelTab={() => setActiveTab('models')}
        onOpenModelBrowser={() => setIsBrowserOpen(true)}
        onSelectAndLoadModel={handleSelectAndLoadModel}
        onSelectOrchestrationTab={() => setActiveTab('orchestration')}
      />

      {/* Primary Workspace Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '0',
        }}
      >
        <button
          onClick={() => setActiveTab('playground')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeTab === 'playground' ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-subtle)',
            borderBottom: activeTab === 'playground' ? '1px solid var(--bg-card)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
            color: activeTab === 'playground' ? 'var(--hero-red)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'playground' ? '700' : '500',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '-1px',
            zIndex: activeTab === 'playground' ? 2 : 1,
          }}
        >
          <Terminal size={14} /> Inference & Chat Playground
        </button>

        <button
          onClick={() => setActiveTab('orchestration')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeTab === 'orchestration' ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-subtle)',
            borderBottom: activeTab === 'orchestration' ? '1px solid var(--bg-card)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
            color: activeTab === 'orchestration' ? 'var(--hero-red)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'orchestration' ? '700' : '500',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '-1px',
            zIndex: activeTab === 'orchestration' ? 2 : 1,
          }}
        >
          <Server size={14} /> AI Orchestration & Sidecars
        </button>

        <button
          onClick={() => setActiveTab('models')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeTab === 'models' ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-subtle)',
            borderBottom: activeTab === 'models' ? '1px solid var(--bg-card)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
            color: activeTab === 'models' ? 'var(--hero-red)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'models' ? '700' : '500',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '-1px',
            zIndex: activeTab === 'models' ? 2 : 1,
          }}
        >
          <Cpu size={14} /> Model Registry & Hardware Monitor
        </button>

        <button
          onClick={() => setActiveTab('vision')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeTab === 'vision' ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-subtle)',
            borderBottom: activeTab === 'vision' ? '1px solid var(--bg-card)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
            color: activeTab === 'vision' ? 'var(--hero-red)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'vision' ? '700' : '500',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '-1px',
            zIndex: activeTab === 'vision' ? 2 : 1,
          }}
        >
          <FileText size={14} /> Visual Document & CAD Inspector
        </button>

        <button
          onClick={() => setActiveTab('evidence')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeTab === 'evidence' ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-subtle)',
            borderBottom: activeTab === 'evidence' ? '1px solid var(--bg-card)' : '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
            color: activeTab === 'evidence' ? 'var(--hero-red)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'evidence' ? '700' : '500',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '-1px',
            zIndex: activeTab === 'evidence' ? 2 : 1,
          }}
        >
          <Search size={14} /> Evidence Explorer & Grounding
        </button>

        {onOpenHelp && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', paddingBottom: '4px' }}>
            <button
              onClick={() => onOpenHelp('ai-studio-overview')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '3px 8px',
                fontSize: '11px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              <BookOpen size={11} color="var(--status-info)" />
              <span>Manual Ch. 17</span>
            </button>
          </div>
        )}
      </div>

      {/* Tab Content Display */}
      <div style={{ marginTop: '8px' }}>
        {activeTab === 'playground' && (
          <ChatPlayground
            models={models}
            activeRuntime={activeRuntime}
            onUpdateRuntime={handleUpdateRuntime}
            onSelectAndLoadModel={handleSelectAndLoadModel}
          />
        )}

        {activeTab === 'orchestration' && (
          <OrchestrationSelector
            selectedProvider={activeRuntime.provider_type}
            onSelectProvider={handleSelectProvider}
          />
        )}

        {activeTab === 'models' && (
          <ModelRegistryMonitor
            models={models}
            providers={providers}
            activeRuntime={activeRuntime}
            onSetActiveModel={handleSelectAndLoadModel}
            onSelectOrchestrationTab={() => setActiveTab('orchestration')}
          />
        )}

        {activeTab === 'vision' && <VisualDocumentInspector />}

        {activeTab === 'evidence' && <EvidenceExplorer />}
      </div>

      {/* Global Model Browser Modal */}
      <ModelBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        models={models}
        activeRuntime={activeRuntime}
        onSelectAndLoadModel={handleSelectAndLoadModel}
      />
    </div>
  );
};
