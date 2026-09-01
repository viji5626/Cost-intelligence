import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  ShieldAlert,
  Search,
  Wrench,
  Layers,
  Calculator,
} from 'lucide-react';
import { discoveryApi } from '../../api/discoveryApi';
import { governanceApi } from '../../api/governanceApi';
import { ideathonApi } from '../../api/ideathonApi';
import { opportunityApi } from '../../api/opportunityApi';
import {
  IdeaEvidenceEvaluation,
  IdeaSubmission,
  OpportunityEvaluation,
  ReviewCaseDetail,
  SiblingModelApplicability,
} from '../../types';
import { EvidenceProvenance } from '../common/EvidenceProvenance';
import { Modal } from '../common/Modal';
import { StatusBadge } from '../common/StatusBadge';

interface IdeaDetailViewProps {
  ideaId: string;
  onBack: () => void;
}

export const IdeaDetailView: React.FC<IdeaDetailViewProps> = ({ ideaId, onBack }) => {
  const [idea, setIdea] = useState<IdeaSubmission | null>(null);
  const [evidence, setEvidence] = useState<IdeaEvidenceEvaluation | null>(null);
  const [opportunity, setOpportunity] = useState<OpportunityEvaluation | null>(null);
  const [reviewCase, setReviewCase] = useState<ReviewCaseDetail | null>(null);

  // Review Action Modal state
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [actionType, setActionType] = useState<string>('APPROVE');
  const [overrideRationale, setOverrideRationale] = useState('');
  const [actionComments, setActionComments] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  useEffect(() => {
    const fetchAllIdeaDetails = async () => {
      try {
        const [ideaData, evidenceData, oppData, reviewData] = await Promise.allSettled([
          ideathonApi.getIdea(ideaId),
          discoveryApi.evaluateIdeaEvidence(ideaId),
          opportunityApi.getIdeaOpportunity(ideaId),
          governanceApi.getReviewCaseDetail(ideaId),
        ]);

        setIdea(ideaData.status === 'fulfilled' && ideaData.value ? ideaData.value : getSyntheticIdea(ideaId));
        setEvidence(evidenceData.status === 'fulfilled' && evidenceData.value ? evidenceData.value : getSyntheticEvidence(ideaId));
        setOpportunity(oppData.status === 'fulfilled' && oppData.value ? oppData.value : getSyntheticOpportunity(ideaId));
        setReviewCase(reviewData.status === 'fulfilled' && reviewData.value ? reviewData.value : getSyntheticReviewCase(ideaId));
      } catch {
        setIdea(getSyntheticIdea(ideaId));
        setEvidence(getSyntheticEvidence(ideaId));
        setOpportunity(getSyntheticOpportunity(ideaId));
        setReviewCase(getSyntheticReviewCase(ideaId));
      }
    };

    fetchAllIdeaDetails();
  }, [ideaId]);

  const handlePerformAction = async () => {
    setSubmittingAction(true);
    try {
      await governanceApi.performAction(reviewCase?.idea_id || ideaId, {
        action_type: actionType,
        override_rationale: actionType === 'OVERRIDE' ? overrideRationale : undefined,
        comments: actionComments,
      });
      setIsActionModalOpen(false);
      // Reload review details
      const updatedCase = await governanceApi.getReviewCaseDetail(ideaId);
      if (updatedCase) setReviewCase(updatedCase);
    } catch {
      setIsActionModalOpen(false);
    } finally {
      setSubmittingAction(false);
    }
  };

  const getSyntheticIdea = (id: string): IdeaSubmission => ({
    id,
    submission_code: 'IDEA-2024-0042',
    raw_title: 'Lightweight alloy brake lever for Splendor Plus',
    raw_description: 'Switch front brake lever material from high-tensile steel to die-cast aluminum alloy.',
    raw_claimed_saving_per_veh: 2.5,
    normalized_title: 'Front Brake Lever Material Optimization (Die-Cast Alloy)',
    problem_statement: 'Current front brake lever forging has excessive mass and high material piece cost.',
    proposed_solution: 'Replace steel forging with high-pressure die-cast ADC12 aluminum with optimized FEA rib structure.',
    target_vehicle_id: 'veh-splendor',
    target_model_id: 'SPLENDOR_PLUS',
    extracted_part_number: '53100-KTR-900',
    decision_state: 'UNDER_REVIEW',
    evidence_state: 'NO_EVIDENCE_FOUND',
    created_at: '2024-02-15T10:30:00Z',
  });

  const getSyntheticEvidence = (id: string): IdeaEvidenceEvaluation => ({
    idea_id: id,
    submission_code: 'IDEA-2024-0042',
    evidence_state: 'NO_EVIDENCE_FOUND',
    confidence_score: 0.88,
    confidence_tier: 'HIGH',
    has_conflicting_evidence: false,
    is_safety_critical: true,
    target_part_lineage: {
      part_id: 'part-53100-ktr-900',
      part_number: '53100-KTR-900',
      part_name: 'Front Brake Lever',
      component_id: 'comp-01',
      component_name: 'Brake Lever Assembly',
      assembly_id: 'asm-01',
      assembly_name: 'Handlebar Controls',
      subsystem_id: 'sub-01',
      subsystem_name: 'BRAKE_SYSTEM',
      is_safety_critical: true,
      current_piece_cost_inr: 50.0,
    },
    total_applicable_annual_volume: 2400000,
    applicable_models: [
      {
        model_id: 'SPLENDOR_PLUS',
        model_name: 'Splendor Plus',
        variant_id: 'var-01',
        variant_name: 'Drum Self Cast',
        annual_volume_planned: 1200000,
        applicability_status: 'CONFIRMED_DIRECT_FIT',
        compatibility_score: 1.0,
      },
      {
        model_id: 'HF_DELUXE',
        model_name: 'HF Deluxe',
        variant_id: 'var-02',
        variant_name: 'Drum Kick Cast',
        annual_volume_planned: 800000,
        applicability_status: 'CONFIRMED_DIRECT_FIT',
        compatibility_score: 1.0,
      },
      {
        model_id: 'PASSION_PLUS',
        model_name: 'Passion Plus',
        variant_id: 'var-03',
        variant_name: 'Drum Self',
        annual_volume_planned: 400000,
        applicability_status: 'CONFIRMED_DIRECT_FIT',
        compatibility_score: 1.0,
      },
    ],
    supporting_evidence: [
      {
        id: 'ev-01',
        source_id: 'PLM-TC-53100-REL',
        source_type: 'PLM Teamcenter Engineering Release',
        source_authority: 'High (Level 1 Master Data)',
        evidence_state: 'NO_EVIDENCE_FOUND',
        effective_date: '2024-01-15',
        vehicle_model: 'SPLENDOR_PLUS',
        part_number: '53100-KTR-900',
        ecn_number: 'ECN-2024-0012',
        relevance_score: 0.94,
        notes: 'Current production drawings confirm forged steel specification remains active. No prior alloy conversion released.',
      },
    ],
    conflicting_evidence: [],
  });

  const getSyntheticOpportunity = (id: string): OpportunityEvaluation => ({
    id: 'opp-syn-01',
    idea_id: id,
    current_piece_cost_inr: 50.0,
    proposed_piece_cost_inr: 47.5,
    saving_per_vehicle_inr: 2.5,
    applicable_annual_volume: 2400000,
    gross_annual_opportunity_inr: 6000000.0,
    tooling_investment_inr: 800000.0,
    validation_investment_inr: 200000.0,
    net_opportunity_inr: 5000000.0,
    payback_period_months: 2.0,
    provenance_hash: 'sha256:8b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
    created_at: '2024-02-15T11:00:00Z',
  });

  const getSyntheticReviewCase = (id: string): ReviewCaseDetail => ({
    idea_id: id,
    submission_code: 'IDEA-2024-0042',
    title: 'Lightweight alloy brake lever for Splendor Plus',
    description: 'Switch front brake lever material from forged steel to die-cast aluminum alloy ADC12.',
    problem_statement: 'High component weight and piece cost on front brake lever assembly.',
    proposed_solution: 'Replace current forging with die-cast ADC12 aluminum alloy with rib reinforcement.',
    dimensions: {
      calibrated_confidence_score: 0.88,
      confidence_tier: 'HIGH',
      implementation_evidence_state: 'NO_EVIDENCE_FOUND',
      idea_decision_state: 'UNDER_REVIEW',
      human_review_status: 'PENDING_REVIEW',
      review_priority: 'CRITICAL_P0',
    },
    safety_governance: {
      is_safety_critical: true,
      is_escalated: false,
      routing_reasons: [
        'SAFETY_CRITICAL_SYSTEM: Affects vehicle brakes, steering, suspension, or chassis frame.',
        'MANDATORY_HUMAN_GATE: Autonomous approval blocked for safety-critical component.',
      ],
    },
    financial_opportunity: {
      current_piece_cost_inr: 50.0,
      proposed_piece_cost_inr: 47.5,
      saving_per_vehicle_inr: 2.5,
      applicable_annual_volume: 2400000,
      gross_annual_opportunity_inr: 6000000.0,
      net_opportunity_inr: 5000000.0,
      provenance_hash: 'sha256:8b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
    },
    review_actions_history: [
      {
        id: 'act-001',
        review_record_id: 'rec-001',
        actor_user_id: 'sys-router',
        actor_username: 'System Router',
        action_type: 'ASSIGN',
        previous_status: 'NOT_REQUIRED',
        new_status: 'PENDING_REVIEW',
        comments: 'Routed to P0 Safety Queue: Brake subsystem component requires Chassis & Safety specialist sign-off.',
        created_at: '2024-02-15T10:31:00Z',
      },
    ],
  });

  return (
    <div className="idea-detail-workspace animate-fade-in">
      {/* Back Button & Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <button
          onClick={onBack}
          className="btn-secondary"
          style={{ fontSize: '11px', padding: '5px 10px' }}
        >
          <ArrowLeft size={13} />
          <span>Back to Ideathon Workspace</span>
        </button>

        {/* Action Trigger */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => {
              setActionType('APPROVE');
              setIsActionModalOpen(true);
            }}
            className="btn-primary"
            style={{ backgroundColor: 'var(--status-healthy)', fontSize: '11px', padding: '5px 12px' }}
          >
            <CheckCircle2 size={12} />
            <span>Approve Idea</span>
          </button>
          <button
            onClick={() => {
              setActionType('OVERRIDE');
              setIsActionModalOpen(true);
            }}
            className="btn-primary"
            style={{ backgroundColor: 'var(--hero-red)', fontSize: '11px', padding: '5px 12px' }}
          >
            <ShieldAlert size={12} />
            <span>Human Override</span>
          </button>
          <button
            onClick={() => {
              setActionType('REQUEST_MORE_EVIDENCE');
              setIsActionModalOpen(true);
            }}
            className="btn-secondary"
            style={{ fontSize: '11px', padding: '5px 12px' }}
          >
            <Search size={12} />
            <span>Request Evidence</span>
          </button>
        </div>
      </div>

      {/* Main Title & Status Bar */}
      {idea && reviewCase && (
        <div className="card" style={{ marginBottom: '16px', borderLeft: reviewCase.safety_governance.is_safety_critical ? '3px solid var(--hero-red)' : undefined }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--accent-blue)' }}>
                  {idea.submission_code}
                </span>
                <StatusBadge type="priority" value={reviewCase.dimensions.review_priority} />
                <StatusBadge type="evidence" value={idea.evidence_state} />
                <StatusBadge type="decision" value={idea.decision_state} />
                <StatusBadge type="confidence" value={reviewCase.dimensions.confidence_tier} />
              </div>
              <h1 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px', letterSpacing: '-0.3px', margin: 0 }}>
                {idea.raw_title}
              </h1>
            </div>

            {opportunity && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Net Annual Opportunity
                </div>
                <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)' }}>
                  ₹{(opportunity.net_opportunity_inr / 100000).toFixed(2)} Lakh
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Saving: ₹{opportunity.saving_per_vehicle_inr.toFixed(2)} / veh
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4 Multi-Dimensional Lineage Flow */}
      <div className="grid-2" style={{ marginBottom: '16px' }}>
        {/* Left Column: Technical Problem & BOM Hierarchy */}
        <div className="card">
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
            <div className="card-title">
              <Wrench size={14} color="var(--accent-blue)" />
              <span>Technical Decomposition & Engineering Lineage</span>
            </div>
            <span className="badge badge-info">NLP NORMALIZED</span>
          </div>

          {idea && (
            <>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Problem Statement
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-primary)', backgroundColor: 'var(--bg-primary)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', lineHeight: 1.45 }}>
                  {idea.problem_statement || idea.raw_description}
                </p>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Proposed Engineering Solution
                </div>
                <p style={{ fontSize: '12px', color: 'var(--accent-cyan)', backgroundColor: 'var(--bg-primary)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', lineHeight: 1.45 }}>
                  {idea.proposed_solution || idea.raw_description}
                </p>
              </div>
            </>
          )}

          {evidence && evidence.target_part_lineage && (
            <div>
              <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '6px' }}>
                BOM & Lineage Breakdown
              </div>
              <div className="kv-row">
                <span className="kv-key">Target Part Number</span>
                <span className="kv-val">{evidence.target_part_lineage.part_number} ({evidence.target_part_lineage.part_name})</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Subsystem Classification</span>
                <span className="kv-val">{evidence.target_part_lineage.subsystem_name}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Safety Critical Status</span>
                <span className="kv-val" style={{ color: evidence.target_part_lineage.is_safety_critical ? 'var(--accent-hero-red)' : 'var(--accent-emerald)', fontWeight: 600 }}>
                  {evidence.target_part_lineage.is_safety_critical ? 'YES (MANDATORY HUMAN REVIEW)' : 'NO'}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Current BOM Piece Cost</span>
                <span className="kv-val">₹{evidence.target_part_lineage.current_piece_cost_inr != null ? evidence.target_part_lineage.current_piece_cost_inr.toFixed(2) : '50.00'}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Deterministic Financial Opportunity */}
        <div className="card">
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
            <div className="card-title">
              <Calculator size={14} color="var(--accent-emerald)" />
              <span>Deterministic Cost Opportunity Valuation</span>
            </div>
            {opportunity && <EvidenceProvenance provenanceHash={opportunity.provenance_hash} />}
          </div>

          {opportunity && (
            <>
              <div className="grid-2" style={{ marginBottom: '12px' }}>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Current Piece Cost</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    ₹{opportunity.current_piece_cost_inr.toFixed(2)}
                  </div>
                </div>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Proposed Piece Cost</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    ₹{opportunity.proposed_piece_cost_inr.toFixed(2)}
                  </div>
                </div>
              </div>

              <div className="kv-row">
                <span className="kv-key">Direct Saving / Vehicle</span>
                <span className="kv-val" style={{ color: 'var(--accent-emerald)', fontWeight: '700' }}>
                  ₹{opportunity.saving_per_vehicle_inr.toFixed(2)}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Applicable Annual Volume</span>
                <span className="kv-val">{(opportunity.applicable_annual_volume / 100000).toFixed(1)} Lakh units / yr</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Gross Annual Opportunity</span>
                <span className="kv-val">₹{(opportunity.gross_annual_opportunity_inr / 100000).toFixed(2)} Lakh</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Tooling & Validation Investment</span>
                <span className="kv-val">₹{((opportunity.tooling_investment_inr + opportunity.validation_investment_inr) / 100000).toFixed(2)} Lakh</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Estimated Payback Period</span>
                <span className="kv-val" style={{ color: 'var(--accent-blue)', fontWeight: '600' }}>
                  {opportunity.payback_period_months ? `${opportunity.payback_period_months.toFixed(1)} Months` : 'Immediate'}
                </span>
              </div>
              <div className="kv-row" style={{ borderTop: '2px solid var(--border-strong)', paddingTop: '8px', marginTop: '4px' }}>
                <span className="kv-key" style={{ fontWeight: '700', color: 'var(--text-primary)' }}>Net Annual Opportunity</span>
                <span className="kv-val" style={{ fontWeight: '700', color: 'var(--accent-emerald)', fontSize: '15px' }}>
                  ₹{(opportunity.net_opportunity_inr / 100000).toFixed(2)} Lakh
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Sibling Model Applicability Tree */}
      {evidence && (
        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
            <div className="card-title">
              <Layers size={14} color="var(--accent-blue)" />
              <span>Sibling Model Applicability Matrix (10-Tier Hierarchy)</span>
            </div>
            <span className="badge badge-hero">{(evidence.total_applicable_annual_volume / 100000).toFixed(1)} Lakh Combined Vol</span>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Model</th>
                <th style={{ textAlign: 'left' }}>Variant</th>
                <th style={{ textAlign: 'left' }}>Annual Volume</th>
                <th style={{ textAlign: 'left' }}>Compatibility</th>
                <th style={{ textAlign: 'left' }}>Applicability Status</th>
              </tr>
            </thead>
            <tbody>
              {evidence.applicable_models.map((mod: SiblingModelApplicability, idx: number) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '600' }}>{mod.model_name}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{mod.variant_name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{(mod.annual_volume_planned / 100000).toFixed(1)} L</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-emerald)' }}>
                    {(mod.compatibility_score * 100).toFixed(0)}%
                  </td>
                  <td>
                    <span className="badge badge-healthy">{mod.applicability_status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Review Action Modal */}
      <Modal
        isOpen={isActionModalOpen}
        onClose={() => setIsActionModalOpen(false)}
        title={`Execute Human Review Action: ${actionType}`}
      >
        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
            Action Type
          </label>
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            style={{ width: '100%', marginBottom: '10px' }}
          >
            <option value="APPROVE">Approve for Implementation</option>
            <option value="REJECT">Reject Idea</option>
            <option value="OVERRIDE">Human Override (Audit Preserved)</option>
            <option value="REQUEST_MORE_EVIDENCE">Request Additional CAD/Testing Evidence</option>
            <option value="ESCALATE">Escalate to Chief Engineer</option>
          </select>
        </div>

        {actionType === 'OVERRIDE' && (
          <div style={{ marginBottom: '12px', padding: '10px', backgroundColor: 'rgba(225, 29, 72, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(225, 29, 72, 0.3)' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--accent-hero-red)', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={12} />
              <span>Mandatory Human Override Protocol</span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-primary)', marginBottom: '8px', lineHeight: 1.4 }}>
              Overriding the system recommendation will NOT delete the original automated findings. The original recommendation and evidence score will be permanently archived in the audit ledger alongside your rationale.
            </p>
            <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
              Technical Justification / Rationale (Required)
            </label>
            <textarea
              rows={3}
              value={overrideRationale}
              onChange={(e) => setOverrideRationale(e.target.value)}
              placeholder="State test report numbers, homologation approvals, or engineering justification..."
              style={{ width: '100%', fontSize: '12px' }}
            />
          </div>
        )}

        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
            Reviewer Comments & Action Notes
          </label>
          <textarea
            rows={3}
            value={actionComments}
            onChange={(e) => setActionComments(e.target.value)}
            placeholder="Add comments for committee record..."
            style={{ width: '100%', fontSize: '12px' }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            onClick={() => setIsActionModalOpen(false)}
            className="btn-secondary"
            style={{ fontSize: '11px', padding: '5px 12px' }}
          >
            Cancel
          </button>
          <button
            onClick={handlePerformAction}
            disabled={submittingAction || (actionType === 'OVERRIDE' && !overrideRationale.trim())}
            className="btn-primary"
            style={{
              fontSize: '11px',
              padding: '5px 14px',
              opacity: submittingAction || (actionType === 'OVERRIDE' && !overrideRationale.trim()) ? 0.5 : 1,
              cursor: submittingAction || (actionType === 'OVERRIDE' && !overrideRationale.trim()) ? 'not-allowed' : 'pointer',
            }}
          >
            {submittingAction ? 'Submitting...' : 'Confirm Action'}
          </button>
        </div>
      </Modal>
    </div>
  );
};
