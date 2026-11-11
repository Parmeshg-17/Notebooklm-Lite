import { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, FileText, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, Maximize2,
  Download, Sparkles, Send, Highlighter
} from 'lucide-react';
import { useDocumentStore, useChatStore } from '../../store';
import Button from '../../components/common/Button';
import { config } from '../../config';

const FALLBACK_TIMESTAMP = '2026-11-01T00:00:00.000Z';

export default function DocumentViewerPage() {
  const { notebookId, documentId } = useParams<{ notebookId: string; documentId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const currentNotebookId = notebookId ?? 'nb-1';
  const currentDocId = documentId ?? '';

  const { documents, loadDocuments } = useDocumentStore();
  const { addMessage } = useChatStore();

  const initialPage = parseInt(searchParams.get('page') || '1', 10);
  const [page, setPage] = useState(initialPage > 0 ? initialPage : 1);
  const [zoom, setZoom] = useState(100);
  const [showCompanion, setShowCompanion] = useState(true);
  const [companionPrompt, setCompanionPrompt] = useState('');

  // Load documents if not already in store
  useEffect(() => {
    if (currentNotebookId) {
      loadDocuments(currentNotebookId);
    }
  }, [currentNotebookId, loadDocuments]);

  // Sync page from URL query param
  useEffect(() => {
    const p = parseInt(searchParams.get('page') || '', 10);
    if (!isNaN(p) && p > 0) {
      setPage(p);
    }
  }, [searchParams]);

  const doc = useMemo(() => {
    return (
      documents.find((d) => d.id === currentDocId) ?? {
        id: currentDocId,
        notebookId: currentNotebookId,
        name: 'Document.pdf',
        type: 'pdf' as const,
        size: 0,
        pageCount: 1,
        tokenCount: 0,
        status: 'indexed' as const,
        uploadedAt: FALLBACK_TIMESTAMP,
      }
    );
  }, [documents, currentDocId, currentNotebookId]);

  const totalPages = doc.pageCount || 10;
  const pdfUrl = `${config.api.baseUrl}/api/v1/documents/${doc.id}/file#page=${page}&zoom=${zoom}`;

  const handleAskAboutPassage = (query?: string) => {
    const q = query || `What are the key points on page ${page} of "${doc.name}"?`;
    addMessage(currentNotebookId, {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date().toISOString(),
    });
    navigate(`/workspace/${currentNotebookId}`);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden" style={{ backgroundColor: 'var(--color-surface)' }}>
      {/* ── Sticky Toolbar ── */}
      <div
        className="h-12 px-4 flex items-center justify-between border-b flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          borderColor: 'var(--color-outline-variant)',
        }}
      >
        {/* Left: Back & Document info */}
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            variant="ghost"
            icon={ArrowLeft}
            onClick={() => navigate(`/workspace/${currentNotebookId}`)}
          >
            Back
          </Button>

          <div className="h-4 w-px bg-[--color-outline-variant]" />

          <div className="flex items-center gap-2">
            <FileText size={16} style={{ color: 'var(--color-primary)' }} />
            <span className="text-label-md font-bold truncate max-w-xs" style={{ color: 'var(--color-on-surface)' }}>
              {doc.name}
            </span>
            <span
              className="text-code-sm px-1.5 py-0.2 rounded font-medium"
              style={{
                backgroundColor: 'var(--color-secondary-container)',
                color: 'var(--color-on-secondary-container)',
              }}
            >
              PDF
            </span>
          </div>
        </div>

        {/* Center: Page controls & Zoom */}
        <div className="flex items-center gap-4">
          {/* Page nav */}
          <div className="flex items-center gap-1.5 text-code-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded hover:bg-[--color-surface-container] disabled:opacity-30"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="font-semibold text-[--color-on-surface]">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded hover:bg-[--color-surface-container] disabled:opacity-30"
            >
              <ChevronRight size={16} />
            </button>
          </div>

          <div className="h-4 w-px bg-[--color-outline-variant]" />

          {/* Zoom controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 10))}
              className="p-1 rounded hover:bg-[--color-surface-container]"
              title="Zoom out"
            >
              <ZoomOut size={15} />
            </button>
            <span className="text-code-sm w-12 text-center font-medium">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(200, z + 10))}
              className="p-1 rounded hover:bg-[--color-surface-container]"
              title="Zoom in"
            >
              <ZoomIn size={15} />
            </button>
            <button
              onClick={() => setZoom(100)}
              className="p-1 rounded hover:bg-[--color-surface-container]"
              title="Fit width"
            >
              <Maximize2 size={14} />
            </button>
          </div>
        </div>

        {/* Right: Actions & AI Companion toggle */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            icon={Download}
            onClick={() => window.open(`${config.api.baseUrl}/api/v1/documents/${doc.id}/file`, '_blank')}
          />

          <Button
            size="sm"
            variant={showCompanion ? 'primary' : 'secondary'}
            icon={Sparkles}
            onClick={() => setShowCompanion(!showCompanion)}
          >
            AI Companion
          </Button>
        </div>
      </div>

      {/* ── Main Viewer Split View ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Real Embedded PDF Display */}
        <div
          className="flex-1 overflow-hidden p-4 flex flex-col items-center justify-center relative"
          style={{ backgroundColor: 'var(--color-surface-container-high)' }}
        >
          {doc.id ? (
            <iframe
              key={`${doc.id}-${page}`}
              src={pdfUrl}
              className="w-full h-full border-0 rounded-xl shadow-2xl bg-white"
              title={doc.name}
            />
          ) : (
            <div className="p-8 text-center text-slate-500">
              <FileText size={48} className="mx-auto mb-3 opacity-40" />
              <p className="font-semibold text-lg">{doc.name}</p>
              <p className="text-sm">Page {page} of {totalPages}</p>
            </div>
          )}
        </div>

        {/* ── AI Companion Panel (Right) ── */}
        {showCompanion && (
          <div
            className="w-96 flex flex-col h-full border-l overflow-hidden animate-in slide-in-from-right-4 duration-200"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
            }}
          >
            {/* Header */}
            <div
              className="p-3.5 border-b flex items-center justify-between"
              style={{ borderColor: 'var(--color-outline-variant)' }}
            >
              <div className="flex items-center gap-2">
                <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />
                <h3 className="text-label-md font-bold uppercase tracking-wider text-[--color-on-surface]">
                  Document Companion
                </h3>
              </div>
              <span className="text-code-sm text-[--color-on-surface-variant]">
                Grounded to p. {page}
              </span>
            </div>

            {/* Scrollable companion body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Document Overview Card */}
              <div
                className="rounded-xl p-3 border space-y-2"
                style={{
                  backgroundColor: 'var(--color-surface-container-low)',
                  borderColor: 'var(--color-outline-variant)',
                }}
              >
                <div className="flex items-center gap-1.5 text-label-sm font-semibold text-[--color-primary]">
                  <Highlighter size={14} />
                  <span>Document Details</span>
                </div>
                <div className="text-body-sm text-[--color-on-surface-variant] space-y-1">
                  <p><strong className="text-[--color-on-surface]">File:</strong> {doc.name}</p>
                  <p><strong className="text-[--color-on-surface]">Current Page:</strong> Page {page} of {totalPages}</p>
                  <p><strong className="text-[--color-on-surface]">Status:</strong> <span className="text-green-600 font-medium capitalize">{doc.status}</span></p>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  className="w-full mt-2"
                  onClick={() => handleAskAboutPassage()}
                >
                  Ask About Page {page} in Chat
                </Button>
              </div>

              {/* Quick Questions */}
              <div className="space-y-2">
                <span className="text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant] block">
                  Suggested Questions
                </span>
                {[
                  `What are the key findings in ${doc.name}?`,
                  `Summarize the methodology described on page ${page}.`,
                  `What are the most important conclusions of this document?`,
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleAskAboutPassage(q)}
                    className="w-full text-left p-2.5 rounded-lg text-body-sm transition-all border hover:border-[--color-primary] hover:bg-[--color-surface-container-low] text-[--color-on-surface]"
                    style={{ borderColor: 'var(--color-outline-variant)' }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Ask Dock */}
            <div className="p-3 border-t" style={{ borderColor: 'var(--color-outline-variant)' }}>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (companionPrompt.trim()) {
                    handleAskAboutPassage(companionPrompt.trim());
                  }
                }}
                className="flex items-center gap-1.5"
              >
                <input
                  type="text"
                  placeholder="Ask about this document..."
                  value={companionPrompt}
                  onChange={(e) => setCompanionPrompt(e.target.value)}
                  className="flex-1 px-3 py-1.5 rounded-lg text-code-sm outline-none border focus:border-[--color-primary]"
                  style={{
                    backgroundColor: 'var(--color-surface-container-low)',
                    borderColor: 'var(--color-outline-variant)',
                  }}
                />
                <button
                  type="submit"
                  disabled={!companionPrompt.trim()}
                  className="p-1.5 rounded-lg text-white disabled:opacity-40"
                  style={{ backgroundColor: 'var(--color-primary)' }}
                >
                  <Send size={14} />
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
