import React, { useEffect, useState } from 'react';
import {
  Lightbulb,
  Factory,
  TrendingUp,
  ShieldAlert,
  ArrowRight,
  FileText,
  AlertTriangle,
  Target,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Lock,
} from 'lucide-react';
import { StatCard } from '../common/StatCard';

export interface ExecutiveSummary {
  total_ideas_submitted: number;
  total_annual_opportunity_inr: number;
  total_verified_savings_inr: number;
  pending_reviews_count: number;
  safety_critical_reviews_count: number;
  active_plants_count: number;
  top_addressable_opex_plant: string;
  plant_opex_gap_inr: number;
}

interface ExecutiveDashboardProps {
  onNavigate: (tab: string) => void;
  onSelectIdea?: (ideaId: string) => void;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({ onNavigate, onSelectIdea }) => {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [showMethodology, setShowMethodology] = useState<boolean>(false);

  useEffect(() => {
    setSummary({
      total_ideas_submitted: 10480,
      total_annual_opportunity_inr: 1425000000,
      total_verified_savings_inr: 450000000,
      pending_reviews_count: 14,
      safety_critical_reviews_count: 2,
      active_plants_count: 6,
      top_addressable_opex_plant: 'Haridwar (Plant A)',
      plant_opex_gap_inr: 126000000,
    });
  }, []);

  return (
    <div className="executive-dashboard animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Executive Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.3px', margin: 0 }}>
            HERO Cost Intelligence Executive Overview
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Air-gapped dual-domain intelligence integrating Plant OPEX benchmarking with Vehicle Ideathon opportunity governance.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: '700',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            DEMO / SYNTHETIC DATA BASELINE
          </span>
          <button
            onClick={() => onNavigate('help')}
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
            <span>Manual Ch. 03</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Row (Tier 1: Core Decisions) */}
      <div className="grid-4">
        <StatCard
          title="Vehicle Ideathon Pipeline"
          value={summary ? summary.total_ideas_submitted.toLocaleString() : '10,480'}
          subtitle="Proposals across 10-tier vehicle hierarchy"
          icon={<Lightbulb size={15} />}
        />
        <StatCard
          title="Net Addressable Opportunity"
          value="₹142.5 Cr"
          subtitle="Portfolio valuation (Net of CAPEX)"
          accentColor="var(--status-healthy)"
          icon={<TrendingUp size={15} />}
          trend="+18.4% YoY"
          trendType="positive"
        />
        <StatCard
          title="Plant OPEX Addressable Gap"
          value="₹12.6 Cr"
          subtitle="Haridwar vs Dharuhera benchmark"
          icon={<Factory size={15} />}
        />
        <StatCard
          title="Pending Human Reviews"
          value="14 Cases"
          subtitle="2 P0 Safety Critical gates pending"
          accentColor="var(--hero-red)"
          icon={<ShieldAlert size={15} />}
        />
      </div>

      {/* Domain Split Cards (Tier 2: Evidence & Breakdown) */}
      <div className="grid-2">
        {/* Vehicle Cost Intelligence Column */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '13px' }}>
              <FileText size={14} color="var(--text-primary)" />
              <span>Vehicle Cost Opportunities & Governance</span>
            </div>
            <button
              onClick={() => onNavigate('ideathon')}
              style={{
                backgroundColor: 'transparent',
                color: 'var(--hero-red)',
                border: 'none',
                fontSize: '11px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>View All 10K+ Ideas</span>
              <ArrowRight size={11} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Implementation Confirmed</span>
              <span style={{ color: 'var(--status-healthy)', fontWeight: '700' }}>1,420 Ideas</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Partially Confirmed / Sibling Fit</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>890 Ideas</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Conflicting ECN Notices</span>
              <span style={{ color: 'var(--status-warning)', fontWeight: '700' }}>3 Cases (P0 Escalated)</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0' }}>
              <span style={{ color: 'var(--text-secondary)' }}>No Implementation Evidence Found</span>
              <span style={{ color: 'var(--text-muted)' }}>8,167 Ideas (Ready for VAVE study)</span>
            </div>
          </div>

          {/* Urgent Safety Gate Box */}
          <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--hero-red-border)', marginTop: 'auto' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--hero-red)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <AlertTriangle size={12} color="var(--hero-red)" />
              <span>Urgent Safety-Critical Human Gate Pending</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  IDEA-2024-0042: Front Brake Lever ADC12 Alloy
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Target: Splendor Plus & HF Deluxe (₹50 Lakh Net Opp)
                </div>
              </div>
              <button
                onClick={() => {
                  if (onSelectIdea) {
                    onSelectIdea('idea-syn-01');
                  } else {
                    onNavigate('governance');
                  }
                }}
                style={{
                  backgroundColor: 'var(--hero-red)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '5px 10px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>Review Gate</span>
                <ArrowRight size={11} />
              </button>
            </div>
          </div>
        </div>

        {/* Manufacturing Plant OPEX Benchmarking Column */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '13px' }}>
              <Factory size={14} color="var(--text-primary)" />
              <span>Manufacturing Plant OPEX Benchmarking</span>
            </div>
            <button
              onClick={() => onNavigate('opex')}
              style={{
                backgroundColor: 'transparent',
                color: 'var(--hero-red)',
                border: 'none',
                fontSize: '11px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>OPEX Workspace</span>
              <ArrowRight size={11} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Plant A (Haridwar) Unit OPEX</span>
              <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>₹595.00 / veh</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Plant B (Dharuhera - Best in Group)</span>
              <span style={{ color: 'var(--status-healthy)', fontWeight: '700' }}>₹520.00 / veh</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Comparability Score</span>
              <span style={{ color: 'var(--text-primary)' }}>88% (Capacity & Automation Aligned)</span>
            </div>
            <div className="kv-row" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '4px 0' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Primary Addressable Inefficiency</span>
              <span style={{ color: 'var(--text-primary)' }}>Electricity & Compressed Air (₹28.00/veh)</span>
            </div>
          </div>

          {/* Annual Opportunity Highlight */}
          <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginTop: 'auto' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--status-healthy)', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Target size={12} color="var(--status-healthy)" />
              <span>Verified Addressable Annual Opportunity</span>
            </div>
            <div style={{ fontSize: '18px', fontWeight: '800', color: 'var(--status-healthy)', fontFamily: 'var(--font-mono)' }}>
              ₹12.60 Crore / year
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Excludes non-addressable structural differences (temperature/climate & fixed overhead).
            </div>
          </div>
        </div>
      </div>

      {/* Tier 3: Collapsible Methodology & Architecture Disclosure */}
      <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
        <button
          onClick={() => setShowMethodology(!showMethodology)}
          style={{
            width: '100%',
            padding: '10px 14px',
            backgroundColor: 'var(--bg-card)',
            border: 'none',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            fontSize: '11px',
            fontWeight: '700',
            color: 'var(--text-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Lock size={12} color="var(--status-healthy)" />
            <span>Methodology, Air-Gap Guarantees & Cryptographic Lineage</span>
          </div>
          {showMethodology ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showMethodology && (
          <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-tertiary)', fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.5', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
                Deterministic Mathematical Valuation:
              </div>
              <p>
                All opportunity numbers are derived strictly using Python Decimal arithmetic across canonical PLM BOMs and volume records. Generative AI is strictly excluded from calculation paths.
              </p>
            </div>
            <div>
              <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
                Air-Gap & Socket Egress Filter:
              </div>
              <p>
                Local workstation execution is enforced with socket-level blocking of external IP addresses. All AI model inference runs on local hardware via GGUF format.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
