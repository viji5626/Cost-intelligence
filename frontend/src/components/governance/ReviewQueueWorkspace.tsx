import React, { useEffect, useState } from 'react';
import { ShieldAlert, ArrowUpRight, Layers, MinusCircle, ArrowRight, AlertTriangle, BookOpen } from 'lucide-react';
import { governanceApi } from '../../api/governanceApi';
import { ReviewPriority, ReviewRecord, ReviewStatus } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

interface ReviewQueueWorkspaceProps {
  onSelectIdea: (ideaId: string) => void;
  onOpenHelp?: (chapterId: string) => void;
}

export const ReviewQueueWorkspace: React.FC<ReviewQueueWorkspaceProps> = ({ onSelectIdea, onOpenHelp }) => {
  const [queue, setQueue] = useState<ReviewRecord[]>([]);
  const [priorityFilter, setPriorityFilter] = useState<ReviewPriority | ''>('');
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('');
  const [safetyOnly, setSafetyOnly] = useState(false);

  const fetchQueue = async () => {
    try {
      const data = await governanceApi.getReviewQueue({
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
        safety_only: safetyOnly || undefined,
      });

      if (data && data.length > 0) {
        setQueue(data);
      } else {
        setQueue(getSyntheticQueue());
      }
    } catch {
      setQueue(getSyntheticQueue());
    }
  };

  const getSyntheticQueue = (): ReviewRecord[] => [
    {
      id: 'rev-01',
      idea_id: 'idea-syn-01',
      submission_code: 'IDEA-2024-0042',
      idea_title: 'Lightweight alloy brake lever for Splendor Plus',
      review_status: 'PENDING_REVIEW',
      review_priority: 'CRITICAL_P0',
      routing_reasons: [
        'SAFETY_CRITICAL_SYSTEM: Affects vehicle brakes, steering, suspension, or frame.',
        'MANDATORY_HUMAN_GATE: Autonomous approval blocked for safety critical items.',
      ],
      is_safety_critical: true,
      is_escalated: false,
      calibrated_confidence_score: 0.88,
      confidence_tier: 'HIGH',
      original_automated_decision: 'REQUIRES_SAFETY_REVIEW',
      original_evidence_state: 'NO_EVIDENCE_FOUND',
      created_at: '2024-02-15T10:30:00Z',
      updated_at: '2024-02-15T10:30:00Z',
    },
    {
      id: 'rev-02',
      idea_id: 'idea-syn-04',
      submission_code: 'IDEA-2024-0312',
      idea_title: 'Polymer bushing on rear brake pedal assembly',
      review_status: 'PENDING_REVIEW',
      review_priority: 'CRITICAL_P0',
      routing_reasons: [
        'CONFLICTING_EVIDENCE: Contradictory engineering change notices or status records found.',
        'SAFETY_CRITICAL_SYSTEM: Brake pedal assembly.',
      ],
      is_safety_critical: true,
      is_escalated: false,
      calibrated_confidence_score: 0.42,
      confidence_tier: 'VERY_LOW',
      original_automated_decision: 'ESCALATE_CONFLICT',
      original_evidence_state: 'CONFLICTING',
      created_at: '2024-02-22T11:45:00Z',
      updated_at: '2024-02-22T11:45:00Z',
    },
    {
      id: 'rev-03',
      idea_id: 'idea-syn-02',
      submission_code: 'IDEA-2024-0108',
      idea_title: 'Cylinder head wall thickness optimization across 100cc portfolio',
      review_status: 'PENDING_REVIEW',
      review_priority: 'HIGH_P1',
      routing_reasons: [
        'HIGH_VALUE_OPPORTUNITY: Net annual opportunity (₹1.4 Crore) exceeds threshold.',
      ],
      is_safety_critical: false,
      is_escalated: false,
      calibrated_confidence_score: 0.78,
      confidence_tier: 'MEDIUM',
      original_automated_decision: 'REQUIRES_EXECUTIVE_STUDY',
      original_evidence_state: 'PARTIALLY_CONFIRMED',
      created_at: '2024-02-18T14:15:00Z',
      updated_at: '2024-02-18T14:15:00Z',
    },
  ];

  useEffect(() => {
    fetchQueue();
  }, [priorityFilter, statusFilter, safetyOnly]);

  return (
    <div className="governance-queue-workspace animate-fade-in">
      {/* Header & Overview */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', letterSpacing: '-0.3px', margin: 0 }}>
            Human-in-the-Loop Governance & Review Queue
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Prioritized review queue enforcing mandatory human review for safety-critical systems, conflicting evidence resolution, high-value opportunities, and calibrated AI score verification.
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('human-review-queue')}
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
            <span>Manual Ch. 14</span>
          </button>
        )}
      </div>

      {/* Priority Summary Badges */}
      <div className="grid-4" style={{ marginBottom: '16px' }}>
        <div className="card card-interactive" style={{ marginBottom: 0, borderTop: '2px solid var(--hero-red)', padding: '12px 14px' }}>
          <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldAlert size={12} color="var(--hero-red)" />
            Critical / Safety (P0)
          </div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '3px' }}>
            {queue.filter((q) => q.review_priority === 'CRITICAL_P0').length} Items
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Mandatory Human Gates</div>
        </div>

        <div className="card card-interactive" style={{ marginBottom: 0, borderTop: '2px solid var(--status-warning)', padding: '12px 14px' }}>
          <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ArrowUpRight size={12} color="var(--status-warning)" />
            High Value / Low Conf (P1)
          </div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '3px' }}>
            {queue.filter((q) => q.review_priority === 'HIGH_P1').length} Items
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>≥ ₹1 Cr Opp or &lt;65% Conf</div>
        </div>

        <div className="card card-interactive" style={{ marginBottom: 0, borderTop: '2px solid var(--border-strong)', padding: '12px 14px' }}>
          <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Layers size={12} color="var(--white)" />
            Cross-Model Fits (P2)
          </div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '3px' }}>
            {queue.filter((q) => q.review_priority === 'MEDIUM_P2').length} Items
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Multi-Platform Sibling Opportunities</div>
        </div>

        <div className="card card-interactive" style={{ marginBottom: 0, borderTop: '2px solid var(--border-subtle)', padding: '12px 14px' }}>
          <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <MinusCircle size={12} color="var(--text-muted)" />
            Routine Reviews (P3)
          </div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '3px' }}>
            {queue.filter((q) => q.review_priority === 'LOW_P3').length} Items
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Low Impact Standard Ideas</div>
        </div>
      </div>

      {/* Control Bar: Filters */}
      <div
        className="card"
        style={{
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div>
            <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
              Priority Level
            </label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value as any)}
              style={{ minWidth: '180px' }}
            >
              <option value="">All Priorities</option>
              <option value="CRITICAL_P0">P0: Critical / Safety</option>
              <option value="HIGH_P1">P1: High Value / Low Conf</option>
              <option value="MEDIUM_P2">P2: Cross-Model Fit</option>
              <option value="LOW_P3">P3: Routine</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
              Review Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              style={{ minWidth: '180px' }}
            >
              <option value="">All Review Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="APPROVED">Approved</option>
              <option value="OVERRIDDEN">Overridden</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '16px' }}>
            <input
              type="checkbox"
              id="safetyOnly"
              checked={safetyOnly}
              onChange={(e) => setSafetyOnly(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="safetyOnly" style={{ fontSize: '12px', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertTriangle size={12} color="var(--hero-red)" />
              Safety Critical Systems Only (Brakes / Steering / Suspension / Frame)
            </label>
          </div>
        </div>
      </div>

      {/* Queue Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              <th style={{ width: '160px' }}>Priority</th>
              <th style={{ width: '220px' }}>Idea Code & Title</th>
              <th>Routing Reason / Safety Gate</th>
              <th style={{ width: '160px' }}>Calibrated Conf</th>
              <th style={{ width: '170px' }}>Evidence State</th>
              <th style={{ width: '140px' }}>Review Status</th>
              <th style={{ width: '100px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((item) => (
              <tr
                key={item.id}
                style={{
                  cursor: 'pointer',
                  backgroundColor: item.is_safety_critical ? 'rgba(255, 0, 0, 0.04)' : undefined,
                }}
                onClick={() => onSelectIdea(item.idea_id)}
              >
                <td>
                  <StatusBadge type="priority" value={item.review_priority} />
                </td>
                <td>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--accent-blue)', fontSize: '12px' }}>
                    {item.submission_code}
                  </div>
                  <div style={{ color: 'var(--text-primary)', fontWeight: '500', marginTop: '2px' }}>
                    {item.idea_title}
                  </div>
                </td>
                <td>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {item.routing_reasons.map((r, i) => (
                      <div key={i} style={{ marginBottom: '2px' }}>
                        • {r}
                      </div>
                    ))}
                  </div>
                </td>
                <td>
                  <StatusBadge type="confidence" value={item.confidence_tier} />
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    Score: {(item.calibrated_confidence_score * 100).toFixed(0)}%
                  </div>
                </td>
                <td>
                  <StatusBadge type="evidence" value={item.original_evidence_state} />
                </td>
                <td>
                  <StatusBadge type="review_status" value={item.review_status} />
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectIdea(item.idea_id);
                    }}
                    className="btn-secondary"
                    style={{ fontSize: '11px', padding: '3px 8px' }}
                  >
                    <span>Review</span>
                    <ArrowRight size={11} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
