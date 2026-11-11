// Server Component: fetches the document list on the server, so the page arrives pre-rendered.

import DocumentList from '../components/DocumentList';
import DocumentUpload from '../components/DocumentUpload';

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Always render on request: the list changes whenever a document is uploaded or deleted.
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Documents — DocuMind',
  description: 'Upload and manage your documents for AI-powered Q&A',
};

async function getDocuments() {
  try {
    const res = await fetch(`${API_URL}/api/documents?limit=100`, { cache: 'no-store' });
    if (!res.ok) return { documents: [], error: `API returned ${res.status}` };
    const body = await res.json();
    return { documents: body.documents, error: null };
  } catch {
    return { documents: [], error: 'Could not reach the API. Is the backend running?' };
  }
}

export default async function DocumentsPage() {
  const { documents, error } = await getDocuments();

  return (
    <div>
      <div className="documents-header">
        <h1>📄 Documents</h1>
      </div>
      <DocumentUpload />
      {error ? (
        <p role="alert" style={{ color: 'var(--danger)' }}>{error}</p>
      ) : (
        <DocumentList documents={documents} />
      )}
    </div>
  );
}
