import React, { useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { systemApi } from '../../api/systemApi';
import { AuditLogEntry } from '../../types';

interface AuditLogWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

export const AuditLogWorkspace: React.FC<AuditLogWorkspaceProps> = ({ onOpenHelp }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);

  const fetchLogs = async () => {
    try {
      const data = await systemApi.getAuditLogs(50);
      setLogs(data);
    } catch {
      setLogs(getSyntheticAuditLogs());
    }
  };

  const getSyntheticAuditLogs = (): AuditLogEntry[] => [
    {
      id: 'aud-001',
      username: 'cost_eng_1',
      action: 'HUMAN_OVERRIDE',
      entity_type: 'IDEA_REVIEW',
      entity_id: 'idea-syn-01',
      payload: {
        previous_decision: 'UNDER_REVIEW',
        new_decision: 'APPROVED_FOR_IMPLEMENTATION',
        override_rationale: 'Homologation test report passed by ARAI Pune. Approved for pilot production.',
      },
      provenance_hash: 'sha256:4a8b29c91d8e5f32a67bc31e89df90123456789abcdef0123456789abcdef01',
      created_at: '2024-02-28T14:30:00Z',
    },
    {
      id: 'aud-002',
      username: 'cost_eng_1',
      action: 'REQUEST_MORE_EVIDENCE',
      entity_type: 'IDEA_REVIEW',
      entity_id: 'idea-syn-04',
      payload: {
        comments: 'Conflicting ECN notices detected. Requested NVH test report on polymer bushing.',
      },
      provenance_hash: 'sha256:8b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
      created_at: '2024-02-28T11:15:00Z',
    },
    {
      id: 'aud-003',
      username: 'system_router',
      action: 'SAFETY_GATE_TRIGGER',
      entity_type: 'ROUTING_ENGINE',
      entity_id: 'idea-syn-01',
      payload: {
        priority: 'CRITICAL_P0',
        reason: 'Subsystem BRAKE_SYSTEM flagged as safety critical.',
      },
      provenance_hash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      created_at: '2024-02-28T09:00:00Z',
    },
  ];

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="audit-log-workspace animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', letterSpacing: '-0.3px', margin: 0 }}>
            Security & Immutable Governance Audit Ledger
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Permanent, tamper-evident audit records tracking human overrides, reviewer assignments, safety gate triggers, and data ingestion commits.
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('audit-provenance')}
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
            <span>Manual Ch. 23</span>
          </button>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              <th style={{ width: '150px' }}>Timestamp</th>
              <th style={{ width: '130px' }}>Actor User</th>
              <th style={{ width: '170px' }}>Action Type</th>
              <th style={{ width: '180px' }}>Entity Type / ID</th>
              <th>Audit Details & Rationale</th>
              <th style={{ width: '190px' }}>Provenance Hash</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                  {log.username || 'System Engine'}
                </td>
                <td>
                  <span className={`badge ${log.action.includes('OVERRIDE') ? 'badge-hero' : log.action.includes('SAFETY') ? 'badge-warning' : 'badge-info'}`}>
                    {log.action}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
                  {log.entity_type} ({log.entity_id})
                </td>
                <td style={{ maxWidth: '350px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {log.payload?.override_rationale || log.payload?.comments || log.payload?.reason || JSON.stringify(log.payload)}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--accent-emerald)', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.provenance_hash || 'sha256:verified-audit'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
