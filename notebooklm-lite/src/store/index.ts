import { create } from 'zustand';
import type { User, Notebook, Document, ChatMessage, ChatSession } from '../types';
import { MOCK_USER } from '../utils/mockData';

import { apiClient } from '../services/api/client';
import { notebookService } from '../services/notebook.service';
import { documentService } from '../services/document.service';
import { chatService } from '../services/chat.service';

// ─── Auth Store ───────────────────────────────────────────
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isCheckingAuth: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token') || localStorage.getItem('auth_token');
};

const initialStoredToken = getStoredToken();

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: initialStoredToken,
  isAuthenticated: Boolean(initialStoredToken),
  isCheckingAuth: true,
  login: async (email: string, password: string) => {
    try {
      const data = await apiClient.post<{ access_token: string; user: User }>('/api/v1/auth/login', {
        email,
        password,
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', data.access_token);
        localStorage.setItem('token', data.access_token);
      }
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isCheckingAuth: false });
    } catch {
      // Offline / fallback mode
      await new Promise((r) => setTimeout(r, 400));
      set({ user: MOCK_USER, isAuthenticated: true, isCheckingAuth: false });
    }
  },
  register: async (email: string, password: string, fullName: string) => {
    try {
      const data = await apiClient.post<{ access_token: string; user: User }>('/api/v1/auth/register', {
        email,
        password,
        full_name: fullName,
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', data.access_token);
        localStorage.setItem('token', data.access_token);
      }
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isCheckingAuth: false });
    } catch {
      set({ user: { ...MOCK_USER, email, name: fullName }, isAuthenticated: true, isCheckingAuth: false });
    }
  },
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('token');
    }
    set({ user: null, token: null, isAuthenticated: false, isCheckingAuth: false });
  },
  checkAuth: async () => {
    const token = getStoredToken();
    if (token) {
      try {
        const user = await apiClient.get<User>('/api/v1/auth/me');
        set({ user, token, isAuthenticated: true, isCheckingAuth: false });
        return;
      } catch {
        // Invalid or expired token
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('token');
        }
      }
    }

    // Auto-authenticate as default enterprise workspace researcher (Dr. Elena Vance)
    try {
      const data = await apiClient.post<{ access_token: string; user: User }>('/api/v1/auth/login', {
        email: 'elena.vance@blackmesa.gov',
        password: 'Password123!',
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', data.access_token);
        localStorage.setItem('token', data.access_token);
      }
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isCheckingAuth: false });
    } catch {
      set({ user: MOCK_USER, isAuthenticated: true, isCheckingAuth: false });
    }
  },
}));

// ─── Notebook Store ───────────────────────────────────────
interface NotebookState {
  notebooks: Notebook[];
  activeNotebookId: string | null;
  loadNotebooks: () => Promise<void>;
  setActiveNotebook: (id: string | null) => void;
  createNotebook: (data: Partial<Notebook>) => Promise<Notebook>;
  updateNotebook: (id: string, data: Partial<Notebook>) => Promise<void>;
  deleteNotebook: (id: string) => Promise<void>;
  toggleStar: (id: string) => void;
}

const getInitialNotebooks = (): Notebook[] => {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem('cached_notebooks') || '[]');
  } catch {
    return [];
  }
};

export const useNotebookStore = create<NotebookState>((set) => ({
  notebooks: getInitialNotebooks(),
  activeNotebookId: null,
  loadNotebooks: async () => {
    try {
      const nbs = await notebookService.list();
      if (nbs) {
        const localCached: Notebook[] = typeof window !== 'undefined'
          ? JSON.parse(localStorage.getItem('cached_notebooks') || '[]')
          : [];
        const map = new Map<string, Notebook>();
        nbs.forEach((nb) => map.set(nb.id, nb));
        localCached.forEach((nb) => {
          if (!map.has(nb.id)) map.set(nb.id, nb);
        });
        const merged = Array.from(map.values());
        if (typeof window !== 'undefined') {
          localStorage.setItem('cached_notebooks', JSON.stringify(merged));
        }
        set({ notebooks: merged });
        return;
      }
    } catch {
      // Keep existing
    }
    const localCached: Notebook[] = typeof window !== 'undefined'
      ? JSON.parse(localStorage.getItem('cached_notebooks') || '[]')
      : [];
    if (localCached.length > 0) {
      set((s) => ({
        notebooks: s.notebooks.length > 0 ? s.notebooks : localCached,
      }));
    }
  },
  setActiveNotebook: (id) => set({ activeNotebookId: id }),
  createNotebook: async (data) => {
    try {
      const nb = await notebookService.create(data);
      set((s) => {
        const next = [nb, ...s.notebooks.filter((n) => n.id !== nb.id)];
        if (typeof window !== 'undefined') {
          localStorage.setItem('cached_notebooks', JSON.stringify(next));
        }
        return { notebooks: next, activeNotebookId: nb.id };
      });
      return nb;
    } catch {
      const fallbackNb: Notebook = {
        id: crypto.randomUUID ? crypto.randomUUID() : `nb-${Date.now()}`,
        title: data.title ?? 'Untitled Notebook',
        description: data.description ?? '',
        tag: data.tag ?? 'General',
        sourceCount: 0,
        lastModified: new Date().toISOString(),
        createdAt: new Date().toISOString(),
        collaborators: [],
        owner: 'User',
        isStarred: false,
        isShared: false,
        ...data,
      };
      set((s) => {
        const next = [fallbackNb, ...s.notebooks.filter((n) => n.id !== fallbackNb.id)];
        if (typeof window !== 'undefined') {
          localStorage.setItem('cached_notebooks', JSON.stringify(next));
        }
        return { notebooks: next, activeNotebookId: fallbackNb.id };
      });
      return fallbackNb;
    }
  },
  updateNotebook: async (id, data) => {
    try {
      await notebookService.update(id, data);
    } catch {
      // Local fallback
    }
    set((s) => {
      const next = s.notebooks.map((n) => (n.id === id ? { ...n, ...data } : n));
      if (typeof window !== 'undefined') {
        localStorage.setItem('cached_notebooks', JSON.stringify(next));
      }
      return { notebooks: next };
    });
  },
  deleteNotebook: async (id) => {
    try {
      await notebookService.delete(id);
    } catch {
      // Local fallback
    }
    set((s) => {
      const next = s.notebooks.filter((n) => n.id !== id);
      if (typeof window !== 'undefined') {
        localStorage.setItem('cached_notebooks', JSON.stringify(next));
      }
      return {
        notebooks: next,
        activeNotebookId: s.activeNotebookId === id ? null : s.activeNotebookId,
      };
    });
  },
  toggleStar: (id) =>
    set((s) => {
      const next = s.notebooks.map((n) => (n.id === id ? { ...n, isStarred: !n.isStarred } : n));
      if (typeof window !== 'undefined') {
        localStorage.setItem('cached_notebooks', JSON.stringify(next));
      }
      return { notebooks: next };
    }),
}));

// ─── Document Store ───────────────────────────────────────
interface DocumentState {
  documents: Document[];
  selectedDocumentIds: Set<string>;
  loadDocuments: (notebookId: string) => Promise<void>;
  addDocument: (doc: Document) => void;
  updateDocument: (id: string, data: Partial<Document>) => void;
  removeDocument: (id: string) => void;
  toggleSelectDocument: (id: string) => void;
  selectAllDocuments: (notebookId: string) => void;
  deselectAllDocuments: () => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  documents: [],
  selectedDocumentIds: new Set<string>(),
  loadDocuments: async (notebookId: string) => {
    try {
      const docs = await documentService.list(notebookId);
      if (docs) {
        set((s) => {
          const otherDocs = s.documents.filter((d) => d.notebookId !== notebookId);
          const seen = new Set<string>();
          const uniqueDocs: Document[] = [];
          for (const d of docs) {
            if (!seen.has(d.id) && !seen.has(d.name)) {
              seen.add(d.id);
              seen.add(d.name);
              uniqueDocs.push(d);
            }
          }
          const allDocs = [...otherDocs, ...uniqueDocs];
          const indexedIds = new Set(uniqueDocs.filter((d) => d.status === 'indexed').map((d) => d.id));
          return { documents: allDocs, selectedDocumentIds: indexedIds };
        });
      }
    } catch {
      // Keep existing
    }
  },
  addDocument: (doc) =>
    set((s) => {
      const filtered = s.documents.filter(
        (d) => d.id !== doc.id && !(d.notebookId === doc.notebookId && d.name === doc.name)
      );
      return {
        documents: [doc, ...filtered],
        selectedDocumentIds: new Set([...s.selectedDocumentIds, doc.id]),
      };
    }),
  updateDocument: (id, data) =>
    set((s) => ({ documents: s.documents.map((d) => (d.id === id ? { ...d, ...data } : d)) })),
  removeDocument: (id) =>
    set((s) => ({
      documents: s.documents.filter((d) => d.id !== id),
      selectedDocumentIds: new Set([...s.selectedDocumentIds].filter((did) => did !== id)),
    })),
  toggleSelectDocument: (id) =>
    set((s) => {
      const next = new Set(s.selectedDocumentIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { selectedDocumentIds: next };
    }),
  selectAllDocuments: (notebookId) =>
    set((s) => ({
      selectedDocumentIds: new Set(
        s.documents.filter((d) => d.notebookId === notebookId && d.status === 'indexed').map((d) => d.id)
      ),
    })),
  deselectAllDocuments: () => set({ selectedDocumentIds: new Set() }),
}));

// ─── Chat Store ───────────────────────────────────────────
interface ChatState {
  sessions: Record<string, ChatSession>;
  getOrCreateSession: (notebookId: string) => ChatSession;
  loadHistory: (notebookId: string) => Promise<void>;
  addMessage: (notebookId: string, message: ChatMessage) => void;
  updateMessage: (notebookId: string, messageId: string, data: Partial<ChatMessage>) => void;
  clearSession: (notebookId: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: {},
  loadHistory: async (notebookId: string) => {
    try {
      const msgs = await chatService.getHistory(notebookId);
      if (msgs && msgs.length > 0) {
        set((state) => ({
          sessions: {
            ...state.sessions,
            [notebookId]: {
              id: `session-${notebookId}`,
              notebookId,
              messages: msgs,
              createdAt: new Date().toISOString(),
            },
          },
        }));
      }
    } catch {
      // Keep existing
    }
  },
  getOrCreateSession: (notebookId) => {
    const s = get();
    if (!s.sessions[notebookId]) {
      const session: ChatSession = {
        id: `session-${notebookId}`,
        notebookId,
        messages: [],
        createdAt: new Date().toISOString(),
      };
      set((state) => ({ sessions: { ...state.sessions, [notebookId]: session } }));
      return session;
    }
    return s.sessions[notebookId];
  },
  addMessage: (notebookId, message) => {
    const session = get().getOrCreateSession(notebookId);
    set((state) => ({
      sessions: {
        ...state.sessions,
        [notebookId]: {
          ...session,
          messages: [...session.messages, message],
        },
      },
    }));
  },
  updateMessage: (notebookId, messageId, data) => {
    const session = get().getOrCreateSession(notebookId);
    set((state) => ({
      sessions: {
        ...state.sessions,
        [notebookId]: {
          ...session,
          messages: session.messages.map((m) => (m.id === messageId ? { ...m, ...data } : m)),
        },
      },
    }));
  },
  clearSession: (notebookId) =>
    set((state) => {
      const next = { ...state.sessions };
      delete next[notebookId];
      return { sessions: next };
    }),
}));

// ─── UI Store ─────────────────────────────────────────────
interface UIState {
  sidebarOpen: boolean;
  uploadModalOpen: boolean;
  createNotebookModalOpen: boolean;
  searchOpen: boolean;
  activeDocumentId: string | null;
  activeCitationId: string | null;
  toggleSidebar: () => void;
  openUploadModal: () => void;
  closeUploadModal: () => void;
  openCreateNotebookModal: () => void;
  closeCreateNotebookModal: () => void;
  openSearch: () => void;
  closeSearch: () => void;
  setActiveDocument: (id: string | null) => void;
  setActiveCitation: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  uploadModalOpen: false,
  createNotebookModalOpen: false,
  searchOpen: false,
  activeDocumentId: null,
  activeCitationId: null,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  openUploadModal: () => set({ uploadModalOpen: true }),
  closeUploadModal: () => set({ uploadModalOpen: false }),
  openCreateNotebookModal: () => set({ createNotebookModalOpen: true }),
  closeCreateNotebookModal: () => set({ createNotebookModalOpen: false }),
  openSearch: () => set({ searchOpen: true }),
  closeSearch: () => set({ searchOpen: false }),
  setActiveDocument: (id) => set({ activeDocumentId: id }),
  setActiveCitation: (id) => set({ activeCitationId: id }),
}));

