import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Plus, Upload, Database, Activity,
  Layers, HardDrive, MessageSquare,
  ArrowRight, Sparkles, Send,
  FileCheck
} from 'lucide-react';
import { useNotebookStore, useUIStore } from '../../store';
import { apiClient } from '../../services/api/client';
import { formatRelativeTime } from '../../utils/mockData';
import NotebookCard from '../../components/notebook/NotebookCard';
import MetricCard from '../../components/analytics/MetricCard';
import Button from '../../components/common/Button';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { notebooks, setActiveNotebook, loadNotebooks } = useNotebookStore();
  const { openCreateNotebookModal, openUploadModal } = useUIStore();
  const [quickPrompt, setQuickPrompt] = useState('');
  const [stats, setStats] = useState({
    total_notebooks: 0,
    total_documents: 0,
    questions_asked: 0,
    storage_used_mb: 0,
  });

  useEffect(() => {
    loadNotebooks();
    apiClient.get<any>('/api/users/me/stats')
      .then((res) => {
        if (res) setStats(res);
      })
      .catch(() => {});
  }, [loadNotebooks]);

  const [today] = useState(() =>
    new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
    })
  );

  const recentNotebooks = notebooks.slice(0, 4);

  const handleQuickPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickPrompt.trim()) return;
    const defaultNbId = notebooks[0]?.id ?? 'nb-1';
    setActiveNotebook(defaultNbId);
    navigate(`/workspace/${defaultNbId}`);
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-6 md:space-y-8 animate-in fade-in duration-300">
      {/* ── Welcome Header Section ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-label-sm font-semibold uppercase tracking-wider" style={{ color: 'var(--color-primary)' }}>
              {today}
            </span>
            <span className="text-label-sm text-[--color-on-surface-variant]">·</span>
            <span className="text-label-sm text-[--color-on-surface-variant]">Workspace Overview</span>
          </div>
          <h1 className="text-display-lg font-bold" style={{ color: 'var(--color-on-surface)' }}>
            Good morning, Dr. Vance
          </h1>
          <p className="text-body-md mt-1" style={{ color: 'var(--color-on-surface-variant)' }}>
            Your research synthesis engine is grounded across 148 indexed sources in 12 workspaces.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="ghost"
            icon={Database}
            onClick={() => alert('Zotero & Google Drive connectors active. 3 external sync jobs running.')}
          >
            Import Sources
          </Button>
          <Button
            variant="secondary"
            icon={Upload}
            onClick={openUploadModal}
          >
            Upload Documents
          </Button>
          <Button
            variant="primary"
            icon={Plus}
            onClick={openCreateNotebookModal}
          >
            Create Notebook
          </Button>
        </div>
      </div>

      {/* ── System Status Strip ── */}
      <div
        className="flex flex-wrap items-center justify-between gap-4 px-4 py-3 rounded-xl shadow-xs"
        style={{
          backgroundColor: 'var(--color-surface-container-lowest)',
          border: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
        }}
      >
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2 text-label-md">
            <span className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-tertiary)' }} />
            <span className="font-semibold" style={{ color: 'var(--color-tertiary)' }}>
              RAG Engine Active
            </span>
          </div>

          <div className="text-body-sm text-[--color-on-surface-variant]">
            <span className="font-medium">Embedding Model:</span>{' '}
            <span className="font-mono text-code-sm px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--color-surface-container-low)' }}>
              text-embedding-3-large (3072d)
            </span>
          </div>

          <div className="text-body-sm text-[--color-on-surface-variant]">
            <span className="font-medium">Grounding Mode:</span>{' '}
            <span className="font-medium" style={{ color: 'var(--color-primary)' }}>
              Strict Grounding (Direct Citation)
            </span>
          </div>
        </div>

        <Link
          to="/analytics"
          className="text-label-sm font-semibold flex items-center gap-1 hover:underline"
          style={{ color: 'var(--color-primary)' }}
        >
          <span>Telemetry & Model Health</span>
          <ArrowRight size={13} />
        </Link>
      </div>

      {/* ── KPI Metric Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Notebooks"
          value={String(notebooks.length || stats.total_notebooks)}
          change={notebooks.length > 0 ? 100 : 0}
          changeLabel="in workspace"
          icon={Layers}
        />
        <MetricCard
          label="Indexed Sources"
          value={String(stats.total_documents)}
          subtitle="grounded documents"
          icon={FileCheck}
        />
        <MetricCard
          label="Queries & Syntheses"
          value={String(stats.questions_asked)}
          subtitle="citations verified"
          icon={MessageSquare}
        />
        <MetricCard
          label="Knowledge Storage"
          value={`${stats.storage_used_mb} MB`}
          progress={{ current: stats.storage_used_mb, max: 1024, unit: 'MB' }}
          icon={HardDrive}
        />
      </div>

      {/* ── Recent Notebooks Section ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-headline-md font-bold" style={{ color: 'var(--color-on-surface)' }}>
              Recent Workspaces
            </h2>
            <span
              className="text-code-sm px-2 py-0.5 rounded-full font-medium"
              style={{
                backgroundColor: 'var(--color-surface-container-high)',
                color: 'var(--color-on-surface-variant)',
              }}
            >
              {notebooks.length} total
            </span>
          </div>
          <Link
            to="/notebooks"
            className="text-label-md font-semibold flex items-center gap-1 hover:underline"
            style={{ color: 'var(--color-primary)' }}
          >
            <span>View All Notebooks</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {recentNotebooks.map((nb) => (
            <NotebookCard key={nb.id} notebook={nb} />
          ))}
        </div>
      </div>

      {/* ── Two Column Lower Section: Activity & Grounded Starters ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 7 cols: Activity Stream */}
        <div
          className="lg:col-span-7 rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
          }}
        >
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--color-surface-container)' }}>
            <div className="flex items-center gap-2">
              <Activity size={18} style={{ color: 'var(--color-primary)' }} />
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                Activity & Indexing Stream
              </h3>
            </div>
            <span className="text-code-sm text-[--color-on-surface-variant]">Live updates</span>
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--color-surface-container)' }}>
            {notebooks.length === 0 ? (
              <div className="py-8 text-center text-body-sm text-[--color-on-surface-variant]">
                No recent activity yet. Create a notebook or upload a PDF document to begin.
              </div>
            ) : (
              notebooks.slice(0, 5).map((nb) => (
                <div key={nb.id} className="py-3.5 first:pt-1 last:pb-0 flex items-start gap-3">
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{
                      backgroundColor: 'var(--color-primary-fixed)',
                      color: 'var(--color-primary)',
                    }}
                  >
                    <Sparkles size={15} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="text-body-md font-semibold truncate" style={{ color: 'var(--color-on-surface)' }}>
                        {nb.title}
                      </span>
                      <span className="text-code-sm flex-shrink-0" style={{ color: 'var(--color-on-surface-variant)' }}>
                        {formatRelativeTime(nb.lastModified || nb.createdAt || new Date().toISOString())}
                      </span>
                    </div>
                    <p className="text-body-sm leading-relaxed" style={{ color: 'var(--color-on-surface-variant)' }}>
                      {nb.description || `Category: ${nb.tag} • ${nb.sourceCount || 0} sources connected`}
                    </p>

                    <button
                      onClick={() => {
                        setActiveNotebook(nb.id);
                        navigate(`/workspace/${nb.id}`);
                      }}
                      className="mt-2 text-label-sm font-semibold flex items-center gap-1 hover:underline"
                      style={{ color: 'var(--color-primary)' }}
                    >
                      <span>Open Workspace</span>
                      <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 5 cols: Grounded Prompt Starters */}
        <div
          className="lg:col-span-5 rounded-2xl p-6 shadow-xs space-y-4"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
          }}
        >
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--color-surface-container)' }}>
            <div className="flex items-center gap-2">
              <Sparkles size={18} style={{ color: 'var(--color-primary)' }} />
              <h3 className="text-headline-sm font-bold" style={{ color: 'var(--color-on-surface)' }}>
                Cross-Corpus Starters
              </h3>
            </div>
            <span className="text-code-sm text-[--color-on-surface-variant]">Enterprise RAG</span>
          </div>

          <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            Synthesize information across multiple indexed notebooks with high precision:
          </p>

          <div className="space-y-2.5">
            {[
              {
                q: 'Compare KV-cache compression techniques across FlashAttention-3 and PagedAttention.',
                targetNb: 'nb-1',
              },
              {
                q: 'What are the formal verification bounds on Raft leader election under network partitions?',
                targetNb: 'nb-5',
              },
              {
                q: 'Extract all SOC2 Type II audit exhibit requirements related to data at rest encryption.',
                targetNb: 'nb-6',
              },
            ].map((starter, i) => (
              <div
                key={i}
                onClick={() => {
                  setActiveNotebook(starter.targetNb);
                  navigate(`/workspace/${starter.targetNb}`);
                }}
                className="p-3 rounded-xl border transition-all cursor-pointer group hover:bg-[--color-surface-container-low] hover:border-[--color-primary]"
                style={{ borderColor: 'var(--color-outline-variant)' }}
              >
                <p className="text-body-sm font-medium text-[--color-on-surface] group-hover:text-[--color-primary] leading-relaxed">
                  "{starter.q}"
                </p>
                <div className="flex items-center justify-between mt-2 text-code-sm text-[--color-on-surface-variant]">
                  <span>1-click synthesis</span>
                  <ArrowRight size={13} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            ))}
          </div>

          {/* Mini Prompt Dock */}
          <form onSubmit={handleQuickPrompt} className="pt-2">
            <div
              className="flex items-center gap-2 p-1.5 rounded-xl border focus-within:border-[--color-primary] transition-all"
              style={{
                backgroundColor: 'var(--color-surface-container-low)',
                borderColor: 'var(--color-outline-variant)',
              }}
            >
              <input
                type="text"
                placeholder="Ask anything across active sources..."
                value={quickPrompt}
                onChange={(e) => setQuickPrompt(e.target.value)}
                className="flex-1 bg-transparent border-none outline-none px-2 text-body-sm text-[--color-on-surface]"
              />
              <button
                type="submit"
                disabled={!quickPrompt.trim()}
                className="p-2 rounded-lg text-white transition-all disabled:opacity-40"
                style={{ backgroundColor: 'var(--color-primary)' }}
              >
                <Send size={14} />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
