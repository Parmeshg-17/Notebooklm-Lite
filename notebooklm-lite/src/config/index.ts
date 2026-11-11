// App configuration — all from environment variables
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL !== undefined ? import.meta.env.VITE_API_BASE_URL : 'http://127.0.0.1:8000',
    timeout: 30_000,
  },
  app: {
    name: 'NotebookLM Lite',
    version: '1.4',
    plan: 'Enterprise',
  },
  features: {
    pdfViewer: true,
    analytics: true,
    collaboration: true,
  },
} as const;

export type Config = typeof config;

