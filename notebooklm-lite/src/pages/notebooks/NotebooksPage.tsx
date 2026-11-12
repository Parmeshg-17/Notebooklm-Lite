import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, LayoutGrid, List, Plus,
  FileText, Clock, Star, ExternalLink,
  ChevronDown
} from 'lucide-react';
import { useNotebookStore, useUIStore } from '../../store';
import NotebookCard from '../../components/notebook/NotebookCard';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import { formatRelativeTime } from '../../utils/mockData';

type SortOption = 'lastModified' | 'createdAt' | 'title' | 'sourceCount';

export default function NotebooksPage() {
  const navigate = useNavigate();
  const { notebooks, setActiveNotebook, toggleStar, loadNotebooks } = useNotebookStore();
  const { openCreateNotebookModal } = useUIStore();

  useEffect(() => {
    loadNotebooks();
  }, [loadNotebooks]);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string>('All');
  const [sortBy, setSortBy] = useState<SortOption>('lastModified');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Compute tag counts
  const tagsWithCounts = useMemo(() => {
    const counts: Record<string, number> = { All: notebooks.length };
    notebooks.forEach((nb) => {
      counts[nb.tag] = (counts[nb.tag] ?? 0) + 1;
    });
    return Object.entries(counts);
  }, [notebooks]);

  // Filter and sort
  const filteredNotebooks = useMemo(() => {
    let result = [...notebooks];

    if (selectedTag !== 'All') {
      result = result.filter((nb) => nb.tag === selectedTag);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (nb) =>
          nb.title.toLowerCase().includes(q) ||
          nb.description.toLowerCase().includes(q)
      );
    }

    result.sort((a, b) => {
      switch (sortBy) {
        case 'lastModified':
          return new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime();
        case 'createdAt':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'title':
          return a.title.localeCompare(b.title);
        case 'sourceCount':
          return b.sourceCount - a.sourceCount;
        default:
          return 0;
      }
    });

    return result;
  }, [notebooks, selectedTag, searchQuery, sortBy]);

  const totalSources = notebooks.reduce((acc, nb) => acc + nb.sourceCount, 0);

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-label-sm font-semibold uppercase tracking-wider"
              style={{ color: 'var(--color-primary)' }}
            >
              Enterprise Knowledge Repository
            </span>
            <span className="text-label-sm text-[--color-on-surface-variant]">·</span>
            <span className="text-label-sm text-[--color-on-surface-variant]">
              {notebooks.length} Workspaces · {totalSources} Sources
            </span>
          </div>
          <h1 className="text-display-lg font-bold" style={{ color: 'var(--color-on-surface)' }}>
            Notebooks Library
          </h1>
        </div>

        <Button
          variant="primary"
          icon={Plus}
          onClick={openCreateNotebookModal}
        >
          New Notebook
        </Button>
      </div>

      {/* ── Action Bar: Search, Sort, View Toggle ── */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[--color-on-surface-variant]"
          />
          <input
            type="text"
            placeholder="Search notebooks by title or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl text-body-md outline-none transition-all"
            style={{
              backgroundColor: 'var(--color-surface-container-lowest)',
              border: '1px solid var(--color-outline-variant)',
              color: 'var(--color-on-surface)',
            }}
          />
        </div>

        {/* Sort & View Toggle Controls */}
        <div className="flex items-center gap-3">
          {/* Sort Dropdown */}
          <div className="relative flex items-center">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="appearance-none pl-3 pr-8 py-2 rounded-xl text-label-md font-medium outline-none cursor-pointer"
              style={{
                backgroundColor: 'var(--color-surface-container-lowest)',
                border: '1px solid var(--color-outline-variant)',
                color: 'var(--color-on-surface)',
              }}
            >
              <option value="lastModified">Sort by: Last Modified</option>
              <option value="createdAt">Sort by: Creation Date</option>
              <option value="title">Sort by: Alphabetical</option>
              <option value="sourceCount">Sort by: Source Count</option>
            </select>
            <ChevronDown size={14} className="absolute right-3 pointer-events-none text-[--color-on-surface-variant]" />
          </div>

          {/* Grid / List Switcher */}
          <div
            className="flex items-center p-1 rounded-xl"
            style={{
              backgroundColor: 'var(--color-surface-container-low)',
              border: '1px solid var(--color-outline-variant)',
            }}
          >
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === 'grid'
                  ? 'bg-[--color-surface-container-lowest] shadow-2xs text-[--color-primary]'
                  : 'text-[--color-on-surface-variant] hover:text-[--color-on-surface]'
              }`}
              title="Grid View"
            >
              <LayoutGrid size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === 'list'
                  ? 'bg-[--color-surface-container-lowest] shadow-2xs text-[--color-primary]'
                  : 'text-[--color-on-surface-variant] hover:text-[--color-on-surface]'
              }`}
              title="List View"
            >
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Tag Filter Chips Row ── */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {tagsWithCounts.map(([tag, count]) => {
          const isActive = selectedTag === tag;
          return (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag)}
              className={`px-3 py-1.5 rounded-full text-label-md font-medium whitespace-nowrap transition-all cursor-pointer flex items-center gap-1.5 ${
                isActive
                  ? 'shadow-xs'
                  : 'hover:bg-[--color-surface-container-low]'
              }`}
              style={{
                backgroundColor: isActive
                  ? 'var(--color-primary)'
                  : 'var(--color-surface-container-lowest)',
                color: isActive ? 'var(--color-on-primary)' : 'var(--color-on-surface-variant)',
                border: `1px solid ${
                  isActive ? 'var(--color-primary)' : 'var(--color-outline-variant)'
                }`,
              }}
            >
              <span>{tag}</span>
              <span
                className={`text-code-sm px-1.5 py-0.2 rounded-full ${
                  isActive ? 'bg-white/20 text-white' : 'bg-[--color-surface-container]'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Content Area: Grid or List ── */}
      {filteredNotebooks.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No notebooks found"
          description={
            searchQuery
              ? `No workspaces matching "${searchQuery}". Try a different search term or category.`
              : 'Create your first research notebook to start synthesizing documents.'
          }
          action={{
            label: 'Create Notebook',
            onClick: openCreateNotebookModal,
            icon: <Plus size={16} />,
          }}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredNotebooks.map((nb) => (
            <NotebookCard key={nb.id} notebook={nb} />
          ))}
        </div>
      ) : (
        /* List View Table */
        <div
          className="rounded-2xl overflow-hidden shadow-xs"
          style={{
            backgroundColor: 'var(--color-surface-container-lowest)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
          }}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr
                  className="text-label-sm font-semibold uppercase tracking-wider border-b"
                  style={{
                    backgroundColor: 'var(--color-surface-container-low)',
                    borderColor: 'var(--color-outline-variant)',
                    color: 'var(--color-on-surface-variant)',
                  }}
                >
                  <th className="py-3 px-4 w-10"></th>
                  <th className="py-3 px-4">Title & Description</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Sources</th>
                  <th className="py-3 px-4">Last Modified</th>
                  <th className="py-3 px-4">Owner</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--color-surface-container)' }}>
                {filteredNotebooks.map((nb) => (
                  <tr
                    key={nb.id}
                    onClick={() => {
                      setActiveNotebook(nb.id);
                      navigate(`/workspace/${nb.id}`);
                    }}
                    className="hover:bg-[--color-surface-container-low] cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => toggleStar(nb.id)}
                        className="text-[--color-on-surface-variant] hover:text-[#f59e0b]"
                      >
                        <Star
                          size={15}
                          fill={nb.isStarred ? '#f59e0b' : 'none'}
                          color={nb.isStarred ? '#f59e0b' : 'currentColor'}
                        />
                      </button>
                    </td>

                    <td className="py-3 px-4 max-w-xs md:max-w-md">
                      <div className="font-semibold text-body-md text-[--color-on-surface] group-hover:text-[--color-primary] transition-colors">
                        {nb.title}
                      </div>
                      <div className="text-body-sm text-[--color-on-surface-variant] line-clamp-1">
                        {nb.description}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <Badge tag={nb.tag} size="sm" />
                    </td>

                    <td className="py-3 px-4 text-body-sm font-medium text-[--color-on-surface]">
                      <div className="flex items-center gap-1.5">
                        <FileText size={14} style={{ color: 'var(--color-primary)' }} />
                        <span>{nb.sourceCount}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-body-sm text-[--color-on-surface-variant]">
                      <div className="flex items-center gap-1">
                        <Clock size={12} />
                        <span>{formatRelativeTime(nb.lastModified)}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-body-sm text-[--color-on-surface-variant]">
                      {nb.owner}
                    </td>

                    <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={ExternalLink}
                        onClick={() => {
                          setActiveNotebook(nb.id);
                          navigate(`/workspace/${nb.id}`);
                        }}
                      >
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
