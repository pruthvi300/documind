'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { deleteDocument } from '../lib/api';

export default function DocumentList({ documents }) {
  const router = useRouter();
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);

  const handleDelete = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}"? Its content will no longer be used in answers.`)) return;
    setDeletingId(doc.id);
    setError(null);
    try {
      await deleteDocument(doc.id);
      router.refresh(); // re-run the server component to fetch the new list
    } catch (e) {
      setError(e.message);
    } finally {
      setDeletingId(null);
    }
  };

  if (documents.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📂</p>
        <p>No documents yet. Upload one above to get started!</p>
      </div>
    );
  }

  return (
    <>
      {error && <p role="alert" style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</p>}
      <div className="document-grid">
        {documents.map((doc) => (
          <div key={doc.id} className="document-card">
            <div className="document-name">📄 {doc.filename}</div>
            <div className="document-meta">
              <div>{doc.chunk_count} chunks indexed</div>
              <div>{doc.file_type.toUpperCase()} • {formatSize(doc.file_size)}</div>
              <div style={{ marginTop: '0.5rem' }}>Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}</div>
            </div>
            <button
              type="button"
              className="btn-delete"
              onClick={() => handleDelete(doc)}
              disabled={deletingId === doc.id}
            >
              {deletingId === doc.id ? 'Deleting…' : '🗑️ Delete'}
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

function formatSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
