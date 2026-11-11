import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, BookOpen, FileText, Sparkles, ArrowRight } from 'lucide-react';
import { useUIStore, useNotebookStore } from '../../store';
import { apiClient } from '../../services/api/client';
import type { SearchResult } from '../../types';

export default function GlobalSearchModal() {
  const { closeSearch } = useUIStore();
  const { notebooks, setActiveNotebook } = useNotebookStore();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recentQueries] = useState<string[]>([
    'Research findings',
    'Architecture',
    'Overview',
    'Summary',
  ]);

  // Keyboard shortcut listener to close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeSearch();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [closeSearch]);

  useEffect(() => {
    if (!query.trim()) {
      setResults(
        notebooks.map((nb) => ({
          type: 'notebook',
          notebookId: nb.id,
          title: nb.title,
          snippet: nb.description || `Category: ${nb.tag}`,
          matchedTerms: [],
          score: 1.0,
        }))
      );
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await apiClient.get<SearchResult[]>(`/api/search?q=${encodeURIComponent(query.trim())}`);
        setResults(res || []);
      } catch {
        const q = query.toLowerCase();
        const filtered = notebooks
          .filter((nb) => nb.title.toLowerCase().includes(q) || (nb.description && nb.description.toLowerCase().includes(q)))
          .map((nb) => ({
            type: 'notebook' as const,
            notebookId: nb.id,
            title: nb.title,
            snippet: nb.description || '',
            matchedTerms: [query],
            score: 0.9,
          }));
        setResults(filtered);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, notebooks]);

  const contentMatches = results.filter((r) => r.type === 'content');
  const notebookMatches = results.filter((r) => r.type === 'notebook');
  const documentMatches = results.filter((r) => r.type === 'document');

  const handleSelectResult = (result: SearchResult) => {
    closeSearch();
    if (result.notebookId) {
      setActiveNotebook(result.notebookId);
      if (result.documentId) {
        navigate(`/workspace/${result.notebookId}/document/${result.documentId}`);
      } else {
        navigate(`/workspace/${result.notebookId}`);
      }
    } else {
      navigate('/notebooks');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
      style={{
        backgroundColor: 'rgba(23, 25, 31, 0.45)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeSearch();
      }}
    >
      <div
        className="w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          border: '1px solid var(--color-outline-variant)',
          maxHeight: '80vh',
        }}
      >
        {/* Search Input Bar */}
        <div
          className="flex items-center gap-3 px-4 py-3.5"
          style={{ borderBottom: '1px solid var(--color-outline-variant)' }}
        >
          <Search size={20} style={{ color: 'var(--color-primary)' }} />
          <input
            type="text"
            autoFocus
            placeholder="Search across all notebooks, documents, and synthesis..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent border-none outline-none text-headline-sm"
            style={{ color: 'var(--color-on-surface)' }}
          />
          {query ? (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded-md hover:bg-[--color-surface-container] text-[--color-on-surface-variant]"
            >
              <X size={16} />
            </button>
          ) : (
            <span
              className="text-code-sm px-2 py-0.5 rounded border"
              style={{
                backgroundColor: 'var(--color-surface-container-low)',
                color: 'var(--color-on-surface-variant)',
                borderColor: 'var(--color-outline-variant)',
              }}
            >
              ESC to close
            </span>
          )}
        </div>

        {/* Recent Search Chips */}
        {!query && (
          <div
            className="px-4 py-2.5 flex items-center gap-2 overflow-x-auto"
            style={{ backgroundColor: 'var(--color-surface-container-low)' }}
          >
            <span className="text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant]">
              Recent:
            </span>
            {recentQueries.map((item) => (
              <button
                key={item}
                onClick={() => setQuery(item)}
                className="px-2.5 py-1 rounded-full text-label-sm transition-colors cursor-pointer"
                style={{
                  backgroundColor: 'var(--color-surface-container-lowest)',
                  color: 'var(--color-on-surface)',
                  border: '1px solid var(--color-outline-variant)',
                }}
              >
                {item}
              </button>
            ))}
          </div>
        )}

        {/* Results Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {results.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-body-md" style={{ color: 'var(--color-on-surface-variant)' }}>
                No results found for "{query}"
              </p>
            </div>
          ) : (
            <>
              {/* Content Matches */}
              {contentMatches.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2 px-2 text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant]">
                    <Sparkles size={14} style={{ color: 'var(--color-primary)' }} />
                    <span>Content & Citations ({contentMatches.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {contentMatches.map((r, i) => (
                      <div
                        key={i}
                        onClick={() => handleSelectResult(r)}
                        className="p-3 rounded-xl transition-all cursor-pointer group hover:bg-[--color-surface-container-low]"
                        style={{ border: '1px solid transparent' }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-headline-sm font-semibold text-[--color-on-surface] group-hover:text-[--color-primary]">
                            {r.title}
                          </span>
                          {r.documentName && (
                            <span className="text-label-sm text-[--color-on-surface-variant]">
                              {r.documentName} {r.pageNumber ? `· p. ${r.pageNumber}` : ''}
                            </span>
                          )}
                        </div>
                        <p className="text-body-sm line-clamp-2 text-[--color-on-surface-variant]">
                          {r.snippet}
                        </p>
                        {r.matchedTerms.length > 0 && (
                          <div className="flex gap-1.5 mt-2">
                            {r.matchedTerms.map((term) => (
                              <span
                                key={term}
                                className="px-1.5 py-0.5 rounded text-code-sm font-medium"
                                style={{
                                  backgroundColor: 'var(--color-primary-fixed)',
                                  color: 'var(--color-on-primary-fixed-variant)',
                                }}
                              >
                                {term}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notebook Matches */}
              {notebookMatches.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2 px-2 text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant]">
                    <BookOpen size={14} style={{ color: 'var(--color-primary)' }} />
                    <span>Notebooks ({notebookMatches.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {notebookMatches.map((r, i) => (
                      <div
                        key={i}
                        onClick={() => handleSelectResult(r)}
                        className="flex items-center justify-between p-3 rounded-xl transition-all cursor-pointer group hover:bg-[--color-surface-container-low]"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: 'var(--color-primary-fixed)' }}
                          >
                            <BookOpen size={16} style={{ color: 'var(--color-primary)' }} />
                          </div>
                          <div>
                            <span className="text-headline-sm font-semibold text-[--color-on-surface] group-hover:text-[--color-primary]">
                              {r.title}
                            </span>
                            <p className="text-body-sm text-[--color-on-surface-variant] line-clamp-1">
                              {r.snippet}
                            </p>
                          </div>
                        </div>
                        <ArrowRight size={16} className="text-[--color-on-surface-variant] group-hover:translate-x-1 transition-transform" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Document Matches */}
              {documentMatches.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2 px-2 text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant]">
                    <FileText size={14} style={{ color: 'var(--color-primary)' }} />
                    <span>Documents ({documentMatches.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {documentMatches.map((r, i) => (
                      <div
                        key={i}
                        onClick={() => handleSelectResult(r)}
                        className="flex items-center justify-between p-3 rounded-xl transition-all cursor-pointer group hover:bg-[--color-surface-container-low]"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: 'var(--color-secondary-container)' }}
                          >
                            <FileText size={16} style={{ color: 'var(--color-on-secondary-container)' }} />
                          </div>
                          <div>
                            <span className="text-headline-sm font-semibold text-[--color-on-surface] group-hover:text-[--color-primary]">
                              {r.title}
                            </span>
                            <p className="text-body-sm text-[--color-on-surface-variant]">
                              {r.snippet}
                            </p>
                          </div>
                        </div>
                        <ArrowRight size={16} className="text-[--color-on-surface-variant] group-hover:translate-x-1 transition-transform" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer info */}
        <div
          className="px-4 py-2.5 flex items-center justify-between text-code-sm"
          style={{
            backgroundColor: 'var(--color-surface-container-low)',
            borderTop: '1px solid var(--color-outline-variant)',
            color: 'var(--color-on-surface-variant)',
          }}
        >
          <span>Use ⌘K to open anytime</span>
          <span>Enterprise Index Active · 42 sources grounded</span>
        </div>
      </div>
    </div>
  );
}
