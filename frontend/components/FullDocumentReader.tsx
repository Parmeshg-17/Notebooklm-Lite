"use client";

import { useEffect, useState } from "react";
import { documentsApi } from "@/lib/api";
import type { CitationViewData } from "./CitationViewerPanel";

interface Props {
  documentId: string;
  initialPage?: number;
  activeCitation?: CitationViewData | null;
  onBackToQA: () => void;
  onSelectCitation?: (cit: CitationViewData) => void;
}

export function FullDocumentReader({
  documentId,
  initialPage = 1,
  activeCitation,
  onBackToQA,
  onSelectCitation,
}: Props) {
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [pageCount, setPageCount] = useState<number>(1);
  const [pageText, setPageText] = useState<string>("");
  const [filename, setFilename] = useState<string>("Document");
  const [loading, setLoading] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    const loadPage = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await documentsApi.getPage(documentId, currentPage);
        if (!isCancelled) {
          setPageText(data.text);
          setFilename(data.filename || "Document");
          setPageCount(data.page_count || 1);
        }
      } catch (err: any) {
        if (!isCancelled) {
          setError(err.message || "Failed to load document page");
        }
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    loadPage();
    return () => {
      isCancelled = true;
    };
  }, [documentId, currentPage]);

  const hasCitationOnCurrentPage =
    activeCitation &&
    activeCitation.document_id === documentId &&
    activeCitation.page === currentPage;

  const handleJumpToCitation = () => {
    if (activeCitation?.page) {
      setCurrentPage(activeCitation.page);
    }
  };

  const renderContentWithCitation = () => {
    if (!pageText) {
      return (
        <p className="text-sm text-[#605E59] italic text-center py-12">
          No extracted text available on this page.
        </p>
      );
    }

    if (!hasCitationOnCurrentPage || !activeCitation?.quote) {
      return (
        <div className="whitespace-pre-wrap font-serif text-[15px] leading-relaxed text-[#1C1C1B] select-text">
          {pageText}
        </div>
      );
    }

    const cleanQuote = activeCitation.quote.trim();
    const lowerFull = pageText.toLowerCase();
    const lowerQuote = cleanQuote.toLowerCase();
    const idx = lowerFull.indexOf(lowerQuote);

    if (idx !== -1) {
      const before = pageText.substring(0, idx);
      const match = pageText.substring(idx, idx + cleanQuote.length);
      const after = pageText.substring(idx + cleanQuote.length);

      return (
        <div className="space-y-4 font-serif text-[15px] leading-relaxed text-[#1C1C1B] select-text">
          {before && <p className="whitespace-pre-wrap">{before}</p>}
          <div
            id="citationAnchor"
            className="relative bg-[#FFDAD3]/35 border-l-3 border-[#A6331B] rounded-r p-4 my-4 shadow-xs"
          >
            <span className="absolute -left-3.5 top-3.5 px-1.5 py-0.5 rounded bg-[#A6331B] text-white font-sans text-xs font-bold font-mono shadow-xs">
              [{activeCitation.marker}]
            </span>
            <p className="font-serif italic font-medium text-base text-[#1C1C1B]">
              “{match}”
            </p>
            <div className="mt-2 pt-2 border-t border-[#A6331B]/20 flex items-center justify-between font-sans text-[11px] text-[#A6331B]">
              <span className="font-semibold flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">verified</span>
                Verified Ground Truth Citation
              </span>
              <span className="font-mono text-[#605E59]">Page {currentPage}</span>
            </div>
          </div>
          {after && <p className="whitespace-pre-wrap">{after}</p>}
        </div>
      );
    }

    return (
      <div className="space-y-4 font-serif text-[15px] leading-relaxed text-[#1C1C1B] select-text">
        <div className="relative bg-[#FFDAD3]/35 border-l-3 border-[#A6331B] rounded-r p-4 my-2">
          <span className="absolute -left-3.5 top-3.5 px-1.5 py-0.5 rounded bg-[#A6331B] text-white font-sans text-xs font-bold font-mono">
            [{activeCitation.marker}]
          </span>
          <p className="font-serif italic font-medium text-base text-[#1C1C1B]">
            “{activeCitation.quote}”
          </p>
        </div>
        <div className="whitespace-pre-wrap">{pageText}</div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-[#FCF9F7] text-[#1C1C1B] select-none">
      {/* ── Document Reader Toolbar ──────────────────────────────────────── */}
      <header className="h-14 px-4 bg-white border-b border-[#E6E4DF] flex items-center justify-between z-20 shadow-xs">
        {/* Left: Back & Context */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBackToQA}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#F6F3F1] hover:bg-[#EAE8E5] text-[#1C1C1B] transition-colors text-xs font-medium border border-[#E6E4DF]"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            <span>Back to Synthesis</span>
          </button>

          <div className="h-4 w-px bg-[#E6E4DF] hidden sm:block"></div>

          <div className="flex items-center gap-2 min-w-0">
            <span className="material-symbols-outlined text-[18px] text-[#A6331B]">
              picture_as_pdf
            </span>
            <span className="text-xs font-semibold truncate max-w-[200px] md:max-w-xs text-[#1C1C1B]">
              {filename}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F0EDEB] text-[#605E59]">
              {pageCount} {pageCount === 1 ? "Page" : "Pages"}
            </span>
          </div>
        </div>

        {/* Center: Page Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-[#F6F3F1] rounded border border-[#E6E4DF] p-0.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1 || loading}
              className="p-1 text-[#605E59] hover:text-[#1C1C1B] disabled:opacity-30 transition-colors"
              title="Previous Page"
            >
              <span className="material-symbols-outlined text-[16px]">chevron_left</span>
            </button>
            <div className="flex items-center px-2 gap-1 text-xs">
              <span className="font-mono font-medium">{currentPage}</span>
              <span className="text-[#605E59]">/</span>
              <span className="font-mono text-[#605E59]">{pageCount}</span>
            </div>
            <button
              onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
              disabled={currentPage >= pageCount || loading}
              className="p-1 text-[#605E59] hover:text-[#1C1C1B] disabled:opacity-30 transition-colors"
              title="Next Page"
            >
              <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            </button>
          </div>

          {/* Zoom controls */}
          <div className="hidden md:flex items-center bg-[#F6F3F1] rounded border border-[#E6E4DF] p-0.5">
            <button
              onClick={() => setZoomLevel((z) => Math.max(80, z - 10))}
              className="p-1 text-[#605E59] hover:text-[#1C1C1B] transition-colors"
              title="Zoom out"
            >
              <span className="material-symbols-outlined text-[16px]">remove</span>
            </button>
            <span className="text-[11px] font-mono text-[#605E59] px-1.5">
              {zoomLevel}%
            </span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(130, z + 10))}
              className="p-1 text-[#605E59] hover:text-[#1C1C1B] transition-colors"
              title="Zoom in"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
            </button>
          </div>
        </div>

        {/* Right: Active Citation Jump */}
        <div className="flex items-center gap-2">
          {activeCitation && (
            <button
              onClick={handleJumpToCitation}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#FFDAD3] text-[#A6331B] hover:bg-[#FFB4A4] border border-[#A6331B]/30 transition-colors text-xs font-semibold"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]">my_location</span>
              <span>Jump to Citation [{activeCitation.marker}]</span>
            </button>
          )}
        </div>
      </header>

      {/* ── Main Layout: Page Thumbnails + Center Reading Paper ─────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Thumbnails Strip */}
        <aside className="w-44 flex-shrink-0 bg-[#F6F3F1] border-r border-[#E6E4DF] overflow-y-auto p-3 hidden md:flex flex-col gap-2">
          <div className="flex items-center justify-between pb-1.5 border-b border-[#EFECE6] text-[10px] uppercase font-semibold text-[#605E59]">
            <span>Pages</span>
            <span className="font-mono">{pageCount}</span>
          </div>

          <div className="flex flex-col gap-2 pt-1">
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => {
              const isSelected = p === currentPage;
              const hasCitation =
                activeCitation &&
                activeCitation.document_id === documentId &&
                activeCitation.page === p;

              return (
                <button
                  key={p}
                  onClick={() => setCurrentPage(p)}
                  className={`w-full text-left p-2 rounded text-xs transition-all flex flex-col gap-1 border ${
                    isSelected
                      ? "bg-white border-[#A6331B] shadow-xs"
                      : "bg-[#FFFFFF]/70 hover:bg-white border-[#E6E4DF]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-[#605E59]">
                      Page {p}
                    </span>
                    {hasCitation && (
                      <span className="px-1 py-0.2 rounded bg-[#A6331B] text-white text-[9px] font-mono font-bold">
                        [{activeCitation.marker}]
                      </span>
                    )}
                  </div>
                  <div className="h-6 w-full bg-[#F6F3F1] rounded-xs flex flex-col justify-center px-1.5 gap-0.5">
                    <div className="h-1 w-3/4 bg-[#E6E4DF] rounded-xs"></div>
                    <div className="h-1 w-1/2 bg-[#E6E4DF] rounded-xs"></div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Center Paper Canvas */}
        <main className="flex-1 overflow-y-auto p-6 md:p-10 flex flex-col items-center bg-[#FCF9F7]">
          <article
            className="w-full max-w-[820px] bg-white rounded border border-[#E6E4DF] shadow-[0_2px_12px_rgba(0,0,0,0.04)] p-8 md:p-12 text-[#1C1C1B] relative"
            style={{ fontSize: `${zoomLevel}%` }}
          >
            {/* Textbook Header */}
            <header className="flex items-center justify-between pb-4 mb-6 border-b border-[#EFECE6] text-[11px] text-[#605E59] font-sans uppercase tracking-widest">
              <span className="truncate max-w-[400px]">{filename}</span>
              <span className="font-mono">Page {currentPage} of {pageCount}</span>
            </header>

            {/* Document Content */}
            {loading ? (
              <div className="py-24 flex flex-col items-center justify-center gap-2 text-[#605E59]">
                <span className="material-symbols-outlined text-[24px] text-[#A6331B] animate-spin-slow">
                  progress_activity
                </span>
                <span className="text-xs">Rendering page {currentPage}…</span>
              </div>
            ) : error ? (
              <div className="p-4 rounded bg-[#FFDAD6]/40 border border-[#BA1A1A]/30 text-[#BA1A1A] text-xs">
                {error}
              </div>
            ) : (
              renderContentWithCitation()
            )}

            {/* Academic Footer */}
            <footer className="mt-12 pt-4 border-t border-[#EFECE6] flex items-center justify-between text-[11px] text-[#605E59] font-sans">
              <span className="font-mono truncate">
                Doc ID: {documentId.slice(0, 8)}…
              </span>
              <span className="font-mono font-medium text-[#1C1C1B]">
                {currentPage}
              </span>
            </footer>
          </article>
        </main>
      </div>
    </div>
  );
}
