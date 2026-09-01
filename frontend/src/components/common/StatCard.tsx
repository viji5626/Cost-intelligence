import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
  accentColor?: string;
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendType = 'neutral',
  accentColor,
  icon,
}) => {
  let trendColor = 'var(--text-secondary)';
  if (trendType === 'positive') trendColor = 'var(--status-healthy)';
  if (trendType === 'negative') trendColor = 'var(--status-warning)';

  return (
    <div
      className="card card-interactive"
      style={{
        marginBottom: 0,
        borderTop: accentColor ? `2px solid ${accentColor}` : undefined,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '14px 16px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {title}
        </span>
        {icon && <span style={{ color: accentColor || 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>{icon}</span>}
      </div>

      <div style={{ marginTop: '10px', marginBottom: '6px' }}>
        <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', letterSpacing: '-0.5px' }}>
          {value}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
        {subtitle && <span style={{ color: 'var(--text-muted)' }}>{subtitle}</span>}
        {trend && (
          <span style={{ color: trendColor, fontWeight: '600', fontFamily: 'var(--font-mono)' }}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
};
