// =============================================
// Home Page — Chat Interface (Server Component wrapper)
// =============================================
// Next.js App Router: this is a SERVER component by default.
// The actual chat logic is in ChatInterface (client component).
// This shows the Server Component → Client Component pattern.
// =============================================

import ChatInterface from './components/ChatInterface';

export default function HomePage() {
  return (
    <div className="chat-container">
      <ChatInterface />
    </div>
  );
}
