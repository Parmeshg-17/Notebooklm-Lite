import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ChevronRight, Share2, Download, Settings,
  Upload, Search, FileText, CheckSquare, Square,
  Sparkles, Layers
} from 'lucide-react';
import {
  useNotebookStore, useDocumentStore,
  useChatStore, useUIStore
} from '../../store';
import { chatService } from '../../services/chat.service';
import DocumentRow from '../../components/documents/DocumentRow';
import ChatMessage from '../../components/chat/ChatMessage';
import ChatInput from '../../components/chat/ChatInput';
import CitationCard from '../../components/chat/CitationCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import type { Citation, ChatMessage as ChatMessageType } from '../../types';
import { formatTokens } from '../../utils/mockData';

const EMPTY_MESSAGES: ChatMessageType[] = [];
const FALLBACK_TIMESTAMP = '2026-11-01T00:00:00.000Z';

export default function WorkspacePage() {
  const { notebookId } = useParams<{ notebookId: string }>();
  const navigate = useNavigate();

  const currentNotebookId = notebookId ?? 'nb-1';

  const { notebooks, setActiveNotebook, loadNotebooks } = useNotebookStore();
  const {
    documents,
    selectedDocumentIds,
    loadDocuments,
    toggleSelectDocument,
    selectAllDocuments,
    deselectAllDocuments,
    removeDocument,
  } = useDocumentStore();
  const { getOrCreateSession, addMessage, updateMessage, loadHistory } = useChatStore();
  const { openUploadModal, setActiveDocument, setActiveCitation } = useUIStore();

  const [documentFilter, setDocumentFilter] = useState('');
  const [activeCitationDetail, setActiveCitationDetail] = useState<Citation | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<'sources' | 'chat' | 'citations'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync active notebook ID in store & load real data
  useEffect(() => {
    setActiveNotebook(currentNotebookId);
    loadNotebooks();
    loadDocuments(currentNotebookId);
    loadHistory(currentNotebookId);
  }, [currentNotebookId, setActiveNotebook, loadNotebooks, loadDocuments, loadHistory]);

  // Current notebook object
  const notebook = useMemo(() => {
    return (
      notebooks.find((n) => n.id === currentNotebookId) ?? {
        id: currentNotebookId,
        title: 'Notebook Workspace',
        description: 'Document-grounded research workspace',
        tag: 'Research',
        sourceCount: 0,
        lastModified: FALLBACK_TIMESTAMP,
        createdAt: FALLBACK_TIMESTAMP,
        collaborators: [],
        owner: 'User',
        isStarred: false,
        isShared: false,
      }
    );
  }, [notebooks, currentNotebookId]);

  // Documents for this notebook (strictly current notebook only, no dummy nb-1)
  const notebookDocs = useMemo(() => {
    return documents.filter((d) => d.notebookId === currentNotebookId);
  }, [documents, currentNotebookId]);

  const groundedCount = useMemo(() => {
    return notebookDocs.filter((d) => selectedDocumentIds.has(d.id)).length;
  }, [notebookDocs, selectedDocumentIds]);

  const filteredDocs = useMemo(() => {
    if (!documentFilter.trim()) return notebookDocs;
    return notebookDocs.filter((d) =>
      d.name.toLowerCase().includes(documentFilter.toLowerCase())
    );
  }, [notebookDocs, documentFilter]);

  // Total tokens of selected documents
  const selectedTokenCount = useMemo(() => {
    return notebookDocs
      .filter((d) => selectedDocumentIds.has(d.id))
      .reduce((acc, d) => acc + (d.tokenCount ?? 0), 0);
  }, [notebookDocs, selectedDocumentIds]);

  const allSelected =
    notebookDocs.length > 0 &&
    notebookDocs.every((d) => selectedDocumentIds.has(d.id));

  // Chat session & messages
  const session = getOrCreateSession(currentNotebookId);
  const messages = session ? session.messages : EMPTY_MESSAGES;

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Find all citations from the latest assistant message
  const latestCitations = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === 'assistant' && m.citations && m.citations.length > 0) {
        return m.citations;
      }
    }
    return [];
  }, [messages]);

  // Handle sending a message
  const handleSendMessage = async (content: string) => {
    const userMsgId = `msg-user-${Date.now()}`;
    const assistantMsgId = `msg-asst-${Date.now()}`;

    // 1. Add user message
    addMessage(currentNotebookId, {
      id: userMsgId,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    });

    // 2. Add placeholder loading assistant message
    addMessage(currentNotebookId, {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isLoading: true,
    });

    try {
      const response = await chatService.sendMessage({
        notebookId: currentNotebookId,
        content,
        selectedDocumentIds: Array.from(selectedDocumentIds),
      });

      updateMessage(currentNotebookId, assistantMsgId, {
        content: response.content,
        citations: response.citations,
        tokenCount: response.tokenCount,
        isLoading: false,
      });

      if (response.citations && response.citations.length > 0) {
        setActiveCitationDetail(response.citations[0]);
      }
    } catch {
      updateMessage(currentNotebookId, assistantMsgId, {
        content: 'An error occurred while generating a response. Please verify your RAG backend connection.',
        isLoading: false,
      });
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setActiveCitation(citation.id);
    setActiveCitationDetail(citation);
    setActiveDocument(citation.documentId);
    setMobileTab('citations');
  };

  const handleOpenViewer = (citation: Citation) => {
    setActiveDocument(citation.documentId);
    navigate(`/workspace/${currentNotebookId}/document/${citation.documentId}?page=${citation.pageNumber}`);
  };

  const handleExport = (format: 'markdown' | 'bibtex' | 'pdf') => {
    setExportOpen(false);
    const content = messages
      .map((m) => `### ${m.role === 'user' ? 'User' : 'Assistant'}\n${m.content}\n`)
      .join('\n---\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${notebook.title}.${format === 'bibtex' ? 'bib' : 'md'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden" style={{ backgroundColor: 'var(--color-surface)' }}>
      {/* ── Sub-header Strip ── */}
      <div
        className="min-h-12 px-3 sm:px-4 md:px-6 py-1.5 flex items-center justify-between border-b flex-shrink-0 gap-2"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          borderColor: 'var(--color-outline-variant)',
        }}
      >
        {/* Left: Breadcrumbs & status */}
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <Link
            to="/notebooks"
            className="text-label-sm sm:text-label-md font-medium text-[--color-on-surface-variant] hover:text-[--color-primary] transition-colors flex-shrink-0"
          >
            Notebooks
          </Link>
          <ChevronRight size={14} className="text-[--color-on-surface-variant] flex-shrink-0" />
          <span
            className="text-label-md sm:text-headline-sm font-bold truncate max-w-[130px] sm:max-w-xs md:max-w-sm"
            style={{ color: 'var(--color-on-surface)' }}
          >
            {notebook.title}
          </span>
          <div className="hidden sm:inline-flex">
            <Badge tag={notebook.tag} size="sm" />
          </div>

          <div
            className="hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded-full text-code-sm font-medium ml-2"
            style={{
              backgroundColor: 'var(--color-tertiary-fixed)',
              color: 'var(--color-on-tertiary-fixed-variant)',
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[--color-tertiary]" />
            <span>{groundedCount} sources grounded</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          {/* Share */}
          <Button
            size="sm"
            variant="ghost"
            icon={Share2}
            onClick={() => alert(`Shared workspace link for "${notebook.title}" copied to clipboard.`)}
          >
            <span className="hidden sm:inline">Share</span>
          </Button>

          {/* Export Dropdown */}
          <div className="relative">
            <Button
              size="sm"
              variant="secondary"
              icon={Download}
              onClick={() => setExportOpen(!exportOpen)}
            >
              <span className="hidden sm:inline">Export</span>
            </Button>
            {exportOpen && (
              <div
                className="absolute right-0 top-full mt-1 w-44 rounded-xl shadow-xl py-1 z-30 animate-in fade-in zoom-in-95"
                style={{
                  backgroundColor: 'var(--color-surface-container-lowest)',
                  border: '1px solid var(--color-outline-variant)',
                }}
              >
                <button
                  onClick={() => handleExport('markdown')}
                  className="w-full px-3 py-1.5 text-label-md text-left hover:bg-[--color-surface-container] text-[--color-on-surface]"
                >
                  Export Markdown (.md)
                </button>
                <button
                  onClick={() => handleExport('bibtex')}
                  className="w-full px-3 py-1.5 text-label-md text-left hover:bg-[--color-surface-container] text-[--color-on-surface]"
                >
                  Export BibTeX (.bib)
                </button>
                <button
                  onClick={() => alert('PDF export compiled with formatted citations.')}
                  className="w-full px-3 py-1.5 text-label-md text-left hover:bg-[--color-surface-container] text-[--color-on-surface]"
                >
                  Export Formatted PDF
                </button>
              </div>
            )}
          </div>

          {/* Settings */}
          <Button
            size="sm"
            variant="ghost"
            icon={Settings}
            onClick={() => navigate('/settings')}
          />
        </div>
      </div>

      {/* ── Mobile Tab Navigation Bar (Visible on mobile / small screens < lg) ── */}
      <div
        className="lg:hidden flex items-center border-b px-2 py-1.5 gap-1.5 flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          borderColor: 'var(--color-outline-variant)',
        }}
      >
        <button
          onClick={() => setMobileTab('sources')}
          className="flex-1 py-1.5 px-2 rounded-lg text-label-sm font-semibold flex items-center justify-center gap-1.5 transition-colors"
          style={{
            backgroundColor: mobileTab === 'sources' ? 'var(--color-primary-container)' : 'transparent',
            color: mobileTab === 'sources' ? 'var(--color-on-primary-container)' : 'var(--color-on-surface-variant)',
          }}
        >
          <Layers size={14} />
          <span>Sources ({notebookDocs.length})</span>
        </button>

        <button
          onClick={() => setMobileTab('chat')}
          className="flex-1 py-1.5 px-2 rounded-lg text-label-sm font-semibold flex items-center justify-center gap-1.5 transition-colors"
          style={{
            backgroundColor: mobileTab === 'chat' ? 'var(--color-primary-container)' : 'transparent',
            color: mobileTab === 'chat' ? 'var(--color-on-primary-container)' : 'var(--color-on-surface-variant)',
          }}
        >
          <Sparkles size={14} />
          <span>Chat</span>
        </button>

        <button
          onClick={() => setMobileTab('citations')}
          className="flex-1 py-1.5 px-2 rounded-lg text-label-sm font-semibold flex items-center justify-center gap-1.5 transition-colors"
          style={{
            backgroundColor: mobileTab === 'citations' ? 'var(--color-primary-container)' : 'transparent',
            color: mobileTab === 'citations' ? 'var(--color-on-primary-container)' : 'var(--color-on-surface-variant)',
          }}
        >
          <FileText size={14} />
          <span>Citations ({latestCitations.length})</span>
        </button>
      </div>

      {/* ── 3-Column Workspace Grid ── */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* ── LEFT COLUMN (col-span-3): Sources Panel ── */}
        <div
          className={`${mobileTab === 'sources' ? 'flex' : 'hidden'} lg:flex lg:col-span-3 flex-col h-full border-r overflow-hidden`}
          style={{
            backgroundColor: 'var(--color-surface-container-low)',
            borderColor: 'var(--color-outline-variant)',
          }}
        >
          {/* Panel Header */}
          <div
            className="p-3.5 border-b flex items-center justify-between"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
            }}
          >
            <div className="flex items-center gap-2">
              <Layers size={16} style={{ color: 'var(--color-primary)' }} />
              <h2 className="text-label-md font-bold uppercase tracking-wider text-[--color-on-surface]">
                Sources ({notebookDocs.length})
              </h2>
            </div>
            <Button
              size="sm"
              variant="primary"
              icon={Upload}
              onClick={openUploadModal}
            >
              Add
            </Button>
          </div>

          {/* Filter Bar */}
          <div className="p-2 border-b" style={{ borderColor: 'var(--color-outline-variant)' }}>
            <div className="relative">
              <Search
                size={14}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[--color-on-surface-variant]"
              />
              <input
                type="text"
                placeholder="Filter sources..."
                value={documentFilter}
                onChange={(e) => setDocumentFilter(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg text-code-sm outline-none"
                style={{
                  backgroundColor: 'var(--color-surface-container-lowest)',
                  border: '1px solid var(--color-outline-variant)',
                  color: 'var(--color-on-surface)',
                }}
              />
            </div>
          </div>

          {/* Selection Toolbar */}
          <div
            className="px-3 py-2 flex items-center justify-between text-code-sm border-b"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
              color: 'var(--color-on-surface-variant)',
            }}
          >
            <button
              onClick={() => {
                if (allSelected) deselectAllDocuments();
                else selectAllDocuments(currentNotebookId);
              }}
              className="flex items-center gap-1.5 hover:text-[--color-on-surface] font-medium"
            >
              {allSelected ? <CheckSquare size={14} /> : <Square size={14} />}
              <span>{allSelected ? 'Deselect All' : 'Select All'}</span>
            </button>
            <span>{formatTokens(selectedTokenCount)} tokens active</span>
          </div>

          {/* Document Rows Scrollable List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {filteredDocs.length === 0 ? (
              <div className="py-8 text-center text-body-sm text-[--color-on-surface-variant]">
                <FileText size={24} className="mx-auto mb-2 opacity-40" />
                <p>No documents found</p>
                <button
                  onClick={openUploadModal}
                  className="mt-2 text-label-sm font-semibold hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                >
                  Upload documents
                </button>
              </div>
            ) : (
              filteredDocs.map((doc) => (
                <DocumentRow
                  key={doc.id}
                  document={doc}
                  isSelected={selectedDocumentIds.has(doc.id)}
                  onToggleSelect={toggleSelectDocument}
                  onClick={(id) => {
                    setActiveDocument(id);
                    navigate(`/workspace/${currentNotebookId}/document/${id}`);
                  }}
                  onDelete={(id) => removeDocument(id)}
                />
              ))
            )}
          </div>
        </div>

        {/* ── CENTER COLUMN (col-span-6): Chat Panel ── */}
        <div
          className={`${mobileTab === 'chat' ? 'flex' : 'hidden'} lg:flex lg:col-span-6 flex-col h-full border-r overflow-hidden`}
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-outline-variant)',
          }}
        >
          {/* Chat Messages Scrollable Area */}
          <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
                  style={{ backgroundColor: 'var(--color-primary-fixed)' }}
                >
                  <Sparkles size={24} style={{ color: 'var(--color-primary)' }} />
                </div>
                <h3 className="text-headline-md font-bold mb-1" style={{ color: 'var(--color-on-surface)' }}>
                  Start grounding your questions
                </h3>
                <p className="text-body-md max-w-sm mb-6" style={{ color: 'var(--color-on-surface-variant)' }}>
                  Ask questions, summarize findings, or extract comparative matrices across your active sources.
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onCitationClick={handleCitationClick}
                  onOpenViewer={handleOpenViewer}
                  onFeedback={(msgId, type) => {
                    useChatStore.getState().updateMessage(currentNotebookId, msgId, { feedbackGiven: type });
                  }}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Sticky Bottom Input Bar */}
          <div
            className="p-2.5 sm:p-4 border-t"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
            }}
          >
            <ChatInput onSend={handleSendMessage} />
          </div>
        </div>

        {/* ── RIGHT COLUMN (col-span-3): Citation Context & Intelligence Panel ── */}
        <div
          className={`${mobileTab === 'citations' ? 'flex' : 'hidden'} lg:flex lg:col-span-3 flex-col h-full overflow-hidden`}
          style={{
            backgroundColor: 'var(--color-surface-container-low)',
          }}
        >
          {/* Panel Header */}
          <div
            className="p-3.5 border-b flex items-center justify-between"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              borderColor: 'var(--color-outline-variant)',
            }}
          >
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />
              <h2 className="text-label-md font-bold uppercase tracking-wider text-[--color-on-surface]">
                Citation Inspector
              </h2>
            </div>
            <span className="text-code-sm text-[--color-on-surface-variant]">
              {latestCitations.length} active
            </span>
          </div>

          {/* Citations List & Follow-ups */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-4">
            {activeCitationDetail && (
              <div>
                <span className="text-label-sm font-semibold uppercase tracking-wider text-[--color-primary] block mb-2">
                  Focused Citation
                </span>
                <CitationCard
                  citation={activeCitationDetail}
                  initiallyExpanded={true}
                  onOpenViewer={handleOpenViewer}
                />
              </div>
            )}

            <div>
              <span className="text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant] block mb-2">
                All Grounded Passages
              </span>
              {latestCitations.length === 0 ? (
                <div className="p-4 rounded-xl text-center border text-body-sm text-[--color-on-surface-variant]" style={{ borderColor: 'var(--color-outline-variant)' }}>
                  Ask a question to see primary source citations and relevance scores.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {latestCitations.map((cit) => (
                    <CitationCard
                      key={cit.id}
                      citation={cit}
                      onOpenViewer={handleOpenViewer}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Suggested Follow-up Queries */}
            <div
              className="p-3.5 rounded-xl border space-y-2.5"
              style={{
                backgroundColor: 'var(--color-surface-container-lowest)',
                borderColor: 'var(--color-outline-variant)',
              }}
            >
              <span className="text-label-sm font-semibold uppercase tracking-wider text-[--color-on-surface-variant] block">
                Suggested Follow-ups
              </span>
              <div className="space-y-1.5">
                {[
                  'What are the key findings in this document?',
                  'Summarize the core methodology and results.',
                  'What are the practical applications or recommendations?',
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    className="w-full text-left p-2 rounded-lg text-body-sm transition-colors hover:bg-[--color-surface-container] text-[--color-on-surface] border hover:border-[--color-primary]"
                    style={{ borderColor: 'transparent' }}
                  >
                    → {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
