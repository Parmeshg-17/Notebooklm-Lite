import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, ArrowUp, Sparkles } from 'lucide-react';
import { useUIStore } from '../../store';

export interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  suggestedQueries?: string[];
  placeholder?: string;
}

const DEFAULT_SUGGESTIONS = [
  'Summarize the core architectural breakthroughs across all indexed papers',
  'What are the latency tradeoffs between FP8 and FP16 inference on H100?',
  'How does PagedAttention reduce KV-cache memory fragmentation?',
];

export default function ChatInput({
  onSend,
  disabled = false,
  suggestedQueries = DEFAULT_SUGGESTIONS,
  placeholder = 'Ask a question grounded in your documents...',
}: ChatInputProps) {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { openUploadModal } = useUIStore();

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  useEffect(() => {
    adjustHeight();
  }, [content]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = content.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleSuggestionClick = (query: string) => {
    if (disabled) return;
    onSend(query);
  };

  return (
    <div className="w-full flex flex-col gap-2">
      {/* Suggested question chips */}
      {suggestedQueries.length > 0 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          <Sparkles size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          {suggestedQueries.map((query, index) => (
            <button
              key={index}
              onClick={() => handleSuggestionClick(query)}
              disabled={disabled}
              className="px-2.5 py-1 rounded-full text-code-sm truncate max-w-xs transition-all cursor-pointer hover:border-[--color-primary] hover:text-[--color-primary] disabled:opacity-50"
              style={{
                backgroundColor: 'var(--color-surface-container-low)',
                border: '1px solid var(--color-outline-variant)',
                color: 'var(--color-on-surface-variant)',
              }}
              title={query}
            >
              {query}
            </button>
          ))}
        </div>
      )}

      {/* Input Box Container */}
      <div
        className="relative rounded-2xl shadow-sm transition-all focus-within:shadow-md"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          border: '1px solid color-mix(in srgb, var(--color-outline-variant) 60%, transparent)',
        }}
      >
        <div className="flex items-end gap-2 p-2.5">
          {/* Attach Button */}
          <button
            type="button"
            onClick={openUploadModal}
            className="p-2 rounded-xl transition-colors hover:bg-[--color-surface-container] text-[--color-on-surface-variant] hover:text-[--color-primary] flex-shrink-0"
            title="Attach or upload documents"
          >
            <Paperclip size={18} />
          </button>

          {/* Expanding Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-none outline-none resize-none py-1.5 text-body-md text-[--color-on-surface] placeholder:text-[--color-on-surface-variant]/60 min-h-[38px] max-h-[160px]"
          />

          {/* Send Button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!content.trim() || disabled}
            className="p-2 rounded-xl transition-all flex-shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
            style={{
              backgroundColor: 'var(--color-primary)',
              color: 'var(--color-on-primary)',
            }}
            title="Send (Enter)"
          >
            <ArrowUp size={18} />
          </button>
        </div>

        {/* Footer shortcuts hint */}
        <div
          className="flex items-center justify-between px-3 pb-2 text-[11px]"
          style={{ color: 'var(--color-on-surface-variant)' }}
        >
          <span>Grounded with active sources</span>
          <span>⏎ Send · ⇧⏎ New line</span>
        </div>
      </div>
    </div>
  );
}
