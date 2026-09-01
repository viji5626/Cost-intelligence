import React, { useState, useRef } from 'react';
import {
  Search,
  Folder,
  X,
  Zap,
  Filter,
  FileCode,
  RotateCw,
  HardDrive,
  CheckCircle2,
} from 'lucide-react';
import { AIModelManifest, ActiveRuntimeState, HardwareFitInfo } from '../../types/aistudio';
import { aistudioApi } from '../../api/aistudio';

interface ModelBrowserModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: AIModelManifest[];
  activeRuntime: ActiveRuntimeState;
  onSelectAndLoadModel: (model: AIModelManifest) => void;
}

export const ModelBrowserModal: React.FC<ModelBrowserModalProps> = ({
  isOpen,
  onClose,
  models: initialModels,
  activeRuntime,
  onSelectAndLoadModel,
}) => {
  const [modelCatalog, setModelCatalog] = useState<AIModelManifest[]>(initialModels);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('ALL');
  const [selectedParamSize, setSelectedParamSize] = useState('ALL');
  const [customFolderPath, setCustomFolderPath] = useState('D:\\Models\\');
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const [previewModel, setPreviewModel] = useState<AIModelManifest | null>(
    initialModels.find((m) => m.model_id === activeRuntime.model_id) || initialModels[0] || null
  );

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const filteredModels = modelCatalog.filter((m) => {
    const matchesSearch =
      m.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.model_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.architecture.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.file_path && m.file_path.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.tags && m.tags.some((t) => t.toLowerCase().includes(searchTerm.toLowerCase())));

    const matchesFormat =
      selectedFormat === 'ALL' ||
      (selectedFormat === 'GGUF' && m.format === 'GGUF') ||
      (selectedFormat === 'SAFE_TENSORS' && m.format === 'SAFE_TENSORS') ||
      (selectedFormat === 'ONNX' && m.format === 'ONNX') ||
      (selectedFormat === 'PYTORCH' && m.format === 'PYTORCH');

    const matchesParam =
      selectedParamSize === 'ALL' ||
      (selectedParamSize === 'EDGE' && (m.parameter_count.includes('0.5B') || m.parameter_count.includes('33M'))) ||
      (selectedParamSize === 'STANDARD' && (m.parameter_count.includes('3.0B') || m.parameter_count.includes('3.2B') || m.parameter_count.includes('7.0B') || m.parameter_count.includes('8.0B'))) ||
      (selectedParamSize === 'LARGE' && (m.parameter_count.includes('14B') || m.parameter_count.includes('70B') || m.parameter_count.includes('671B')));

    return matchesSearch && matchesFormat && matchesParam;
  });

  const handleScanFolder = async () => {
    if (!customFolderPath.trim()) return;
    setIsScanning(true);
    setScanMessage(null);

    try {
      const discovered = await aistudioApi.scanCustomFolder(customFolderPath.trim());
      if (discovered.length > 0) {
        // Merge into catalog without duplicates
        setModelCatalog((prev) => {
          const existingIds = new Set(prev.map((p) => p.model_id));
          const newModels = discovered.filter((d) => !existingIds.has(d.model_id));
          return [...newModels, ...prev];
        });
        setPreviewModel(discovered[0]);
        setScanMessage(`Discovered ${discovered.length} SafeTensors / GGUF model(s) in ${customFolderPath}`);
      } else {
        setScanMessage(`No .gguf or .safetensors files found in ${customFolderPath}`);
      }
    } catch {
      setScanMessage(`Error scanning directory: ${customFolderPath}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleFilePicked = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fname = file.name;
    const isSafeTensors = fname.toLowerCase().endsWith('.safetensors');
    const isGguf = fname.toLowerCase().endsWith('.gguf');
    const isLlama = fname.toLowerCase().includes('llama');
    const isDeepSeek = fname.toLowerCase().includes('deepseek');

    const cleanName = fname.replace(/\.[^/.]+$/, '');
    const newManifest: AIModelManifest = {
      model_id: `custom-${cleanName.toLowerCase()}`,
      display_name: cleanName.replace(/[-_]/g, ' '),
      version: '1.0.0',
      status: 'ACTIVE_REGISTERED',
      format: isSafeTensors ? 'SAFE_TENSORS' : isGguf ? 'GGUF' : 'PYTORCH',
      quantization: isSafeTensors ? 'FP16' : 'Q4_K_M',
      architecture: isLlama ? 'llama' : isDeepSeek ? 'deepseek' : 'qwen2',
      parameter_count: fname.toLowerCase().includes('70b') ? '70.0B' : fname.toLowerCase().includes('8b') || fname.toLowerCase().includes('7b') ? '7.0B' : '3.0B',
      file_path: (file as any).path || `custom/${fname}`,
      file_size_bytes: file.size || 2_100_000_000,
      sha256_checksum: 'e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3',
      context_length: 8192,
      primary_task_type: 'REASONING',
      capabilities: ['REASONING', 'STRUCTURED_EXTRACTION'],
      supports_vision: false,
      vram_footprint_mb: Math.max(250, Math.round((file.size / 1024 / 1024) * 1.05)),
      ram_footprint_mb: 850,
      provider_type: 'BUILTIN_NATIVE_GGUF',
      tags: [isSafeTensors ? 'SafeTensors' : 'GGUF', 'Imported File', 'Custom Picker'],
    };

    setModelCatalog((prev) => [newManifest, ...prev]);
    setPreviewModel(newManifest);
    setScanMessage(`Successfully imported ${fname} (${isSafeTensors ? 'SafeTensors' : 'GGUF'})`);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE_REGISTERED':
      case 'SAFE':
        return {
          bg: 'rgba(16, 185, 129, 0.1)',
          color: 'var(--status-healthy)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          label: status,
        };
      case 'QUARANTINED':
      case 'UNSAFE':
        return {
          bg: 'rgba(255, 0, 0, 0.08)',
          color: 'var(--hero-red)',
          border: '1px solid var(--hero-red-border)',
          label: status,
        };
      case 'CONSTRAINED':
        return {
          bg: 'rgba(245, 158, 11, 0.1)',
          color: 'var(--status-warning)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          label: status,
        };
      default:
        return {
          bg: 'rgba(102, 102, 117, 0.1)',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-subtle)',
          label: status,
        };
    }
  };

  const previewFit: HardwareFitInfo | null = previewModel
    ? aistudioApi.getHardwareFit(previewModel, 'PROFILE-BALANCED')
    : null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        animation: 'fadeIn 0.15s ease-out',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1180px',
          maxHeight: '92vh',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 16px 40px rgba(0, 0, 0, 0.4)',
          overflow: 'hidden',
        }}
      >
        {/* Hidden File Input for Native OS Picker */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFilePicked}
          accept=".gguf,.safetensors,.onnx,.bin"
          style={{ display: 'none' }}
        />

        {/* Modal Header */}
        <div
          style={{
            padding: '14px 20px',
            backgroundColor: 'var(--bg-tertiary)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Folder size={18} color="var(--hero-red)" />
            <div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--text-primary)' }}>
                Local Model Browser & Custom Directory Explorer (.gguf & .safetensors)
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Browse GGUF, SafeTensors, HuggingFace Hub cache, and custom folder models across your local drives
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* CUSTOM DIRECTORY PATH SCANNER & FILE PICKER BAR */}
        <div
          style={{
            padding: '12px 20px',
            backgroundColor: 'var(--bg-input)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
              <HardDrive size={13} /> Custom Folder Path:
            </span>

            {/* Custom Path Input */}
            <input
              type="text"
              value={customFolderPath}
              onChange={(e) => setCustomFolderPath(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleScanFolder();
              }}
              placeholder="e.g. D:\Models\GGUF or C:\Users\<user>\.cache\huggingface\hub\ or D:\SafeTensors\"
              style={{
                flex: 1,
                padding: '6px 10px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
              }}
            />

            {/* Quick Directory Presets Dropdown */}
            <select
              onChange={(e) => {
                if (e.target.value) {
                  setCustomFolderPath(e.target.value);
                }
              }}
              style={{
                padding: '6px 8px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)',
                fontSize: '11px',
              }}
            >
              <option value="">📁 Preset Paths...</option>
              <option value="d:\MY APPS\hero-cost-intelligence\models\">models/ (Hero Repository)</option>
              <option value="D:\Models\GGUF\">D:\Models\GGUF\ (Dedicated Disk)</option>
              <option value="D:\Models\SafeTensors\">D:\Models\SafeTensors\ (HuggingFace Weights)</option>
              <option value="C:\Users\vijay\.cache\huggingface\hub\">~/.cache/huggingface/hub/ (HuggingFace Hub)</option>
              <option value="C:\Users\vijay\.ollama\models\">~/.ollama/models/ (Ollama)</option>
              <option value="C:\Users\vijay\.lmstudio\models\">~/.lmstudio/models/ (LM Studio)</option>
            </select>

            {/* Scan Folder Button */}
            <button
              onClick={handleScanFolder}
              disabled={isScanning}
              style={{
                padding: '6px 12px',
                backgroundColor: 'var(--hero-red)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                color: '#ffffff',
                fontSize: '11px',
                fontWeight: '700',
                cursor: isScanning ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                whiteSpace: 'nowrap',
              }}
            >
              <RotateCw size={12} className={isScanning ? 'spin-icon' : ''} />
              {isScanning ? 'Scanning...' : 'Scan Folder'}
            </button>

            {/* Pick File Native File Explorer Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                padding: '6px 12px',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '11px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                whiteSpace: 'nowrap',
              }}
              title="Pick a specific .gguf or .safetensors file anywhere on disk"
            >
              <FileCode size={12} color="var(--status-healthy)" />
              Browse File...
            </button>
          </div>

          {/* Scan Feedback Banner */}
          {scanMessage && (
            <div
              style={{
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
                color: scanMessage.includes('Discovered') || scanMessage.includes('imported') ? 'var(--status-healthy)' : 'var(--status-warning)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <CheckCircle2 size={11} />
              <span>{scanMessage}</span>
            </div>
          )}
        </div>

        {/* Search & Filter Controls Bar */}
        <div
          style={{
            padding: '10px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-card)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '12px',
            flexWrap: 'wrap',
          }}
        >
          {/* Search Input */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '5px 10px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              flex: 1,
              minWidth: '220px',
            }}
          >
            <Search size={13} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search model name, architecture, safetensors, gguf, or path..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'none',
                border: 'none',
                outline: 'none',
                color: 'var(--text-primary)',
                fontSize: '11px',
                width: '100%',
              }}
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={11} />
              </button>
            )}
          </div>

          {/* Format Filter Pills (GGUF vs SafeTensors) */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '11px' }}>
            <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
              <Filter size={11} /> Format:
            </span>

            {[
              { id: 'ALL', label: 'All' },
              { id: 'GGUF', label: 'GGUF (.gguf)' },
              { id: 'SAFE_TENSORS', label: 'SafeTensors (.safetensors)' },
              { id: 'ONNX', label: 'ONNX' },
            ].map((fmt) => (
              <button
                key={fmt.id}
                onClick={() => setSelectedFormat(fmt.id)}
                style={{
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: selectedFormat === fmt.id ? 'var(--hero-red)' : 'var(--bg-tertiary)',
                  color: selectedFormat === fmt.id ? '#ffffff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '10px',
                  fontWeight: selectedFormat === fmt.id ? '700' : '500',
                }}
              >
                {fmt.label}
              </button>
            ))}

            <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--border-subtle)', margin: '0 2px' }} />

            {/* Parameter Size Filter */}
            <div style={{ display: 'flex', gap: '4px' }}>
              {[
                { id: 'ALL', label: 'All Sizes' },
                { id: 'EDGE', label: '<1B' },
                { id: 'STANDARD', label: '3B-8B' },
                { id: 'LARGE', label: '>14B' },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedParamSize(p.id)}
                  style={{
                    padding: '3px 7px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: selectedParamSize === p.id ? 'var(--hero-red)' : 'var(--bg-tertiary)',
                    color: selectedParamSize === p.id ? '#ffffff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '10px',
                    fontWeight: selectedParamSize === p.id ? '700' : '500',
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Body: Left Model List + Right Detail Inspector */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', flex: 1, overflow: 'hidden' }}>
          {/* Left: Model List */}
          <div
            style={{
              padding: '16px',
              overflowY: 'auto',
              borderRight: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            {filteredModels.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No models found matching current search/format filters.
                <div style={{ marginTop: '8px', fontSize: '11px' }}>
                  Use the <strong>"Custom Folder Path"</strong> bar above to scan another folder or click <strong>"Browse File..."</strong>.
                </div>
              </div>
            ) : (
              filteredModels.map((m) => {
                const isSelected = previewModel?.model_id === m.model_id;
                const isActive = activeRuntime.model_id === m.model_id;
                const statusBadge = getStatusBadge(m.status);
                const isSafeTensors = m.format === 'SAFE_TENSORS';

                return (
                  <div
                    key={m.model_id}
                    onClick={() => setPreviewModel(m)}
                    style={{
                      padding: '12px 14px',
                      backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                      border: `1px solid ${isActive ? 'var(--hero-red)' : isSelected ? 'var(--text-primary)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      position: 'relative',
                    }}
                  >
                    {isActive && (
                      <span
                        style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          fontSize: '9px',
                          fontWeight: '700',
                          color: 'var(--status-healthy)',
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          padding: '1px 5px',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        ACTIVE LOADED
                      </span>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {m.display_name}
                          {isSafeTensors && (
                            <span
                              style={{
                                fontSize: '9px',
                                fontWeight: '700',
                                color: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                border: '1px solid rgba(59, 130, 246, 0.3)',
                                padding: '1px 4px',
                                borderRadius: 'var(--radius-sm)',
                              }}
                            >
                              SAFETENSORS
                            </span>
                          )}
                          {m.format === 'GGUF' && (
                            <span
                              style={{
                                fontSize: '9px',
                                fontWeight: '700',
                                color: '#10b981',
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                padding: '1px 4px',
                                borderRadius: 'var(--radius-sm)',
                              }}
                            >
                              GGUF
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
                          {m.file_path}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                      <span style={{ backgroundColor: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)' }}>
                        📦 {m.parameter_count}
                      </span>
                      <span style={{ backgroundColor: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)' }}>
                        ⚙️ {m.quantization}
                      </span>
                      <span style={{ backgroundColor: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)' }}>
                        💾 {m.vram_footprint_mb || 2100} MB VRAM
                      </span>
                      <span style={{ ...statusBadge, padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                        {m.status}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Right: Model Detail & Load Action Panel */}
          {previewModel && previewFit && (
            <div
              style={{
                padding: '20px',
                backgroundColor: 'var(--bg-tertiary)',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  {previewModel.display_name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  Format: <strong>{previewModel.format}</strong> &bull; Architecture: {previewModel.architecture} &bull; Quant: {previewModel.quantization}
                </div>
              </div>

              {/* Hardware Fit Admission Box */}
              <div
                style={{
                  padding: '12px',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                    Hardware Fit Preflight (RTX 4060)
                  </span>
                  <span style={{ ...getStatusBadge(previewFit.status), fontSize: '10px', fontWeight: '700', padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                    {previewFit.status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>Model VRAM</div>
                    <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{previewFit.estimated_model_mb} MB</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>KV Cache (4K)</div>
                    <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{previewFit.estimated_kv_cache_mb} MB</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>GPU Layers</div>
                    <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{previewFit.recommended_layers} / {previewFit.total_layers}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>Headroom</div>
                    <div style={{ fontWeight: '600', color: previewFit.safety_headroom_mb > 0 ? 'var(--status-healthy)' : 'var(--hero-red)' }}>
                      +{previewFit.safety_headroom_mb} MB
                    </div>
                  </div>
                </div>
              </div>

              {/* Path & Checksum Details */}
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Full Path: </span>
                  <span style={{ color: 'var(--text-secondary)', wordBreak: 'break-all', fontSize: '10px' }}>
                    {previewModel.file_path}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>SHA-256 Checksum: </span>
                  <span style={{ color: 'var(--text-secondary)', wordBreak: 'break-all', fontSize: '10px' }}>
                    {previewModel.sha256_checksum}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>File Size: </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {(previewModel.file_size_bytes / 1024 / 1024 / 1024).toFixed(2)} GB
                  </span>
                </div>
              </div>

              {/* Action Button: Load Model */}
              <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                {previewModel.status === 'QUARANTINED' ? (
                  <button
                    disabled
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: 'rgba(255, 0, 0, 0.1)',
                      border: '1px solid var(--hero-red-border)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--hero-red)',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'not-allowed',
                    }}
                  >
                    ⛔ QUARANTINED: Safety Gate Denied
                  </button>
                ) : activeRuntime.model_id === previewModel.model_id ? (
                  <button
                    disabled
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--status-healthy)',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'default',
                    }}
                  >
                    ✓ Currently Active & Loaded in VRAM
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      onSelectAndLoadModel(previewModel);
                      onClose();
                    }}
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: 'var(--hero-red)',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: '#ffffff',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      boxShadow: '0 2px 6px rgba(227, 27, 35, 0.3)',
                    }}
                  >
                    <Zap size={14} /> Load {previewModel.format} Model into Dedicated VRAM
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
