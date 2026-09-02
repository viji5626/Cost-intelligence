import React, { useEffect, useState } from 'react';
import { BookOpen, ShieldCheck, Download, AlertTriangle, Search, RefreshCw } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { fetchAuditLogs, verifyAuditIntegrity, AuditLogItem, IntegrityVerificationResult } from '../../api/auditApi';

interface AuditLogWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

export const AuditLogWorkspace: React.FC<AuditLogWorkspaceProps> = ({ onOpenHelp }) => {
  const { token } = useAuth();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [integrity, setIntegrity] = useState<IntegrityVerificationResult | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<AuditLogItem | null>(null);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await fetchAuditLogs(token, { search: searchTerm, pageSize: 100 });
      setLogs(data.events || []);

      const integ = await verifyAuditIntegrity(token);
      setIntegrity(integ);
    } catch (err) {
      console.warn('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token, searchTerm]);

  const handleExport = (format: 'csv' | 'xlsx' | 'pdf' | 'html') => {
    if (!token) return;
    window.open(`/api/v1/audit/export/${format}?token=${encodeURIComponent(token)}`, '_blank');
  };

  return (
    <div className="audit-log-workspace p-6 max-w-7xl mx-auto space-y-6 animate-fade-in text-slate-100">
      {/* Header */}
      <div className="flex justify-between items-start flex-wrap gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-xl font-bold text-slate-100">
              Authoritative Tamper-Evident Audit Ledger
            </h1>
            {integrity && (
              <span
                className={`flex items-center space-x-1.5 px-2.5 py-0.5 rounded text-xs font-semibold border ${
                  integrity.is_valid
                    ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60'
                    : 'bg-red-950/80 text-red-300 border-red-700/60'
                }`}
              >
                {integrity.is_valid ? <ShieldCheck size={13} /> : <AlertTriangle size={13} />}
                <span>SHA-256 HASH CHAIN: {integrity.chain_status}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Layer 1 cryptographic audit trail recording all human overrides, authentication events, AI actions, and dataset commits.
          </p>
        </div>

        {/* 4 Export Buttons */}
        <div className="flex items-center space-x-2 flex-wrap">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs transition-colors"
          >
            <Download size={12} />
            <span>CSV</span>
          </button>
          <button
            onClick={() => handleExport('xlsx')}
            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs transition-colors"
          >
            <Download size={12} />
            <span>Excel (.xlsx)</span>
          </button>
          <button
            onClick={() => handleExport('pdf')}
            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs transition-colors"
          >
            <Download size={12} />
            <span>PDF</span>
          </button>
          <button
            onClick={() => handleExport('html')}
            className="flex items-center space-x-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg text-xs shadow transition-colors"
          >
            <Download size={12} />
            <span>Offline HTML</span>
          </button>
          {onOpenHelp && (
            <button
              onClick={() => onOpenHelp('audit-provenance')}
              className="flex items-center space-x-1 px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-slate-400 rounded-lg text-xs hover:text-slate-200"
            >
              <BookOpen size={12} />
              <span>Ch. 23</span>
            </button>
          )}
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center space-x-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search by action, user, entity ID, or hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-red-500"
          />
        </div>
        <button
          onClick={loadData}
          className="p-2 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 text-slate-400"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Audit Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 uppercase font-semibold text-[11px] border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Seq</th>
              <th className="px-4 py-3">Timestamp (UTC)</th>
              <th className="px-4 py-3">User & Role</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity Target</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">SHA-256 Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">Loading audit trail...</td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">No audit events found.</td>
              </tr>
            ) : (
              logs.map((ev) => (
                <tr
                  key={ev.id}
                  onClick={() => setSelectedEvent(ev)}
                  className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-400">{ev.sequence_number || '—'}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {ev.timestamp ? ev.timestamp.replace('T', ' ').substring(0, 19) : ''}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-semibold text-slate-100">{ev.username}</span>
                    <span className="ml-1.5 px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-400">
                      {ev.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium text-amber-400">{ev.action}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {ev.entity_type} {ev.entity_id ? `(${ev.entity_id})` : ''}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 text-[10px]">
                      {ev.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-sky-400">
                    {ev.event_hash ? ev.event_hash.substring(0, 16) + '...' : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
          onClick={() => setSelectedEvent(null)}
        >
          <div
            className="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-2xl text-slate-100 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start border-b border-slate-800 pb-3 mb-4">
              <div>
                <h3 className="text-base font-bold text-red-400">
                  Event #{selectedEvent.sequence_number}: {selectedEvent.action}
                </h3>
                <div className="text-xs text-slate-400 mt-0.5">
                  {selectedEvent.timestamp} • {selectedEvent.username} ({selectedEvent.role})
                </div>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded border border-slate-800">
                <div><b>Entity:</b> {selectedEvent.entity_type} ({selectedEvent.entity_id || 'N/A'})</div>
                <div><b>Status:</b> {selectedEvent.status}</div>
                <div><b>Department:</b> {selectedEvent.department || 'N/A'}</div>
                <div><b>Plant Scope:</b> {selectedEvent.scope || 'N/A'}</div>
                <div><b>Client IP:</b> {selectedEvent.client_ip || 'N/A'}</div>
                <div><b>Session ID:</b> {selectedEvent.session_id || 'N/A'}</div>
              </div>

              <div>
                <div className="font-semibold text-slate-300 mb-1">Cryptographic Provenance</div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] space-y-1">
                  <div className="text-slate-400">Prev Hash: <span className="text-slate-200">{selectedEvent.previous_event_hash}</span></div>
                  <div className="text-slate-400">Event Hash: <span className="text-sky-300">{selectedEvent.event_hash}</span></div>
                </div>
              </div>

              <div>
                <div className="font-semibold text-slate-300 mb-1">Payload JSON</div>
                <pre className="bg-slate-950 p-3 rounded border border-slate-800 text-emerald-300 font-mono text-[11px] overflow-x-auto max-h-48">
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
