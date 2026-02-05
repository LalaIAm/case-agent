/**
 * Compact banner showing current session context and quick actions.
 */
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

interface SessionContextIndicatorProps {
  currentSession: CaseSession | null;
  totalSessions: number;
  onSwitchSession?: () => void;
  onCompleteSession?: () => void;
  blockCount?: number;
}

export function SessionContextIndicator({
  currentSession,
  totalSessions,
  onSwitchSession,
  onCompleteSession,
  blockCount,
}: SessionContextIndicatorProps) {
  const viewingAll = !currentSession;
  const label = viewingAll
    ? 'Viewing All Sessions'
    : `Viewing Session ${currentSession.session_number} of ${totalSessions}`;

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 bg-white px-4 py-2 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {currentSession && (
          <>
            <Badge variant={getStatusVariant(currentSession.status)}>
              {currentSession.status}
            </Badge>
            <span className="text-xs text-gray-500">
              Started {formatDate(currentSession.started_at)}
            </span>
            {blockCount != null && (
              <span className="text-xs text-gray-500">
                · {blockCount} memory blocks
              </span>
            )}
          </>
        )}
      </div>
      <div className="flex gap-2">
        {onSwitchSession && (
          <Button variant="secondary" onClick={onSwitchSession}>
            Switch Session
          </Button>
        )}
        {currentSession?.status === 'active' && onCompleteSession && (
          <Button variant="secondary" onClick={onCompleteSession}>
            Complete Session
          </Button>
        )}
      </div>
    </div>
  );
}
