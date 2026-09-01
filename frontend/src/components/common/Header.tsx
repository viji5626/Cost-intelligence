import React, { useState, useEffect } from 'react';
import { ShieldCheck, User, Sun, Moon, HelpCircle } from 'lucide-react';
import { HardwareStatusBadge } from './HardwareStatusBadge';

interface HeaderProps {
  activeTab?: string;
  onOpenHelp?: (chapterId?: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab = 'overview', onOpenHelp }) => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    const savedTheme = (localStorage.getItem('hero-theme') as 'dark' | 'light') || 'dark';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('hero-theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const getWorkspaceTitle = (tab: string) => {
    switch (tab) {
      case 'overview':
        return 'Executive Overview';
      case 'opex':
        return 'Plant OPEX & Benchmark';
      case 'opportunity':
        return 'Opportunity Simulator';
      case 'ideathon':
        return 'Vehicle Ideathon (10K+)';
      case 'idea-detail':
        return 'Idea Investigation & Lineage';
      case 'governance':
        return 'Human Review & Safety';
      case 'ingestion':
        return 'Data Ingestion Studio';
      case 'aistudio':
        return 'AI Studio Control Center';
      case 'hardware':
        return 'Hardware & Runtime';
      case 'audit':
        return 'Security & Audit Log';
      case 'help':
        return 'User Manual & Knowledge Base';
      default:
        return 'Engineering Workstation';
    }
  };

  const getChapterMapping = (tab: string) => {
    switch (tab) {
      case 'overview':
        return 'executive-dashboard';
      case 'opex':
        return 'plant-opex';
      case 'opportunity':
        return 'opportunity-valuation';
      case 'ideathon':
        return 'ideathon-search';
      case 'idea-detail':
        return 'evidence-grounding';
      case 'governance':
        return 'human-review-queue';
      case 'ingestion':
        return 'data-ingestion';
      case 'aistudio':
        return 'ai-studio-overview';
      case 'hardware':
        return 'hardware-profiles';
      case 'audit':
        return 'audit-provenance';
      default:
        return 'getting-started';
    }
  };

  return (
    <header
      style={{
        height: 'var(--header-height)',
        backgroundColor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Left: Brand + Active Workspace Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            backgroundColor: 'var(--hero-red)',
            color: '#FFFFFF',
            padding: '2px 7px',
            borderRadius: 'var(--radius-sm)',
            fontWeight: '900',
            fontSize: '11px',
            letterSpacing: '0.8px',
            lineHeight: 1.1,
          }}
        >
          HERO
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Workstation /</span>
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
            {getWorkspaceTitle(activeTab)}
          </span>
        </div>
      </div>

      {/* Center: Hardware Telemetry Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <HardwareStatusBadge />
      </div>

      {/* Right: Help Trigger + Airgap Badge + Theme Toggle + User Session */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Contextual Help Trigger */}
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp(getChapterMapping(activeTab))}
            title="Open Interactive Engineering Manual for this workspace"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              fontSize: '11px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <HelpCircle size={12} color="var(--status-info)" />
            <span>Help</span>
          </button>
        )}

        {/* Theme Switcher */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
          }}
        >
          {theme === 'dark' ? <Sun size={11} color="var(--status-warning)" /> : <Moon size={11} color="var(--status-info)" />}
          <span>{theme === 'dark' ? 'LIGHT' : 'DARK'}</span>
        </button>

        {/* Air-Gap Status Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--status-healthy)',
            backgroundColor: 'rgba(16, 185, 129, 0.08)',
            padding: '2px 7px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
          }}
        >
          <ShieldCheck size={11} />
          <span>Air-Gap Active</span>
        </div>

        {/* User Session Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <User size={12} color="var(--text-secondary)" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-primary)', lineHeight: 1.1 }}>
              Cost Engineer
            </span>
            <span style={{ fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1.1 }}>
              VAVE / Ops
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
