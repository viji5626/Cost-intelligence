import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Lightbulb,
  Factory,
  ShieldAlert,
  Calculator,
  FolderInput,
  Cpu,
  ScrollText,
  Terminal,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  LucideIcon,
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingReviewsCount?: number;
}

interface NavGroup {
  groupName: string;
  items: {
    id: string;
    label: string;
    icon: LucideIcon;
    badge?: string;
    isCritical?: boolean;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  pendingReviewsCount = 14,
}) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  useEffect(() => {
    const saved = localStorage.getItem('hero-sidebar-collapsed');
    if (saved !== null) {
      setIsCollapsed(saved === 'true');
    }
  }, []);

  const toggleCollapse = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem('hero-sidebar-collapsed', String(next));
  };

  const navGroups: NavGroup[] = [
    {
      groupName: 'OVERVIEW',
      items: [
        { id: 'overview', label: 'Executive Dashboard', icon: LayoutDashboard },
      ],
    },
    {
      groupName: 'OPERATIONS',
      items: [
        { id: 'opex', label: 'Plant OPEX & Benchmark', icon: Factory },
        { id: 'opportunity', label: 'Opportunity Simulator', icon: Calculator },
      ],
    },
    {
      groupName: 'ENGINEERING INTELLIGENCE',
      items: [
        { id: 'ideathon', label: 'Vehicle Ideathon (10K+)', icon: Lightbulb },
        {
          id: 'governance',
          label: 'Human Review & Safety',
          icon: ShieldAlert,
          badge: `${pendingReviewsCount}`,
          isCritical: true,
        },
      ],
    },
    {
      groupName: 'DATA',
      items: [
        { id: 'ingestion', label: 'Data Ingestion Studio', icon: FolderInput },
      ],
    },
    {
      groupName: 'SYSTEM',
      items: [
        { id: 'aistudio', label: 'AI Studio Workspace', icon: Terminal },
        { id: 'hardware', label: 'Hardware & AI Runtime', icon: Cpu },
        { id: 'audit', label: 'Security & Audit Log', icon: ScrollText },
      ],
    },
    {
      groupName: 'HELP & MANUAL',
      items: [
        { id: 'help', label: 'Help & User Manual', icon: BookOpen },
      ],
    },
  ];

  return (
    <aside
      style={{
        width: isCollapsed ? '60px' : '230px',
        backgroundColor: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        padding: isCollapsed ? '12px 6px' : '14px 10px',
        transition: 'width var(--transition-fast)',
        userSelect: 'none',
        overflowX: 'hidden',
        overflowY: 'auto',
        position: 'relative',
      }}
    >
      {/* Collapse / Expand Toggle Button */}
      <div
        style={{
          display: 'flex',
          justifyContent: isCollapsed ? 'center' : 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
          padding: '0 4px',
        }}
      >
        {!isCollapsed && (
          <span
            style={{
              fontSize: '10px',
              fontWeight: '700',
              color: 'var(--text-muted)',
              letterSpacing: '0.6px',
            }}
          >
            NAVIGATION
          </span>
        )}
        <button
          onClick={toggleCollapse}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-tertiary)',
          }}
        >
          {isCollapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
        </button>
      </div>

      {/* Navigation Groups */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
        {navGroups.map((group) => (
          <div key={group.groupName} style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
            {!isCollapsed && (
              <div
                style={{
                  fontSize: '9px',
                  fontWeight: '700',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.6px',
                  padding: '4px 8px 2px 8px',
                }}
              >
                {group.groupName}
              </div>
            )}

            {group.items.map((item) => {
              const isActive = activeTab === item.id;
              const Icon = item.icon;

              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  title={isCollapsed ? item.label : undefined}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: isCollapsed ? 'center' : 'space-between',
                    padding: isCollapsed ? '8px 0' : '7px 8px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    borderLeft: isActive ? '3px solid var(--hero-red)' : '3px solid transparent',
                    backgroundColor: isActive ? 'var(--bg-tertiary)' : 'transparent',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: isActive ? '700' : '500',
                    textAlign: 'left',
                    transition: 'all var(--transition-fast)',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Icon size={14} color={isActive ? 'var(--hero-red)' : 'var(--text-muted)'} />
                    {!isCollapsed && <span>{item.label}</span>}
                  </div>

                  {item.badge && !isCollapsed && (
                    <span
                      style={{
                        backgroundColor: item.isCritical ? 'rgba(255, 0, 0, 0.12)' : 'var(--bg-card)',
                        color: item.isCritical ? 'var(--hero-red)' : 'var(--text-secondary)',
                        border: item.isCritical ? '1px solid var(--hero-red-border)' : '1px solid var(--border-subtle)',
                        fontSize: '9px',
                        fontWeight: '700',
                        fontFamily: 'var(--font-mono)',
                        padding: '1px 5px',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}

                  {item.badge && isCollapsed && (
                    <span
                      style={{
                        position: 'absolute',
                        top: '4px',
                        right: '8px',
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        backgroundColor: item.isCritical ? 'var(--hero-red)' : 'var(--status-info)',
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom System Status */}
      {!isCollapsed ? (
        <div
          style={{
            marginTop: 'auto',
            padding: '8px 10px',
            backgroundColor: 'var(--bg-card)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            System Baseline
          </div>
          <div
            style={{
              fontSize: '10px',
              fontWeight: '600',
              color: 'var(--text-primary)',
              marginTop: '2px',
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <span style={{ display: 'inline-block', width: '5px', height: '5px', borderRadius: '50%', backgroundColor: 'var(--status-healthy)' }} />
            <span>v3.1.1-AIRGAP</span>
          </div>
        </div>
      ) : (
        <div
          title="v3.1.1-AIRGAP Online"
          style={{
            marginTop: 'auto',
            display: 'flex',
            justifyContent: 'center',
            padding: '6px 0',
          }}
        >
          <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--status-healthy)' }} />
        </div>
      )}
    </aside>
  );
};
