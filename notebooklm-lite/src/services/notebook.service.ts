import { apiClient } from './api/client';
import type { Notebook } from '../types';

export const notebookService = {
  async list(): Promise<Notebook[]> {
    try {
      const res = await apiClient.get<Notebook[]>('/api/notebooks');
      return res || [];
    } catch {
      return [];
    }
  },

  async get(id: string): Promise<Notebook> {
    return await apiClient.get<Notebook>(`/api/notebooks/${id}`);
  },

  async create(data: Partial<Notebook>): Promise<Notebook> {
    return await apiClient.post<Notebook>('/api/notebooks', data);
  },

  async update(id: string, data: Partial<Notebook>): Promise<Notebook> {
    return await apiClient.patch<Notebook>(`/api/notebooks/${id}`, data);
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/notebooks/${id}`);
  },
};

