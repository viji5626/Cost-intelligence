import React, { useState } from 'react';
import {
  Compass,
  Send,
  CheckCircle2,
  AlertCircle,
  FileText,
  ShieldCheck,
  RefreshCw,
  BookOpen,
  ArrowRight,
  Database,
  Search,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  ExecutiveCopilotResponse,
  queryExecutiveCopilot,
} from '../../api/copilotApi';

interface ExecutiveCopilotWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

const CURATED_QUESTIONS = [
  {
    category: 'Enterprise Opportunity',
    text: 'What is our total verified annual cost reduction opportunity across all operations?',
  },
  {
    category: 'Plant Operations',
    text: 'Why is Haridwar total OPEX ₹27/vehicle higher than the Dharuhera benchmark?',
  },
  {
    category: 'Utility Consumption',
    text: 'What is driving compressed air specific consumption at Haridwar and how do we close the gap?',
  },
  {
    category: 'Component Sourcing',
    text: 'Which chassis and suspension components have the largest cross-plant purchase price variance?',
  },
  {
    category: 'Supplier Commercials',
    text: 'What is our supplier negotiation leverage on Front Fork Assembly (Part 51400-KCC-900)?',
  },
  {
    category: 'Ideathon & VAVE',
    text: 'Is Idea IDEA-0042 (Brake Lever Section Optimization) already implemented in production?',
  },
  {
    category: 'Safety Governance',
    text: 'Why are 14 ideathon proposals in mandatory human review queue under CRITICAL_P0?',
  },
  {
    category: 'Benchmarking',
    text: 'Which manufacturing plant is our overall benchmark leader and what practices are transferable?',
  },
];

export const ExecutiveCopilotWorkspace: React.FC<ExecutiveCopilotWorkspaceProps> = ({ onOpenHelp }) => {
  const [queryInput, setQueryInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeResponse, setActiveResponse] = useState<ExecutiveCopilotResponse | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const handleAsk = async (text: string) => {
    if (!text.trim()) return;
    setIsLoading(true);
    setShowTechnicalDetails(false);
    try {
      const res = await queryExecutiveCopilot({
        query: text,
        page_context: { page: 'EXECUTIVE_ASSISTANT' },
      });
      setActiveResponse(res);
    } catch (e) {
      console.error('Failed to query assistant:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (queryInput.trim()) {
      handleAsk(queryInput);
      setQueryInput('');
    }
  };

  return (
    <div className="executive-assistant-workspace animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                backgroundColor: 'var(--hero-red)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
              }}
            >
              <Compass size={16} />
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.3px', margin: 0 }}>
              Executive Assistant
            </h2>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', padding: '2px 8px', borderRadius: '4px' }}>
              Enterprise Decision Support
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '12px' }}>
            Conversational analysis translating multi-plant OPEX, BOM cost masters, and 10,000+ ideathon proposals into clear business findings.
          </p>
        </div>

        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('executive-dashboard')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <BookOpen size={12} color="var(--status-info)" />
            <span>Manual Ch. 1</span>
          </button>
        )}
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', alignItems: 'start' }}>
        {/* Left Column: Curated Inquiries & Input */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Ask Input Card */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ paddingBottom: '6px', marginBottom: '8px' }}>
              <div className="card-title">
                <Search size={14} color="var(--text-primary)" />
                <span>Ask Question</span>
              </div>
            </div>

            <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <textarea
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Ask about cost, plant variance, sourcing, or VAVE proposals..."
                rows={3}
                style={{
                  width: '100%',
                  fontSize: '11px',
                  padding: '8px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-strong)',
                  backgroundColor: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  resize: 'none',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
              <button
                type="submit"
                disabled={isLoading || !queryInput.trim()}
                className="btn-primary"
                style={{
                  fontSize: '11px',
                  padding: '7px 12px',
                  justifyContent: 'center',
                  opacity: isLoading || !queryInput.trim() ? 0.6 : 1,
                }}
              >
                {isLoading ? <RefreshCw size={12} className="spin" /> : <Send size={12} />}
                <span>Analyze Evidence</span>
              </button>
            </form>
          </div>

          {/* Curated Prompts */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
              Common Executive Inquiries
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {CURATED_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAsk(q.text)}
                  style={{
                    textAlign: 'left',
                    fontSize: '11px',
                    padding: '8px 10px',
                    backgroundColor: 'var(--bg-primary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    transition: 'border-color var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--hero-red)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '9px', fontWeight: '700', color: 'var(--status-info)', textTransform: 'uppercase' }}>
                      {q.category}
                    </span>
                    <ArrowRight size={10} color="var(--text-muted)" />
                  </div>
                  <span style={{ fontSize: '11px', lineHeight: 1.35 }}>{q.text}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Executive Briefing & Findings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Loading State */}
          {isLoading && (
            <div className="card" style={{ padding: '30px', textAlign: 'center', color: 'var(--status-info)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
              <RefreshCw size={24} className="spin" />
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Analyzing Verified Cost Data...
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Correlating OPEX benchmarks, BOM piece costs, and validated ideathon records.
              </div>
            </div>
          )}

          {/* Active Response Display */}
          {activeResponse && !isLoading && (
            <>
              {/* Executive Answer Card */}
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
                  <div className="card-title">
                    <Compass size={15} color="var(--hero-red)" />
                    <span>Executive Briefing</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className={`badge ${
                        activeResponse.evidence_state === 'VERIFIED'
                          ? 'badge-healthy'
                          : activeResponse.evidence_state === 'NO_IMPLEMENTATION_EVIDENCE_FOUND'
                          ? 'badge-neutral'
                          : 'badge-warning'
                      }`}
                    >
                      {activeResponse.evidence_state === 'VERIFIED' && <CheckCircle2 size={11} />}
                      {activeResponse.evidence_state === 'NO_IMPLEMENTATION_EVIDENCE_FOUND' && <AlertCircle size={11} />}
                      <span>{activeResponse.evidence_state.replace(/_/g, ' ')}</span>
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {activeResponse.task_id}
                    </span>
                  </div>
                </div>

                {/* Plain-Language Main Explanation */}
                <div
                  style={{
                    fontSize: '13px',
                    lineHeight: '1.6',
                    color: 'var(--text-primary)',
                    backgroundColor: 'var(--bg-primary)',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    marginBottom: '12px',
                  }}
                >
                  {activeResponse.answer}
                </div>

                {/* Verified Financial Numbers Grid */}
                {Object.keys(activeResponse.verified_metrics).length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Business Impact & Verified Metrics
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                      {Object.entries(activeResponse.verified_metrics).map(([k, v]) => (
                        <div
                          key={k}
                          style={{
                            padding: '8px 10px',
                            backgroundColor: 'var(--bg-primary)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          <div style={{ fontSize: '9px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                            {k.replace(/_/g, ' ')}
                          </div>
                          <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            {typeof v === 'number' && v >= 100000 ? `₹${(v / 10000000 >= 1 ? `${(v / 10000000).toFixed(2)} Cr` : `${(v / 100000).toFixed(2)} Lakh`)}` : typeof v === 'number' && k.includes('pct') ? `${v}%` : typeof v === 'boolean' ? (v ? 'YES' : 'NO') : String(v)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Findings */}
                {activeResponse.summary_points.length > 0 && (
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', marginBottom: '12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Key Findings
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                      {activeResponse.summary_points.map((pt, i) => (
                        <li key={i} style={{ marginBottom: '4px' }}>
                          {pt}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommended Next Actions */}
                {activeResponse.recommended_next_actions.length > 0 && (
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Recommended Next Actions
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      {activeResponse.recommended_next_actions.map((act, i) => (
                        <div
                          key={i}
                          style={{
                            fontSize: '11px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '6px 10px',
                            backgroundColor: 'var(--bg-primary)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                            color: 'var(--text-primary)',
                          }}
                        >
                          <ArrowRight size={12} color="var(--hero-red)" />
                          <span>{act}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Authoritative Citations & Technical Details Card */}
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card-header" style={{ paddingBottom: '6px', marginBottom: '10px' }}>
                  <div className="card-title">
                    <Database size={14} color="var(--status-info)" />
                    <span>Evidence Sources</span>
                  </div>
                </div>

                {/* Citations Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px', marginBottom: '12px' }}>
                  {activeResponse.citations.map((c, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '8px 10px',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '11px',
                      }}
                    >
                      <div style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <FileText size={12} color="var(--status-info)" />
                        <span>{c.label}</span>
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px', display: 'flex', justifyContent: 'space-between' }}>
                        <span>{c.dataset}</span>
                        <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{c.source_id}</strong>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Technical Details (Collapsed by default) */}
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '11px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: 0,
                    }}
                  >
                    <ShieldCheck size={13} color="var(--status-healthy)" />
                    <span>Technical Details & Audit Lineage</span>
                    {showTechnicalDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>

                  {showTechnicalDetails && (
                    <div
                      style={{
                        marginTop: '8px',
                        padding: '10px 12px',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '10.5px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.6,
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <div style={{ marginBottom: '4px', color: 'var(--text-primary)', fontWeight: '600' }}>
                        Presentation Context: {activeResponse.persona_resolution_reason}
                      </div>
                      {activeResponse.execution_trace.map((tr, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                          <span style={{ color: 'var(--status-healthy)', fontWeight: '700' }}>✓</span>
                          <span>{tr}</span>
                        </div>
                      ))}
                      <div style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '9.5px' }}>
                        Audit Hash: {activeResponse.audit_hash}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Initial / Empty State */}
          {!activeResponse && !isLoading && (
            <div className="card" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <Compass size={32} color="var(--hero-red)" style={{ margin: '0 auto 12px' }} />
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
                Executive Decision Intelligence
              </div>
              <div style={{ fontSize: '12px', maxWidth: '480px', margin: '0 auto', lineHeight: 1.5 }}>
                Select a common inquiry from the left or ask any cost, plant variance, component sourcing, or VAVE ideathon question to receive verified analysis.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
