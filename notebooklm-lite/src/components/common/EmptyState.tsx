import React from 'react';
import type { LucideIcon } from 'lucide-react';
import Button from './Button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{ backgroundColor: 'var(--color-primary-fixed)' }}
      >
        <Icon size={28} style={{ color: 'var(--color-primary)' }} />
      </div>
      <h3 className="text-headline-sm mb-2" style={{ color: 'var(--color-on-surface)' }}>
        {title}
      </h3>
      <p className="text-body-md max-w-sm mb-6" style={{ color: 'var(--color-on-surface-variant)' }}>
        {description}
      </p>
      {action && (
        <Button variant="primary" icon={action.icon} onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

