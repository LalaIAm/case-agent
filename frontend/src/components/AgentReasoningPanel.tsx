/**
 * Expandable card showing agent name, status, progress, reasoning, and timestamp.
 */
import { useState } from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';

export interface AgentReasoningPanelProps {
  agentName: string;
  reasoning: string | null;
  status: string;
  progress: number;
  timestamp: number;
}

function formatRelativeTime(ts: number): string {
  const sec = Math.floor((Date.now() - ts) / 1000);
  if (sec < 60) return 'Just now';
  if (sec < 3600) return `${Math.floor(sec / 60)} minute(s) ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} hour(s) ago`;
  return `${Math.floor(sec / 86400)} day(s) ago`;
}

function badgeVariant(status: string): 'draft' | 'active' | 'completed' | 'error' {
  const s = status.toLowerCase();
  if (s === 'completed' || s === 'skipped') return 'completed';
  if (s === 'failed') return 'error';
  if (s === 'running') return 'active';
  return 'draft';
}

function displayName(name: string): string {
  const labels: Record<string, string> = {
    intake: 'Intake',
    research: 'Research',
    document: 'Document Analysis',
    strategy: 'Strategy',
    drafting: 'Drafting',
  };
  return labels[name] ?? name;
}

export function AgentReasoningPanel({
  agentName,
  reasoning,
  status,
  progress,
  timestamp,
}: AgentReasoningPanelProps) {
  const [expanded, setExpanded] = useState(true);
  const hasReasoning = Boolean(reasoning?.trim());

  return (
    <Card className="transition-all duration-200">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <span className="font-medium text-gray-900">
              {displayName(agentName)}
            </span>
            <Badge variant={badgeVariant(status)}>{status}</Badge>
            <span
              className="text-xs text-gray-500"
              title={new Date(timestamp).toLocaleString()}
            >
              {formatRelativeTime(timestamp)}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-expanded={expanded ? 'true' : 'false'}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </div>
        {status === 'running' && (
          <ProgressBar progress={progress} variant="primary" />
        )}
        {expanded && (
          <div className="mt-1">
            {hasReasoning ? (
              <p className="whitespace-pre-wrap text-sm text-gray-600">
                {reasoning!.trim()}
              </p>
            ) : (
              <p className="text-sm italic text-gray-400">No reasoning yet.</p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
