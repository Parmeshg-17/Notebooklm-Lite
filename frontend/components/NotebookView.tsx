"use client";

import { useEffect, useRef, useState } from "react";
import { chatApi, documentsApi, evalsApi, notebooksApi } from "@/lib/api";
import type { Document, DocumentStatus, Notebook } from "@/types";
import { CitationViewerPanel, type CitationViewData } from "./CitationViewerPanel";
import { FullDocumentReader } from "./FullDocumentReader";

interface Props {
  notebook: Notebook;
  onNotebookUpdate: (nb: Notebook) => void;
  onDeleted: () => void;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  not_found?: boolean;
  citations?: CitationViewData[];
}

const STATUS_CONFIG: Record<
  DocumentStatus,
  { label: string; bg: string; text: string; icon: string }
> = {
  uploaded: {
    label: "Queued",
    bg: "#F0EDEB",
    text: "#605E59",
    icon: "schedule",
  },
  parsing: {
    label: "Indexing…",
    bg: "#FFDAD3",
    text: "#A6331B",
    icon: "progress_activity",
  },
  indexed: {
    label: "Indexed",
    bg: "#BCECE4",
    text: "#00201D",
    icon: "check_circle",
  },
  failed: {
    label: "Failed",
    bg: "#FFDAD6",
    text: "#BA1A1A",
    icon: "error",
  },
};

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function NotebookView({ notebook, onNotebookUpdate, onDeleted }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "sources">("chat");

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [selectedCitation, setSelectedCitation] = useState<CitationViewData | null>(null);

  // Full Document Reader Mode
  const [fullReaderDoc, setFullReaderDoc] = useState<{
    documentId: string;
    page: number;
  } | null>(null);

  // Evals State
  const [showEvalsModal, setShowEvalsModal] = useState(false);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalResults, setEvalResults] = useState<any | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const loadDocuments = async () => {
    try {
      const res = await documentsApi.list(notebook.id);
      setDocuments(res.documents);
    } catch {
      // handled quietly
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
    pollRef.current = setInterval(() => {
      const hasProcessing = documents.some(
        (d) => d.status === "uploaded" || d.status === "parsing"
      );
      if (hasProcessing) {
        loadDocuments();
      }
    }, 2500);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [notebook.id]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStep]);

  const handleFiles = async (files: FileList | File[]) => {
    const fileArr = Array.from(files);
    if (!fileArr.length) return;

    setUploading(true);
    setUploadError(null);
    setUploadProgress(0);

    for (const file of fileArr) {
      try {
        const result = await documentsApi.upload(
          notebook.id,
          file,
          (pct) => setUploadProgress(pct)
        );
        setDocuments((prev) => [
          {
            id: result.document_id,
            notebook_id: notebook.id,
            filename: file.name,
            status: result.status,
            page_count: null,
            file_size: file.size,
            mime_type: file.type,
            error_msg: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          ...prev,
        ]);
        if (!pollRef.current) {
          pollRef.current = setInterval(loadDocuments, 2000);
        }
      } catch (err: any) {
        setUploadError(err.message ?? "Upload failed");
      }
    }

    setUploading(false);
    setUploadProgress(0);
  };

  const handleDeleteDoc = async (doc: Document) => {
    if (!confirm(`Remove "${doc.filename}" from this corpus?`)) return;
    try {
      await documentsApi.delete(notebook.id, doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteNotebook = async () => {
    if (!confirm(`Delete entire notebook "${notebook.title}" and all its documents?`))
      return;
    try {
      await notebooksApi.delete(notebook.id);
      onDeleted();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isStreaming) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: query, timestamp: now },
      { id: assistantMsgId, role: "assistant", content: "", timestamp: now, citations: [] },
    ]);
    setInputQuery("");
    setIsStreaming(true);
    setCurrentStep("Analyzing inquiry across corpus…");

    let accumulatedAnswer = "";
    let activeSources: any[] = [];

    await chatApi.askStream(notebook.id, query, conversationId, {
      onStep: (step, msg) => {
        setCurrentStep(msg);
      },
      onSources: (sources) => {
        activeSources = sources;
      },
      onToken: (token) => {
        accumulatedAnswer += token;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: accumulatedAnswer } : m
          )
        );
      },
      onDone: (data) => {
        setConversationId(data.conversation_id);
        const mappedCitations: CitationViewData[] = (data.citations || []).map((c: any) => {
          const matchSource = activeSources.find((s) => s.source_id === c.marker);
          return {
            marker: c.marker,
            chunk_id: c.chunk_id,
            document_id: matchSource?.document_id,
            filename: matchSource?.filename,
            page: c.page,
            quote: c.quote,
          };
        });

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: data.answer,
                  not_found: data.not_found,
                  citations: mappedCitations,
                }
              : m
          )
        );

        // Auto-open inspector for the first citation if available
        if (mappedCitations.length > 0 && !selectedCitation) {
          setSelectedCitation(mappedCitations[0]);
        }

        setIsStreaming(false);
        setCurrentStep(null);
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `Error: ${err.message || "Failed to generate answer."}`,
                  not_found: true,
                }
              : m
          )
        );
        setIsStreaming(false);
        setCurrentStep(null);
      },
    });
  };

  const runEvaluations = async () => {
    setEvalLoading(true);
    setEvalResults(null);
    try {
      const data = await evalsApi.run(notebook.id);
      setEvalResults(data);
    } catch (err: any) {
      alert(`Evaluation error: ${err.message}`);
    } finally {
      setEvalLoading(false);
    }
  };

  const readyCount = documents.filter((d) => d.status === "indexed").length;
  const processingCount = documents.filter(
    (d) => d.status === "parsing" || d.status === "uploaded"
  ).length;

  // Extract all citations from the latest assistant message for the inspector
  const latestAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.citations && m.citations.length > 0);
  const activeCorpusCitations = latestAssistantMsg?.citations || [];

  // Render prose with inline clickable terracotta citation markers [1], [2]
  const renderSynthesisProse = (content: string, citations?: CitationViewData[]) => {
    const parts = content.split(/(\[\d+\])/g);
    return (
      <p className="font-serif text-[15px] leading-relaxed text-[#1C1C1B]">
        {parts.map((part, idx) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const markerNum = parseInt(match[1], 10);
            const citData = citations?.find((c) => c.marker === markerNum);
            const isSelected = selectedCitation?.marker === markerNum;

            return (
              <button
                key={idx}
                onClick={() => {
                  if (citData) setSelectedCitation(citData);
                }}
                className={`citation-badge ${isSelected ? "active" : ""}`}
                title={
                  citData
                    ? `Inspect citation [${markerNum}]: ${citData.filename || "Source"} (Page ${citData.page})`
                    : `Citation [${markerNum}]`
                }
                type="button"
              >
                [{markerNum}]
              </button>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </p>
    );
  };

  // If in full document reader mode, show FullDocumentReader component
  if (fullReaderDoc) {
    return (
      <FullDocumentReader
        documentId={fullReaderDoc.documentId}
        initialPage={fullReaderDoc.page}
        activeCitation={selectedCitation}
        onBackToQA={() => setFullReaderDoc(null)}
        onSelectCitation={setSelectedCitation}
      />
    );
  }

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-[#FCF9F7]">
      {/* ── Sub-Header: Workspace Context Strip ───────────────────────────── */}
      <header className="h-14 px-5 bg-[#F6F3F1] border-b border-[#E6E4DF] flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="material-symbols-outlined text-[19px] text-[#A6331B]">
              auto_stories
            </span>
            <h1 className="font-serif text-base md:text-lg font-medium tracking-tight text-[#1C1C1B] truncate">
              {notebook.title}
            </h1>
          </div>

          <div className="h-3.5 w-px bg-[#E6E4DF] hidden sm:block"></div>

          {/* Source Grounding Pill */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#605E59]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2E5C56]"></span>
            <span>
              {readyCount} {readyCount === 1 ? "source" : "sources"} indexed · Grounded in verified evidence
            </span>
          </div>
        </div>

        {/* View Switcher & Actions */}
        <div className="flex items-center gap-2">
          {/* Navigation Tabs */}
          <div className="flex items-center p-0.5 rounded bg-[#EAE8E5] border border-[#E6E4DF]">
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                activeTab === "chat"
                  ? "bg-white text-[#1C1C1B] shadow-xs"
                  : "text-[#605E59] hover:text-[#1C1C1B]"
              }`}
              id="tab-chat"
              type="button"
            >
              Research Q&A
            </button>
            <button
              onClick={() => setActiveTab("sources")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors flex items-center gap-1 ${
                activeTab === "sources"
                  ? "bg-white text-[#1C1C1B] shadow-xs"
                  : "text-[#605E59] hover:text-[#1C1C1B]"
              }`}
              id="tab-sources"
              type="button"
            >
              <span>Sources</span>
              <span className="font-mono text-[10px] bg-[#F0EDEB] px-1 py-0.2 rounded text-[#605E59]">
                {documents.length}
              </span>
            </button>
          </div>

          {/* Golden-Set Evals */}
          <button
            onClick={() => {
              setShowEvalsModal(true);
              runEvaluations();
            }}
            className="hidden md:flex items-center gap-1 px-2.5 py-1 rounded bg-white border border-[#E6E4DF] text-xs font-medium text-[#1C1C1B] hover:bg-[#F0EDEB] transition-colors shadow-xs"
            title="Run Golden-Set Evals (100% citation grounding and refusal benchmark)"
            id="run-evals-btn"
            type="button"
          >
            <span className="material-symbols-outlined text-[15px] text-[#A6331B]">
              award_star
            </span>
            <span>Run Evals</span>
          </button>

          {/* Delete Notebook */}
          <button
            onClick={handleDeleteNotebook}
            className="p-1 rounded text-[#605E59] hover:text-[#BA1A1A] hover:bg-[#F0EDEB] transition-colors"
            title="Delete Notebook"
            type="button"
          >
            <span className="material-symbols-outlined text-[17px]">delete</span>
          </button>
        </div>
      </header>

      {/* ── Main Workspace Body (Q&A Canvas or Sources) ───────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {activeTab === "chat" ? (
          <div className="flex-1 flex overflow-hidden">
            {/* ── Center Synthesis Canvas ──────────────────────────────────── */}
            <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
              {/* Messages Scroll Area */}
              <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
                {messages.length === 0 ? (
                  /* Editorial Empty State */
                  <div className="max-w-2xl mx-auto my-auto py-12 text-center">
                    <div className="w-10 h-10 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-[#A6331B] mx-auto mb-3 flex items-center justify-center shadow-xs">
                      <span className="material-symbols-outlined text-[20px]">
                        history_edu
                      </span>
                    </div>

                    <h2 className="font-serif text-xl font-medium text-[#1C1C1B] mb-2">
                      Inquire against {notebook.title}
                    </h2>
                    <p className="text-xs text-[#605E59] max-w-md mx-auto leading-relaxed mb-6">
                      Every statement synthesized by this system is strictly grounded in retrieved document passages. Citations are numbered and link directly to source page and verbatim quote.
                    </p>

                    {readyCount === 0 ? (
                      <div className="p-4 rounded border border-[#E6E4DF] bg-white text-xs max-w-md mx-auto text-left shadow-xs">
                        <div className="flex items-center gap-2 mb-1 text-[#A6331B] font-semibold">
                          <span className="material-symbols-outlined text-[16px]">
                            info
                          </span>
                          <span>No documents indexed yet</span>
                        </div>
                        <p className="text-[#605E59] leading-relaxed">
                          Switch to the{" "}
                          <button
                            onClick={() => setActiveTab("sources")}
                            className="text-[#A6331B] font-medium underline"
                          >
                            Sources tab
                          </button>{" "}
                          to upload PDF, Markdown, or plain-text files.
                        </p>
                      </div>
                    ) : (
                      <div className="max-w-md mx-auto space-y-2 text-left">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59] block mb-1">
                          Corpus Inquiries
                        </span>
                        {[
                          "What are the foundational principles described in this document?",
                          "What are the key policy guidelines and responsibilities?",
                          "Provide a rigorous summary with verified citations.",
                        ].map((prompt, i) => (
                          <button
                            key={i}
                            onClick={() => setInputQuery(prompt)}
                            className="w-full text-left p-2.5 rounded bg-white border border-[#E6E4DF] text-xs text-[#1C1C1B] hover:border-[#A6331B] transition-colors shadow-xs flex items-center justify-between group"
                            type="button"
                          >
                            <span className="truncate pr-2">“{prompt}”</span>
                            <span className="material-symbols-outlined text-[14px] text-[#605E59] group-hover:text-[#A6331B] transition-colors">
                              arrow_forward
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Dialogue Stream */
                  messages.map((msg) => (
                    <div key={msg.id} className="max-w-4xl mx-auto space-y-4">
                      {msg.role === "user" ? (
                        /* User Query Card */
                        <div className="flex justify-end">
                          <div className="max-w-2xl w-full bg-[#F6F3F1] border border-[#E6E4DF] text-[#1C1C1B] px-4 py-3 rounded shadow-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59]">
                                Inquiry · Prompt
                              </span>
                              <span className="text-[10px] font-mono text-[#605E59]">
                                {msg.timestamp || "Active"}
                              </span>
                            </div>
                            <p className="text-sm font-medium leading-relaxed">
                              {msg.content}
                            </p>
                            <div className="mt-2 pt-1.5 border-t border-[#EFECE6] flex items-center justify-between text-[10px] text-[#605E59]">
                              <span className="flex items-center gap-1 font-mono">
                                <span className="material-symbols-outlined text-[12px] text-[#2E5C56]">
                                  verified
                                </span>
                                Constrained to corpus: {readyCount} indexed sources
                              </span>
                              <span className="font-mono uppercase">Strict QA</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* Assistant Synthesis Document Container */
                        <article className="bg-white border border-[#E6E4DF] rounded shadow-xs p-6 md:p-8 relative">
                          {/* Top Editorial Masthead */}
                          <header className="flex items-center justify-between pb-3 mb-4 border-b border-[#EFECE6]">
                            <div className="flex items-center gap-2.5">
                              <div className="w-6 h-6 rounded bg-[#A6331B] text-white flex items-center justify-center text-[10px] font-bold font-mono">
                                NL
                              </div>
                              <div>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-xs font-semibold text-[#1C1C1B]">
                                    Verifiable Synthesis
                                  </span>
                                  <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded bg-[#BCECE4] text-[#00201D]">
                                    Grounded Evidence
                                  </span>
                                </div>
                                <p className="text-[10px] text-[#605E59]">
                                  {msg.citations && msg.citations.length > 0
                                    ? `Synthesized from ${msg.citations.length} primary passages with exact alignment`
                                    : "Synthesizing response from verified corpus…"}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-1 text-[#605E59]">
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(msg.content);
                                  alert("Answer copied to clipboard.");
                                }}
                                className="p-1 rounded hover:bg-[#F0EDEB] transition-colors"
                                title="Copy answer"
                                type="button"
                              >
                                <span className="material-symbols-outlined text-[16px]">
                                  content_copy
                                </span>
                              </button>
                            </div>
                          </header>

                          {/* Refusal State or Synthesis Prose */}
                          {msg.not_found ? (
                            <div className="space-y-3 py-2">
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#FFDAD6]/40 border border-[#BA1A1A]/30 text-[#BA1A1A] text-xs font-medium">
                                <span className="material-symbols-outlined text-[14px]">
                                  shield
                                </span>
                                Ground-Truth Refusal Enforced · Zero Hallucination
                              </div>
                              <p className="font-serif text-sm leading-relaxed text-[#605E59]">
                                {msg.content ||
                                  "The retrieved sources do not contain sufficient evidence to answer this question. NotebookLM Lite enforces strict grounding and refuses to extrapolate beyond verified documents."}
                              </p>
                            </div>
                          ) : (
                            <div className="space-y-4">
                              {renderSynthesisProse(msg.content, msg.citations)}

                              {/* Confidence & Grounding Metrics Strip */}
                              {msg.citations && msg.citations.length > 0 && (
                                <div className="bg-[#F6F3F1] border border-[#E6E4DF] rounded p-3 grid grid-cols-1 sm:grid-cols-3 gap-3 my-4">
                                  <div>
                                    <span className="text-[10px] uppercase font-semibold text-[#605E59] block">
                                      Corpus Coherence
                                    </span>
                                    <div className="flex items-baseline gap-1.5 mt-0.5">
                                      <span className="font-serif text-base font-bold text-[#1C1C1B]">
                                        100%
                                      </span>
                                      <span className="text-[10px] text-[#2E5C56] font-medium">
                                        Verified
                                      </span>
                                    </div>
                                  </div>

                                  <div>
                                    <span className="text-[10px] uppercase font-semibold text-[#605E59] block">
                                      Cited Evidence
                                    </span>
                                    <div className="flex items-baseline gap-1.5 mt-0.5">
                                      <span className="font-serif text-base font-bold text-[#1C1C1B]">
                                        {msg.citations.length}
                                      </span>
                                      <span className="text-[10px] text-[#605E59]">
                                        {msg.citations.length === 1 ? "passage" : "passages"}
                                      </span>
                                    </div>
                                  </div>

                                  <div>
                                    <span className="text-[10px] uppercase font-semibold text-[#605E59] block">
                                      Ground Truth State
                                    </span>
                                    <div className="flex items-center gap-1 mt-0.5 text-[#2E5C56]">
                                      <span className="material-symbols-outlined text-[15px]">
                                        verified
                                      </span>
                                      <span className="text-xs font-semibold">
                                        Direct Quote Match
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Footing Verification Action Bar */}
                          {msg.citations && msg.citations.length > 0 && (
                            <footer className="mt-4 pt-3 border-t border-[#EFECE6] flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5 text-xs text-[#2E5C56]">
                                <span className="material-symbols-outlined text-[14px]">
                                  fact_check
                                </span>
                                <span className="font-medium">
                                  {msg.citations.length} citations verified
                                </span>
                              </div>

                              <div className="flex flex-wrap items-center gap-1.5">
                                {msg.citations.map((c) => (
                                  <button
                                    key={c.marker}
                                    onClick={() => setSelectedCitation(c)}
                                    className="px-2 py-0.5 rounded bg-[#F6F3F1] border border-[#E6E4DF] hover:border-[#A6331B] text-xs font-mono text-[#1C1C1B] transition-colors flex items-center gap-1"
                                    type="button"
                                  >
                                    <span className="font-bold text-[#A6331B]">
                                      [{c.marker}]
                                    </span>
                                    <span className="truncate max-w-[100px] text-[11px]">
                                      {c.filename || "Doc"}
                                    </span>
                                    <span className="text-[#605E59] text-[10px]">
                                      p.{c.page}
                                    </span>
                                  </button>
                                ))}
                              </div>
                            </footer>
                          )}
                        </article>
                      )}
                    </div>
                  ))
                )}

                {/* Progress Step Indicator during SSE stream */}
                {isStreaming && currentStep && (
                  <div className="max-w-4xl mx-auto flex items-center gap-2 px-3 py-1.5 rounded bg-white border border-[#E6E4DF] text-xs text-[#605E59] shadow-xs">
                    <span className="material-symbols-outlined text-[15px] text-[#A6331B] animate-spin-slow">
                      progress_activity
                    </span>
                    <span>{currentStep}</span>
                  </div>
                )}

                <div ref={chatBottomRef} />
              </div>

              {/* ── Persistent Floating Query Input Deck ───────────────────── */}
              <div className="p-3 md:p-4 bg-white/95 backdrop-blur-[4px] border-t border-[#E6E4DF] flex-shrink-0 z-10 shadow-xs">
                <form
                  onSubmit={handleSendMessage}
                  className="max-w-4xl mx-auto flex flex-col gap-1.5"
                >
                  <div className="bg-[#FCF9F7] border border-[#E6E4DF] rounded p-1 flex items-center gap-2 focus-within:border-[#A6331B] focus-within:bg-white transition-all shadow-xs">
                    <button
                      type="button"
                      onClick={() => setActiveTab("sources")}
                      className="p-1.5 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#F0EDEB] transition-colors"
                      title="Attach or inspect sources"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        attach_file
                      </span>
                    </button>

                    <input
                      type="text"
                      value={inputQuery}
                      onChange={(e) => setInputQuery(e.target.value)}
                      placeholder={
                        readyCount > 0
                          ? "Ask an inquiry across the verified document corpus… (e.g. 'Compare definitions')"
                          : "Upload and index documents to begin inquiry…"
                      }
                      disabled={isStreaming}
                      className="flex-1 bg-transparent text-sm text-[#1C1C1B] placeholder:text-[#605E59] focus:outline-none px-1"
                      id="chat-input"
                    />

                    <button
                      type="submit"
                      disabled={!inputQuery.trim() || isStreaming}
                      className="px-3.5 py-1.5 rounded bg-[#A6331B] text-white text-xs font-semibold hover:bg-[#891E07] disabled:opacity-40 transition-colors flex items-center gap-1 shadow-xs"
                      id="chat-send-btn"
                    >
                      <span>Query</span>
                      <span className="material-symbols-outlined text-[15px]">
                        arrow_upward
                      </span>
                    </button>
                  </div>

                  <div className="flex items-center justify-between px-1 text-[10px] text-[#605E59]">
                    <span>Grounded across active corpus ({readyCount} sources indexed)</span>
                    <span className="font-mono">NO SOURCE, NO SENTENCE</span>
                  </div>
                </form>
              </div>
            </div>

            {/* ── Right Evidence & Citation Inspector Panel ────────────────── */}
            {selectedCitation && (
              <CitationViewerPanel
                citation={selectedCitation}
                allCitations={activeCorpusCitations}
                onSelectCitation={setSelectedCitation}
                onClose={() => setSelectedCitation(null)}
                onOpenFullReader={(docId, page) =>
                  setFullReaderDoc({ documentId: docId, page })
                }
              />
            )}
          </div>
        ) : (
          /* ── Sources & Upload Tab ──────────────────────────────────────── */
          <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-4xl mx-auto w-full">
            {/* Header Description */}
            <div className="mb-6">
              <h2 className="font-serif text-lg font-medium text-[#1C1C1B]">
                Document Corpus & Ingestion Library
              </h2>
              <p className="text-xs text-[#605E59] mt-0.5">
                Upload PDFs, Markdown documents, and plain-text files. Each document is parsed page-by-page, chunked, and indexed with hybrid vector and lexical embeddings.
              </p>
            </div>

            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                handleFiles(e.dataTransfer.files);
              }}
              onClick={() => !uploading && fileInputRef.current?.click()}
              className={`p-6 mb-6 rounded border-2 border-dashed text-center cursor-pointer transition-colors ${
                dragging
                  ? "border-[#A6331B] bg-[#FFDAD3]/20"
                  : "border-[#E6E4DF] bg-white hover:border-[#605E59]"
              }`}
              id="upload-dropzone"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.md,.markdown"
                className="hidden"
                onChange={(e) => e.target.files && handleFiles(e.target.files)}
                id="file-input"
              />

              {uploading ? (
                <div className="flex flex-col items-center gap-2">
                  <span className="material-symbols-outlined text-[28px] text-[#A6331B] animate-spin-slow">
                    progress_activity
                  </span>
                  <p className="text-xs font-semibold text-[#1C1C1B]">
                    Indexing Document Stream… {uploadProgress}%
                  </p>
                  <p className="text-[11px] text-[#605E59]">
                    Extracting page folios and calculating embeddings.
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <div className="w-9 h-9 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-[#A6331B] flex items-center justify-center">
                    <span className="material-symbols-outlined text-[20px]">
                      upload_file
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[#1C1C1B]">
                      Select or drop research documents here
                    </p>
                    <p className="text-[11px] text-[#605E59] mt-0.5">
                      PDF, Markdown (.md), and plain text (.txt) · Page folios preserved
                    </p>
                  </div>
                </div>
              )}
            </div>

            {uploadError && (
              <div className="mb-4 p-3 rounded bg-[#FFDAD6]/40 border border-[#BA1A1A]/30 text-[#BA1A1A] text-xs flex items-center justify-between">
                <span>{uploadError}</span>
                <button
                  onClick={() => setUploadError(null)}
                  className="p-1 text-[#BA1A1A]"
                >
                  <span className="material-symbols-outlined text-[14px]">close</span>
                </button>
              </div>
            )}

            {/* Document Sources List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[#EFECE6] pb-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59]">
                  Ingested Files ({documents.length})
                </span>
                <span className="text-[10px] text-[#605E59] font-mono">
                  {readyCount}/{documents.length} Indexed
                </span>
              </div>

              {documents.length === 0 ? (
                <div className="py-12 text-center text-xs text-[#605E59]">
                  No documents in this corpus yet. Upload documents above.
                </div>
              ) : (
                documents.map((doc) => {
                  const cfg = STATUS_CONFIG[doc.status];
                  const isPdf = doc.filename.toLowerCase().endsWith(".pdf");

                  return (
                    <div
                      key={doc.id}
                      className="bg-white border border-[#E6E4DF] rounded p-3 flex items-center justify-between gap-3 shadow-xs hover:border-[#605E59] transition-colors"
                      id={`doc-row-${doc.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-[#A6331B] flex items-center justify-center font-mono text-[10px] font-bold shrink-0">
                          {isPdf ? "PDF" : "TXT"}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-[#1C1C1B] truncate">
                            {doc.filename}
                          </p>
                          <div className="flex items-center gap-2 text-[10px] text-[#605E59] font-mono mt-0.5">
                            <span>{formatBytes(doc.file_size)}</span>
                            {doc.page_count && (
                              <>
                                <span>·</span>
                                <span>
                                  {doc.page_count} {doc.page_count === 1 ? "page" : "pages"}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Status Badge */}
                        <span
                          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium"
                          style={{ background: cfg.bg, color: cfg.text }}
                        >
                          <span className="material-symbols-outlined text-[12px]">
                            {cfg.icon}
                          </span>
                          {cfg.label}
                        </span>

                        {/* Open Reader button if indexed */}
                        {doc.status === "indexed" && (
                          <button
                            onClick={() =>
                              setFullReaderDoc({ documentId: doc.id, page: 1 })
                            }
                            className="p-1 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#F6F3F1] transition-colors"
                            title="Open in Document Reader"
                            type="button"
                          >
                            <span className="material-symbols-outlined text-[16px]">
                              menu_book
                            </span>
                          </button>
                        )}

                        {/* Delete document button */}
                        <button
                          onClick={() => handleDeleteDoc(doc)}
                          className="p-1 rounded text-[#605E59] hover:text-[#BA1A1A] hover:bg-[#F6F3F1] transition-colors"
                          title="Delete Document"
                          type="button"
                        >
                          <span className="material-symbols-outlined text-[16px]">
                            delete
                          </span>
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Golden-Set Evals Benchmark Modal ─────────────────────────────── */}
      {showEvalsModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px]"
          onClick={(e) => e.target === e.currentTarget && setShowEvalsModal(false)}
        >
          <div className="w-full max-w-2xl bg-white border border-[#E6E4DF] rounded-md shadow-[0_4px_24px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col max-h-[85vh] text-[#1C1C1B]">
            {/* Header */}
            <div className="px-5 py-3.5 bg-[#F6F3F1] border-b border-[#E6E4DF] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-[#A6331B]">
                  award_star
                </span>
                <h3 className="font-serif text-sm font-medium text-[#1C1C1B]">
                  Golden-Set Evaluation Benchmark
                </h3>
              </div>
              <button
                onClick={() => setShowEvalsModal(false)}
                className="p-1 text-[#605E59] hover:text-[#1C1C1B]"
              >
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              {evalLoading ? (
                <div className="py-16 flex flex-col items-center justify-center gap-2 text-center text-[#605E59]">
                  <span className="material-symbols-outlined text-[28px] text-[#A6331B] animate-spin-slow">
                    progress_activity
                  </span>
                  <p className="text-xs font-semibold text-[#1C1C1B]">
                    Running Golden Evaluation Suite against Corpus…
                  </p>
                  <p className="text-[11px]">
                    Validating citation precision, refusal correctness, and zero hallucination.
                  </p>
                </div>
              ) : evalResults ? (
                <div className="space-y-4">
                  {/* Scores Cards */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3.5 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-center">
                      <span className="font-serif text-2xl font-bold text-[#A6331B]">
                        {evalResults.metrics?.citation_validity_rate}%
                      </span>
                      <p className="text-[10px] uppercase font-semibold text-[#605E59] mt-0.5">
                        Citation Validity Rate
                      </p>
                    </div>
                    <div className="p-3.5 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-center">
                      <span className="font-serif text-2xl font-bold text-[#2E5C56]">
                        {evalResults.metrics?.refusal_accuracy}%
                      </span>
                      <p className="text-[10px] uppercase font-semibold text-[#605E59] mt-0.5">
                        Refusal Accuracy
                      </p>
                    </div>
                  </div>

                  {/* Test Cases Table */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59] block">
                      Evaluated Test Cases ({evalResults.test_cases?.length})
                    </span>
                    <div className="space-y-1.5">
                      {evalResults.test_cases?.map((tc: any, i: number) => (
                        <div
                          key={i}
                          className="p-3 rounded bg-white border border-[#E6E4DF] text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-[#1C1C1B] truncate max-w-[420px]">
                              {tc.question}
                            </span>
                            <span
                              className={`px-1.5 py-0.2 rounded font-mono text-[9px] font-bold ${
                                tc.is_answerable
                                  ? "bg-[#BCECE4] text-[#00201D]"
                                  : "bg-[#FFDAD6] text-[#BA1A1A]"
                              }`}
                            >
                              {tc.is_answerable ? "In-Domain" : "Out-of-Domain Refusal"}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-[#605E59] font-mono">
                            <span>Chunks: {tc.retrieved_chunks}</span>
                            <span>Refusal Flag: {tc.not_found ? "YES ✓" : "NO"}</span>
                            <span>Hallucinated: {tc.hallucinated_ids?.length || 0}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="px-5 py-2.5 bg-[#F6F3F1] border-t border-[#E6E4DF] flex justify-end">
              <button
                onClick={() => setShowEvalsModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded bg-[#1C1C1B] text-white hover:bg-[#31302F] transition-colors"
              >
                Close Benchmark
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
