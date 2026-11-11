import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
  icon?: React.ElementType;
  progress?: {
    current: number;
    max: number;
    unit?: string;
  };
}

export default function MetricCard({
  label,
  value,
  change,
  changeLabel,
  trend,
  subtitle,
  icon: Icon,
  progress,
}: MetricCardProps) {
  const isPositive = trend === 'up' || (change !== undefined && change > 0);
  const isNegative = trend === 'down' || (change !== undefined && change < 0);

  return (
    <div
      className="rounded-xl p-5 shadow-xs transition-all hover:shadow-sm flex flex-col justify-between"
      style={{
        backgroundColor: 'var(--color-surface-container-lowest)',
        border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
      }}
    >
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-label-md font-medium uppercase tracking-wider" style={{ color: 'var(--color-on-surface-variant)' }}>
            {label}
          </span>
          {Icon && (
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'var(--color-primary-fixed)',
                color: 'var(--color-primary)',
              }}
            >
              <Icon size={16} />
            </div>
          )}
        </div>

        {/* Big value */}
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-display-lg font-bold tabular-nums" style={{ color: 'var(--color-on-surface)' }}>
            {value}
          </span>
        </div>

        {/* Progress bar if present */}
        {progress && (
          <div className="my-2">
            <div
              className="w-full h-1.5 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--color-surface-container-high)' }}
            >
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, (progress.current / progress.max) * 100)}%`,
                  backgroundColor: 'var(--color-primary)',
                }}
              />
            </div>
            <div className="flex justify-between text-code-sm mt-1" style={{ color: 'var(--color-on-surface-variant)' }}>
              <span>{progress.current} {progress.unit} used</span>
              <span>{progress.max} {progress.unit} quota</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer / Trend */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t" style={{ borderColor: 'var(--color-surface-container)' }}>
        {change !== undefined && (
          <div
            className="flex items-center gap-0.5 text-label-sm font-semibold"
            style={{
              color: isPositive
                ? 'var(--color-tertiary)'
                : isNegative
                ? 'var(--color-error)'
                : 'var(--color-on-surface-variant)',
            }}
          >
            {isPositive ? <TrendingUp size={14} /> : isNegative ? <TrendingDown size={14} /> : null}
            <span>{change > 0 ? `+${change}%` : `${change}%`}</span>
          </div>
        )}

        {(changeLabel || subtitle) && (
          <span className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            {changeLabel || subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
