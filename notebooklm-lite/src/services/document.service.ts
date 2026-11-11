import { apiClient } from './api/client';
import type { Document } from '../types';

export const documentService = {
  async list(notebookId: string): Promise<Document[]> {
    try {
      const docs = await apiClient.get<Document[]>(`/api/notebooks/${notebookId}/documents`);
      return docs || [];
    } catch {
      return [];
    }
  },

  async get(documentId: string): Promise<Document> {
    return await apiClient.get<Document>(`/api/documents/${documentId}`);
  },

  async upload(
    notebookId: string,
    file: File,
    onProgress: (progress: number) => void
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    onProgress(30);
    const doc = await apiClient.post<Document>(
      `/api/notebooks/${notebookId}/documents`,
      formData
    );
    onProgress(45);

    // Poll status reliably until indexed or failed
    let pollCount = 0;
    let currentDoc = doc;
    const isPending = (status?: string) => {
      if (!status) return false;
      const s = status.toUpperCase();
      return ['UPLOADED', 'PENDING', 'PROCESSING', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'INDEXING'].includes(s);
    };

    while (pollCount < 60 && isPending(currentDoc.status || (currentDoc as any).processing_status)) {
      await new Promise((r) => setTimeout(r, 1000));
      pollCount++;
      try {
        const statusRes = await apiClient.get<{ status: string; progress: number; error?: string }>(
          `/api/documents/${doc.id}/status`
        );
        onProgress(Math.min(95, Math.max(45, statusRes.progress || 50)));
        const st = (statusRes.status || '').toUpperCase();
        if (st === 'INDEXED') {
          currentDoc = { ...currentDoc, status: 'indexed', progress: 100 };
          break;
        } else if (st === 'FAILED') {
          throw new Error(statusRes.error || 'Document processing failed');
        }
      } catch (err: any) {
        if (err.message && err.message.includes('failed')) throw err;
        // Non-fatal status check failure (e.g. temporary network blip)
      }
    }

    onProgress(100);
    return currentDoc;
  },

  async delete(documentId: string): Promise<void> {
    await apiClient.delete(`/api/documents/${documentId}`);
  },
};
