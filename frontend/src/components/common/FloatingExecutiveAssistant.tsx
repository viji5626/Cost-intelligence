import React, { useState, useRef } from 'react';
import {
  X,
  Maximize2,
  Send,
  CheckCircle2,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  ExecutiveCopilotResponse,
  queryExecutiveCopilot,
} from '../../api/copilotApi';
import { HeroCompanionBot } from './HeroCompanionBot';

interface FloatingExecutiveAssistantProps {
  currentPage: string;
  onNavigateToCopilotWorkspace?: () => void;
}

export const FloatingExecutiveAssistant: React.FC<FloatingExecutiveAssistantProps> = ({
  currentPage,
  onNavigateToCopilotWorkspace,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [queryInput, setQueryInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<ExecutiveCopilotResponse | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Derive human-readable page context description
  const getContextLabel = (): string => {
    switch (currentPage) {
      case 'opex':
        return 'Plant OPEX • Haridwar vs Dharuhera (FY24)';
      case 'ideathon':
        return 'Vehicle Ideathon • 10,480 Proposals Pipeline';
      case 'opportunity':
        return 'Opportunity Simulator • Component & Tooling Models';
      case 'governance':
        return 'Safety Governance • Review Queue & P0 Gates';
      case 'ingestion':
        return 'Data Ingestion • File Ingestion & Parsing';
      case 'executive':
      case 'overview':
      default:
        return 'Executive Overview • Enterprise Cost Scope';
    }
  };

  // Generate page-aware contextual prompt chips
  const getContextPrompts = (): string[] => {
    switch (currentPage) {
      case 'opex':
        return [
          'Why is Haridwar OPEX higher than Dharuhera?',
          'What is the addressable utility savings opportunity?',
          'Which plant leads utility efficiency?',
        ];
      case 'ideathon':
        return [
          'Is Idea IDEA-0042 already implemented?',
          'What is our validated VAVE savings pipeline?',
          'What evidence supports brake lever optimization?',
        ];
      case 'opportunity':
        return [
          'What is the payback timeline for ₹10k piece cost?',
          'How much tooling investment is required?',
          'What assumptions drive this net opportunity?',
        ];
      case 'governance':
        return [
          'Why are brake and steering parts classified as CRITICAL_P0?',
          'How many proposals are pending mandatory human signoff?',
        ];
      case 'executive':
      case 'overview':
      default:
        return [
          'What is our total verified annual cost reduction opportunity?',
          'What are the top 3 cost levers across plants and sourcing?',
          'Where is our biggest procurement price gap?',
        ];
    }
  };

  const handleExecuteQuery = async (queryText: string) => {
    if (!queryText.trim()) return;
    setIsLoading(true);
    setShowTechnicalDetails(false);

    try {
      const resp = await queryExecutiveCopilot({
        query: queryText,
        page_context: {
          page: currentPage.toUpperCase(),
          plant_id: currentPage === 'opex' ? 'HARIDWAR' : undefined,
          period: 'FY2024',
        },
      });
      setCurrentResponse(resp);
    } catch (err) {
      console.error('Executive Assistant query error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (queryInput.trim()) {
      handleExecuteQuery(queryInput);
      setQueryInput('');
    }
  };

  return (
    <div style={{ position: 'fixed', bottom: '42px', right: '24px', zIndex: 9999 }}>
      {/* 3D Animated Hero AI Companion Floating Trigger Button (Slim Compact) */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="floating-copilot-trigger"
          title="Hero AI Companion • Click to Open Assistant"
        >
          {/* 3D Companion Bot (Slim Waving Avatar) */}
          <HeroCompanionBot
            size={26}
            isHovered={isHovered}
            isLoading={isLoading}
            showBody={true}
          />
          <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', lineHeight: 1.15 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', fontWeight: '800', color: '#F59E0B' }}>
              <span>Hero AI Copilot</span>
              <Sparkles size={10} color="#FFCC00" />
            </div>
            <div style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Executive Assistant
            </div>
          </div>
        </button>
      )}

      {/* Floating Drawer */}
      {isOpen && (
        <div
          ref={drawerRef}
          className="card animate-fade-in"
          style={{
            width: '440px',
            maxHeight: '620px',
            display: 'flex',
            flexDirection: 'column',
            padding: 0,
            overflow: 'hidden',
            backgroundColor: 'var(--bg-card)',
            border: '1.5px solid var(--border-strong)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 16px 45px rgba(0, 0, 0, 0.40)',
            marginBottom: 0,
          }}
        >
          {/* Header with 3D Robot Head */}
          <div
            style={{
              padding: '10px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-primary)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* 3D Animated Head in Header */}
              <div style={{ width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <HeroCompanionBot
                  size={34}
                  showBody={false}
                  emotion={isLoading ? 'thinking' : (currentResponse ? 'happy' : 'curious')}
                  isLoading={isLoading}
                />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '800', color: 'var(--text-primary)' }}>
                  <span>Hero AI Executive Assistant</span>
                  <span
                    style={{
                      fontSize: '9px',
                      padding: '1px 6px',
                      backgroundColor: 'rgba(245, 158, 11, 0.15)',
                      color: '#F59E0B',
                      borderRadius: '10px',
                      fontWeight: '700',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    VIDA AI
                  </span>
                </div>
                <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>
                  {getContextLabel()}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {onNavigateToCopilotWorkspace && (
                <button
                  onClick={() => {
                    setIsOpen(false);
                    onNavigateToCopilotWorkspace();
                  }}
                  title="Expand to Full-Screen Workspace"
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '4px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  <Maximize2 size={13} />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* Body Content Area */}
          <div style={{ padding: '14px 16px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '420px' }}>
            {/* Context Prompt Chips */}
            <div>
              <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Suggested Inquiries
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {getContextPrompts().map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleExecuteQuery(p)}
                    style={{
                      textAlign: 'left',
                      fontSize: '11px',
                      padding: '6px 10px',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'border-color var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--hero-red)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                  >
                    <span>{p}</span>
                    <ArrowRight size={11} color="var(--text-muted)" />
                  </button>
                ))}
              </div>
            </div>

            {/* Loading Indicator */}
            {isLoading && (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--status-info)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '12px' }}>
                <RefreshCw size={14} className="spin" />
                <span>Analyzing cost data and checking evidence...</span>
              </div>
            )}

            {/* Answer Display */}
            {currentResponse && !isLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Evidence State Badge */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span
                    className={`badge ${
                      currentResponse.evidence_state === 'VERIFIED'
                        ? 'badge-healthy'
                        : currentResponse.evidence_state === 'NO_IMPLEMENTATION_EVIDENCE_FOUND'
                        ? 'badge-neutral'
                        : 'badge-warning'
                    }`}
                    style={{ fontSize: '9px' }}
                  >
                    {currentResponse.evidence_state === 'VERIFIED' && <CheckCircle2 size={10} />}
                    {currentResponse.evidence_state === 'NO_IMPLEMENTATION_EVIDENCE_FOUND' && <AlertCircle size={10} />}
                    <span>{currentResponse.evidence_state.replace(/_/g, ' ')}</span>
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {currentResponse.task_id}
                  </span>
                </div>

                {/* Plain-Language Answer */}
                <div
                  style={{
                    fontSize: '12px',
                    lineHeight: '1.5',
                    color: 'var(--text-primary)',
                    backgroundColor: 'var(--bg-primary)',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {currentResponse.answer}
                </div>

                {/* Key Findings */}
                {currentResponse.summary_points.length > 0 && (
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Key Findings
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                      {currentResponse.summary_points.map((pt, i) => (
                        <li key={i} style={{ marginBottom: '3px' }}>
                          {pt}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Authoritative Sources */}
                {currentResponse.citations.length > 0 && (
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Evidence Sources ({currentResponse.citations.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {currentResponse.citations.map((c, idx) => (
                        <div
                          key={idx}
                          style={{
                            fontSize: '10px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 6px',
                            backgroundColor: 'var(--bg-primary)',
                            borderRadius: '3px',
                            border: '1px solid var(--border-subtle)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          <FileText size={10} color="var(--status-info)" />
                          <strong>{c.label}</strong>
                          <span style={{ color: 'var(--text-muted)', marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>
                            {c.source_id}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Technical Details (Collapsed by default) */}
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
                  <button
                    type="button"
                    onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '10px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: 0,
                    }}
                  >
                    <ShieldCheck size={11} color="var(--status-healthy)" />
                    <span>Technical Details & Audit Lineage</span>
                    {showTechnicalDetails ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  </button>

                  {showTechnicalDetails && (
                    <div
                      style={{
                        marginTop: '6px',
                        padding: '8px 10px',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '10px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5,
                      }}
                    >
                      <div style={{ marginBottom: '4px', color: 'var(--text-primary)', fontWeight: '600' }}>
                        Presentation Context: {currentResponse.persona_resolution_reason}
                      </div>
                      {currentResponse.execution_trace.map((tr, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
                          <span style={{ color: 'var(--status-healthy)' }}>✓</span>
                          <span>{tr}</span>
                        </div>
                      ))}
                      <div style={{ marginTop: '4px', color: 'var(--text-muted)', fontSize: '9px' }}>
                        Audit Hash: {currentResponse.audit_hash}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Query Input Footer */}
          <form
            onSubmit={handleSubmit}
            style={{
              padding: '10px 14px',
              borderTop: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-primary)',
              display: 'flex',
              gap: '8px',
            }}
          >
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Ask about cost, plant, or VAVE data..."
              disabled={isLoading}
              style={{
                flex: 1,
                fontSize: '11px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-strong)',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-primary)',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={isLoading || !queryInput.trim()}
              className="btn-primary"
              style={{ padding: '6px 10px', fontSize: '11px', opacity: isLoading || !queryInput.trim() ? 0.6 : 1 }}
            >
              <Send size={12} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
