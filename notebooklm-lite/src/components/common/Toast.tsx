import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface ToastProps {
  id?: string;
  type?: 'success' | 'error' | 'info';
  message: string;
  description?: string;
  duration?: number;
  onClose?: () => void;
}

export default function Toast({
  type = 'info',
  message,
  description,
  duration = 4000,
  onClose,
}: ToastProps) {
  React.useEffect(() => {
    if (!duration || !onClose) return;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const icons = {
    success: <CheckCircle2 size={18} style={{ color: 'var(--color-tertiary)' }} />,
    error: <AlertCircle size={18} style={{ color: 'var(--color-error)' }} />,
    info: <Info size={18} style={{ color: 'var(--color-primary)' }} />,
  };

  const borderColors = {
    success: 'var(--color-tertiary)',
    error: 'var(--color-error)',
    info: 'var(--color-primary)',
  };

  return (
    <div
      role="alert"
      className="flex items-start gap-3 p-3.5 rounded-xl shadow-lg transition-all animate-in fade-in slide-in-from-top-2"
      style={{
        backgroundColor: 'var(--color-surface-container-lowest)',
        borderLeft: `4px solid ${borderColors[type]}`,
        borderTop: '1px solid var(--color-outline-variant)',
        borderRight: '1px solid var(--color-outline-variant)',
        borderBottom: '1px solid var(--color-outline-variant)',
        maxWidth: '380px',
      }}
    >
      <div className="flex-shrink-0 mt-0.5">{icons[type]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-body-md font-semibold" style={{ color: 'var(--color-on-surface)' }}>
          {message}
        </p>
        {description && (
          <p className="text-body-sm mt-0.5" style={{ color: 'var(--color-on-surface-variant)' }}>
            {description}
          </p>
        )}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[--color-surface-container] transition-colors"
          style={{ color: 'var(--color-on-surface-variant)' }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
