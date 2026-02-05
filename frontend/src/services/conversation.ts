/**
 * Conversation (advisor) API: SSE streaming, history, reanalyze, clear.
 */
import { getStoredToken } from './api';
import type { ConversationMessage } from '../types/conversation';

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';


/**
 * Send a message and stream the response via SSE. Calls onChunk for each chunk,
 * onComplete when done, onError on failure.
 */
export async function sendMessage(
  caseId: string,
  message: string,
  callbacks: {
    onChunk: (chunk: string) => void;
    onComplete: () => void;
    onError: (error: Error) => void;
  },
  options?: { includeContext?: boolean }
): Promise<void> {
  const token = getStoredToken();
  if (!token) {
    callbacks.onError(new Error('Not authenticated'));
    return;
  }
  const url = `${baseURL}/api/cases/${caseId}/advisor/message`;
  const body = JSON.stringify({
    message,
    include_context: options?.includeContext ?? true,
  });
  const controller = new AbortController();
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body,
      signal: controller.signal,
    });
    if (!res.ok) {
      const errText = await res.text();
      callbacks.onError(new Error(errText || `HTTP ${res.status}`));
      return;
    }
    const reader = res.body?.getReader();
    if (!reader) {
      callbacks.onError(new Error('No response body'));
      return;
    }
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data) callbacks.onChunk(data);
        }
      }
    }
    if (buffer.trim()) {
      const line = buffer.trim();
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (data) callbacks.onChunk(data);
      }
    }
    callbacks.onComplete();
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error(String(err)));
  }
}

/**
 * Fetch conversation history. Returns messages newest-first from API;
 * reverse for display (oldest first) if needed in the UI.
 */
export async function getConversationHistory(
  caseId: string,
  limit?: number
): Promise<ConversationMessage[]> {
  const token = getStoredToken();
  if (!token) throw new Error('Not authenticated');
  const url = new URL(`${baseURL}/api/cases/${caseId}/advisor/history`);
  if (limit != null) url.searchParams.set('limit', String(limit));
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text().then((t) => t || `HTTP ${res.status}`));
  const data = (await res.json()) as ConversationMessage[];
  return data;
}

/**
 * Trigger agent re-analysis (full workflow or single agent).
 */
export async function triggerReanalysis(
  caseId: string,
  agentName?: string
): Promise<{ status: string; message?: string; agent_name?: string }> {
  const token = getStoredToken();
  if (!token) throw new Error('Not authenticated');
  const url = `${baseURL}/api/cases/${caseId}/advisor/reanalyze`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(agentName != null ? { agent_name: agentName } : {}),
  });
  if (!res.ok) throw new Error(await res.text().then((t) => t || `HTTP ${res.status}`));
  return res.json();
}

/**
 * Fetch suggested questions (from memory blocks type "question") for the case.
 */
export async function getSuggestedQuestions(
  caseId: string,
  limit?: number
): Promise<string[]> {
  const token = getStoredToken();
  if (!token) throw new Error('Not authenticated');
  const url = new URL(`${baseURL}/api/cases/${caseId}/advisor/suggestions`);
  if (limit != null) url.searchParams.set('limit', String(limit));
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text().then((t) => t || `HTTP ${res.status}`));
  return res.json();
}

/**
 * Clear conversation history for the case.
 */
export async function clearHistory(caseId: string): Promise<void> {
  const token = getStoredToken();
  if (!token) throw new Error('Not authenticated');
  const url = `${baseURL}/api/cases/${caseId}/advisor/history`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text().then((t) => t || `HTTP ${res.status}`));
}
