import React from 'react';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { ModelLoadingProgress } from '../../types/aistudio';

interface ModelLoadingBarProps {
  progress: ModelLoadingProgress;
  onDismiss?: () => void;
}

export const ModelLoadingBar: React.FC<ModelLoadingBarProps> = ({ progress, onDismiss }) => {
  if (!progress.is_loading && progress.percentage === 0) {
    return null;
  }

  const isComplete = progress.percentage >= 100 && !progress.is_loading;

  return (
    <div
      style={{
        padding: '12px 16px',
        backgroundColor: isComplete ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-card)',
        border: `1px solid ${isComplete ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-subtle)'}`,
        borderRadius: 'var(--radius-sm)',
        marginBottom: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
        animation: 'fadeIn 0.2s ease-in-out',
      }}
    >
      {/* Top Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isComplete ? (
            <CheckCircle2 size={16} color="var(--status-healthy)" />
          ) : (
            <Loader2 size={16} className="spin-icon" color="var(--hero-red)" />
          )}
          <span style={{ fontWeight: '700', fontSize: '12px', color: 'var(--text-primary)' }}>
            {isComplete
              ? `Model Loaded: ${progress.target_model_name || progress.target_model_id}`
              : `Loading Model: ${progress.target_model_name || progress.target_model_id}`}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: 'var(--text-muted)' }}>
            ⏱️ {progress.elapsed_seconds.toFixed(1)}s elapsed
          </span>
          <span
            style={{
              fontWeight: '700',
              color: isComplete ? 'var(--status-healthy)' : 'var(--hero-red)',
              fontSize: '12px',
            }}
          >
            {progress.percentage}%
          </span>
          {isComplete && onDismiss && (
            <button
              onClick={onDismiss}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '10px',
                textDecoration: 'underline',
              }}
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      {/* Animated Progress Bar Track */}
      <div
        style={{
          width: '100%',
          height: '6px',
          backgroundColor: 'var(--bg-tertiary)',
          borderRadius: '3px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: `${progress.percentage}%`,
            height: '100%',
            backgroundColor: isComplete ? 'var(--status-healthy)' : 'var(--hero-red)',
            transition: 'width 0.25s ease-out',
            borderRadius: '3px',
            backgroundImage: isComplete
              ? 'none'
              : 'linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent)',
            backgroundSize: '20px 20px',
            animation: isComplete ? 'none' : 'progressStripe 1s linear infinite',
          }}
        />
      </div>

      {/* Stage Description & Step Indicators */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '10px',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
            {progress.stage_title}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '4px' }}>
          {[1, 2, 3, 4, 5].map((step) => {
            const isStepDone = progress.stage_index > step || isComplete;
            const isStepActive = progress.stage_index === step && !isComplete;
            return (
              <span
                key={step}
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: isStepDone
                    ? 'var(--status-healthy)'
                    : isStepActive
                    ? 'var(--hero-red)'
                    : 'var(--border-subtle)',
                  display: 'inline-block',
                }}
                title={`Stage ${step}`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};
