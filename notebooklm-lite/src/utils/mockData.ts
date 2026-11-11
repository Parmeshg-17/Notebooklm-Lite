import type { Notebook, Document, ChatMessage, Citation, ActivityEvent, AnalyticsData, SearchResult } from '../types';

// ─────────────────────────────────────────────
// MOCK DATA — Replace with API calls in Phase 2
// ─────────────────────────────────────────────

export const MOCK_USER = {
  id: 'user-1',
  name: 'Dr. Elena Vance',
  email: 'e.vance@research.ai',
  avatar: 'https://ui-avatars.com/api/?name=Elena+Vance&background=493ebf&color=fff&size=64',
  plan: 'enterprise' as const,
};

export const MOCK_NOTEBOOKS: Notebook[] = [
  {
    id: 'nb-1',
    title: 'LLM Inference Latency & KV-Cache Optimization',
    description: 'FlashAttention-3 benchmarks, speculative decoding trade-offs, and FP8 quantization notes.',
    tag: 'Machine Learning',
    sourceCount: 18,
    lastModified: new Date(Date.now() - 24 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [
      { id: 'u1', name: 'Dr. Elena Vance', avatar: 'https://ui-avatars.com/api/?name=Elena+Vance&background=493ebf&color=fff' },
      { id: 'u2', name: 'Alex Chen', avatar: 'https://ui-avatars.com/api/?name=Alex+Chen&background=006040&color=fff' },
    ],
    owner: 'Dr. Vance',
    isStarred: true,
    isShared: false,
    tokenCount: 142000,
    iconName: 'description',
  },
  {
    id: 'nb-2',
    title: 'Enterprise RAG Architecture & Vector Benchmarks',
    description: 'Hybrid search evaluation, ColBERT re-ranking latency, and Chunking strategy comparisons.',
    tag: 'Infrastructure',
    sourceCount: 24,
    lastModified: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [
      { id: 'u3', name: 'Marcus Webb', avatar: 'https://ui-avatars.com/api/?name=Marcus+Webb&background=5a5e6a&color=fff' },
      { id: 'u4', name: '+3', avatar: '' },
    ],
    owner: 'Team Infra',
    isStarred: false,
    isShared: true,
    tokenCount: 218000,
    iconName: 'analytics',
  },
  {
    id: 'nb-3',
    title: 'Q3 Generative AI Market & Competitive Analysis',
    description: 'Financial reports, proprietary vs open-source adoption, revenue per GPU hour metrics.',
    tag: 'Strategy',
    sourceCount: 11,
    lastModified: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [
      { id: 'u5', name: 'Sarah Kim', avatar: 'https://ui-avatars.com/api/?name=Sarah+Kim&background=D99A32&color=fff' },
    ],
    owner: 'Elena & Mkt',
    isStarred: false,
    isShared: true,
    tokenCount: 89000,
    iconName: 'hub',
  },
  {
    id: 'nb-4',
    title: 'Biomedical Literature: CRISPR Off-Target Detection',
    description: 'Clinical trial protocols, deep learning gRNA specificity predictors.',
    tag: 'Genomics',
    sourceCount: 35,
    lastModified: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [
      { id: 'u6', name: 'Dr. Patel', avatar: 'https://ui-avatars.com/api/?name=Dr+Patel&background=006040&color=fff' },
      { id: 'u7', name: 'R. Torres', avatar: 'https://ui-avatars.com/api/?name=R+Torres&background=493ebf&color=fff' },
    ],
    owner: 'Bio Lab Core',
    isStarred: true,
    isShared: false,
    tokenCount: 341000,
    iconName: 'biotech',
  },
  {
    id: 'nb-5',
    title: 'Distributed Systems: Consensus Algorithms Review',
    description: 'Raft vs Paxos vs Viewstamped Replication. Formal verification approaches and TLA+ specs.',
    tag: 'Systems',
    sourceCount: 9,
    lastModified: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [{ id: 'u8', name: 'Dr. Vance', avatar: 'https://ui-avatars.com/api/?name=Elena+Vance&background=493ebf&color=fff' }],
    owner: 'Dr. Vance',
    isStarred: false,
    isShared: false,
    tokenCount: 67000,
    iconName: 'hub',
  },
  {
    id: 'nb-6',
    title: 'SOC2 Type II Audit & Compliance Framework',
    description: 'Security controls documentation, audit exhibits, and remediation tracking for enterprise certification.',
    tag: 'Security',
    sourceCount: 8,
    lastModified: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    collaborators: [
      { id: 'u9', name: 'T. Nguyen', avatar: 'https://ui-avatars.com/api/?name=T+Nguyen&background=ba1a1a&color=fff' },
    ],
    owner: 'Team Infra',
    isStarred: false,
    isShared: true,
    tokenCount: 52000,
    iconName: 'security',
  },
];

export const MOCK_DOCUMENTS: Document[] = [
  {
    id: 'doc-1',
    notebookId: 'nb-1',
    name: 'FlashAttention-3_Fast_Accurate.pdf',
    type: 'pdf',
    size: 2_456_789,
    pageCount: 28,
    tokenCount: 18400,
    chunkCount: 114,
    status: 'indexed',
    uploadedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    indexedAt: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-2',
    notebookId: 'nb-1',
    name: 'Speculative_Decoding_Survey_2024.pdf',
    type: 'pdf',
    size: 2_567_234,
    pageCount: 24,
    tokenCount: 16200,
    chunkCount: 98,
    status: 'indexed',
    uploadedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    indexedAt: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-3',
    notebookId: 'nb-1',
    name: 'vLLM_PagedAttention_Kwon_2023.pdf',
    type: 'pdf',
    size: 1_234_567,
    pageCount: 16,
    tokenCount: 9800,
    chunkCount: 61,
    status: 'indexed',
    uploadedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    indexedAt: new Date(Date.now() - 4.5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-4',
    notebookId: 'nb-1',
    name: 'FP8_Quantization_H100_Benchmarks.docx',
    type: 'docx',
    size: 567_890,
    pageCount: 12,
    tokenCount: 7200,
    chunkCount: 45,
    status: 'processing',
    progress: 67,
    uploadedAt: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-5',
    notebookId: 'nb-1',
    name: 'FlashAttention3_Architecture_Draft.pdf',
    type: 'pdf',
    size: 3_456_789,
    pageCount: 32,
    tokenCount: 21000,
    chunkCount: 0,
    status: 'uploading',
    progress: 45,
    uploadedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
  {
    id: 'doc-6',
    notebookId: 'nb-1',
    name: 'LoRA_Finetuning_Efficiency_Report.pdf',
    type: 'pdf',
    size: 1_890_234,
    pageCount: 20,
    tokenCount: 12800,
    chunkCount: 79,
    status: 'indexed',
    uploadedAt: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
    indexedAt: new Date(Date.now() - 9 * 60 * 60 * 1000).toISOString(),
  },
];

export const MOCK_CITATIONS: Citation[] = [
  {
    id: 'cit-1',
    documentId: 'doc-1',
    documentName: 'FlashAttention-3_Fast_Accurate.pdf',
    pageNumber: 7,
    excerpt: 'FlashAttention-3 achieves 1.5–2.0x speedup over FlashAttention-2 on H100 GPUs by exploiting WGMMA instructions and asynchronous data movement through the TMA (Tensor Memory Accelerator).',
    relevanceScore: 0.97,
  },
  {
    id: 'cit-2',
    documentId: 'doc-2',
    documentName: 'Speculative_Decoding_Survey_2024.pdf',
    pageNumber: 14,
    excerpt: 'Speculative decoding with draft models of size n achieves an effective speedup of α / (1-αβ) where α is the draft acceptance rate and β accounts for verification overhead on the target model.',
    relevanceScore: 0.93,
  },
  {
    id: 'cit-3',
    documentId: 'doc-3',
    documentName: 'vLLM_PagedAttention_Kwon_2023.pdf',
    pageNumber: 4,
    excerpt: 'PagedAttention stores the KV cache in non-contiguous paged memory blocks, reducing memory fragmentation by 20.4% compared to contiguous allocation and enabling 24x higher throughput for concurrent requests.',
    relevanceScore: 0.89,
  },
];

export const MOCK_CHAT_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'assistant',
    content: 'Welcome to the **LLM Inference Latency & KV-Cache Optimization** workspace. I have indexed **18 sources** across your corpus, totaling approximately **142,000 tokens**. Ask me anything about your documents — I\'ll ground every response with precise citations.',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'msg-2',
    role: 'user',
    content: 'What are the key techniques for reducing LLM inference latency described in these papers?',
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: 'msg-3',
    role: 'assistant',
    content: `Based on your uploaded documents, there are **four major techniques** for reducing LLM inference latency:

**1. Attention Kernel Optimization (FlashAttention-3)**
FlashAttention-3 achieves 1.5–2.0× speedup over FlashAttention-2 on H100 GPUs by exploiting WGMMA instructions and asynchronous data movement via the TMA (Tensor Memory Accelerator). This is complemented by a new overlapping scheme that hides memory latency behind compute.

**2. Speculative Decoding**
Rather than auto-regressively generating one token at a time, a small draft model proposes *n* candidate tokens which the target LLM then accepts or rejects in parallel. The effective speedup is approximately α / (1−αβ), where α is the draft acceptance rate and β accounts for verification overhead.

**3. KV-Cache Memory Management (PagedAttention)**
vLLM's PagedAttention stores the KV cache in non-contiguous paged memory blocks, reducing memory fragmentation by 20.4% and enabling 24× higher throughput for concurrent batch requests compared to contiguous allocation.

**4. Quantization (FP8 on H100)**
FP8 inference on H100 GPUs reduces both memory bandwidth and compute requirements by 2×, enabling higher batch sizes with minimal quality degradation (< 0.3% perplexity increase on standard benchmarks).`,
    citations: MOCK_CITATIONS,
    timestamp: new Date(Date.now() - 44 * 60 * 1000).toISOString(),
    tokenCount: 312,
  },
];

export const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: 'act-1',
    type: 'document_indexed',
    title: 'FlashAttention3_Architecture_Draft.pdf',
    description: '32 pages parsed, 114 chunks vector-indexed into LLM Inference Latency.',
    timestamp: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
    notebookId: 'nb-1',
    notebookName: 'LLM Inference Latency',
  },
  {
    id: 'act-2',
    type: 'synthesis_generated',
    title: 'Compared speculative decoding algorithms across 3 papers',
    description: 'Derived speedup curves on speculative draft tokens with temperature scaling bounds.',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    notebookId: 'nb-1',
    citations: [{ label: 'Leviathan et al., 2023' }, { label: 'Chen et al., 2023' }, { label: 'Miao et al., 2024' }],
  },
  {
    id: 'act-3',
    type: 'note_added',
    title: 'Discrepancy in TTFT measurements across A100 vs H100 clusters',
    description: 'Annotated under Enterprise RAG Architecture with 4 telemetry graphs attached.',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    notebookId: 'nb-2',
    attachmentCount: 4,
  },
  {
    id: 'act-4',
    type: 'notebook_created',
    title: 'SOC2 Type II Audit & Compliance Framework',
    description: 'New workspace created with 8 source documents queued for indexing.',
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    notebookId: 'nb-6',
  },
];

// Generate time-series data for analytics
function generateTimeSeries(days: number, baseValue: number, variance: number): { date: string; value: number }[] {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (days - i - 1));
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.max(0, Math.round(baseValue + (Math.random() - 0.5) * variance)),
    };
  });
}

export const MOCK_ANALYTICS: AnalyticsData = {
  totalQueries: 1429,
  successfulQueries: 1384,
  failedQueries: 45,
  avgLatencyMs: 1240,
  p95LatencyMs: 3800,
  inputTokens: 2_840_000,
  outputTokens: 1_120_000,
  estimatedCostUsd: 18.47,
  userSatisfactionScore: 4.3,
  queriesOverTime: generateTimeSeries(14, 102, 40),
  tokenUsageOverTime: generateTimeSeries(14, 280000, 80000),
  latencyOverTime: generateTimeSeries(14, 1240, 400),
};

export const MOCK_SEARCH_RESULTS: SearchResult[] = [
  {
    type: 'content',
    notebookId: 'nb-1',
    documentId: 'doc-2',
    title: 'Speculative Decoding — Acceptance Rate Analysis',
    snippet: '...the **acceptance rate** α is the key determinant of speedup. For draft models of size 1B parameters, empirical acceptance rates of 0.7–0.85 are achievable on code generation tasks...',
    matchedTerms: ['acceptance rate', 'speculative decoding'],
    documentName: 'Speculative_Decoding_Survey_2024.pdf',
    pageNumber: 14,
    score: 0.97,
  },
  {
    type: 'content',
    notebookId: 'nb-1',
    documentId: 'doc-1',
    title: 'FlashAttention-3 WGMMA Instructions',
    snippet: '...leverages **warp-group matrix multiply-accumulate** (WGMMA) instructions introduced in the Hopper architecture to achieve near-theoretical peak FLOPS utilization...',
    matchedTerms: ['WGMMA', 'FlashAttention'],
    documentName: 'FlashAttention-3_Fast_Accurate.pdf',
    pageNumber: 7,
    score: 0.94,
  },
  {
    type: 'notebook',
    notebookId: 'nb-1',
    title: 'LLM Inference Latency & KV-Cache Optimization',
    snippet: 'FlashAttention-3 benchmarks, speculative decoding trade-offs, and FP8 quantization notes. 18 indexed sources.',
    matchedTerms: ['LLM', 'inference', 'latency'],
    score: 0.88,
  },
];

// Utility
export function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatTokens(count: number): string {
  if (count < 1000) return `${count}`;
  return `${(count / 1000).toFixed(1)}k`;
}

