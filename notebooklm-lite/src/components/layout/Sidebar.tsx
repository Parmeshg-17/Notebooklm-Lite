import React, { useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Home, FolderOpen, Clock, Star, Share2, Plus, BarChart2,
  Settings, BookOpen, ChevronsUpDown, FileText,
  Beaker, Link2, ShieldCheck,
} from 'lucide-react';
import { useNotebookStore, useAuthStore, useUIStore } from '../../store';

const NOTEBOOK_ICONS: Record<string, React.ElementType> = {
  description: FileText,
  analytics: BarChart2,
  biotech: Beaker,
  hub: Link2,
  security: ShieldCheck,
};

export default function Sidebar() {
  const { notebooks, activeNotebookId, setActiveNotebook, loadNotebooks } = useNotebookStore();
  const { user } = useAuthStore();
  const { openCreateNotebookModal } = useUIStore();
  const navigate = useNavigate();

  useEffect(() => {
    loadNotebooks();
  }, [loadNotebooks]);

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase()
    : 'U';

  return (
    <aside
      className="fixed left-0 top-0 h-full w-[260px] flex flex-col justify-between select-none z-50"
      style={{
        backgroundColor: 'var(--color-surface-container-low)',
        borderRight: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
      }}
    >
      {/* Top scrollable area */}
      <div className="flex flex-col min-h-0 flex-1">
        {/* Logo header */}
        <div
          className="h-14 px-3 flex items-center justify-between gap-2"
          style={{
            borderBottom: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              <BookOpen size={16} color="white" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-headline-sm truncate leading-tight" style={{ color: 'var(--color-on-surface)' }}>
                NotebookLM
              </span>
              <span className="text-code-sm truncate" style={{ color: 'var(--color-on-surface-variant)' }}>
                Lite
              </span>
            </div>
          </div>
          <span
            className="px-1.5 py-0.5 rounded-lg text-code-sm font-medium uppercase tracking-wider flex-shrink-0"
            style={{
              backgroundColor: 'var(--color-secondary-container)',
              color: 'var(--color-on-secondary-container)',
            }}
          >
            v1.4 Ent
          </span>
        </div>

        {/* Scrollable nav */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
          {/* Overview section */}
          <nav className="space-y-0.5">
            <div className="px-1 pb-1 text-label-sm uppercase tracking-wider font-semibold" style={{ color: 'var(--color-on-surface-variant)' }}>
              Overview
            </div>
            <NavItem to="/dashboard" icon={Home} label="Home" />
            <NavItem to="/notebooks" icon={FolderOpen} label="My Notebooks" badge={notebooks.length > 0 ? String(notebooks.length) : undefined} />
            <NavItem to="/activity" icon={Clock} label="Recent Activity" />
            <NavItem to="/starred" icon={Star} label="Starred" />
            <NavItem to="/shared" icon={Share2} label="Shared with Me" />
          </nav>

          {/* Workspaces section */}
          <div className="space-y-1">
            <div className="flex items-center justify-between px-1">
              <span className="text-label-sm uppercase tracking-wider font-semibold" style={{ color: 'var(--color-on-surface-variant)' }}>
                Workspaces
              </span>
              <button
                onClick={openCreateNotebookModal}
                className="p-1 rounded-lg transition-colors flex items-center justify-center"
                style={{ color: 'var(--color-on-surface-variant)' }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-surface-variant)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--color-primary)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = 'var(--color-on-surface-variant)';
                }}
                title="Create Notebook"
              >
                <Plus size={16} />
              </button>
            </div>

            <nav className="space-y-0.5">
              {notebooks.slice(0, 6).map((nb) => {
                const IconComp = NOTEBOOK_ICONS[nb.iconName ?? 'description'] ?? FileText;
                const isActive = activeNotebookId === nb.id;
                return (
                  <button
                    key={nb.id}
                    onClick={() => {
                      setActiveNotebook(nb.id);
                      navigate(`/workspace/${nb.id}`);
                    }}
                    className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-body-md text-left transition-colors"
                    style={{
                      backgroundColor: isActive ? 'var(--color-primary-fixed)' : 'transparent',
                      color: isActive ? 'var(--color-on-primary-fixed-variant)' : 'var(--color-on-surface-variant)',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-surface-variant)';
                        (e.currentTarget as HTMLElement).style.color = 'var(--color-on-surface)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                        (e.currentTarget as HTMLElement).style.color = 'var(--color-on-surface-variant)';
                      }
                    }}
                  >
                    <IconComp size={16} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
                    <span className="truncate">{nb.title}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Bottom section */}
      <div
        className="p-2 space-y-2"
        style={{
          borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
          backgroundColor: 'var(--color-surface-container-low)',
        }}
      >
        <nav className="space-y-0.5">
          <NavItem to="/analytics" icon={BarChart2} label="Analytics & Observability" />
          <NavItem to="/settings" icon={Settings} label="Settings" />
          <NavItem to="/help" icon={BookOpen} label="Help & Documentation" />
        </nav>

        {/* User profile */}
        <div
          className="pt-2 flex items-center justify-between gap-2 px-1"
          style={{ borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 20%, transparent)' }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-label-md font-semibold"
              style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
            >
              {initials}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-label-md font-semibold truncate" style={{ color: 'var(--color-on-surface)' }}>
                {user?.name ?? 'Researcher'}
              </span>
              <span className="text-code-sm truncate" style={{ color: 'var(--color-on-surface-variant)' }}>
                {user?.plan ?? 'Pro'}
              </span>
            </div>
          </div>
          <button className="p-1 rounded-lg transition-colors flex-shrink-0" style={{ color: 'var(--color-on-surface-variant)' }}>
            <ChevronsUpDown size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}

// ── NavItem helper ───────────────────────────────────────────────────────────
interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: string;
}

function NavItem({ to, icon: Icon, label, badge }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className="flex items-center justify-between px-2 py-1.5 rounded-lg text-body-md transition-colors"
      style={({ isActive }) => ({
        backgroundColor: isActive ? 'var(--color-primary-container)' : 'transparent',
        color: isActive ? 'var(--color-on-primary-container)' : 'var(--color-on-surface-variant)',
        fontWeight: isActive ? 500 : 400,
      })}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement;
        if (!el.getAttribute('aria-current')) {
          el.style.backgroundColor = 'var(--color-surface-variant)';
          el.style.color = 'var(--color-on-surface)';
        }
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        if (!el.getAttribute('aria-current')) {
          el.style.backgroundColor = 'transparent';
          el.style.color = 'var(--color-on-surface-variant)';
        }
      }}
    >
      <div className="flex items-center gap-2">
        <Icon size={18} />
        <span>{label}</span>
      </div>
      {badge && (
        <span
          className="px-1.5 py-0.5 rounded-full text-code-sm font-medium"
          style={{
            backgroundColor: 'var(--color-secondary-container)',
            color: 'var(--color-on-secondary-container)',
          }}
        >
          {badge}
        </span>
      )}
    </NavLink>
  );
}
