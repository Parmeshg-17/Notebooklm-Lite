import React from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode | React.ElementType;
  iconPosition?: 'left' | 'right';
  children?: React.ReactNode;
}

const sizeStyles: Record<Size, string> = {
  sm: 'px-2.5 py-1 text-label-sm gap-1',
  md: 'px-3 py-1.5 text-label-md gap-1.5',
  lg: 'px-4 py-2 text-body-md gap-2',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconPosition = 'left',
  children,
  disabled,
  style,
  onMouseEnter,
  onMouseLeave,
  className = '',
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;

  const getBaseStyle = (): React.CSSProperties => {
    switch (variant) {
      case 'primary':
        return {
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-on-primary)',
          border: 'none',
        };
      case 'secondary':
        return {
          backgroundColor: 'var(--color-surface-container-lowest)',
          color: 'var(--color-on-surface)',
          border: '1px solid var(--color-outline-variant)',
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: 'var(--color-on-surface-variant)',
          border: 'none',
        };
      case 'danger':
        return {
          backgroundColor: 'var(--color-error-container)',
          color: 'var(--color-on-error-container)',
          border: 'none',
        };
      case 'outline':
        return {
          backgroundColor: 'transparent',
          color: 'var(--color-on-surface)',
          border: '1px solid var(--color-outline-variant)',
        };
    }
  };

  const getHoverStyle = (): React.CSSProperties => {
    switch (variant) {
      case 'primary':
        return { backgroundColor: 'var(--color-primary-container)' };
      case 'secondary':
        return { backgroundColor: 'var(--color-surface-container-high)' };
      case 'ghost':
        return { backgroundColor: 'var(--color-surface-variant)', color: 'var(--color-on-surface)' };
      case 'danger':
        return { backgroundColor: 'var(--color-error)', color: 'var(--color-on-error)' };
      case 'outline':
        return { backgroundColor: 'var(--color-surface-container-high)' };
    }
  };

  const [hovered, setHovered] = React.useState(false);

  const renderIcon = () => {
    if (!icon) return null;
    if (React.isValidElement(icon)) return icon;
    const Comp = icon as React.ElementType;
    return <Comp size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />;
  };

  return (
    <button
      {...rest}
      disabled={isDisabled}
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors cursor-pointer ${sizeStyles[size]} ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      style={{
        ...getBaseStyle(),
        ...(hovered && !isDisabled ? getHoverStyle() : {}),
        ...style,
      }}
      onMouseEnter={(e) => {
        setHovered(true);
        onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        setHovered(false);
        onMouseLeave?.(e);
      }}
    >
      {loading ? (
        <Loader2 size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} className="animate-spin" />
      ) : (
        iconPosition === 'left' && renderIcon()
      )}
      {children}
      {!loading && iconPosition === 'right' && renderIcon()}
    </button>
  );
}
