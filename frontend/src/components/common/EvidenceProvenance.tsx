import React, { useState } from 'react';
import { ShieldCheck, Hash, X } from 'lucide-react';

interface EvidenceProvenanceProps {
  provenanceHash: string;
  sourceAuthority?: string;
  timestamp?: string;
  modelContext?: string;
}

export const EvidenceProvenance: React.FC<EvidenceProvenanceProps> = ({
  provenanceHash,
  sourceAuthority = 'Level 1 Master Authority',
  timestamp = new Date().toISOString(),
  modelContext = 'Deterministic Rule & Arithmetic Validation Engine',
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ display: 'inline-block', position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn-secondary"
        style={{
          fontSize: '11px',
          padding: '3px 8px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--white)',
          borderColor: 'var(--border-strong)',
          background: 'var(--bg-tertiary)',
        }}
        title="Inspect Cryptographic Lineage & Authority"
      >
        <Hash size={11} color="var(--hero-red)" />
        <span>sha256:{provenanceHash.slice(7, 15)}...</span>
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            zIndex: 100,
            right: 0,
            marginTop: '6px',
            width: '320px',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.7)',
            padding: '12px',
            fontSize: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px' }}>
            <span style={{ fontWeight: '700', color: 'var(--white)', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldCheck size={13} color="var(--hero-red)" />
              Evidence Provenance Lineage
            </span>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
            >
              <X size={13} />
            </button>
          </div>

          <div style={{ marginBottom: '6px' }}>
            <span className="kv-key" style={{ display: 'block', fontSize: '10px' }}>Cryptographic Hash</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--white)', wordBreak: 'break-all' }}>
              {provenanceHash}
            </span>
          </div>

          <div style={{ marginBottom: '6px' }}>
            <span className="kv-key" style={{ display: 'block', fontSize: '10px' }}>Data Authority Level</span>
            <span style={{ color: 'var(--white)', fontWeight: '600' }}>{sourceAuthority}</span>
          </div>

          <div style={{ marginBottom: '6px' }}>
            <span className="kv-key" style={{ display: 'block', fontSize: '10px' }}>Validation Timestamp</span>
            <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{timestamp}</span>
          </div>

          <div>
            <span className="kv-key" style={{ display: 'block', fontSize: '10px' }}>Execution Engine</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{modelContext}</span>
          </div>
        </div>
      )}
    </div>
  );
};
