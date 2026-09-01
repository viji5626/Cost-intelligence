import React from 'react';
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  AlertTriangle,
  Layers,
  FileText,
  Search,
  MinusCircle,
  XCircle,
  ShieldAlert,
  ArrowUpRight,
} from 'lucide-react';
import {
  ConfidenceTier,
  IdeaDecisionState,
  ImplementationEvidenceState,
  ReviewPriority,
  ReviewStatus,
} from '../../types';

interface StatusBadgeProps {
  type: 'evidence' | 'decision' | 'priority' | 'confidence' | 'review_status';
  value: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  let badgeClass = 'badge badge-info';
  let label = value;
  let icon: React.ReactNode = null;

  switch (type) {
    case 'evidence': {
      const state = value as ImplementationEvidenceState;
      switch (state) {
        case 'IMPLEMENTED':
          badgeClass = 'badge badge-healthy';
          label = 'Implemented Confirmed';
          icon = <CheckCircle2 size={11} />;
          break;
        case 'PARTIALLY_CONFIRMED':
          badgeClass = 'badge badge-info';
          label = 'Partially Confirmed';
          icon = <Layers size={11} />;
          break;
        case 'HISTORICAL':
          badgeClass = 'badge badge-neutral';
          label = 'Historical Record';
          icon = <FileText size={11} />;
          break;
        case 'POTENTIAL_EVIDENCE':
          badgeClass = 'badge badge-warning';
          label = 'Potential Evidence';
          icon = <Search size={11} />;
          break;
        case 'NO_EVIDENCE_FOUND':
          badgeClass = 'badge badge-neutral';
          label = 'No Evidence Found';
          icon = <MinusCircle size={11} />;
          break;
        case 'INSUFFICIENT':
          badgeClass = 'badge badge-warning';
          label = 'Insufficient Evidence';
          icon = <AlertCircle size={11} />;
          break;
        case 'CONFLICTING':
          badgeClass = 'badge badge-hero';
          label = 'Conflicting Records';
          icon = <AlertTriangle size={11} />;
          break;
        default:
          badgeClass = 'badge badge-neutral';
          label = value;
      }
      break;
    }

    case 'decision': {
      const decision = value as IdeaDecisionState;
      switch (decision) {
        case 'SUBMITTED':
          badgeClass = 'badge badge-neutral';
          label = 'Submitted';
          icon = <FileText size={11} />;
          break;
        case 'UNDER_REVIEW':
          badgeClass = 'badge badge-info';
          label = 'Under Review';
          icon = <Clock size={11} />;
          break;
        case 'ACCEPTED_FOR_STUDY':
          badgeClass = 'badge badge-healthy';
          label = 'Accepted for Study';
          icon = <CheckCircle2 size={11} />;
          break;
        case 'APPROVED_FOR_IMPLEMENTATION':
          badgeClass = 'badge badge-healthy';
          label = 'Approved';
          icon = <CheckCircle2 size={11} />;
          break;
        case 'REJECTED':
          badgeClass = 'badge badge-neutral';
          label = 'Rejected';
          icon = <XCircle size={11} />;
          break;
        case 'ON_HOLD':
          badgeClass = 'badge badge-warning';
          label = 'On Hold';
          icon = <Clock size={11} />;
          break;
        default:
          badgeClass = 'badge badge-neutral';
          label = value;
      }
      break;
    }

    case 'priority': {
      const priority = value as ReviewPriority;
      switch (priority) {
        case 'CRITICAL_P0':
          badgeClass = 'badge badge-hero';
          label = 'P0 Critical / Safety';
          icon = <ShieldAlert size={11} />;
          break;
        case 'HIGH_P1':
          badgeClass = 'badge badge-warning';
          label = 'P1 High Value';
          icon = <ArrowUpRight size={11} />;
          break;
        case 'MEDIUM_P2':
          badgeClass = 'badge badge-info';
          label = 'P2 Cross-Model';
          icon = <Layers size={11} />;
          break;
        case 'LOW_P3':
          badgeClass = 'badge badge-neutral';
          label = 'P3 Routine';
          icon = <MinusCircle size={11} />;
          break;
        default:
          badgeClass = 'badge badge-neutral';
          label = value;
      }
      break;
    }

    case 'confidence': {
      const conf = value as ConfidenceTier;
      switch (conf) {
        case 'HIGH':
          badgeClass = 'badge badge-healthy';
          label = 'High Confidence';
          icon = <CheckCircle2 size={11} />;
          break;
        case 'MEDIUM':
          badgeClass = 'badge badge-info';
          label = 'Medium Confidence';
          icon = <Layers size={11} />;
          break;
        case 'LOW':
          badgeClass = 'badge badge-warning';
          label = 'Low Confidence';
          icon = <AlertCircle size={11} />;
          break;
        case 'VERY_LOW':
          badgeClass = 'badge badge-hero';
          label = 'Very Low Conf';
          icon = <AlertTriangle size={11} />;
          break;
        default:
          badgeClass = 'badge badge-neutral';
          label = value;
      }
      break;
    }

    case 'review_status': {
      const rev = value as ReviewStatus;
      switch (rev) {
        case 'PENDING_REVIEW':
          badgeClass = 'badge badge-warning';
          label = 'Pending Review';
          icon = <Clock size={11} />;
          break;
        case 'UNDER_REVIEW':
          badgeClass = 'badge badge-info';
          label = 'Under Review';
          icon = <Clock size={11} />;
          break;
        case 'APPROVED':
          badgeClass = 'badge badge-healthy';
          label = 'Approved';
          icon = <CheckCircle2 size={11} />;
          break;
        case 'OVERRIDDEN':
          badgeClass = 'badge badge-hero';
          label = 'Overridden';
          icon = <ShieldAlert size={11} />;
          break;
        case 'MORE_EVIDENCE_REQUESTED':
          badgeClass = 'badge badge-info';
          label = 'Evidence Req';
          icon = <Search size={11} />;
          break;
        case 'ESCALATED':
          badgeClass = 'badge badge-hero';
          label = 'Escalated';
          icon = <AlertTriangle size={11} />;
          break;
        default:
          badgeClass = 'badge badge-neutral';
          label = value;
      }
      break;
    }
  }

  return (
    <span className={badgeClass}>
      {icon}
      <span>{label}</span>
    </span>
  );
};
