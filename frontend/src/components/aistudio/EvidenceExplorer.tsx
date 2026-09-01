import React, { useState } from 'react';
import {
  Search,
  BookOpen,
  ShieldCheck,
  Zap,
  Calendar,
  Factory,
} from 'lucide-react';
import { aistudioApi } from '../../api/aistudio';
import { EvidenceCitationItem } from '../../types/aistudio';

export const EvidenceExplorer: React.FC = () => {
  const [query, setQuery] = useState('Haridwar Cylinder Head ADC12 OPEX variance on Splendor Plus');
  const [isSearching, setIsSearching] = useState(false);
  const [citations, setCitations] = useState<EvidenceCitationItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const res = await aistudioApi.searchEvidence(query);
      setCitations(res);
      setHasSearched(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const getAuthorityBadge = (level: string) => {
    switch (level) {
      case 'CANONICAL_MASTER':
        return {
          bg: 'rgba(16, 185, 129, 0.1)',
          color: 'var(--status-healthy)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          label: 'Canonical Master PLM',
        };
      case 'CONTROLLED_ECN':
        return {
          bg: 'rgba(59, 130, 246, 0.1)',
          color: 'var(--status-info)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          label: 'Controlled ECN Release',
        };
      case 'PLANT_ACTUAL':
      default:
        return {
          bg: 'rgba(245, 158, 11, 0.1)',
          color: 'var(--status-warning)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          label: 'Plant Actual Ingestion',
        };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Query Bar */}
      <div
        style={{
          display: 'flex',
          gap: '10px',
          padding: '12px 16px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          alignItems: 'center',
        }}
      >
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search engineering evidence corpus (ECNs, BOM Lineage, Plant OPEX)..."
            style={{
              width: '100%',
              padding: '7px 10px 7px 32px',
              fontSize: '12px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={isSearching || !query.trim()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 16px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: 'var(--hero-red)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: isSearching ? 'wait' : 'pointer',
          }}
        >
          <Search size={13} />
          <span>{isSearching ? 'Searching...' : 'Formulate & Retrieve'}</span>
        </button>
      </div>

      {/* Semantic Distinction Warning Banner (Correction 21) */}
      <div
        style={{
          padding: '8px 12px',
          backgroundColor: 'var(--bg-tertiary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <ShieldCheck size={13} color="var(--status-info)" />
        <span>
          <strong>Grounding Axiom:</strong> Relevance (Cosine) &ne; Authority (PLM Level) &ne; Grounding (Citation Weight) &ne; Business Truth (Human Approver).
        </span>
      </div>

      {/* Results Explorer */}
      {isSearching ? (
        <div style={{ padding: '60px 20px', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Zap size={24} color="var(--status-info)" className="animate-spin" style={{ margin: '0 auto 10px' }} />
          <div>Running Dense Semantic Search & Cross-Encoder Reranking...</div>
        </div>
      ) : hasSearched && citations.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {citations.map((c) => {
            const badge = getAuthorityBadge(c.authority_level);
            return (
              <div
                key={c.citation_id}
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <BookOpen size={14} color="var(--status-info)" />
                    <span style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>
                      {c.source_document}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        ...badge,
                        fontSize: '10px',
                        fontWeight: '700',
                        padding: '2px 7px',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {badge.label}
                    </span>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      RRF Rank #{c.rrf_rank}
                    </span>
                  </div>
                </div>

                {/* Evidence Snippet Text */}
                <div
                  style={{
                    padding: '8px 10px',
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    lineHeight: 1.45,
                  }}
                >
                  {c.snippet_text}
                </div>

                {/* Metadata & Applicability Row */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '12px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    paddingTop: '6px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span>
                      Reranker: <strong style={{ color: 'var(--text-primary)' }}>{c.reranker_score.toFixed(3)}</strong>
                    </span>
                    <span>
                      Dense Sim: <strong style={{ color: 'var(--text-primary)' }}>{c.dense_similarity.toFixed(3)}</strong>
                    </span>
                    <span>
                      Grounding Contribution: <strong style={{ color: 'var(--status-healthy)' }}>{(c.grounding_weight * 100).toFixed(0)}%</strong>
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={11} color="var(--text-muted)" />
                      {c.temporal_validity}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Factory size={11} color="var(--text-muted)" />
                      {c.applicable_plants.join(', ')}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{ padding: '60px 20px', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
          Enter a query above to inspect hybrid retrieval vectors, cross-encoder reranking, and citation grounding.
        </div>
      )}
    </div>
  );
};
