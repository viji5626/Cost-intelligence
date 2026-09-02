import React, { useState } from 'react';
import { bootstrapAdmin } from '../../api/authApi';
import { useAuth } from '../../context/AuthContext';
import { useSystemReadiness } from '../../context/SystemReadinessContext';
import { User, Mail, KeyRound, AlertTriangle, ArrowRight } from 'lucide-react';

export const FirstBootAdminSetupModal: React.FC = () => {
  const { setAuthSession } = useAuth();
  const { refreshReadiness } = useSystemReadiness();

  const [username, setUsername] = useState('admin_hero');
  const [email, setEmail] = useState('admin@hero.internal');
  const [displayName, setDisplayName] = useState('Chief Administrator');
  const [password, setPassword] = useState('HeroAdmin@2026!');
  const [confirmPassword, setConfirmPassword] = useState('HeroAdmin@2026!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const res = await bootstrapAdmin({
        username,
        email,
        display_name: displayName,
        password,
        confirm_password: confirmPassword,
      });

      setAuthSession(res.access_token, {
        user_id: res.user_id,
        username: res.username,
        display_name: res.display_name,
        roles: res.roles,
        plant_scope: res.plant_scope,
        department: res.department,
        session_id: res.session_id,
        is_active: true,
        is_superuser: true,
      });

      await refreshReadiness();
    } catch (err: any) {
      setError(err.message || 'Setup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card" style={{ maxWidth: '480px' }}>
        {/* Header */}
        <div className="auth-header" style={{ alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              backgroundColor: '#FFFFFF',
              padding: '5px 10px',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 2px 10px rgba(0, 0, 0, 0.4), 0 0 16px rgba(255, 0, 0, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <img
              src="/assets/hero_cim_logo.png"
              alt="Hero Cost Intelligence Model"
              style={{
                height: '34px',
                width: 'auto',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </div>
          <div>
            <h1 className="auth-title">First-Boot Administrator Setup</h1>
            <div className="auth-subtitle">Initialize Root Security & Governance Officer</div>
          </div>
        </div>

        {error && (
          <div className="auth-error-banner">
            <AlertTriangle size={18} style={{ flexShrink: 0, color: '#EF4444', marginTop: '1px' }} />
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="auth-input-group">
              <label className="auth-label">Username</label>
              <div className="auth-input-wrapper">
                <User size={16} className="auth-input-icon" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="auth-input"
                />
              </div>
            </div>

            <div className="auth-input-group">
              <label className="auth-label">Display Name</label>
              <div className="auth-input-wrapper">
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="auth-input"
                  style={{ paddingLeft: '14px' }}
                />
              </div>
            </div>
          </div>

          <div className="auth-input-group">
            <label className="auth-label">Email Address</label>
            <div className="auth-input-wrapper">
              <Mail size={16} className="auth-input-icon" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="auth-input"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="auth-input-group">
              <label className="auth-label">Password</label>
              <div className="auth-input-wrapper">
                <KeyRound size={16} className="auth-input-icon" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-input"
                />
              </div>
            </div>

            <div className="auth-input-group">
              <label className="auth-label">Confirm Password</label>
              <div className="auth-input-wrapper">
                <KeyRound size={16} className="auth-input-icon" />
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="auth-input"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="auth-submit-btn"
          >
            {loading ? (
              <span>Provisioning Root Administrator...</span>
            ) : (
              <>
                <span>Complete Initial Setup</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Footers & Air-Gap Assurance */}
        <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              padding: '4px 8px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <img
              src="/assets/hero_cim_footer.png"
              alt="Powered by Hero CIM"
              style={{ height: '18px', width: 'auto', objectFit: 'contain', borderRadius: '3px' }}
            />
            <img
              src="/assets/tasc_footer.png"
              alt="Engineered & Developed by Tenacious Automation"
              style={{ height: '18px', width: 'auto', objectFit: 'contain', borderRadius: '3px' }}
            />
          </div>

          <div className="auth-footer" style={{ marginTop: '0' }}>
            <div className="auth-footer-dot" />
            <span>Air-Gapped Setup • Zero External Dependencies • Local Secret Storage</span>
          </div>
        </div>
      </div>
    </div>
  );
};
