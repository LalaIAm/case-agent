/**
 * Session selector: dropdown to switch session, mark active as completed.
 */
import { useState } from 'react';
import { updateSession } from '../services/cases';
import type { CaseSession } from '../types/case';
import { Badge } from './Badge';
import { Button } from './Button';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

function getStatusVariant(
  status: string
): 'draft' | 'active' | 'completed' | 'error' {
  const s = status.toLowerCase();
  if (s === 'active') return 'active';
  if (s === 'completed') return 'completed';
  return 'draft';
}

interface SessionSelectorProps {
  caseId: string;
  sessions: CaseSession[];
  activeSessionId: string | null;
  onSessionChange: (sessionId: string) => void;
  onSessionUpdated?: () => void;
}

export function SessionSelector({
  caseId,
  sessions,
  activeSessionId,
  onSessionChange,
  onSessionUpdated,
}: SessionSelectorProps) {
  const [completingId, setCompletingId] = useState<string | null>(null);

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? null;
  const displayLabel = activeSessionId
    ? activeSession
      ? `Session ${activeSession.session_number} - ${activeSession.status}`
      : 'All Sessions'
    : sessions.length > 0
      ? 'Select session…'
      : 'No sessions';

  async function handleMarkCompleted(sessionId: string) {
      setCompletingId(sessionId);
      try {
        await updateSession(caseId, sessionId, {
          status: 'completed',
          completed_at: new Date().toISOString(),
        });
        onSessionUpdated?.();
      } finally {
      setCompletingId(null);
    }
  }

  return (
    <div className="relative inline-block">
      <div className="flex items-center gap-2">
        <select
          value={activeSessionId || 'all'}
          onChange={(e) => {
            const v = e.target.value;
            onSessionChange(v === 'all' ? '' : v);
          }}
          className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          aria-label="Select session"
        >
          <option value="all">All Sessions</option>
          {[...sessions]
            .sort((a, b) => b.session_number - a.session_number)
            .map((s) => (
              <option key={s.id} value={s.id}>
                Session {s.session_number} - {s.status} · {formatDate(s.started_at)}
              </option>
            ))}
        </select>
        {activeSession?.status === 'active' && (
          <Button
            variant="secondary"
            onClick={() => handleMarkCompleted(activeSession.id)}
            disabled={completingId === activeSession.id}
          >
            {completingId === activeSession.id ? 'Completing…' : 'Mark as Completed'}
          </Button>
        )}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1">
        {activeSession && (
          <Badge variant={getStatusVariant(activeSession.status)}>
            {activeSession.status}
          </Badge>
        )}
        {activeSession && (
          <span className="text-xs text-gray-500">
            {formatDate(activeSession.started_at)}
          </span>
        )}
      </div>
    </div>
  );
}
