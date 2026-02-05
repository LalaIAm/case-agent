/**
 * Session details card: timestamps, status, memory block breakdown, actions.
 */
import type { CaseSession, CaseSessionSummary } from '../types/case';
import { Badge } from './Badge';
import { Button } from './Button';
import { Card } from './Card';
import { ProgressBar } from './ProgressBar';

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

interface SessionMetadataProps {
  session: CaseSession;
  summary: CaseSessionSummary | null;
  onCompleteSession?: (sessionId: string) => void;
  onViewMemoryBlocks?: (sessionId: string) => void;
  onExportSession?: (sessionId: string) => void;
}

export function SessionMetadata({
  session,
  summary,
  onCompleteSession,
  onViewMemoryBlocks,
  onExportSession,
}: SessionMetadataProps) {
  const totalBlocks = summary?.total_blocks ?? 0;
  const isActive = session.status.toLowerCase() === 'active';
  const completionPercent = isActive
    ? Math.min(100, totalBlocks * 5)
    : 100;

  return (
    <Card title={`Session ${session.session_number}`}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={getStatusVariant(session.status)}>
            {session.status}
          </Badge>
          <span className="text-sm text-gray-600">
            Started {formatDate(session.started_at)}
          </span>
          {session.completed_at && (
            <span className="text-sm text-gray-600">
              · Completed {formatDate(session.completed_at)}
            </span>
          )}
        </div>

        {isActive && (
          <div>
            <p className="mb-1 text-sm text-gray-600">Progress (estimate)</p>
            <ProgressBar progress={completionPercent} />
          </div>
        )}

        {summary && summary.memory_block_counts.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">
              Memory blocks by type
            </p>
            <ul className="space-y-1 text-sm text-gray-600">
              {summary.memory_block_counts.map((c) => (
                <li key={c.block_type}>
                  {c.block_type}: {c.count}
                </li>
              ))}
            </ul>
            <p className="mt-1 text-xs text-gray-500">
              Total: {summary.total_blocks} blocks
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {isActive && onCompleteSession && (
            <Button
              variant="primary"
              onClick={() => onCompleteSession(session.id)}
            >
              Complete Session
            </Button>
          )}
          {onViewMemoryBlocks && (
            <Button
              variant="secondary"
              onClick={() => onViewMemoryBlocks(session.id)}
            >
              View Memory Blocks
            </Button>
          )}
          {onExportSession && (
            <Button
              variant="secondary"
              onClick={() => onExportSession(session.id)}
            >
              Export Session
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
