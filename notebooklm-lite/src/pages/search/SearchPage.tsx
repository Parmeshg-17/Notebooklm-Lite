import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Sparkles, BookOpen, FileText, ArrowRight } from 'lucide-react';
import { useNotebookStore } from '../../store';
import { apiClient } from '../../services/api/client';
import type { SearchResult } from '../../types';

export default function SearchPage() {
  const navigate = useNavigate();
  const { notebooks, setActiveNotebook } = useNotebookStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);

  useEffect(() => {
    if (!query.trim()) {
      // Default to user's real notebooks
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
    }, 250);

    return () => clearTimeout(timer);
  }, [query, notebooks]);

  const handleSelectResult = (result: SearchResult) => {
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
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-display-lg font-bold" style={{ color: 'var(--color-on-surface)' }}>
          Search Knowledge Base
        </h1>
        <p className="text-body-md mt-1" style={{ color: 'var(--color-on-surface-variant)' }}>
          Query across all indexed documents, research notes, and synthesized answers.
        </p>
      </div>

      <div className="relative">
        <Search
          size={20}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-[--color-primary]"
        />
        <input
          type="text"
          autoFocus
          placeholder="Search by keywords, citations, equations, or methods..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 rounded-2xl text-body-lg shadow-sm outline-none border focus:border-[--color-primary]"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            borderColor: 'var(--color-outline-variant)',
            color: 'var(--color-on-surface)',
          }}
        />
      </div>

      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant]">
          <span>Search Results ({results.length})</span>
          <span>Enterprise RAG Index</span>
        </div>

        {results.map((r, i) => (
          <div
            key={i}
            onClick={() => handleSelectResult(r)}
            className="p-4 rounded-2xl border transition-all cursor-pointer group hover:bg-[--color-surface-container-low] hover:border-[--color-primary]"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                  style={{
                    backgroundColor:
                      r.type === 'content'
                        ? 'var(--color-primary-fixed)'
                        : r.type === 'notebook'
                        ? 'var(--color-tertiary-fixed)'
                        : 'var(--color-secondary-container)',
                    color:
                      r.type === 'content'
                        ? 'var(--color-primary)'
                        : r.type === 'notebook'
                        ? 'var(--color-tertiary)'
                        : 'var(--color-on-secondary-container)',
                  }}
                >
                  {r.type === 'content' ? (
                    <Sparkles size={18} />
                  ) : r.type === 'notebook' ? (
                    <BookOpen size={18} />
                  ) : (
                    <FileText size={18} />
                  )}
                </div>

                <div>
                  <h3 className="text-headline-sm font-semibold text-[--color-on-surface] group-hover:text-[--color-primary] transition-colors">
                    {r.title}
                  </h3>
                  {r.documentName && (
                    <p className="text-code-sm text-[--color-primary] font-medium mt-0.5">
                      Source: {r.documentName} {r.pageNumber ? `(Page ${r.pageNumber})` : ''}
                    </p>
                  )}
                  <p className="text-body-md text-[--color-on-surface-variant] mt-1.5 leading-relaxed">
                    {r.snippet}
                  </p>
                </div>
              </div>

              <ArrowRight size={18} className="text-[--color-on-surface-variant] group-hover:translate-x-1 group-hover:text-[--color-primary] transition-all flex-shrink-0 mt-1" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
