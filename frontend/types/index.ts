// ─── Notebooks ───────────────────────────────────────────────────────────────

export interface Notebook {
  id: string;
  title: string;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotebookListResponse {
  notebooks: Notebook[];
  total: number;
}

// ─── Documents ───────────────────────────────────────────────────────────────

export type DocumentStatus = "uploaded" | "parsing" | "indexed" | "failed";

export interface Document {
  id: string;
  notebook_id: string;
  filename: string;
  status: DocumentStatus;
  page_count: number | null;
  file_size: number | null;
  mime_type: string | null;
  error_msg: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  status: DocumentStatus;
  message: string;
}

// ─── Conversations ────────────────────────────────────────────────────────────

export interface Conversation {
  id: string;
  notebook_id: string;
  title: string | null;
  created_at: string;
}

// ─── Messages & Citations ─────────────────────────────────────────────────────

export interface Citation {
  id: string;
  marker: number;
  quote: string;
  page: number;
  chunk_id: string;
  document_id: string | null;
  filename: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  not_found: boolean;
  citations: Citation[];
  created_at: string;
}

// ─── Ask / Stream ─────────────────────────────────────────────────────────────

export interface AskRequest {
  question: string;
  conversation_id?: string;
}

export interface StreamChunk {
  type: "token" | "citations" | "done" | "error" | "not_found";
  content?: string;
  citations?: Citation[];
  error?: string;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
}

export interface ReadyResponse {
  status: string;
  checks: Record<string, boolean>;
}
