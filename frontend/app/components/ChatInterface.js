'use client';

import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { streamChat } from '../lib/api';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Stop an in-flight stream if the user navigates away.
  useEffect(() => () => abortRef.current?.abort(), []);

  const updateLast = (patch) =>
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = { ...next[next.length - 1], ...patch(next[next.length - 1]) };
      return next;
    });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '', sources: [] },
    ]);
    setInput('');
    setIsLoading(true);
    abortRef.current = new AbortController();

    try {
      await streamChat({ question, conversationId, signal: abortRef.current.signal }, (event) => {
        if (event.type === 'token') updateLast((m) => ({ content: m.content + event.content }));
        else if (event.type === 'sources') updateLast(() => ({ sources: event.sources }));
        else if (event.type === 'done') setConversationId(event.conversation_id);
        else if (event.type === 'error') updateLast(() => ({ content: event.error, error: true }));
      });
    } catch (error) {
      if (error.name !== 'AbortError') {
        updateLast(() => ({ content: error.message || 'Something went wrong. Please try again.', error: true }));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
  };

  return (
    <>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: '2rem', marginBottom: '1rem' }}>🧠</p>
            <p style={{ fontSize: '1.1rem' }}>Upload a document and start asking questions</p>
            <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>Answers cite the passages they come from</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <div className="message-avatar" aria-hidden="true">{msg.role === 'user' ? '👤' : '🧠'}</div>
            <div className="message-content" style={msg.error ? { color: 'var(--danger)' } : undefined}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>

              {msg.sources?.length > 0 && (
                <div className="sources">
                  <div className="sources-title">Sources</div>
                  {msg.sources.map((src, j) => (
                    <span key={j} className="source-chip" title={src.chunk_text}>
                      [{j + 1}] 📄 {src.document}
                      {src.page_number ? ` — p.${src.page_number}` : ''}
                    </span>
                  ))}
                </div>
              )}

              {msg.role === 'assistant' && msg.content === '' && isLoading && (
                <div className="loading-dots" aria-label="Thinking">
                  <span></span><span></span><span></span>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          {messages.length > 0 && (
            <button type="button" className="btn-send" onClick={newChat} disabled={isLoading} title="Start a new conversation">
              New
            </button>
          )}
          <input
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={conversationId ? 'Ask a follow-up…' : 'Ask a question about your documents…'}
            aria-label="Question"
            maxLength={2000}
            disabled={isLoading}
          />
          <button type="submit" className="btn-send" disabled={isLoading || !input.trim()}>
            {isLoading ? '…' : 'Send'}
          </button>
        </form>
      </div>
    </>
  );
}
