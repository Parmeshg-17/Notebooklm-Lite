import React from 'react';
import { X } from 'lucide-react';

export interface BadgeProps {
  tag?: string;
  size?: 'sm' | 'md';
  removable?: boolean;
  onRemove?: () => void;
  children?: React.ReactNode;
  className?: string;
}

export default function Badge({
  tag,
  size = 'md',
  removable = false,
  onRemove,
  children,
  className = '',
}: BadgeProps) {
  const label = children ?? tag ?? '';
  const text = typeof label === 'string' ? label.toLowerCase() : '';

  // Determine color scheme based on tag name or context
  let bg = 'var(--color-secondary-container)';
  let color = 'var(--color-on-secondary-container)';

  if (text.includes('machine learning') || text.includes('ml') || text.includes('genomics') || text.includes('ai')) {
    bg = 'var(--color-primary-fixed)';
    color = 'var(--color-on-primary-fixed-variant)';
  } else if (text.includes('infrastructure') || text.includes('biomed') || text.includes('success')) {
    bg = 'var(--color-tertiary-fixed)';
    color = 'var(--color-on-tertiary-fixed-variant)';
  } else if (text.includes('strategy') || text.includes('systems') || text.includes('finance')) {
    bg = 'var(--color-secondary-container)';
    color = 'var(--color-on-secondary-container)';
  } else if (text.includes('security') || text.includes('error') || text.includes('failed')) {
    bg = 'var(--color-error-container)';
    color = 'var(--color-on-error-container)';
  }

  const sizeClass = size === 'sm' ? 'px-1.5 py-0.5 text-label-sm' : 'px-2 py-0.5 text-label-md';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium transition-colors ${sizeClass} ${className}`}
      style={{ backgroundColor: bg, color }}
    >
      <span>{label}</span>
      {removable && onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="hover:opacity-75 focus:outline-none rounded-full"
        >
          <X size={size === 'sm' ? 10 : 12} />
        </button>
      )}
    </span>
  );
}
