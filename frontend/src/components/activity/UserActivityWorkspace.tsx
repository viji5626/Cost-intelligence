import React, { useState, useEffect } from 'react';
import { Sparkles, Clock, Activity, Cpu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { fetchSessionTimeline, generateSessionNarration, SessionTimelineResponse, SessionNarrationResponse } from '../../api/auditApi';

export const UserActivityWorkspace: React.FC = () => {
  const { token, currentUser } = useAuth();
  const [timelineData, setTimelineData] = useState<SessionTimelineResponse | null>(null);
  const [narration, setNarration] = useState<SessionNarrationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [narrating, setNarrating] = useState(false);

  const sessionId = currentUser?.session_id || 'current-session';

  const loadTimeline = async () => {
    if (!token || !sessionId) return;
    setLoading(true);
    try {
      const data = await fetchSessionTimeline(token, sessionId);
      setTimelineData(data);
    } catch (err) {
      console.warn('Failed to load session timeline:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerNarration = async () => {
    if (!token || !sessionId) return;
    setNarrating(true);
    try {
      const narr = await generateSessionNarration(token, sessionId);
      setNarration(narr);
    } catch (err) {
      console.warn('Failed to generate narration:', err);
    } finally {
      setNarrating(false);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, [token, sessionId]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <Activity size={20} className="text-red-500" />
            <span>User Activity & Session Reconstruction</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic Layer 1 chronological workflow tracking with Layer 2 AI Executive Session Narration.
          </p>
        </div>

        <button
          onClick={handleTriggerNarration}
          disabled={narrating}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-red-950/40 transition-all disabled:opacity-50"
        >
          <Sparkles size={14} className={narrating ? 'animate-spin' : ''} />
          <span>{narrating ? 'Synthesizing Narration...' : 'Generate AI Session Narration'}</span>
        </button>
      </div>

      {/* AI Session Narration Card (Layer 2) */}
      {narration && (
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-amber-500/40 rounded-xl p-5 shadow-xl space-y-3">
          <div className="flex justify-between items-center border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2">
              <Sparkles size={16} className="text-amber-400" />
              <h3 className="text-sm font-bold text-amber-300">Executive AI Session Narration</h3>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px] text-slate-300 flex items-center space-x-1">
                <Cpu size={10} />
                <span>Model: {narration.model_id}</span>
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50 text-[10px] text-emerald-400">
                Source Events: {narration.source_event_count}
              </span>
            </div>
          </div>

          <p className="text-xs leading-relaxed text-slate-200">{narration.summary}</p>

          {narration.highlights && narration.highlights.length > 0 && (
            <div className="pt-2 border-t border-slate-800/60">
              <div className="text-[11px] font-semibold text-slate-400 mb-1.5">Key Highlights:</div>
              <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                {narration.highlights.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Layer 1 Chronological Timeline */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow space-y-4">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-200">Chronological Workflow Stream</h3>
            <p className="text-[11px] text-slate-400">Session ID: {sessionId}</p>
          </div>
          <div className="text-xs text-slate-400">
            Total Steps: <span className="font-semibold text-slate-200">{timelineData?.event_count || 0}</span>
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-center text-xs text-slate-500">Reconstructing workflow timeline...</div>
        ) : !timelineData || timelineData.timeline.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">No activity recorded for this active session.</div>
        ) : (
          <div className="relative border-l border-slate-700 ml-4 space-y-6 py-2">
            {timelineData.timeline.map((ev, idx) => (
              <div key={ev.id || idx} className="relative pl-6">
                {/* Node icon */}
                <div className="absolute -left-2.5 top-0.5 w-5 h-5 rounded-full bg-slate-900 border-2 border-red-500 flex items-center justify-center">
                  <Clock size={10} className="text-red-400" />
                </div>

                <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-3 space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-xs text-slate-100">{ev.activity_type}</span>
                    <span className="text-[10px] text-slate-500">{ev.timestamp.replace('T', ' ').substring(0, 19)}</span>
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-center space-x-3">
                    <span>Page: <b className="text-slate-300">{ev.page}</b></span>
                    {ev.plant_id && <span>Plant: <b className="text-blue-400">{ev.plant_id}</b></span>}
                    {ev.status && <span>Status: <b className="text-emerald-400">{ev.status}</b></span>}
                  </div>

                  {ev.details && Object.keys(ev.details).length > 0 && (
                    <pre className="text-[10px] font-mono text-slate-400 bg-slate-900 p-2 rounded overflow-x-auto max-h-24">
                      {JSON.stringify(ev.details, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
