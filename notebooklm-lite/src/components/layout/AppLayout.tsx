import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import UploadModal from '../documents/UploadModal';
import CreateNotebookModal from '../notebook/CreateNotebookModal';
import GlobalSearchModal from '../common/GlobalSearchModal';
import { useUIStore } from '../../store';

export default function AppLayout() {
  const { uploadModalOpen, createNotebookModalOpen, searchOpen, sidebarOpen, closeSidebar } = useUIStore();

  return (
    <div style={{ backgroundColor: 'var(--color-surface)', minHeight: '100vh' }}>
      <Sidebar />
      <TopBar />

      {/* Mobile Backdrop Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden backdrop-blur-xs transition-opacity duration-300"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Main content */}
      <main className="pl-0 md:pl-[260px] pt-14 min-h-screen w-full overflow-x-hidden">
        <Outlet />
      </main>

      {/* Global modals */}
      {uploadModalOpen && <UploadModal />}
      {createNotebookModalOpen && <CreateNotebookModal />}
      {searchOpen && <GlobalSearchModal />}
    </div>
  );
}

