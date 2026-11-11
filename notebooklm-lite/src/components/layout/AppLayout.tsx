import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import UploadModal from '../documents/UploadModal';
import CreateNotebookModal from '../notebook/CreateNotebookModal';
import GlobalSearchModal from '../common/GlobalSearchModal';
import { useUIStore } from '../../store';

export default function AppLayout() {
  const { uploadModalOpen, createNotebookModalOpen, searchOpen } = useUIStore();

  return (
    <div style={{ backgroundColor: 'var(--color-surface)', minHeight: '100vh' }}>
      <Sidebar />
      <TopBar />

      {/* Main content */}
      <main className="pl-[260px] pt-14 min-h-screen">
        <Outlet />
      </main>

      {/* Global modals */}
      {uploadModalOpen && <UploadModal />}
      {createNotebookModalOpen && <CreateNotebookModal />}
      {searchOpen && <GlobalSearchModal />}
    </div>
  );
}

