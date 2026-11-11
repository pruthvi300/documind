// Browser-side API helpers. All paths are same-origin and proxied to FastAPI by next.config.js.

export async function apiError(res, fallback) {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join('; ');
  } catch {
    // non-JSON error body
  }
  return fallback;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/documents/upload', { method: 'POST', body: formData });
  if (!res.ok) throw new Error(await apiError(res, 'Upload failed. Please try again.'));
  return res.json();
}

export async function deleteDocument(id) {
  const res = await fetch(`/api/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await apiError(res, 'Delete failed.'));
}

/**
 * POST a question to /api/chat/stream and call `onEvent` for each SSE event.
 * Events: {type:'token',content} | {type:'sources',sources} | {type:'done',conversation_id} | {type:'error',error}
 */
export async function streamChat({ question, conversationId, signal }, onEvent) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId || undefined }),
    signal,
  });
  if (!res.ok) throw new Error(await apiError(res, 'Failed to get a response.'));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // An event can be split across network reads; only parse complete ones.
    const events = buffer.split('\n\n');
    buffer = events.pop();
    for (const event of events) {
      const line = event.split('\n').find((l) => l.startsWith('data: '));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
