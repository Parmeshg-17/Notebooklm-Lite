import { useState } from 'react';
import { FileText, ExternalLink, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import type { Citation } from '../../types';

export interface CitationCardProps {
  citation: Citation;
  onOpenViewer?: (citation: Citation) => void;
  initiallyExpanded?: boolean;
}

export default function CitationCard({
  citation,
  onOpenViewer,
  initiallyExpanded = false,
}: CitationCardProps) {
  const [expanded, setExpanded] = useState(initiallyExpanded);

  const relevancePct = Math.round((citation.relevanceScore ?? 0.9) * 100);

  return (
    <div
      className="rounded-xl p-3.5 transition-all shadow-xs hover:shadow-sm"
      style={{
        backgroundColor: 'var(--color-surface-container-lowest)',
        border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: 'var(--color-primary-fixed)' }}
          >
            <FileText size={15} style={{ color: 'var(--color-primary)' }} />
          </div>
          <div className="min-w-0">
            <h4
              className="text-label-md font-semibold truncate"
              style={{ color: 'var(--color-on-surface)' }}
              title={citation.documentName}
            >
              {citation.documentName}
            </h4>
            <div className="flex items-center gap-1.5 text-code-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
              <span
                className="px-1.5 py-0.2 rounded font-medium"
                style={{ backgroundColor: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' }}
              >
                Page {citation.pageNumber}
              </span>
              <span>·</span>
              <span className="flex items-center gap-0.5 text-tertiary font-medium" style={{ color: 'var(--color-tertiary)' }}>
                <Sparkles size={11} />
                {relevancePct}% match
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Relevance Score Bar */}
      <div
        className="w-full h-1 rounded-full overflow-hidden mb-2.5"
        style={{ backgroundColor: 'var(--color-surface-container-high)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${relevancePct}%`,
            backgroundColor: relevancePct > 90 ? 'var(--color-tertiary)' : 'var(--color-primary)',
          }}
        />
      </div>

      {/* Excerpt */}
      <p
        className={`text-body-sm leading-relaxed transition-all ${
          expanded ? '' : 'line-clamp-3'
        }`}
        style={{ color: 'var(--color-on-surface-variant)' }}
      >
        "{citation.excerpt}"
      </p>

      {/* Actions */}
      <div
        className="mt-2.5 pt-2 flex items-center justify-between text-code-sm"
        style={{ borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 25%, transparent)' }}
      >
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[--color-on-surface-variant] hover:text-[--color-primary] transition-colors"
        >
          {expanded ? (
            <>
              <span>Less</span>
              <ChevronUp size={12} />
            </>
          ) : (
            <>
              <span>Expand excerpt</span>
              <ChevronDown size={12} />
            </>
          )}
        </button>

        {onOpenViewer && (
          <button
            onClick={() => onOpenViewer(citation)}
            className="flex items-center gap-1 font-medium hover:underline transition-colors"
            style={{ color: 'var(--color-primary)' }}
          >
            <span>View in PDF</span>
            <ExternalLink size={12} />
          </button>
        )}
      </div>
    </div>
  );
}
