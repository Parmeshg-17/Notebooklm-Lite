import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MoreVertical, FileText, Clock, Star, Trash2, Edit3,
  ExternalLink
} from 'lucide-react';
import type { Notebook } from '../../types';
import Badge from '../common/Badge';
import { useNotebookStore } from '../../store';
import { formatRelativeTime } from '../../utils/mockData';

export interface NotebookCardProps {
  notebook: Notebook;
}

export default function NotebookCard({ notebook }: NotebookCardProps) {
  const navigate = useNavigate();
  const { toggleStar, deleteNotebook, setActiveNotebook } = useNotebookStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const handleCardClick = () => {
    setActiveNotebook(notebook.id);
    navigate(`/workspace/${notebook.id}`);
  };

  return (
    <div
      onClick={handleCardClick}
      className="group relative flex flex-col justify-between rounded-xl p-5 transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md"
      style={{
        backgroundColor: 'var(--color-surface-container-lowest)',
        border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
      }}
    >
      <div>
        {/* Top bar: Badge & actions */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <Badge tag={notebook.tag} size="sm" />

          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => toggleStar(notebook.id)}
              className="p-1.5 rounded-lg transition-colors hover:bg-[--color-surface-container]"
              style={{
                color: notebook.isStarred
                  ? '#f59e0b'
                  : 'var(--color-on-surface-variant)',
              }}
              title={notebook.isStarred ? 'Unstar' : 'Star'}
            >
              <Star
                size={16}
                fill={notebook.isStarred ? '#f59e0b' : 'none'}
              />
            </button>

            {/* Context Menu Trigger */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-1.5 rounded-lg transition-colors hover:bg-[--color-surface-container]"
                style={{ color: 'var(--color-on-surface-variant)' }}
                title="Options"
              >
                <MoreVertical size={16} />
              </button>

              {menuOpen && (
                <div
                  className="absolute right-0 top-full mt-1 w-44 rounded-xl shadow-xl py-1 z-30 animate-in fade-in zoom-in-95"
                  style={{
                    backgroundColor: 'var(--color-surface-container-lowest)',
                    border: '1px solid var(--color-outline-variant)',
                  }}
                >
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      handleCardClick();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-label-md text-left transition-colors hover:bg-[--color-surface-container]"
                    style={{ color: 'var(--color-on-surface)' }}
                  >
                    <ExternalLink size={14} />
                    <span>Open Workspace</span>
                  </button>

                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      toggleStar(notebook.id);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-label-md text-left transition-colors hover:bg-[--color-surface-container]"
                    style={{ color: 'var(--color-on-surface)' }}
                  >
                    <Star size={14} />
                    <span>{notebook.isStarred ? 'Unstar' : 'Star'}</span>
                  </button>

                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      const newTitle = prompt('Rename notebook:', notebook.title);
                      if (newTitle) {
                        useNotebookStore.getState().updateNotebook(notebook.id, { title: newTitle });
                      }
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-label-md text-left transition-colors hover:bg-[--color-surface-container]"
                    style={{ color: 'var(--color-on-surface)' }}
                  >
                    <Edit3 size={14} />
                    <span>Rename</span>
                  </button>

                  <div
                    className="my-1 border-t"
                    style={{ borderColor: 'var(--color-outline-variant)' }}
                  />

                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      if (confirm(`Delete "${notebook.title}"?`)) {
                        deleteNotebook(notebook.id);
                      }
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-label-md text-left transition-colors hover:bg-[--color-error-container]"
                    style={{ color: 'var(--color-error)' }}
                  >
                    <Trash2 size={14} />
                    <span>Delete</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Title */}
        <h3
          className="text-headline-sm font-semibold transition-colors group-hover:text-[--color-primary] mb-1.5"
          style={{ color: 'var(--color-on-surface)' }}
        >
          {notebook.title}
        </h3>

        {/* Description */}
        <p
          className="text-body-md line-clamp-3 mb-4"
          style={{ color: 'var(--color-on-surface-variant)' }}
        >
          {notebook.description || 'No description provided.'}
        </p>
      </div>

      {/* Footer */}
      <div
        className="pt-3 flex items-center justify-between text-body-sm"
        style={{
          borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
          color: 'var(--color-on-surface-variant)',
        }}
      >
        {/* Source count & Relative time */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-medium">
            <FileText size={14} style={{ color: 'var(--color-primary)' }} />
            <span>{notebook.sourceCount} sources</span>
          </span>
          <span className="flex items-center gap-1">
            <Clock size={12} />
            <span>{formatRelativeTime(notebook.lastModified)}</span>
          </span>
        </div>

        {/* Collaborators / Owner */}
        <div className="flex items-center gap-1.5">
          {notebook.collaborators && notebook.collaborators.length > 0 ? (
            <div className="flex -space-x-1.5 overflow-hidden">
              {notebook.collaborators.slice(0, 3).map((c, i) => (
                <div
                  key={c.id || i}
                  className="inline-block h-5 w-5 rounded-full ring-2 ring-white flex items-center justify-center text-[10px] font-bold text-white uppercase"
                  style={{ backgroundColor: 'var(--color-primary)' }}
                  title={c.name}
                >
                  {c.avatar ? (
                    <img src={c.avatar} alt={c.name} className="h-full w-full rounded-full object-cover" />
                  ) : (
                    c.name.slice(0, 2)
                  )}
                </div>
              ))}
              {notebook.collaborators.length > 3 && (
                <div
                  className="inline-block h-5 w-5 rounded-full ring-2 ring-white flex items-center justify-center text-[9px] font-medium"
                  style={{
                    backgroundColor: 'var(--color-secondary-container)',
                    color: 'var(--color-on-secondary-container)',
                  }}
                >
                  +{notebook.collaborators.length - 3}
                </div>
              )}
            </div>
          ) : (
            <span className="text-code-sm truncate max-w-[100px]">{notebook.owner}</span>
          )}
        </div>
      </div>
    </div>
  );
}
