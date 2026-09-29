"use client";

import { useState } from "react";
import { notebooksApi } from "@/lib/api";
import type { Notebook } from "@/types";

interface Props {
  onCreated: (notebook: Notebook) => void;
  onClose: () => void;
}

export function CreateNotebookModal({ onCreated, onClose }: Props) {
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const notebook = await notebooksApi.create(title.trim());
      onCreated(notebook);
    } catch (err: any) {
      setError(err.message ?? "Failed to create notebook");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px]"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-md bg-white rounded-md border border-[#E6E4DF] shadow-[0_4px_24px_rgba(0,0,0,0.06)] p-6 text-[#1C1C1B]"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 mb-4 border-b border-[#EFECE6]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-[18px] text-[#A6331B]">
                menu_book
              </span>
              <h2 className="font-serif text-lg font-medium text-[#1C1C1B]">
                New Research Notebook
              </h2>
            </div>
            <p className="text-xs text-[#605E59]">
              Define an indexed corpus for citation-verified document analysis.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#605E59] hover:text-[#1C1C1B] hover:bg-[#F6F3F1] transition-colors"
            title="Close"
            id="close-create-modal-btn"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="notebook-title"
              className="block text-[11px] font-semibold uppercase tracking-wider text-[#605E59] mb-1.5"
            >
              Corpus Title
            </label>
            <input
              id="notebook-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Statistical Learning & Optimization"
              autoFocus
              className="w-full px-3 py-2 text-sm bg-[#FCF9F7] border border-[#E6E4DF] rounded text-[#1C1C1B] placeholder:text-[#9A9790] focus:outline-none focus:border-[#A6331B] transition-colors"
            />
          </div>

          {error && (
            <div className="p-3 text-xs rounded bg-[#FFDAD6]/40 border border-[#BA1A1A]/30 text-[#BA1A1A]">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium rounded border border-[#E6E4DF] bg-[#F6F3F1] text-[#605E59] hover:bg-[#EAE8E5] hover:text-[#1C1C1B] transition-colors"
              id="cancel-create-modal-btn"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim() || loading}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-[#A6331B] text-white hover:bg-[#891E07] disabled:opacity-40 transition-colors flex items-center gap-1.5"
              id="confirm-create-notebook-btn"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[14px] animate-spin-slow">
                    progress_activity
                  </span>
                  Creating…
                </>
              ) : (
                <>
                  <span>Create Notebook</span>
                  <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
