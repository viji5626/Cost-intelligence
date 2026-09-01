import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen,
  Search,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  CheckCircle2,
  FileText,
  Workflow,
  Wrench,
  Shield,
  ArrowRight,
  Hash,
} from 'lucide-react';
import {
  HELP_CHAPTERS,
  GLOSSARY_TERMS,
  TROUBLESHOOTING_GUIDE,
} from '../../data/helpManualData';

interface HelpManualWorkspaceProps {
  initialChapterId?: string;
  onNavigateWorkspace?: (workspaceId: string) => void;
}

export const HelpManualWorkspace: React.FC<HelpManualWorkspaceProps> = ({
  initialChapterId,
  onNavigateWorkspace,
}) => {
  const [activeTab, setActiveTab] = useState<'manual' | 'glossary' | 'troubleshooting'>('manual');
  const [selectedChapterId, setSelectedChapterId] = useState<string>(
    initialChapterId || HELP_CHAPTERS[0].id
  );
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  useEffect(() => {
    if (initialChapterId) {
      setSelectedChapterId(initialChapterId);
      setActiveTab('manual');
    }
  }, [initialChapterId]);

  const activeChapter = useMemo(() => {
    return HELP_CHAPTERS.find((c) => c.id === selectedChapterId) || HELP_CHAPTERS[0];
  }, [selectedChapterId]);

  const currentIndex = HELP_CHAPTERS.findIndex((c) => c.id === activeChapter.id);
  const prevChapter = currentIndex > 0 ? HELP_CHAPTERS[currentIndex - 1] : null;
  const nextChapter = currentIndex < HELP_CHAPTERS.length - 1 ? HELP_CHAPTERS[currentIndex + 1] : null;

  // Filtered chapters for table of contents
  const filteredChapters = useMemo(() => {
    return HELP_CHAPTERS.filter((c) => {
      const matchesCategory = selectedCategory === 'ALL' || c.category === selectedCategory;
      const matchesSearch =
        searchQuery.trim() === '' ||
        c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.whatItIs.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [searchQuery, selectedCategory]);

  // Filtered glossary terms
  const filteredGlossary = useMemo(() => {
    return GLOSSARY_TERMS.filter((g) => {
      const q = searchQuery.toLowerCase();
      return (
        g.term.toLowerCase().includes(q) ||
        g.definition.toLowerCase().includes(q) ||
        g.category.toLowerCase().includes(q)
      );
    });
  }, [searchQuery]);

  // Filtered troubleshooting entries
  const filteredTroubleshooting = useMemo(() => {
    return TROUBLESHOOTING_GUIDE.filter((t) => {
      const q = searchQuery.toLowerCase();
      return (
        t.symptom.toLowerCase().includes(q) ||
        t.likelyCause.toLowerCase().includes(q) ||
        t.action.toLowerCase().includes(q)
      );
    });
  }, [searchQuery]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '12px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={20} color="var(--hero-red)" />
            <h1 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
              Hero Cost Intelligence User Manual & Knowledge System
            </h1>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '3px' }}>
            Official industrial engineering operations guide, deterministic calculation rules, and failure remediation matrix.
          </p>
        </div>

        {/* Top Segmented Navigation Tabs */}
        <div style={{ display: 'flex', gap: '6px', backgroundColor: 'var(--bg-tertiary)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => setActiveTab('manual')}
            style={{
              padding: '5px 12px',
              fontSize: '11px',
              fontWeight: activeTab === 'manual' ? '700' : '500',
              backgroundColor: activeTab === 'manual' ? 'var(--bg-card)' : 'transparent',
              color: activeTab === 'manual' ? 'var(--hero-red)' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              boxShadow: activeTab === 'manual' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            Engineering Manual (25 Ch.)
          </button>
          <button
            onClick={() => setActiveTab('glossary')}
            style={{
              padding: '5px 12px',
              fontSize: '11px',
              fontWeight: activeTab === 'glossary' ? '700' : '500',
              backgroundColor: activeTab === 'glossary' ? 'var(--bg-card)' : 'transparent',
              color: activeTab === 'glossary' ? 'var(--hero-red)' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              boxShadow: activeTab === 'glossary' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            Glossary ({GLOSSARY_TERMS.length})
          </button>
          <button
            onClick={() => setActiveTab('troubleshooting')}
            style={{
              padding: '5px 12px',
              fontSize: '11px',
              fontWeight: activeTab === 'troubleshooting' ? '700' : '500',
              backgroundColor: activeTab === 'troubleshooting' ? 'var(--bg-card)' : 'transparent',
              color: activeTab === 'troubleshooting' ? 'var(--hero-red)' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              boxShadow: activeTab === 'troubleshooting' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            Troubleshooting Guide
          </button>
        </div>
      </div>

      {/* Global Search Bar */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search manual topics, calculation formulas, terms (e.g. Specific Power, ECN, GBNF, P0), or error symptoms..."
            style={{
              width: '100%',
              padding: '7px 10px 7px 32px',
              fontSize: '12px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
            }}
          />
        </div>
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            style={{ padding: '6px 12px', fontSize: '11px', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            Clear Search
          </button>
        )}
      </div>

      {/* TAB 1: ENGINEERING USER MANUAL */}
      {activeTab === 'manual' && (
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '16px', alignItems: 'start' }}>
          {/* Left TOC Sidebar */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              maxHeight: 'calc(100vh - 200px)',
              overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Table of Contents
              </span>
              <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                {filteredChapters.length} / {HELP_CHAPTERS.length}
              </span>
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{
                width: '100%',
                padding: '4px 6px',
                fontSize: '11px',
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="ALL">All Categories</option>
              <option value="CORE">1. Core System & Overview</option>
              <option value="OPERATIONS">2. Plant OPEX & Utilities</option>
              <option value="VEHICLE_ENGINEERING">3. Vehicle Ideathon & VAVE</option>
              <option value="DATA_GOVERNANCE">4. Governance & Ingestion</option>
              <option value="AI_SYSTEM">5. Local AI Architecture</option>
              <option value="REFERENCE">6. Reference & Troubleshooting</option>
            </select>

            {/* Chapter Items List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {filteredChapters.map((ch) => {
                const isSelected = ch.id === selectedChapterId;
                return (
                  <button
                    key={ch.id}
                    onClick={() => setSelectedChapterId(ch.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px',
                      padding: '7px 8px',
                      borderRadius: 'var(--radius-sm)',
                      border: 'none',
                      borderLeft: isSelected ? '3px solid var(--hero-red)' : '3px solid transparent',
                      backgroundColor: isSelected ? 'var(--bg-tertiary)' : 'transparent',
                      color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '11px',
                      fontWeight: isSelected ? '700' : '500',
                      lineHeight: '1.3',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span style={{ fontFamily: 'var(--font-mono)', color: isSelected ? 'var(--hero-red)' : 'var(--text-muted)', fontSize: '10px', minWidth: '18px' }}>
                      {ch.chapterNumber.toString().padStart(2, '0')}.
                    </span>
                    <span style={{ flex: 1 }}>{ch.title}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Chapter Reader Panel */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '20px 24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {/* Chapter Top Bar */}
            <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontSize: '10px', fontWeight: '700', fontFamily: 'var(--font-mono)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--hero-red-subtle)', color: 'var(--hero-red)', border: '1px solid var(--hero-red-border)' }}>
                  CHAPTER {activeChapter.chapterNumber.toString().padStart(2, '0')}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                  {activeChapter.category.replace('_', ' ')}
                </span>
              </div>
              <h2 style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>
                {activeChapter.title}
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.5' }}>
                {activeChapter.summary}
              </p>
            </div>

            {/* Section 1: What it is & Why it matters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div style={{ padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText size={13} color="var(--status-info)" /> What It Is
                </div>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                  {activeChapter.whatItIs}
                </p>
              </div>

              <div style={{ padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Shield size={13} color="var(--hero-red)" /> Why It Matters
                </div>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                  {activeChapter.whyItMatters}
                </p>
              </div>
            </div>

            {/* Section 2: How To Use It */}
            <div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Workflow size={14} color="var(--status-healthy)" /> Step-by-Step Operating Instructions
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {activeChapter.howToUse.map((step, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      gap: '10px',
                      padding: '8px 10px',
                      backgroundColor: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '11px',
                      color: 'var(--text-primary)',
                      lineHeight: '1.4',
                    }}
                  >
                    <span style={{ fontWeight: '700', color: 'var(--hero-red)', fontFamily: 'var(--font-mono)' }}>
                      {(idx + 1).toString().padStart(2, '0')}.
                    </span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 3: Input -> Process -> Output Pipeline (if available) */}
            {activeChapter.pipeline && (
              <div style={{ padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px' }}>
                  Transformation Data Flow: Input → Process → Output
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr auto 1fr', gap: '8px', alignItems: 'center', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                  <div style={{ padding: '6px 8px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ color: 'var(--text-muted)', fontWeight: '700', marginBottom: '2px' }}>INPUTS:</div>
                    {activeChapter.pipeline.inputs.map((i, k) => <div key={k}>• {i}</div>)}
                  </div>
                  <ArrowRight size={14} color="var(--text-muted)" />
                  <div style={{ padding: '6px 8px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ color: 'var(--text-muted)', fontWeight: '700', marginBottom: '2px' }}>PROCESS:</div>
                    {activeChapter.pipeline.process.map((p, k) => <div key={k}>• {p}</div>)}
                  </div>
                  <ArrowRight size={14} color="var(--text-muted)" />
                  <div style={{ padding: '6px 8px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ color: 'var(--hero-red)', fontWeight: '700', marginBottom: '2px' }}>OUTPUTS:</div>
                    {activeChapter.pipeline.outputs.map((o, k) => <div key={k}>• {o}</div>)}
                  </div>
                </div>
              </div>
            )}

            {/* Section 4: Interpretation Rules & Common Mistakes */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div style={{ padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--status-healthy)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <CheckCircle2 size={13} /> Interpretation & Business Rules
                </div>
                <ul style={{ paddingLeft: '16px', fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.45', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {activeChapter.interpretationRules.map((rule, idx) => (
                    <li key={idx}>{rule}</li>
                  ))}
                </ul>
              </div>

              <div style={{ padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--status-warning)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <AlertCircle size={13} /> Common Operational Mistakes
                </div>
                <ul style={{ paddingLeft: '16px', fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.45', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {activeChapter.commonMistakes.map((mistake, idx) => (
                    <li key={idx}>{mistake}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Section 5: Troubleshooting Action */}
            <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wrench size={13} color="var(--hero-red)" />
                <span style={{ color: 'var(--text-secondary)' }}>
                  <strong>Troubleshooting:</strong> {activeChapter.troubleshootingAction}
                </span>
              </div>
              <button
                onClick={() => setActiveTab('troubleshooting')}
                style={{
                  padding: '3px 8px',
                  fontSize: '10px',
                  fontWeight: '700',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--hero-red)',
                  cursor: 'pointer',
                }}
              >
                View Failure Matrix
              </button>
            </div>

            {/* Bottom Chapter Navigation Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', marginTop: 'auto' }}>
              {prevChapter ? (
                <button
                  onClick={() => setSelectedChapterId(prevChapter.id)}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <ChevronLeft size={13} /> Ch. {prevChapter.chapterNumber}: {prevChapter.title.slice(0, 30)}...
                </button>
              ) : <div />}

              {nextChapter && (
                <button
                  onClick={() => setSelectedChapterId(nextChapter.id)}
                  style={{
                    padding: '6px 14px',
                    backgroundColor: 'var(--hero-red)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontWeight: '700',
                    color: '#ffffff',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  Next: Ch. {nextChapter.chapterNumber} <ChevronRight size={13} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ENGINEERING GLOSSARY */}
      {activeTab === 'glossary' && (
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Hash size={15} color="var(--hero-red)" /> Searchable Engineering Glossary ({filteredGlossary.length} terms)
            </div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Industrial Cost Intelligence Terminology
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '10px' }}>
            {filteredGlossary.map((g, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {g.term}
                  </span>
                  <span style={{ fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-card)', color: 'var(--text-muted)', border: '1px solid var(--border-subtle)' }}>
                    {g.category}
                  </span>
                </div>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {g.definition}
                </p>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', borderTop: '1px solid var(--border-subtle)', paddingTop: '4px' }}>
                  <strong>Example:</strong> {g.exampleOrContext}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: TROUBLESHOOTING GUIDE */}
      {activeTab === 'troubleshooting' && (
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Wrench size={15} color="var(--hero-red)" /> System Failure Remediation Matrix ({filteredTroubleshooting.length} scenarios)
            </div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Symptom → Likely Cause → Check → Action
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {filteredTroubleshooting.map((t) => (
              <div
                key={t.id}
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={14} color="var(--hero-red)" />
                    <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {t.symptom}
                    </span>
                  </div>
                  {onNavigateWorkspace && (
                    <button
                      onClick={() => onNavigateWorkspace(t.workspaceId)}
                      style={{
                        padding: '3px 8px',
                        fontSize: '10px',
                        backgroundColor: 'var(--bg-card)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                      }}
                    >
                      Open {t.workspaceId.toUpperCase()} Workspace
                    </button>
                  )}
                </div>

                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  <strong>Likely Cause:</strong> {t.likelyCause}
                </div>

                <div style={{ padding: '6px 10px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                  <div style={{ color: 'var(--text-muted)', fontWeight: '700', marginBottom: '2px' }}>DIAGNOSTIC CHECKS:</div>
                  {t.check.map((c, i) => (
                    <div key={i} style={{ color: 'var(--text-secondary)' }}>• {c}</div>
                  ))}
                </div>

                <div style={{ padding: '6px 10px', backgroundColor: 'rgba(16, 185, 129, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.25)', fontSize: '11px', color: 'var(--status-healthy)' }}>
                  <strong>Recommended Action:</strong> {t.action}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
