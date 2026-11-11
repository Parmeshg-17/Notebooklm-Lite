import React, { useState, useRef } from 'react';
import { X, Upload, FileText, File, AlertCircle, CheckCircle, Loader2, RefreshCw } from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import { useUIStore, useNotebookStore, useDocumentStore } from '../../store';
import { documentService } from '../../services/document.service';
import type { UploadFile } from '../../types';
import { formatBytes } from '../../utils/mockData';

const ACCEPTED_TYPES = '.pdf,.docx,.txt';
const MAX_SIZE_MB = 50;

export default function UploadModal() {
  const { closeUploadModal } = useUIStore();
  const { activeNotebookId } = useNotebookStore();
  const { addDocument } = useDocumentStore();

  const [uploads, setUploads] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const newUploads: UploadFile[] = Array.from(files).map((file) => ({
      id: `upload-${Date.now()}-${Math.random()}`,
      file,
      status: 'queued',
      progress: 0,
    }));
    setUploads((prev) => [...prev, ...newUploads]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const processUpload = async (upload: UploadFile) => {
    const notebookId = activeNotebookId ?? 'nb-1';

    setUploads((prev) =>
      prev.map((u) => (u.id === upload.id ? { ...u, status: 'uploading', progress: 0 } : u))
    );

    try {
      const doc = await documentService.upload(notebookId, upload.file, (progress) => {
        setUploads((prev) =>
          prev.map((u) => (u.id === upload.id ? { ...u, progress } : u))
        );
      });

      setUploads((prev) =>
        prev.map((u) => (u.id === upload.id ? { ...u, status: 'done', progress: 100 } : u))
      );

      addDocument(doc);
    } catch (err: any) {
      const errMsg = err?.message || 'Upload failed. Please retry.';
      setUploads((prev) =>
        prev.map((u) =>
          u.id === upload.id ? { ...u, status: 'error', errorMessage: errMsg } : u
        )
      );
    }
  };

  const startUploads = () => {
    uploads.filter((u) => u.status === 'queued').forEach(processUpload);
  };

  const removeUpload = (id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  const retryUpload = (upload: UploadFile) => {
    setUploads((prev) =>
      prev.map((u) => (u.id === upload.id ? { ...u, status: 'queued', progress: 0, errorMessage: undefined } : u))
    );
    processUpload({ ...upload, status: 'queued', progress: 0 });
  };

  const queuedCount = uploads.filter((u) => u.status === 'queued').length;
  const allDone = uploads.length > 0 && uploads.every((u) => u.status === 'done');

  return (
    <Modal
      title="Upload Documents"
      onClose={closeUploadModal}
      width="max-w-2xl"
      footer={
        <>
          <Button variant="secondary" onClick={closeUploadModal}>Cancel</Button>
          {allDone ? (
            <Button variant="primary" onClick={closeUploadModal}>Done</Button>
          ) : (
            <Button
              variant="primary"
              onClick={startUploads}
              disabled={queuedCount === 0}
              icon={<Upload size={16} />}
            >
              Upload {queuedCount > 0 ? `${queuedCount} file${queuedCount !== 1 ? 's' : ''}` : ''}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        {/* Drag & Drop Zone */}
        <div
          className="relative rounded-xl p-10 text-center transition-all cursor-pointer"
          style={{
            border: `2px dashed ${isDragOver ? 'var(--color-primary)' : 'var(--color-outline-variant)'}`,
            backgroundColor: isDragOver ? 'var(--color-primary-fixed)' : 'var(--color-surface-container-low)',
          }}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPTED_TYPES}
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3"
            style={{ backgroundColor: 'var(--color-primary-fixed)', color: 'var(--color-primary)' }}
          >
            <Upload size={24} />
          </div>
          <p className="text-body-lg font-medium mb-1" style={{ color: 'var(--color-on-surface)' }}>
            Drop files here or click to browse
          </p>
          <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
            Supports PDF, DOCX, TXT · Max {MAX_SIZE_MB}MB per file
          </p>
          <div className="flex items-center justify-center gap-2 mt-3">
            {['PDF', 'DOCX', 'TXT'].map((fmt) => (
              <span
                key={fmt}
                className="px-2 py-0.5 rounded text-code-sm font-medium"
                style={{ backgroundColor: 'var(--color-surface-container)', color: 'var(--color-on-surface-variant)' }}
              >
                {fmt}
              </span>
            ))}
          </div>
        </div>

        {/* File list */}
        {uploads.length > 0 && (
          <div className="space-y-2">
            {uploads.map((upload) => (
              <UploadItem
                key={upload.id}
                upload={upload}
                onRemove={() => removeUpload(upload.id)}
                onRetry={() => retryUpload(upload)}
              />
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

function UploadItem({
  upload,
  onRemove,
  onRetry,
}: {
  upload: UploadFile;
  onRemove: () => void;
  onRetry: () => void;
}) {
  const getStatusIcon = () => {
    switch (upload.status) {
      case 'done': return <CheckCircle size={16} style={{ color: 'var(--color-tertiary)' }} />;
      case 'error': return <AlertCircle size={16} style={{ color: 'var(--color-error)' }} />;
      case 'uploading':
      case 'processing': return <Loader2 size={16} className="animate-spin" style={{ color: 'var(--color-primary)' }} />;
      default: return <File size={16} style={{ color: 'var(--color-on-surface-variant)' }} />;
    }
  };

  const getStatusText = () => {
    switch (upload.status) {
      case 'queued': return 'Ready to upload';
      case 'uploading': return `Uploading... ${upload.progress}%`;
      case 'processing': return 'Processing & indexing...';
      case 'done': return 'Indexed successfully';
      case 'error': return upload.errorMessage ?? 'Upload failed';
    }
  };

  return (
    <div
      className="flex items-center gap-3 p-3 rounded-lg"
      style={{ backgroundColor: 'var(--color-surface-container-low)', border: '1px solid var(--color-surface-container-high)' }}
    >
      <FileText size={20} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-body-sm font-medium truncate" style={{ color: 'var(--color-on-surface)' }}>
            {upload.file.name}
          </span>
          <span className="text-code-sm flex-shrink-0" style={{ color: 'var(--color-on-surface-variant)' }}>
            {formatBytes(upload.file.size)}
          </span>
        </div>
        {(upload.status === 'uploading' || upload.status === 'processing') && (
          <div className="mt-1.5 w-full rounded-full h-1" style={{ backgroundColor: 'var(--color-surface-container-high)' }}>
            <div
              className="h-1 rounded-full transition-all"
              style={{
                width: `${upload.progress}%`,
                backgroundColor: upload.status === 'processing' ? 'var(--color-tertiary)' : 'var(--color-primary)',
              }}
            />
          </div>
        )}
        <div className="flex items-center gap-1 mt-1">
          {getStatusIcon()}
          <span
            className="text-code-sm"
            style={{ color: upload.status === 'error' ? 'var(--color-error)' : upload.status === 'done' ? 'var(--color-tertiary)' : 'var(--color-on-surface-variant)' }}
          >
            {getStatusText()}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {upload.status === 'error' && (
          <button onClick={onRetry} className="p-1 rounded" style={{ color: 'var(--color-primary)' }} title="Retry">
            <RefreshCw size={14} />
          </button>
        )}
        {(upload.status === 'queued' || upload.status === 'done' || upload.status === 'error') && (
          <button onClick={onRemove} className="p-1 rounded" style={{ color: 'var(--color-on-surface-variant)' }}>
            <X size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

