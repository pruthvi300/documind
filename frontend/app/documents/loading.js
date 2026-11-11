export default function DocumentsLoading() {
  return (
    <div>
      <div className="documents-header">
        <h1>📄 Documents</h1>
      </div>
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        <div className="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <p style={{ marginTop: '1rem' }}>Loading documents...</p>
      </div>
    </div>
  );
}
