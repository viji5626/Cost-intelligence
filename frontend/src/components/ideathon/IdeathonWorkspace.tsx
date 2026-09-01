import React, { useEffect, useState } from 'react';
import { Search, ArrowRight, ChevronLeft, ChevronRight, X, BookOpen } from 'lucide-react';
import { ideathonApi } from '../../api/ideathonApi';
import { IdeaSubmission } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

interface IdeathonWorkspaceProps {
  onSelectIdea: (ideaId: string) => void;
  onOpenHelp?: (chapterId: string) => void;
}

const getSyntheticIdeas = (): IdeaSubmission[] => [
  {
    id: 'idea-syn-01',
    submission_code: 'IDEA-2024-0042',
    raw_title: 'Lightweight alloy brake lever for Splendor Plus',
    raw_description: 'Switch front brake lever material from high-tensile steel to die-cast aluminum alloy.',
    raw_claimed_saving_per_veh: 2.5,
    normalized_title: 'Front Brake Lever Material Optimization (Die-Cast Alloy)',
    problem_statement: 'High weight and piece cost on front brake lever assembly.',
    proposed_solution: 'Replace current forging with die-cast ADC12 aluminum alloy with rib reinforcement.',
    target_vehicle_id: 'veh-splendor',
    target_model_id: 'SPLENDOR_PLUS',
    extracted_part_number: '53100-KTR-900',
    decision_state: 'UNDER_REVIEW',
    evidence_state: 'NO_EVIDENCE_FOUND',
    created_at: '2024-02-15T10:30:00Z',
  },
  {
    id: 'idea-syn-02',
    submission_code: 'IDEA-2024-0108',
    raw_title: 'Cylinder head wall thickness optimization',
    raw_description: 'Reduce cylinder head casting wall thickness by 0.5mm across 100cc engine portfolio.',
    raw_claimed_saving_per_veh: 14.0,
    normalized_title: 'Cylinder Head Casting Wall Thickness Reduction',
    problem_statement: 'Excessive casting material thickness in low-stress cylinder head regions.',
    proposed_solution: 'Optimize core tooling to reduce wall thickness from 3.5mm to 3.0mm.',
    target_vehicle_id: 'veh-hf-deluxe',
    target_model_id: 'HF_DELUXE',
    extracted_part_number: '12200-KTR-A00',
    decision_state: 'ACCEPTED_FOR_STUDY',
    evidence_state: 'PARTIALLY_CONFIRMED',
    created_at: '2024-02-18T14:15:00Z',
  },
  {
    id: 'idea-syn-03',
    submission_code: 'IDEA-2024-0215',
    raw_title: 'LED Headlamp Driver IC standardization with Glamour',
    raw_description: 'Use common LED driver board across Passion Plus and Glamour XTEC.',
    raw_claimed_saving_per_veh: 8.5,
    normalized_title: 'Standardized LED Headlamp Driver Module',
    problem_statement: 'Fragmented electronic BOMs across sibling models.',
    proposed_solution: 'Standardize on single unified constant-current LED driver IC.',
    target_vehicle_id: 'veh-passion',
    target_model_id: 'PASSION_PLUS',
    extracted_part_number: '33100-KCC-900',
    decision_state: 'APPROVED_FOR_IMPLEMENTATION',
    evidence_state: 'IMPLEMENTED',
    created_at: '2024-02-20T09:00:00Z',
  },
  {
    id: 'idea-syn-04',
    submission_code: 'IDEA-2024-0312',
    raw_title: 'Polymer bushing on rear brake pedal assembly',
    raw_description: 'Replace sintered bronze bushing with self-lubricating POM polymer bushing.',
    raw_claimed_saving_per_veh: 1.2,
    normalized_title: 'Brake Pedal Bushing Material Substitution',
    problem_statement: 'High cost of imported bronze bushing.',
    proposed_solution: 'Substitute with automotive grade POM polymer.',
    target_vehicle_id: 'veh-splendor',
    target_model_id: 'SPLENDOR_PLUS',
    extracted_part_number: '46500-KTR-900',
    decision_state: 'UNDER_REVIEW',
    evidence_state: 'CONFLICTING',
    created_at: '2024-02-22T11:45:00Z',
  },
];

export const IdeathonWorkspace: React.FC<IdeathonWorkspaceProps> = ({ onSelectIdea, onOpenHelp }) => {
  const [ideas, setIdeas] = useState<IdeaSubmission[]>(getSyntheticIdeas());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvidenceState, setSelectedEvidenceState] = useState('');
  const [selectedDecisionState, setSelectedDecisionState] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 15;

  const fetchIdeas = async () => {
    try {
      const data = await ideathonApi.listIdeas({
        skip: page * pageSize,
        limit: pageSize,
        query: searchQuery || undefined,
        evidence_state: selectedEvidenceState || undefined,
        decision_state: selectedDecisionState || undefined,
        vehicle_model: selectedModel || undefined,
      });

      if (data && data.length > 0) {
        setIdeas(data);
      } else {
        // Filter synthetic ideas
        let filtered = getSyntheticIdeas();
        if (searchQuery) {
          filtered = filtered.filter(
            (i) =>
              i.extracted_part_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
              i.submission_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
              i.normalized_title?.toLowerCase().includes(searchQuery.toLowerCase())
          );
        }
        if (selectedEvidenceState) {
          filtered = filtered.filter((i) => i.evidence_state === selectedEvidenceState);
        }
        if (selectedDecisionState) {
          filtered = filtered.filter((i) => i.decision_state === selectedDecisionState);
        }
        if (selectedModel) {
          filtered = filtered.filter((i) => i.target_model_id === selectedModel);
        }
        setIdeas(filtered);
      }
    } catch {
      setIdeas(getSyntheticIdeas());
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchIdeas();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedEvidenceState, selectedDecisionState, selectedModel, page]);

  return (
    <div className="ideathon-workspace animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', letterSpacing: '-0.3px', margin: 0 }}>
            Vehicle Ideathon Intelligence Workspace
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Scalable repository of 10,000+ vehicle cost reduction proposals with NLP normalization, duplicate clustering, and deterministic BOM valuation.
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('ideathon-search')}
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
            <span>Manual Ch. 09</span>
          </button>
        )}
      </div>

      {/* Filter Row */}
      <div
        className="card"
        style={{
          padding: '12px 14px',
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr 1fr auto',
          gap: '10px',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        {/* Search */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={13} color="var(--text-muted)" style={{ position: 'absolute', left: '10px' }} />
          <input
            type="text"
            placeholder="Search part number, code, or title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '28px', width: '100%' }}
          />
        </div>

        {/* Evidence State Filter */}
        <select
          value={selectedEvidenceState}
          onChange={(e) => setSelectedEvidenceState(e.target.value)}
        >
          <option value="">All Evidence States</option>
          <option value="IMPLEMENTED">Implementation Confirmed</option>
          <option value="PARTIALLY_CONFIRMED">Partially Confirmed</option>
          <option value="HISTORICAL">Historical Implementation</option>
          <option value="POTENTIAL_EVIDENCE">Potential Evidence</option>
          <option value="NO_EVIDENCE_FOUND">No Evidence Found</option>
          <option value="CONFLICTING">Conflicting Records</option>
        </select>

        {/* Decision State Filter */}
        <select
          value={selectedDecisionState}
          onChange={(e) => setSelectedDecisionState(e.target.value)}
        >
          <option value="">All Decision States</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="ACCEPTED_FOR_STUDY">Accepted for Study</option>
          <option value="APPROVED_FOR_IMPLEMENTATION">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>

        {/* Model Filter */}
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
        >
          <option value="">All Vehicle Models</option>
          <option value="SPLENDOR_PLUS">Splendor Plus</option>
          <option value="HF_DELUXE">HF Deluxe</option>
          <option value="PASSION_PLUS">Passion Plus</option>
          <option value="GLAMOUR_XTEC">Glamour XTEC</option>
          <option value="XPULSE_200">Xpulse 200</option>
        </select>

        {/* Clear Filters */}
        <button
          onClick={() => {
            setSearchQuery('');
            setSelectedEvidenceState('');
            setSelectedDecisionState('');
            setSelectedModel('');
          }}
          className="btn-secondary"
          style={{ fontSize: '11px', padding: '6px 10px' }}
          title="Clear all filters"
        >
          <X size={12} />
          Clear
        </button>
      </div>

      {/* Ideas Data Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '14px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              <th style={{ width: '130px' }}>Code</th>
              <th>Idea Title & Normalized Scope</th>
              <th style={{ width: '130px' }}>Target Model</th>
              <th style={{ width: '130px' }}>Part Number</th>
              <th style={{ width: '110px' }}>Claimed Saving</th>
              <th style={{ width: '180px' }}>Evidence State</th>
              <th style={{ width: '170px' }}>Decision State</th>
              <th style={{ width: '100px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {ideas.map((idea) => (
              <tr
                key={idea.id}
                style={{ cursor: 'pointer' }}
                onClick={() => onSelectIdea(idea.id)}
              >
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--accent-blue)' }}>
                  {idea.submission_code}
                </td>
                <td>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {idea.raw_title}
                  </div>
                  {idea.normalized_title && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
                      ↳ {idea.normalized_title}
                    </div>
                  )}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {idea.target_model_id || 'Cross-Platform'}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {idea.extracted_part_number || 'N/A'}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--text-primary)' }}>
                  ₹{idea.raw_claimed_saving_per_veh != null ? idea.raw_claimed_saving_per_veh.toFixed(2) : '0.00'}
                </td>
                <td>
                  <StatusBadge type="evidence" value={idea.evidence_state} />
                </td>
                <td>
                  <StatusBadge type="decision" value={idea.decision_state} />
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectIdea(idea.id);
                    }}
                    className="btn-secondary"
                    style={{ fontSize: '11px', padding: '3px 8px' }}
                  >
                    <span>Inspect</span>
                    <ArrowRight size={11} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-secondary)' }}>
        <div>
          Showing Page <span style={{ fontWeight: '600', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{page + 1}</span> ({ideas.length} ideas loaded)
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
            className="btn-secondary"
            style={{ fontSize: '11px', padding: '4px 10px', opacity: page === 0 ? 0.5 : 1, cursor: page === 0 ? 'not-allowed' : 'pointer' }}
          >
            <ChevronLeft size={12} />
            Previous
          </button>
          <button
            onClick={() => setPage(page + 1)}
            className="btn-secondary"
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            Next
            <ChevronRight size={12} />
          </button>
        </div>
      </div>
    </div>
  );
};
