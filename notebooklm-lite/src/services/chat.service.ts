import { apiClient } from './api/client';
import type { ChatMessage, Citation } from '../types';

interface SendMessagePayload {
  notebookId: string;
  content: string;
  selectedDocumentIds: string[];
}

interface ChatApiResponse {
  id: string;
  content: string;
  citations: Citation[];
  tokenCount?: number;
  token_usage?: number;
  timestamp?: string;
  created_at?: string;
}

export const chatService = {
  /**
   * Send a message to the RAG backend.
   */
  async sendMessage(payload: SendMessagePayload): Promise<ChatMessage> {
    const response = await apiClient.post<ChatApiResponse>(
      `/api/notebooks/${payload.notebookId}/chat`,
      {
        content: payload.content,
        document_ids: payload.selectedDocumentIds,
      }
    );

    return {
      id: String(response.id),
      role: 'assistant',
      content: response.content,
      citations: response.citations || [],
      timestamp: response.timestamp || response.created_at || new Date().toISOString(),
      tokenCount: response.tokenCount || response.token_usage || 0,
    };
  },

  async getHistory(notebookId: string): Promise<ChatMessage[]> {
    try {
      const res = await apiClient.get<any[]>(`/api/notebooks/${notebookId}/chat/history`);
      if (Array.isArray(res)) {
        return res.map((m) => ({
          id: String(m.id),
          role: m.role || 'assistant',
          content: m.content || '',
          citations: m.citations || [],
          timestamp: m.timestamp || m.created_at || new Date().toISOString(),
          tokenCount: m.tokenCount || m.token_usage || 0,
        }));
      }
      return [];
    } catch {
      return [];
    }
  },
};

