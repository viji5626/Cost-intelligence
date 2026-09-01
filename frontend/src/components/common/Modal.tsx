import React from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = '580px',
}) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width,
          maxWidth: '92vw',
          maxHeight: '90vh',
          overflowY: 'auto',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-strong)',
          boxShadow: '0 20px 30px -10px rgba(0, 0, 0, 0.6)',
          padding: '20px',
          marginBottom: 0,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-header" style={{ marginBottom: '16px', paddingBottom: '8px' }}>
          <div className="card-title" style={{ fontSize: '15px' }}>
            {title}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={15} />
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
};
