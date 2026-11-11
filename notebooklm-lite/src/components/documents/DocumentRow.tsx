import {
  FileText, FileCode, File, CheckCircle2,
  AlertCircle, Loader2, RotateCw, Trash2
} from 'lucide-react';
import type { Document } from '../../types';
import { formatTokens } from '../../utils/mockData';

export interface DocumentRowProps {
  document: Document;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onClick?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export default function DocumentRow({
  document,
  isSelected,
  onToggleSelect,
  onClick,
  onDelete,
}: DocumentRowProps) {
  const getFileIcon = () => {
    switch (document.type) {
      case 'pdf':
        return <FileText size={16} style={{ color: 'var(--color-primary)' }} />;
      case 'docx':
        return <FileCode size={16} style={{ color: '#2563eb' }} />;
      case 'txt':
      default:
        return <File size={16} style={{ color: 'var(--color-secondary)' }} />;
    }
  };

  const renderStatus = () => {
    switch (document.status) {
      case 'indexed':
        return (
          <span title="Indexed and ready for grounding" className="flex items-center text-label-sm font-medium gap-1" style={{ color: 'var(--color-tertiary)' }}>
            <CheckCircle2 size={14} />
          </span>
        );
      case 'processing':
        return (
          <div className="flex items-center gap-1.5 w-20" title={`Processing (${document.progress ?? 50}%)`}>
            <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-surface-container-high)' }}>
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${document.progress ?? 50}%`,
                  backgroundColor: 'var(--color-primary)',
                }}
              />
            </div>
            <span className="text-code-sm" style={{ color: 'var(--color-primary)' }}>
              {document.progress ?? 50}%
            </span>
          </div>
        );
      case 'uploading':
        return (
          <div className="flex items-center gap-1.5 w-20" title={`Uploading (${document.progress ?? 30}%)`}>
            <Loader2 size={13} className="animate-spin" style={{ color: 'var(--color-primary)' }} />
            <span className="text-code-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
              {document.progress ?? 30}%
            </span>
          </div>
        );
      case 'failed':
        return (
          <div className="flex items-center gap-1 text-label-sm font-medium" style={{ color: 'var(--color-error)' }}>
            <AlertCircle size={14} />
            <button
              onClick={(e) => {
                e.stopPropagation();
                // trigger retry
              }}
              title="Retry indexing"
              className="hover:opacity-80 p-0.5 rounded"
            >
              <RotateCw size={12} />
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      onClick={() => onClick?.(document.id)}
      className="group flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg transition-colors cursor-pointer select-none hover:bg-[--color-surface-container]"
      style={{
        backgroundColor: isSelected
          ? 'color-mix(in srgb, var(--color-primary-fixed) 40%, transparent)'
          : 'transparent',
      }}
    >
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => {
            e.stopPropagation();
            onToggleSelect(document.id);
          }}
          disabled={document.status !== 'indexed'}
          className="rounded cursor-pointer accent-[--color-primary] w-3.5 h-3.5"
          onClick={(e) => e.stopPropagation()}
        />

        {/* File Icon */}
        <div className="flex-shrink-0">{getFileIcon()}</div>

        {/* Filename & Details */}
        <div className="flex flex-col min-w-0 flex-1">
          <span
            className="text-body-md font-medium truncate"
            style={{ color: 'var(--color-on-surface)' }}
            title={document.name}
          >
            {document.name}
          </span>
          <div className="flex items-center gap-1.5 text-code-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            {(document.pageCount ?? 0) > 0 && <span>{document.pageCount} pages</span>}
            {(document.pageCount ?? 0) > 0 && (document.tokenCount ?? 0) > 0 && <span>·</span>}
            {(document.tokenCount ?? 0) > 0 && <span>{formatTokens(document.tokenCount!)} tokens</span>}
          </div>
        </div>
      </div>

      {/* Right status & Delete action on hover */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {renderStatus()}

        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(document.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[--color-surface-container-high] text-[--color-on-surface-variant] hover:text-[--color-error] transition-all"
            title="Remove document"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
