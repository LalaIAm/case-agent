/**
 * Session history: timeline list of sessions with expandable summaries.
 */
import { useState, useCallback } from 'react';
import { getSessionSummary } from '../services/cases';
import type { CaseSession, CaseSessionSummary } from '../types/case';
import { Badge } from './Badge';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    dateStyle: 'medium',
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

function formatDuration(started: string, completed: string | null): string {
  if (!completed) return '—';
  const a = new Date(started).getTime();
  const b = new Date(completed).getTime();
  const mins = Math.round((b - a) / 60000);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

interface SessionHistoryProps {
  caseId: string;
  sessions: CaseSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
}

export function SessionHistory({
  caseId,
  sessions,
  activeSessionId,
  onSelectSession,
}: SessionHistoryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [summaryCache, setSummaryCache] = useState<Map<string, CaseSessionSummary>>(new Map());
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const sortedSessions = [...sessions].sort(
    (a, b) => b.session_number - a.session_number
  );

  const loadSummary = useCallback(
    async (sessionId: string) => {
      if (summaryCache.has(sessionId)) {
        setExpandedId((prev) => (prev === sessionId ? null : sessionId));
        return;
      }
      setLoadingId(sessionId);
      try {
        const summary = await getSessionSummary(caseId, sessionId);
        setSummaryCache((prev) => new Map(prev).set(sessionId, summary));
        setExpandedId(sessionId);
      } finally {
        setLoadingId(null);
      }
    },
    [caseId, summaryCache]
  );

  return (
    <ul className="space-y-2" aria-label="Session history">
      {sortedSessions.map((s) => {
        const isSelected = activeSessionId === s.id;
        const isExpanded = expandedId === s.id;
        const summary = summaryCache.get(s.id);

        return (
          <li
            key={s.id}
            className={`rounded border px-4 py-3 ${
              isSelected
                ? 'border-blue-500 bg-blue-50/50'
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-gray-900">
                  Session {s.session_number}
                </span>
                <Badge variant={getStatusVariant(s.status)}>{s.status}</Badge>
                <span className="text-sm text-gray-500">
                  Started {formatDate(s.started_at)}
                </span>
                {s.completed_at && (
                  <span className="text-sm text-gray-500">
                    · Completed {formatDate(s.completed_at)} ·{' '}
                    {formatDuration(s.started_at, s.completed_at)}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => onSelectSession(s.id)}
                >
                  View Context
                </Button>
                <button
                  type="button"
                  onClick={() => loadSummary(s.id)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  {isExpanded ? 'Hide details' : 'Show details'}
                </button>
              </div>
            </div>
            {loadingId === s.id && (
              <div className="mt-2 flex items-center gap-2 text-sm text-gray-500">
                <LoadingSpinner size="sm" />
                Loading summary…
              </div>
            )}
            {isExpanded && summary && (
              <div className="mt-3 border-t border-gray-200 pt-3">
                <p className="text-sm font-medium text-gray-700">
                  Memory blocks: {summary.total_blocks} total
                </p>
                <ul className="mt-1 flex flex-wrap gap-2 text-sm text-gray-600">
                  {summary.memory_block_counts.map((c) => (
                    <li key={c.block_type}>
                      {c.block_type}: {c.count}
                    </li>
                  ))}
                  {summary.memory_block_counts.length === 0 && (
                    <li>No blocks yet</li>
                  )}
                </ul>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
