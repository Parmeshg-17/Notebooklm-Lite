// Core domain types for NotebookLM Lite

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  plan: 'free' | 'pro' | 'enterprise';
}

export type NotebookTag =
  | 'Machine Learning'
  | 'Infrastructure'
  | 'Strategy'
  | 'Genomics'
  | 'Systems'
  | 'BioMed'
  | 'Finance'
  | 'Security'
  | string;

export interface Notebook {
  id: string;
  title: string;
  description: string;
  tag: NotebookTag;
  sourceCount: number;
  lastModified: string; // ISO string
  createdAt: string;
  collaborators: Collaborator[];
  owner: string;
  isStarred: boolean;
  isShared: boolean;
  tokenCount?: number;
  iconName?: string;
}

export interface Collaborator {
  id: string;
  name: string;
  avatar?: string;
}

export type DocumentStatus = 'uploading' | 'processing' | 'indexed' | 'failed';

export interface Document {
  id: string;
  notebookId: string;
  name: string;
  type: 'pdf' | 'docx' | 'txt';
  size: number; // bytes
  pageCount?: number;
  tokenCount?: number;
  chunkCount?: number;
  status: DocumentStatus;
  progress?: number; // 0-100
  uploadedAt: string;
  indexedAt?: string;
  errorMessage?: string;
}

export interface Citation {
  id: string;
  documentId: string;
  documentName: string;
  pageNumber: number;
  excerpt: string;
  relevanceScore?: number; // 0-1
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: string;
  isLoading?: boolean;
  feedbackGiven?: 'positive' | 'negative';
  tokenCount?: number;
}

export interface ChatSession {
  id: string;
  notebookId: string;
  messages: ChatMessage[];
  createdAt: string;
}

export interface ActivityEvent {
  id: string;
  type: 'document_indexed' | 'synthesis_generated' | 'note_added' | 'notebook_created';
  title: string;
  description: string;
  timestamp: string;
  notebookId?: string;
  documentId?: string;
  citations?: { label: string }[];
  attachmentCount?: number;
  notebookName?: string;
}

export interface AnalyticsData {
  totalQueries: number;
  successfulQueries: number;
  failedQueries: number;
  avgLatencyMs: number;
  p95LatencyMs: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
  userSatisfactionScore: number; // 0-5
  queriesOverTime: TimeSeriesPoint[];
  tokenUsageOverTime: TimeSeriesPoint[];
  latencyOverTime: TimeSeriesPoint[];
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
  value2?: number;
}

export interface SearchResult {
  type: 'notebook' | 'document' | 'content';
  notebookId?: string;
  documentId?: string;
  title: string;
  snippet: string;
  matchedTerms: string[];
  documentName?: string;
  pageNumber?: number;
  score: number;
}

export interface UploadFile {
  id: string;
  file: File;
  status: 'queued' | 'uploading' | 'processing' | 'done' | 'error';
  progress: number;
  errorMessage?: string;
}

// API response shapes
export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

