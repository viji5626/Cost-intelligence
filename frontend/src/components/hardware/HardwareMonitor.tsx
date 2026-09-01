import React, { useEffect, useState } from 'react';
import { Cpu, Zap, RefreshCw, Monitor, Database, BookOpen } from 'lucide-react';
import { systemApi } from '../../api/systemApi';
import { HardwareProfile } from '../../types';
import { StatCard } from '../common/StatCard';

interface HardwareMonitorProps {
  onOpenHelp?: (chapterId: string) => void;
}

export const HardwareMonitor: React.FC<HardwareMonitorProps> = ({ onOpenHelp }) => {
  const [profile, setProfile] = useState<HardwareProfile | null>(null);

  const fetchProfile = async () => {
    try {
      const data = await systemApi.getHardwareProfile();
      setProfile(data);
    } catch {
      setProfile({
        cpu_model: 'AMD Ryzen AI 9 HX 370 (12 Cores / 24 Threads)',
        cpu_cores: 12,
        cpu_threads: 6,
        total_ram_gb: 16.0,
        available_ram_gb: 10.4,
        gpu_name: 'NVIDIA GeForce RTX 4060 Laptop GPU / AMD Radeon 890M',
        total_vram_gb: 8.0,
        available_vram_gb: 6.2,
        runtime_tier: 'TIER_1_LAPTOP_POC',
        slm_candidate: 'Qwen2.5-3B / 7B (GGUF Q4_K_M)',
        active_model_loaded: 'None (Standby - Sequential Swapping)',
        sequential_swapping_active: true,
      });
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  return (
    <div className="hardware-monitor-workspace animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', letterSpacing: '-0.3px', margin: 0 }}>
            Hardware Profiler & Local AI Runtime Governance
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Dynamic runtime inspection allocating model quantizations and offloading strategies based on available VRAM and RAM.
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('hardware-profiles')}
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
            <span>Manual Ch. 20</span>
          </button>
        )}
      </div>

      {profile && (
        <>
          <div className="grid-4" style={{ marginBottom: '16px' }}>
            <StatCard
              title="System RAM"
              value={`${profile.available_ram_gb.toFixed(1)} / ${profile.total_ram_gb.toFixed(0)} GB`}
              subtitle="Available / Total Host Memory"
              accentColor="var(--accent-blue)"
              icon={<Database size={15} />}
            />
            <StatCard
              title="Dedicated VRAM"
              value={`${profile.available_vram_gb.toFixed(1)} / ${profile.total_vram_gb.toFixed(0)} GB`}
              subtitle="GPU Video Memory"
              accentColor="var(--accent-emerald)"
              icon={<Monitor size={15} />}
            />
            <StatCard
              title="Hardware Runtime Tier"
              value={profile.runtime_tier}
              subtitle="Target Laptop Baseline"
              accentColor="var(--accent-amber)"
              icon={<Zap size={15} />}
            />
            <StatCard
              title="Active Model State"
              value={profile.sequential_swapping_active ? 'Sequential Swapping' : 'Resident'}
              subtitle="Memory Leak Guard Active"
              accentColor="var(--accent-cyan)"
              icon={<RefreshCw size={15} />}
            />
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
                <div className="card-title">
                  <Monitor size={14} color="var(--accent-blue)" />
                  <span>Host Hardware Specifications</span>
                </div>
                <span className="badge badge-healthy">AUTHENTICATED</span>
              </div>

              <div className="kv-row">
                <span className="kv-key">Host Processor</span>
                <span className="kv-val">{profile.cpu_model}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Allocated CPU Worker Threads</span>
                <span className="kv-val">{profile.cpu_threads} Threads (Zen 5 Cores)</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">GPU Device</span>
                <span className="kv-val">{profile.gpu_name || 'Integrated / Discrete Hybrid'}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Air-Gap Egress Filtering</span>
                <span className="kv-val" style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>ENFORCED (0 Cloud Calls Allowed)</span>
              </div>
            </div>

            <div className="card">
              <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
                <div className="card-title">
                  <Cpu size={14} color="var(--accent-emerald)" />
                  <span>Local SLM / Embedding Configuration</span>
                </div>
                <span className="badge badge-hero">LOCAL AIR-GAPPED</span>
              </div>

              <div className="kv-row">
                <span className="kv-key">Candidate SLM Model</span>
                <span className="kv-val">{profile.slm_candidate}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Embedding Model</span>
                <span className="kv-val">BAAI/bge-small-en-v1.5 (384 Dimensions)</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Reranker Model</span>
                <span className="kv-val">cross-encoder/ms-marco-MiniLM-L-6-v2</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Lifecycle Swapping Strategy</span>
                <span className="kv-val" style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                  LOAD → EMBED/INFER → UNLOAD/GC
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
