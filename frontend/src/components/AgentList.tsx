/**
 * List of agent cards with AgentReasoningPanel; highlights current, scrolls to current.
 */
import { useEffect, useRef } from 'react';
import { AgentReasoningPanel } from './AgentReasoningPanel';

export interface AgentListItem {
  name: string;
  status: string;
  reasoning: string | null;
  progress: number;
  timestamp: number;
}

export interface AgentListProps {
  agents: AgentListItem[];
  currentAgent: string | null;
}

const WORKFLOW_ORDER = ['intake', 'research', 'document', 'strategy', 'drafting'];

export function AgentList({ agents, currentAgent }: AgentListProps) {
  const currentRef = useRef<HTMLDivElement>(null);

  const ordered = [...agents].sort((a, b) => {
    const ia = WORKFLOW_ORDER.indexOf(a.name);
    const ib = WORKFLOW_ORDER.indexOf(b.name);
    if (ia === -1 && ib === -1) return 0;
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  useEffect(() => {
    if (currentAgent && currentRef.current) {
      currentRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [currentAgent]);

  if (ordered.length === 0) return null;

  return (
    <ul className="space-y-3" role="list" aria-label="Agent status list">
      {ordered.map((agent) => {
        const isCurrent = currentAgent === agent.name;
        const isCompleted = agent.status === 'completed' || agent.status === 'skipped';
        const isFailed = agent.status === 'failed';
        return (
          <li key={agent.name}>
            <div
              ref={isCurrent ? currentRef : undefined}
              className={`rounded-lg transition-all duration-200 ${
                isCurrent
                  ? 'ring-2 ring-blue-400 ring-offset-2'
                  : ''
              } ${isFailed ? 'border border-red-200' : ''}`}
            >
              <div className="relative">
                {isCompleted && (
                  <span
                    className="absolute right-2 top-2 text-green-600"
                    aria-hidden
                    title="Completed"
                  >
                    ✓
                  </span>
                )}
                {isFailed && (
                  <span
                    className="absolute right-2 top-2 text-red-600"
                    aria-hidden
                    title="Failed"
                  >
                    ✕
                  </span>
                )}
                <AgentReasoningPanel
                  agentName={agent.name}
                  reasoning={agent.reasoning}
                  status={agent.status}
                  progress={agent.progress}
                  timestamp={agent.timestamp}
                />
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
