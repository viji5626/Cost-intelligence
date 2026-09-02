import React, { useState, useEffect } from 'react';
import { User, Sun, Moon, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  activeTab?: string;
}

export const Header: React.FC<HeaderProps> = ({ activeTab = 'overview' }) => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const { currentUser, logout } = useAuth();

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
      case 'executive_copilot':
        return 'Executive Assistant';
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
      case 'users':
        return 'User & Access Management';
      case 'activity':
        return 'User Activity & Session Reconstruction';
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

  return (
    <header
      style={{
        height: 'var(--header-height)',
        backgroundColor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Left: Brand + Active Workspace Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#FFFFFF',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.25)',
          }}
        >
          <img
            src="/assets/hero_cim_logo.png"
            alt="Hero Cost Intelligence Model"
            style={{
              height: '22px',
              width: 'auto',
              display: 'block',
              objectFit: 'contain',
            }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Workstation /</span>
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
            {getWorkspaceTitle(activeTab)}
          </span>
        </div>
      </div>

      {/* Right: Clean Theme Toggle + User Session */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Theme Switcher */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 10px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            fontWeight: '600',
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
          }}
        >
          {theme === 'dark' ? <Sun size={12} color="var(--status-warning)" /> : <Moon size={12} color="var(--status-info)" />}
          <span>{theme === 'dark' ? 'LIGHT' : 'DARK'}</span>
        </button>

        {/* User Session Profile */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '3px 10px',
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
          }}
        >
          <div
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
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
            <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', lineHeight: 1.1 }}>
              {currentUser?.display_name || 'Chief Administrator'}
            </span>
            <span style={{ fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1.1 }}>
              {currentUser?.roles?.[0] || 'ADMINISTRATOR'} • {currentUser?.plant_scope?.join(', ') || 'ALL'}
            </span>
          </div>
          {currentUser && (
            <button
              onClick={() => logout()}
              title="Sign Out"
              style={{
                marginLeft: '6px',
                padding: '3px 5px',
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <LogOut size={12} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
