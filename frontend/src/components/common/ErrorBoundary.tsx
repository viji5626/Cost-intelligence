import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <div className="card" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'left', borderLeft: '3px solid var(--hero-red)' }}>
            <div className="card-header">
              <div className="card-title" style={{ color: 'var(--hero-red)' }}>
                <AlertTriangle size={15} color="var(--hero-red)" />
                <span>Application Runtime Notice</span>
              </div>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
              An unexpected interface error occurred. Platform state and air-gapped data persistence remain intact.
            </p>
            {this.state.error && (
              <pre
                style={{
                  background: 'var(--bg-primary)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--hero-red)',
                  overflowX: 'auto',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {this.state.error.message}
              </pre>
            )}
            <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                <RefreshCw size={12} />
                <span>Reload Application</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
