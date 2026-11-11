'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument } from '../lib/api';

export default function DocumentUpload() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null);

  const onDrop = useCallback(
    async (acceptedFiles, rejections) => {
      if (rejections.length > 0) {
        setStatus({ type: 'error', message: 'Unsupported file. Use PDF, TXT, Markdown, CSV or DOCX.' });
        return;
      }
      if (acceptedFiles.length === 0) return;

      setUploading(true);
      setStatus(null);
      try {
        const doc = await uploadDocument(acceptedFiles[0]);
        setStatus({ type: 'success', message: `Indexed "${doc.filename}" (${doc.chunk_count} chunks).` });
        router.refresh();
      } catch (e) {
        setStatus({ type: 'error', message: e.message || 'Network error. Is the API running?' });
      } finally {
        setUploading(false);
      }
    },
    [router],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  const ok = status?.type === 'success';
  return (
    <div>
      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'dropzone-active' : ''}`}>
        <input {...getInputProps()} />
        {uploading ? (
          <div className="dropzone-text">
            <div className="loading-dots"><span></span><span></span><span></span></div>
            <p style={{ marginTop: '0.5rem' }}>Processing document…</p>
          </div>
        ) : (
          <>
            <p className="dropzone-text">
              {isDragActive ? '📥 Drop your document here' : '📄 Drag & drop a document, or click to browse'}
            </p>
            <p className="dropzone-hint">Supports PDF, TXT, Markdown, CSV, DOCX</p>
          </>
        )}
      </div>

      {status && (
        <div
          role={ok ? 'status' : 'alert'}
          style={{
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            background: ok ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: ok ? 'var(--success)' : 'var(--danger)',
            border: `1px solid ${ok ? 'var(--success)' : 'var(--danger)'}`,
          }}
        >
          {status.message}
        </div>
      )}
    </div>
  );
}
