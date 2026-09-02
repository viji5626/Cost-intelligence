import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSystemReadiness } from '../../context/SystemReadinessContext';
import { User, KeyRound, AlertTriangle, ArrowRight, Eye, EyeOff, Sun, Moon, ChevronDown } from 'lucide-react';
import { IndustrialBackground } from './IndustrialBackground';
import { BrandingPlates } from './BrandingPlates';
import { fetchAvailableUsers, AvailableUserItem } from '../../api/authApi';

const DEFAULT_USERS: AvailableUserItem[] = [
  {
    username: 'admin_hero',
    display_name: 'Chief Administrator',
    role: 'ADMINISTRATOR',
    department: 'MANAGEMENT',
    plant_scope: ['ALL'],
  },
  {
    username: 'plant_head_haridwar',
    display_name: 'Haridwar Plant Head',
    role: 'PLANT_HEAD',
    department: 'OPERATIONS',
    plant_scope: ['HARIDWAR'],
  },
];

export const LoginModal: React.FC = () => {
  const { login } = useAuth();
  const { refreshReadiness } = useSystemReadiness();

  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [username, setUsername] = useState('admin_hero');
  const [password, setPassword] = useState('HeroAdmin@2026!');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [userOptions, setUserOptions] = useState<AvailableUserItem[]>(DEFAULT_USERS);

  useEffect(() => {
    const savedTheme = (localStorage.getItem('hero-theme') as 'dark' | 'light') || 'dark';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Fetch registered active users from backend DB
    fetchAvailableUsers()
      .then((users) => {
        if (users && users.length > 0) {
          // Merge with default list avoiding duplicates
          const merged = [...users];
          DEFAULT_USERS.forEach((def) => {
            if (!merged.some((u) => u.username === def.username)) {
              merged.push(def);
            }
          });
          setUserOptions(merged);
        }
      })
      .catch(() => {
        // Fallback to default user accounts on offline/isolated cold starts
        setUserOptions(DEFAULT_USERS);
      });
  }, []);

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('hero-theme', next);
    document.documentElement.setAttribute('data-theme', next);
  };

  const handleUserChange = (selectedUsername: string) => {
    setUsername(selectedUsername);
    if (selectedUsername === 'admin_hero') {
      setPassword('HeroAdmin@2026!');
    } else if (selectedUsername === 'plant_head_haridwar') {
      setPassword('PlantHead@2026!');
    } else {
      setPassword('');
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      await refreshReadiness();
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials or check account lockout state.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay" data-theme={theme}>
      {/* 1. Animated Fine Particle Network Background */}
      <IndustrialBackground theme={theme} />

      {/* 2. Theme Switcher (Top Right) */}
      <button
        type="button"
        onClick={toggleTheme}
        className="auth-theme-toggle"
        title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
      >
        {theme === 'dark' ? <Sun size={13} color="#FBBF24" /> : <Moon size={13} color="#475569" />}
        <span>{theme === 'dark' ? 'LIGHT MODE' : 'DARK MODE'}</span>
      </button>

      {/* 3. Primary Authentication Card */}
      <div className="auth-card">
        {/* Header Branding */}
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
            <h1 className="auth-title">Hero Cost Intelligence</h1>
            <div className="auth-subtitle">Enterprise Authentication Gate</div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="auth-error-banner">
            <AlertTriangle size={18} style={{ flexShrink: 0, color: '#EF4444', marginTop: '1px' }} />
            <div>{error}</div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ marginTop: '4px' }}>
          {/* Registered User Dropdown Selector */}
          <div className="auth-input-group">
            <label className="auth-label">Registered User / Account</label>
            <div className="auth-input-wrapper" style={{ position: 'relative' }}>
              <User size={16} className="auth-input-icon" />
              <select
                value={username}
                onChange={(e) => handleUserChange(e.target.value)}
                className="auth-input"
                style={{
                  cursor: 'pointer',
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  paddingRight: '36px',
                }}
              >
                {userOptions.map((u) => (
                  <option key={u.username} value={u.username} style={{ backgroundColor: '#18181B', color: '#FFFFFF' }}>
                    {u.display_name} ({u.username}) — {u.role}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                style={{
                  position: 'absolute',
                  right: '12px',
                  pointerEvents: 'none',
                  color: 'var(--text-muted, #71717A)',
                }}
              />
            </div>
          </div>

          {/* Password Input */}
          <div className="auth-input-group">
            <label className="auth-label">Password</label>
            <div className="auth-input-wrapper">
              <KeyRound size={16} className="auth-input-icon" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="auth-input"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="auth-input-reveal"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            disabled={loading}
            className="auth-submit-btn"
            style={{ marginTop: '8px' }}
          >
            {loading ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <span>Sign In to Workstation</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Security Baseline Footer Note */}
        <div
          style={{
            marginTop: '20px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--status-healthy, #10B981)', display: 'inline-block' }} />
          <span>Air-Gapped • SHA-256 Ledger • 5-Attempt Lockout Guard</span>
        </div>
      </div>

      {/* 4. Theme-Aware Branding Plates in Bottom Corners */}
      <BrandingPlates theme={theme} />
    </div>
  );
};
