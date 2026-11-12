import { Bell, Upload, Search, Menu } from 'lucide-react';
import { useUIStore, useAuthStore, useDocumentStore } from '../../store';

export default function TopBar() {
  const { openUploadModal, openSearch, toggleSidebar } = useUIStore();
  const { user } = useAuthStore();
  const { documents } = useDocumentStore();

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase()
    : 'U';

  return (
    <header
      className="fixed top-0 left-0 md:left-[260px] right-0 h-14 z-40 px-3 md:px-4 flex items-center justify-between gap-2 md:gap-4"
      style={{
        backgroundColor: 'var(--color-surface-container-lowest)',
        borderBottom: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
      }}
    >
      {/* Mobile Menu Button + Search bar */}
      <div className="flex items-center gap-2 flex-1 max-w-xl min-w-0">
        <button
          onClick={toggleSidebar}
          className="md:hidden p-1.5 rounded-lg transition-colors flex items-center justify-center flex-shrink-0"
          style={{ color: 'var(--color-on-surface-variant)' }}
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>

        <button
          onClick={openSearch}
          className="w-full flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-lg transition-all text-left min-w-0"
          style={{
            backgroundColor: 'var(--color-surface-container-low)',
            border: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
            color: 'var(--color-on-surface-variant)',
          }}
        >
          <Search size={16} className="flex-shrink-0" />
          <span className="text-body-sm sm:text-body-md flex-1 truncate">
            Search documents & citations...
          </span>
          <span
            className="hidden sm:inline-flex text-code-sm px-1.5 py-0.5 rounded flex-shrink-0"
            style={{
              backgroundColor: 'var(--color-surface-container-high)',
              color: 'var(--color-on-surface-variant)',
            }}
          >
            ⌘K
          </span>
        </button>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
        {/* Sync status */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-full text-label-sm font-medium"
          style={{
            backgroundColor: 'color-mix(in srgb, var(--color-tertiary-container) 15%, transparent)',
            color: 'var(--color-tertiary)',
          }}
        >
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: 'var(--color-tertiary)' }}
          />
          <span>Synced with {documents.length} sources</span>
        </div>

        <div
          className="h-4 w-px hidden md:block"
          style={{ backgroundColor: 'color-mix(in srgb, var(--color-outline-variant) 40%, transparent)' }}
        />

        {/* Notifications */}
        <button
          className="relative p-1.5 rounded-lg transition-colors flex items-center justify-center"
          style={{ color: 'var(--color-on-surface-variant)' }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-surface-variant)';
            (e.currentTarget as HTMLElement).style.color = 'var(--color-on-surface)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
            (e.currentTarget as HTMLElement).style.color = 'var(--color-on-surface-variant)';
          }}
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ backgroundColor: 'var(--color-error)' }}
          />
        </button>

        {/* Upload button */}
        <button
          onClick={openUploadModal}
          className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-label-md transition-colors shadow-sm flex-shrink-0"
          style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-on-primary)' }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-primary-container)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-primary)';
          }}
        >
          <Upload size={16} />
          <span className="hidden sm:inline">Upload</span>
        </button>

        {/* User avatar */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-label-md font-semibold cursor-pointer flex-shrink-0"
          style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
        >
          {initials}
        </div>
      </div>
    </header>
  );
}

