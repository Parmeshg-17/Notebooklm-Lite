"use client";

import { useEffect, useState } from "react";
import { notebooksApi } from "@/lib/api";
import type { Notebook } from "@/types";
import { CreateNotebookModal } from "@/components/CreateNotebookModal";
import { NotebookView } from "@/components/NotebookView";

export default function HomePage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadNotebooks = async () => {
    try {
      setLoading(true);
      const res = await notebooksApi.list();
      setNotebooks(res.notebooks);
      if (res.notebooks.length > 0 && !selectedNotebook) {
        setSelectedNotebook(res.notebooks[0]);
      }
    } catch (e) {
      setError("Could not connect to backend engine. Ensure the server is active.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotebooks();
  }, []);

  // Keyboard shortcut listener: ⌘N for new notebook
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") {
        e.preventDefault();
        setShowCreate(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleNotebookCreated = (notebook: Notebook) => {
    setNotebooks((prev) => [notebook, ...prev]);
    setSelectedNotebook(notebook);
    setShowCreate(false);
  };

  const filteredNotebooks = notebooks.filter((n) =>
    n.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[#FCF9F7] text-[#1C1C1B]">
      {/* ── Left Rail Sidebar ────────────────────────────────────────────── */}
      <aside className="w-72 flex-shrink-0 flex flex-col justify-between bg-[#F6F3F1] border-r border-[#E6E4DF] select-none z-20">
        <div className="flex flex-col min-h-0">
          {/* Masthead Header */}
          <div className="h-14 px-4 flex items-center justify-between border-b border-[#EFECE6]">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded bg-[#A6331B] text-white flex items-center justify-center font-bold text-xs tracking-tight shadow-xs">
                NL
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-sm tracking-tight text-[#1C1C1B]">
                  NotebookLM
                </span>
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-[#E3DFD9] text-[#64625D]">
                  Lite
                </span>
              </div>
            </div>
            <span
              className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#EAE8E5] text-[#605E59]"
              title="Verified RAG mode"
            >
              RAG v1.0
            </span>
          </div>

          {/* New Notebook Action */}
          <div className="p-3">
            <button
              onClick={() => setShowCreate(true)}
              className="w-full flex items-center justify-between px-3 py-2 rounded bg-white border border-[#E6E4DF] text-[#1C1C1B] hover:bg-[#F0EDEB] transition-colors shadow-xs group"
              type="button"
              id="create-notebook-btn"
            >
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[17px] text-[#A6331B] group-hover:scale-110 transition-transform">
                  add
                </span>
                <span className="text-xs font-medium">New notebook</span>
              </div>
              <kbd className="text-[10px] font-mono text-[#605E59] bg-[#F6F3F1] px-1.5 py-0.5 rounded border border-[#E6E4DF]">
                ⌘N
              </kbd>
            </button>
          </div>

          {/* Corpus Search Filter */}
          <div className="px-3 pb-2">
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-2.5 text-[15px] text-[#605E59]">
                search
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search notebooks…"
                className="w-full pl-8 pr-3 py-1.5 bg-[#F0EDEB] rounded text-xs text-[#1C1C1B] placeholder:text-[#605E59] border border-transparent focus:border-[#E6E4DF] focus:bg-white focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Section Header */}
          <div className="px-4 pt-3 pb-1.5 flex items-center justify-between">
            <span className="text-[10px] font-semibold text-[#605E59] uppercase tracking-wider">
              Research Corpora
            </span>
            <span className="text-[10px] font-mono text-[#605E59]">
              {notebooks.length}
            </span>
          </div>

          {/* Notebooks List */}
          <nav className="flex-1 overflow-y-auto px-2 space-y-1">
            {loading && (
              <div className="flex items-center gap-2 px-3 py-3 text-xs text-[#605E59]">
                <span className="material-symbols-outlined text-[15px] animate-spin-slow">
                  progress_activity
                </span>
                Loading corpora…
              </div>
            )}

            {error && (
              <div className="mx-2 p-2.5 rounded text-xs bg-[#FFDAD6]/50 border border-[#BA1A1A]/30 text-[#BA1A1A]">
                {error}
              </div>
            )}

            {!loading && notebooks.length === 0 && !error && (
              <div className="px-3 py-4 text-xs text-[#605E59] text-center">
                No notebooks created yet.
                <button
                  onClick={() => setShowCreate(true)}
                  className="block mx-auto mt-2 text-[#A6331B] font-medium underline"
                >
                  Create one now
                </button>
              </div>
            )}

            {filteredNotebooks.map((nb) => {
              const isSelected = selectedNotebook?.id === nb.id;
              return (
                <button
                  key={nb.id}
                  onClick={() => setSelectedNotebook(nb)}
                  id={`notebook-${nb.id}`}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded text-left transition-all group ${
                    isSelected
                      ? "bg-white text-[#1C1C1B] font-semibold shadow-xs border-l-2 border-[#A6331B] border-y border-r border-[#E6E4DF]"
                      : "text-[#605E59] hover:bg-[#F0EDEB] hover:text-[#1C1C1B]"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate min-w-0">
                    <span
                      className={`material-symbols-outlined text-[16px] shrink-0 ${
                        isSelected ? "text-[#A6331B]" : "text-[#605E59]"
                      }`}
                    >
                      menu_book
                    </span>
                    <span className="text-xs truncate">{nb.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-[#605E59] bg-[#EAE8E5] px-1.5 py-0.5 rounded shrink-0">
                    Active
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer Identity Rail */}
        <div className="p-3 border-t border-[#EFECE6] bg-[#F6F3F1] flex flex-col gap-2">
          <div className="flex items-center justify-between px-2 py-1.5 bg-[#F0EDEB] rounded border border-[#E6E4DF]">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2E5C56]"></span>
              <span className="text-[11px] text-[#605E59]">Corpus Integrity</span>
            </div>
            <span className="text-[11px] font-mono font-medium text-[#2E5C56]">
              Verified
            </span>
          </div>

          <div className="flex items-center justify-between pt-1 px-1">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-full bg-[#EAE8E5] border border-[#E6E4DF] flex items-center justify-center text-[10px] font-semibold text-[#605E59]">
                R
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-[#1C1C1B] truncate">
                  Research Session
                </p>
                <p className="text-[10px] text-[#605E59] truncate font-mono">
                  No Source, No Sentence
                </p>
              </div>
            </div>
            <span
              className="material-symbols-outlined text-[16px] text-[#605E59]"
              title="Ground-truth constraints enforced"
            >
              verified_user
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main Workspace ──────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#FCF9F7]">
        {selectedNotebook ? (
          <NotebookView
            notebook={selectedNotebook}
            onNotebookUpdate={(nb) => {
              setSelectedNotebook(nb);
              setNotebooks((prev) => prev.map((n) => (n.id === nb.id ? nb : n)));
            }}
            onDeleted={() => {
              setNotebooks((prev) => prev.filter((n) => n.id !== selectedNotebook.id));
              setSelectedNotebook(null);
            }}
          />
        ) : (
          <EmptyCorpusState onCreateClick={() => setShowCreate(true)} />
        )}
      </main>

      {/* ── Create Notebook Modal ────────────────────────────────────────── */}
      {showCreate && (
        <CreateNotebookModal
          onCreated={handleNotebookCreated}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}

function EmptyCorpusState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="h-full flex items-center justify-center p-8 bg-[#FCF9F7]">
      <div className="max-w-xl w-full text-center">
        {/* Academic Seal */}
        <div className="w-12 h-12 rounded bg-[#F6F3F1] border border-[#E6E4DF] text-[#A6331B] mx-auto mb-4 flex items-center justify-center shadow-xs">
          <span className="material-symbols-outlined text-[24px]">auto_stories</span>
        </div>

        <span className="text-[10px] font-semibold uppercase tracking-widest text-[#605E59] mb-2 block">
          Document Research & Evidence Engine
        </span>

        <h1 className="font-serif text-2xl md:text-3xl font-medium text-[#1C1C1B] mb-3">
          NotebookLM Lite
        </h1>

        <p className="text-sm text-[#605E59] leading-relaxed mb-6 max-w-lg mx-auto">
          An editorial research workspace anchored in strict ground-truth verification. Every answer is synthesized exclusively from ingested PDF, Markdown, and text sources with numbered citation markers linked directly to page and quote.
        </p>

        {/* Visual Chain Blueprint */}
        <div className="bg-white border border-[#E6E4DF] rounded-md p-4 mb-6 text-left shadow-xs">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#605E59] block mb-2">
            The Evidence Chain
          </span>
          <div className="flex flex-wrap items-center justify-between text-xs gap-2 py-1 font-mono text-[#1C1C1B]">
            <span className="px-2 py-1 bg-[#F6F3F1] rounded border border-[#E6E4DF]">
              1. Question
            </span>
            <span className="text-[#605E59]">→</span>
            <span className="px-2 py-1 bg-[#F6F3F1] rounded border border-[#E6E4DF]">
              2. Answer
            </span>
            <span className="text-[#605E59]">→</span>
            <span className="px-2 py-1 bg-[#FFDAD3] text-[#A6331B] font-bold rounded border border-[#A6331B]/30">
              3. Citation [n]
            </span>
            <span className="text-[#605E59]">→</span>
            <span className="px-2 py-1 bg-[#F6F3F1] rounded border border-[#E6E4DF]">
              4. Source
            </span>
            <span className="text-[#605E59]">→</span>
            <span className="px-2 py-1 bg-[#F6F3F1] rounded border border-[#E6E4DF]">
              5. Page
            </span>
            <span className="text-[#605E59]">→</span>
            <span className="px-2 py-1 bg-[#F0EDEB] rounded border border-[#E6E4DF] font-serif italic">
              6. Quote
            </span>
          </div>
        </div>

        <button
          onClick={onCreateClick}
          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-[#A6331B] text-white text-xs font-semibold hover:bg-[#891E07] transition-colors shadow-xs"
          id="empty-create-notebook-btn"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          <span>Create Research Notebook</span>
        </button>
      </div>
    </div>
  );
}
