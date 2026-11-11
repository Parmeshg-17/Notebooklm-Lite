export function NotebookCardSkeleton() {
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ backgroundColor: 'var(--color-surface-container-lowest)', border: '1px solid var(--color-surface-container-high)' }}
    >
      <div className="flex items-start justify-between">
        <div className="w-24 h-5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-6 h-6 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      </div>
      <div className="space-y-2">
        <div className="w-3/4 h-4 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-full h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
        <div className="w-2/3 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
      </div>
      <div className="pt-3 border-t flex items-center justify-between" style={{ borderColor: 'var(--color-surface-container)' }}>
        <div className="w-20 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-12 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      </div>
    </div>
  );
}

export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3 py-4">
      <div className="w-8 h-8 rounded-full flex-shrink-0 animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      <div className="flex-1 space-y-2">
        <div className="w-3/4 h-4 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-full h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
        <div className="w-2/3 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
      </div>
    </div>
  );
}

export function DocumentRowSkeleton() {
  return (
    <div className="flex items-center gap-2 p-2">
      <div className="w-3.5 h-3.5 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      <div className="w-5 h-5 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      <div className="flex-1 space-y-1">
        <div className="w-3/4 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-1/3 h-2.5 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
      </div>
    </div>
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="rounded-xl p-4 space-y-3" style={{ backgroundColor: 'var(--color-surface-container-lowest)' }}>
      <div className="flex items-start justify-between">
        <div className="w-24 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
        <div className="w-8 h-8 rounded-lg animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      </div>
      <div className="w-20 h-8 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container-high)' }} />
      <div className="w-28 h-3 rounded animate-pulse" style={{ backgroundColor: 'var(--color-surface-container)' }} />
    </div>
  );
}

