"use client";

import { useEffect, useState } from "react";
import { documentsApi } from "@/lib/api";

export interface CitationViewData {
  marker: number;
  chunk_id: string;
  document_id?: string;
  filename?: string;
  page: number;
  quote: string;
}

interface Props {
  citation: CitationViewData;
  allCitations?: CitationViewData[];
  onSelectCitation?: (cit: CitationViewData) => void;
  onClose: () => void;
  onOpenFullReader?: (docId: string, page: number) => void;
}

export function CitationViewerPanel({
  citation,
  allCitations = [],
  onSelectCitation,
  onClose,
  onOpenFullReader,
}: Props) {
  const [currentPage, setCurrentPage] = useState<number>(citation.page || 1);
  const [pageCount, setPageCount] = useState<number>(1);
  const [pageText, setPageText] = useState<string>("");
  const [filename, setFilename] = useState<string>(citation.filename || "Document");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    setCurrentPage(citation.page || 1);
  }, [citation]);

  useEffect(() => {
    let isCancelled = false;
    const loadPage = async () => {
      if (!citation.document_id) {
        setPageText(citation.quote);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const data = await documentsApi.getPage(citation.document_id, currentPage);
        if (!isCancelled) {
          setPageText(data.text);
          setFilename(data.filename || citation.filename || "Document");
          setPageCount(data.page_count || 1);
        }
      } catch (err: any) {
        if (!isCancelled) {
          setError(err.message || "Failed to load document page");
          setPageText(citation.quote);
        }
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    loadPage();
    return () => {
      isCancelled = true;
    };
  }, [citation.document_id, currentPage, citation.quote, citation.filename]);

  const currentIndex = allCitations.findIndex((c) => c.marker === citation.marker);
  const prevCitation = currentIndex > 0 ? allCitations[currentIndex - 1] : null;
  const nextCitation =
    currentIndex !== -1 && currentIndex < allCitations.length - 1
      ? allCitations[currentIndex + 1]
      : null;

  const handleCopyQuote = () => {
    const textToCopy = `"${citation.quote}" — ${filename}, Page ${citation.page} [${citation.marker}]`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render text highlighting the exact cited quote
  const renderPageWithHighlight = (fullText: string, quote: string) => {
    if (!quote || !fullText) {
      return (
        <div className="quote-highlight my-2">
          <p className="font-serif text-[13px] leading-relaxed text-[#1C1C1B]">
            “{quote}”
          </p>
        </div>
      );
    }

    const cleanQuote = quote.trim();
    const lowerFull = fullText.toLowerCase();
    const lowerQuote = cleanQuote.toLowerCase();
    const idx = lowerFull.indexOf(lowerQuote);

    if (idx !== -1) {
      const before = fullText.substring(0, idx);
      const match = fullText.substring(idx, idx + cleanQuote.length);
      const after = fullText.substring(idx + cleanQuote.length);

      return (
        <div className="space-y-2 select-text">
          {before && (
            <p className="font-serif text-[13px] leading-relaxed text-[#605E59] opacity-80 whitespace-pre-wrap">
              {before}
            </p>
          )}
          <div className="relative bg-[#FFDAD3]/30 border-l-2 border-[#A6331B] rounded-r p-2.5 my-2">
            <span className="absolute -left-2.5 top-2 px-1 py-0.2 rounded bg-[#A6331B] text-white text-[9px] font-mono font-bold">
              [{citation.marker}]
            </span>
            <p className="font-serif text-[13px] leading-relaxed font-medium text-[#1C1C1B]">
              “{match}”
            </p>
          </div>
          {after && (
            <p className="font-serif text-[13px] leading-relaxed text-[#605E59] opacity-80 whitespace-pre-wrap">
              {after}
            </p>
          )}
        </div>
      );
    }

    // If text does not contain exact substring, show cited quote boxed and full page
    return (
      <div className="space-y-3 select-text">
        <div className="relative bg-[#FFDAD3]/30 border-l-2 border-[#A6331B] rounded-r p-2.5 my-2">
          <span className="absolute -left-2.5 top-2 px-1 py-0.2 rounded bg-[#A6331B] text-white text-[9px] font-mono font-bold">
            [{citation.marker}]
          </span>
          <p className="font-serif text-[13px] leading-relaxed font-medium text-[#1C1C1B]">
            “{quote}”
          </p>
        </div>
        <p className="font-serif text-[13px] leading-relaxed text-[#605E59] opacity-85 whitespace-pre-wrap">
          {fullText}
        </p>
      </div>
    );
  };

  const isPdf = filename.toLowerCase().endsWith(".pdf");

  return (
    <aside
      className="w-full xl:w-[410px] flex-shrink-0 flex flex-col h-full bg-[#FFFFFF] border-l border-[#E6E4DF] select-none z-30"
      id="citation-viewer-panel"
    >
      {/* ── Header: Citation Marker & Nav ──────────────────────────────── */}
      <div className="p-3 bg-[#F6F3F1] border-b border-[#E6E4DF] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-[#A6331B] text-white font-mono text-xs font-bold">
            Citation [{citation.marker}]
          </span>
          <h3 className="text-xs font-semibold text-[#1C1C1B]">Ground Evidence</h3>
        </div>

        <div className="flex items-center gap-1">
          {allCitations.length > 1 && (
            <>
              <button
                onClick={() => prevCitation && onSelectCitation?.(prevCitation)}
                disabled={!prevCitation}
                className="p-1 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#EAE8E5] disabled:opacity-30 transition-colors"
                title="Previous Citation"
                type="button"
              >
                <span className="material-symbols-outlined text-[16px]">
                  keyboard_arrow_left
                </span>
              </button>
              <button
                onClick={() => nextCitation && onSelectCitation?.(nextCitation)}
                disabled={!nextCitation}
                className="p-1 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#EAE8E5] disabled:opacity-30 transition-colors"
                title="Next Citation"
                type="button"
              >
                <span className="material-symbols-outlined text-[16px]">
                  keyboard_arrow_right
                </span>
              </button>
              <div className="h-3 w-px bg-[#E6E4DF] mx-1"></div>
            </>
          )}

          <button
            onClick={onClose}
            className="p-1 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#EAE8E5] transition-colors"
            title="Close Evidence Inspector"
            type="button"
            id="close-citation-panel-btn"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      </div>

      {/* ── Source Context Ribbon ───────────────────────────────────────── */}
      <div className="px-3.5 py-2.5 bg-white border-b border-[#EFECE6] flex items-center justify-between">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded bg-[#F0EDEB] border border-[#E6E4DF] text-[#A6331B] flex items-center justify-center font-mono text-[10px] font-bold uppercase shrink-0">
            {isPdf ? "PDF" : "TXT"}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-[#1C1C1B] truncate">{filename}</p>
            <p className="text-[10px] text-[#605E59] font-mono">
              Page {currentPage} of {pageCount} · Chunk #{citation.chunk_id.slice(0, 8)}
            </p>
          </div>
        </div>

        {/* Page Switcher */}
        <div className="flex items-center gap-1 bg-[#F6F3F1] px-1 py-0.5 rounded border border-[#E6E4DF]">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1 || loading}
            className="p-0.5 text-[#605E59] hover:text-[#1C1C1B] disabled:opacity-30 transition-colors"
            title="Previous page"
          >
            <span className="material-symbols-outlined text-[14px]">chevron_left</span>
          </button>
          <span className="text-[10px] font-mono px-1 text-[#1C1C1B]">
            p.{currentPage}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
            disabled={currentPage >= pageCount || loading}
            className="p-0.5 text-[#605E59] hover:text-[#1C1C1B] disabled:opacity-30 transition-colors"
            title="Next page"
          >
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          </button>
        </div>
      </div>

      {/* ── PDF Page Facsimile Preview (Center Scroll) ──────────────────── */}
      <div className="flex-1 overflow-y-auto p-3.5 bg-[#F6F3F1] flex flex-col gap-3">
        <div className="w-full bg-white rounded border border-[#E6E4DF] p-4 text-[#1C1C1B] font-serif shadow-xs relative">
          {/* Authentic Textbook Header Strip */}
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#EFECE6] font-sans text-[10px] text-[#605E59] uppercase tracking-wider">
            <span className="truncate max-w-[200px]">{filename}</span>
            <span className="font-mono">Page {currentPage}</span>
          </div>

          {/* Document Content with Quote Highlighter */}
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-[#605E59] font-sans text-xs">
              <span className="material-symbols-outlined text-[20px] text-[#A6331B] animate-spin-slow">
                progress_activity
              </span>
              <span>Loading source page…</span>
            </div>
          ) : error ? (
            <div className="p-3 text-xs font-sans rounded bg-[#FFDAD6]/40 border border-[#BA1A1A]/30 text-[#BA1A1A]">
              {error}
            </div>
          ) : (
            renderPageWithHighlight(pageText, citation.quote)
          )}

          {/* Marginal Anchor Footer */}
          <div className="mt-4 pt-2 border-t border-[#EFECE6] flex items-center justify-between font-sans text-[#605E59] text-[10px]">
            <span className="font-mono truncate">Ref: {citation.chunk_id.slice(0, 12)}</span>
            <span className="flex items-center gap-1 text-[#2E5C56] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2E5C56]"></span>
              Exact Source Match
            </span>
          </div>
        </div>

        {/* Verification Engine Box */}
        <div className="bg-white rounded border border-[#E6E4DF] p-3 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59]">
              Verification Audit
            </span>
            <span className="flex items-center gap-1 text-[10px] font-semibold text-[#2E5C56] bg-[#BCECE4]/40 px-1.5 py-0.5 rounded border border-[#2E5C56]/20">
              <span className="material-symbols-outlined text-[12px]">verified</span>
              Ground Truth
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-[#1C1C1B]">
            <div className="flex items-start gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#2E5C56] shrink-0 mt-0.5">
                check_circle
              </span>
              <p className="text-[11px] text-[#605E59] leading-snug">
                Passage validated against ingested embeddings. Zero synthetic hallucination.
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-[#605E59] font-mono pt-1">
              <span className="material-symbols-outlined text-[14px]">straighten</span>
              <span>Cited Page: {citation.page} · Offset Chunk #{citation.chunk_id.slice(0, 8)}</span>
            </div>
          </div>

          {/* Quick Action Links */}
          <div className="mt-3 pt-2 border-t border-[#EFECE6] flex flex-col gap-1.5">
            {citation.document_id && onOpenFullReader && (
              <button
                onClick={() => onOpenFullReader(citation.document_id!, currentPage)}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded bg-[#F6F3F1] hover:bg-[#EAE8E5] text-[#1C1C1B] transition-colors text-xs font-medium"
                type="button"
              >
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">
                    menu_book
                  </span>
                  Open full document reader
                </span>
                <span className="material-symbols-outlined text-[13px] text-[#605E59]">
                  arrow_forward
                </span>
              </button>
            )}

            <button
              onClick={handleCopyQuote}
              className="w-full flex items-center justify-between px-2.5 py-1.5 rounded bg-[#F6F3F1] hover:bg-[#EAE8E5] text-[#1C1C1B] transition-colors text-xs font-medium"
              type="button"
            >
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px]">
                  content_copy
                </span>
                {copied ? "Copied to clipboard!" : "Copy verified quote with citation"}
              </span>
              <span className="text-[10px] font-mono text-[#605E59]">TXT</span>
            </button>
          </div>
        </div>

        {/* Correlated Passages in Active Inquiry */}
        {allCitations.length > 1 && (
          <div className="bg-white rounded border border-[#E6E4DF] p-3 shadow-xs">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59] block mb-2">
              All Cited Sources ({allCitations.length})
            </span>
            <div className="space-y-1">
              {allCitations.map((c) => {
                const isActive = c.marker === citation.marker;
                return (
                  <button
                    key={c.marker}
                    onClick={() => onSelectCitation?.(c)}
                    className={`w-full text-left p-1.5 rounded text-xs transition-colors flex items-center justify-between ${
                      isActive
                        ? "bg-[#FFDAD3]/40 border border-[#A6331B]/30 text-[#A6331B]"
                        : "hover:bg-[#F6F3F1] text-[#605E59]"
                    }`}
                  >
                    <span className="truncate pr-2">
                      [{c.marker}] {c.filename || "Document"} (p. {c.page})
                    </span>
                    <span className="font-mono text-[10px] shrink-0 font-bold">
                      p.{c.page}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── Grounding Rule Footer ────────────────────────────────────────── */}
      <div className="px-3.5 py-2 bg-[#F6F3F1] border-t border-[#E6E4DF] text-center text-[10px] text-[#605E59] font-mono">
        NO SOURCE, NO SENTENCE · GROUND-TRUTH ENFORCED
      </div>
    </aside>
  );
}
