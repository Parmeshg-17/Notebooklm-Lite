import React from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  width?: string;
  footer?: React.ReactNode;
}

export default function Modal({ title, onClose, children, width = 'max-w-lg', footer }: ModalProps) {
  // Close on backdrop click
  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Close on Escape key
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(23, 25, 31, 0.20)' }}
      onClick={handleBackdrop}
    >
      <div
        className={`w-full ${width} rounded-xl shadow-2xl flex flex-col`}
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          border: '1px solid var(--color-outline-variant)',
          boxShadow: '0 12px 32px 0 rgba(23, 25, 31, 0.12), 0 2px 6px 0 rgba(23, 25, 31, 0.04)',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: '1px solid var(--color-outline-variant)' }}
        >
          <h2 className="text-headline-sm" style={{ color: 'var(--color-on-surface)' }}>
            {title}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--color-on-surface-variant)' }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-surface-container-high)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div
            className="px-5 py-4 flex items-center justify-end gap-2"
            style={{ borderTop: '1px solid var(--color-outline-variant)' }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

