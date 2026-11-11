import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles, ThumbsUp, ThumbsDown, Copy,
  Check, Bookmark
} from 'lucide-react';
import type { ChatMessage as ChatMessageType, Citation } from '../../types';
import { formatRelativeTime } from '../../utils/mockData';

export interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (citation: Citation) => void;
  onOpenViewer?: (citation: Citation) => void;
  onFeedback?: (messageId: string, type: 'positive' | 'negative') => void;
}

export default function ChatMessage({
  message,
  onCitationClick,
  onOpenViewer,
  onFeedback,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-3 shadow-xs"
          style={{
            backgroundColor: 'var(--color-primary-fixed)',
            color: 'var(--color-on-primary-fixed)',
          }}
        >
          <p className="text-body-md whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
          <div className="mt-1 text-right">
            <span
              className="text-code-sm opacity-60"
              style={{ color: 'var(--color-on-primary-fixed-variant)' }}
            >
              {formatRelativeTime(message.timestamp)}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex items-start gap-3 mb-6 group">
      {/* AI Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs"
        style={{
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-on-primary)',
        }}
      >
        <Sparkles size={16} />
      </div>

      {/* Message container */}
      <div className="flex-1 min-w-0">
        <div
          className="rounded-2xl rounded-tl-sm p-4 shadow-xs"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-1.5 py-2">
              <span className="w-2 h-2 rounded-full animate-bounce bg-[--color-primary]" />
              <span className="w-2 h-2 rounded-full animate-bounce delay-150 bg-[--color-primary]" />
              <span className="w-2 h-2 rounded-full animate-bounce delay-300 bg-[--color-primary]" />
              <span className="text-body-sm ml-2 text-[--color-on-surface-variant]">
                Synthesizing grounded answer...
              </span>
            </div>
          ) : (
            <>
              {/* Markdown Content */}
              <div
                className="text-body-md prose prose-sm max-w-none space-y-2 leading-relaxed"
                style={{ color: 'var(--color-on-surface)' }}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                    strong: ({ children }) => (
                      <strong className="font-semibold" style={{ color: 'var(--color-primary)' }}>
                        {children}
                      </strong>
                    ),
                    ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                    code: ({ children }) => (
                      <code
                        className="px-1.5 py-0.5 rounded text-code-sm font-mono"
                        style={{
                          backgroundColor: 'var(--color-surface-container-high)',
                          color: 'var(--color-primary)',
                        }}
                      >
                        {children}
                      </code>
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>

              {/* Citation Pills */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t flex flex-wrap gap-1.5" style={{ borderColor: 'var(--color-surface-container)' }}>
                  <div className="w-full flex items-center gap-1 text-label-sm font-medium mb-1" style={{ color: 'var(--color-on-surface-variant)' }}>
                    <Bookmark size={12} />
                    <span>Grounded Sources ({message.citations.length}):</span>
                  </div>
                  {message.citations.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => onCitationClick?.(c)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-label-sm transition-all hover:scale-105 cursor-pointer shadow-2xs group/cit"
                      style={{
                        backgroundColor: 'var(--color-primary-fixed)',
                        color: 'var(--color-on-primary-fixed-variant)',
                        border: '1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)',
                      }}
                      title={`${c.excerpt}\n(Click to inspect, click page number to view in PDF)`}
                    >
                      <span className="font-medium truncate max-w-[140px]">{c.documentName}</span>
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onOpenViewer) onOpenViewer(c);
                          else onCitationClick?.(c);
                        }}
                        className="text-code-sm px-1.5 py-0.5 rounded-full hover:underline font-mono"
                        style={{ backgroundColor: 'var(--color-surface-container-lowest)' }}
                        title="Open exact PDF page"
                      >
                        p. {c.pageNumber} ↗
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Action bar below assistant response */}
        {!message.isLoading && (
          <div className="flex items-center justify-between mt-1.5 px-2 text-code-sm text-[--color-on-surface-variant]">
            <div className="flex items-center gap-1">
              <button
                onClick={() => onFeedback?.(message.id, 'positive')}
                className="p-1 rounded hover:bg-[--color-surface-container] transition-colors"
                style={{
                  color: message.feedbackGiven === 'positive' ? 'var(--color-tertiary)' : 'inherit',
                }}
                title="Helpful response"
              >
                <ThumbsUp size={13} fill={message.feedbackGiven === 'positive' ? 'currentColor' : 'none'} />
              </button>

              <button
                onClick={() => onFeedback?.(message.id, 'negative')}
                className="p-1 rounded hover:bg-[--color-surface-container] transition-colors"
                style={{
                  color: message.feedbackGiven === 'negative' ? 'var(--color-error)' : 'inherit',
                }}
                title="Not helpful"
              >
                <ThumbsDown size={13} fill={message.feedbackGiven === 'negative' ? 'currentColor' : 'none'} />
              </button>

              <button
                onClick={handleCopy}
                className="p-1 rounded hover:bg-[--color-surface-container] transition-colors flex items-center gap-1 ml-1"
                title="Copy to clipboard"
              >
                {copied ? <Check size={13} style={{ color: 'var(--color-tertiary)' }} /> : <Copy size={13} />}
                {copied && <span className="text-[10px] text-[--color-tertiary]">Copied</span>}
              </button>
            </div>

            <div className="flex items-center gap-2">
              {message.tokenCount && (
                <span>~{message.tokenCount} tokens</span>
              )}
              <span>·</span>
              <span>{formatRelativeTime(message.timestamp)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
