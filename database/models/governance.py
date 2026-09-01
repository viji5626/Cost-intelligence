"""
Governance, Human-in-the-Loop Review, and Confidence Calibration Models
Implements independent multi-dimensional governance state machines and immutable review audits.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class ReviewStatus(str, Enum):
    """Lifecycle states of the human review queue workflow."""
    NOT_REQUIRED = "NOT_REQUIRED"                    # Routine high-confidence non-safety item
    PENDING_REVIEW = "PENDING_REVIEW"                # Queued for specialist assignment
    UNDER_REVIEW = "UNDER_REVIEW"                    # Currently assigned and undergoing human review
    APPROVED = "APPROVED"                            # Formally approved by human specialist
    REJECTED = "REJECTED"                            # Formally rejected by human specialist
    OVERRIDDEN = "OVERRIDDEN"                        # System recommendation overridden with rationale
    MORE_EVIDENCE_REQUESTED = "MORE_EVIDENCE_REQUESTED" # Specialist requested additional CAD/ECN drawings
    ESCALATED = "ESCALATED"                          # Escalated to Chief Engineer / VAVE Committee


class ReviewPriority(str, Enum):
    """Deterministic urgency tiers for human review routing."""
    CRITICAL_P0 = "CRITICAL_P0"                      # Safety-critical systems (Brakes/Steering) or conflicting records
    HIGH_P1 = "HIGH_P1"                              # High financial opportunity (>= ₹1 Cr) or low AI confidence
    MEDIUM_P2 = "MEDIUM_P2"                          # Ambiguous taxonomy or cross-model portfolio impact
    LOW_P3 = "LOW_P3"                                # Standard routine clarification


class ReviewActionType(str, Enum):
    """Audit action types executed by reviewers."""
    ASSIGN = "ASSIGN"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    OVERRIDE = "OVERRIDE"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    ESCALATE = "ESCALATE"
    REOPEN = "REOPEN"


class ConfidenceTier(str, Enum):
    """Calibrated confidence tiers backed by measurable evidence criteria."""
    HIGH = "HIGH"                                    # Score >= 0.85 (Multi-source authoritative match)
    MEDIUM = "MEDIUM"                                # 0.65 <= Score < 0.85 (Single source or minor ambiguity)
    LOW = "LOW"                                      # 0.45 <= Score < 0.65 (Semantic only, weak ECN)
    VERY_LOW = "VERY_LOW"                            # Score < 0.45 (Unresolved taxonomy or severe conflict)


class IdeaReviewRecord(BaseModel):
    """
    Maintains the human review queue state, priority, and calibrated confidence metrics.
    Decoupled from IdeaDecisionState and ImplementationEvidenceState.
    """

    __tablename__ = "idea_review_records"

    idea_id: Mapped[str] = mapped_column(String(36), ForeignKey("idea_submissions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default=ReviewStatus.PENDING_REVIEW.value, index=True, nullable=False)
    review_priority: Mapped[str] = mapped_column(String(50), default=ReviewPriority.MEDIUM_P2.value, index=True, nullable=False)
    assigned_reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Deterministic Routing Rationale
    routing_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Calibrated Evidence-Based Confidence
    calibrated_confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence_tier: Mapped[str] = mapped_column(String(50), default=ConfidenceTier.MEDIUM.value, nullable=False)
    confidence_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Original Automated Baseline (Immutable preservation)
    original_automated_decision: Mapped[str] = mapped_column(String(50), default="REQUIRES_REVIEW", nullable=False)
    original_evidence_state: Mapped[str] = mapped_column(String(50), default="NOT_EVALUATED", nullable=False)

    # Final Decision Audit
    final_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    final_decision_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    final_decision_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    final_decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    idea: Mapped["IdeaSubmission"] = relationship("IdeaSubmission", back_populates="review_record")  # type: ignore
    actions: Mapped[List["IdeaReviewAction"]] = relationship("IdeaReviewAction", back_populates="review_record", cascade="all, delete-orphan")


class IdeaReviewAction(BaseModel):
    """
    Immutable chronological ledger of all human review actions and overrides.
    """

    __tablename__ = "idea_review_actions"

    review_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("idea_review_records.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)

    reviewer_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    review_record: Mapped["IdeaReviewRecord"] = relationship("IdeaReviewRecord", back_populates="actions")
