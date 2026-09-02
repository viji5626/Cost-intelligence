import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer
      style={{
        height: '32px',
        minHeight: '32px',
        backgroundColor: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        fontSize: '11px',
        color: 'var(--text-muted)',
        zIndex: 40,
      }}
    >
      {/* Left: Hero CIM Banner Plate */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <img
          src="/assets/hero_cim_footer.png"
          alt="Powered by Hero CIM"
          style={{
            height: '20px',
            width: 'auto',
            objectFit: 'contain',
            borderRadius: '3px',
          }}
        />
      </div>

      {/* Right: Status & Audit Assurance + TASC Engineering Banner Plate */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-secondary)',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--status-healthy)',
            }}
          />
          <span>AIR-GAPPED WORKSTATION</span>
          <span>•</span>
          <span>SHA-256 AUDIT LEDGER</span>
          <span>•</span>
          <span>v3.1.1</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img
            src="/assets/tasc_footer.png"
            alt="Engineered & Developed by Tenacious Automation (TASC)"
            style={{
              height: '20px',
              width: 'auto',
              objectFit: 'contain',
              borderRadius: '3px',
            }}
          />
        </div>
      </div>
    </footer>
  );
};
