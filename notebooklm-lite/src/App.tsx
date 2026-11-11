import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './store';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import NotebooksPage from './pages/notebooks/NotebooksPage';
import WorkspacePage from './pages/workspace/WorkspacePage';
import DocumentViewerPage from './pages/workspace/DocumentViewerPage';
import AnalyticsPage from './pages/analytics/AnalyticsPage';
import SettingsPage from './pages/settings/SettingsPage';
import SearchPage from './pages/search/SearchPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCheckingAuth } = useAuthStore();
  const location = useLocation();

  if (isCheckingAuth) {
    return (
      <div className="flex h-screen w-full items-center justify-center" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-8 h-8 rounded-full border-3 animate-spin"
            style={{
              borderColor: 'var(--color-primary)',
              borderTopColor: 'transparent',
            }}
          />
          <span className="text-body-sm font-medium" style={{ color: 'var(--color-on-surface-variant)' }}>
            Restoring workspace session...
          </span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const { checkAuth } = useAuthStore();

  React.useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <Routes>
      {/* Root redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Public auth routes */}
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<RegisterPage />} />

      {/* Protected application routes wrapped in AppLayout */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/notebooks" element={<NotebooksPage />} />
        <Route path="/workspace/:notebookId" element={<WorkspacePage />} />
        <Route
          path="/workspace/:notebookId/document/:documentId"
          element={<DocumentViewerPage />}
        />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/search" element={<SearchPage />} />

        {/* Sidebar auxiliary routes */}
        <Route path="/activity" element={<Navigate to="/dashboard" replace />} />
        <Route path="/starred" element={<Navigate to="/notebooks" replace />} />
        <Route path="/shared" element={<Navigate to="/notebooks" replace />} />
        <Route path="/help" element={<Navigate to="/settings" replace />} />
      </Route>

      {/* Fallback 404 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
