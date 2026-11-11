import Link from 'next/link';
import './globals.css';

export const metadata = {
  title: 'DocuMind — AI Document Intelligence',
  description: 'Upload documents. Ask questions. Get AI-powered answers with source citations.',
  keywords: ['AI', 'RAG', 'Document Intelligence', 'LangChain', 'ChromaDB'],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div id="app-root">
          <nav className="navbar">
            <div className="navbar-brand">
              <span className="navbar-logo">🧠</span>
              <span className="navbar-title">DocuMind</span>
            </div>
            <div className="navbar-links">
              <Link href="/" className="nav-link">Chat</Link>
              <Link href="/documents" className="nav-link">Documents</Link>
            </div>
          </nav>
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
