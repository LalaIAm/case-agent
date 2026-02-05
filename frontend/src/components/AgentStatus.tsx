/**
 * Real-time agent monitoring: WebSocket connection, workflow diagram, agent list, notifications.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { createAgentWebSocket, AgentWebSocketClient } from '../services/websocket';
import type { WebSocketMessage, ConnectionStatus } from '../types/websocket';
import { Card } from './Card';
import { Badge } from './Badge';
import { Button } from './Button';
import { ProgressBar } from './ProgressBar';
import { LoadingSpinner } from './LoadingSpinner';
import { EmptyState } from './EmptyState';
import { AgentWorkflowDiagram } from './AgentWorkflowDiagram';
import { AgentList } from './AgentList';
import type { AgentListItem } from './AgentList';
import {
  AgentNotificationContainer,
  type AgentNotificationItem,
} from './AgentNotification';
import { ConnectionStatus as ConnectionStatusIndicator } from './ConnectionStatus';
import type { ConnectionState } from '../services/websocket';

const WORKFLOW_STEPS = ['intake', 'research', 'document', 'strategy', 'drafting'];

export interface AgentStatusInitialStatus {
  progress_percentage: number;
  workflow_status: string;
  current_agent: string | null;
}

export interface AgentStatusProps {
  caseId: string;
  initialStatus?: AgentStatusInitialStatus;
  onRunAgents?: () => void;
}

function workflowBadgeVariant(
  status: string
): 'draft' | 'active' | 'completed' | 'error' {
  const s = status.toLowerCase();
  if (s === 'completed') return 'completed';
  if (s === 'failed') return 'error';
  if (s === 'running' || s === 'in_progress') return 'active';
  return 'draft';
}

export function AgentStatus({
  caseId,
  initialStatus,
  onRunAgents,
}: AgentStatusProps) {
  const [agentStatuses, setAgentStatuses] = useState<
    Map<string, { status: string; reasoning: string | null; progress: number; timestamp: number }>
  >(new Map());
  const [workflowState, setWorkflowState] = useState({
    current_agent: initialStatus?.current_agent ?? null,
    completed_agents: [] as string[],
    workflow_status: initialStatus?.workflow_status ?? 'pending',
    error: null as string | null,
    progress_percentage: initialStatus?.progress_percentage ?? 0,
  });
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('connecting');
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsClientRef = useRef<AgentWebSocketClient | null>(null);
  const [notifications, setNotifications] = useState<AgentNotificationItem[]>([]);
  const notificationIdRef = useRef(0);

  const addNotification = useCallback(
    (agentName: string, status: string, variant: AgentNotificationItem['variant']) => {
      const message =
        variant === 'started'
          ? 'Agent started'
          : variant === 'completed'
            ? 'Agent completed'
            : 'Agent failed';
      setNotifications((prev) => [
        ...prev,
        {
          id: `n-${++notificationIdRef.current}`,
          agentName,
          status,
          variant,
          message,
        },
      ]);
    },
    []
  );

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  useEffect(() => {
    const client = createAgentWebSocket(
      caseId,
      (message: WebSocketMessage) => {
        if (message.type === 'agent_status') {
          setAgentStatuses((prev) => {
            const next = new Map(prev);
            next.set(message.agent_name, {
              status: message.status,
              reasoning: message.reasoning ?? null,
              progress: message.progress ?? 0,
              timestamp: Date.now(),
            });
            return next;
          });
          if (message.status === 'running') {
            addNotification(message.agent_name, message.status, 'started');
          } else if (message.status === 'completed' || message.status === 'skipped') {
            addNotification(message.agent_name, message.status, 'completed');
          } else if (message.status === 'failed') {
            addNotification(message.agent_name, message.status, 'failed');
          }
        } else if (message.type === 'workflow_update') {
          setWorkflowState({
            current_agent: message.current_agent ?? null,
            completed_agents: message.completed_agents ?? [],
            workflow_status: message.workflow_status ?? 'pending',
            error: message.error ?? null,
            progress_percentage: message.progress_percentage ?? 0,
          });
        }
      },
      {
        onConnect: () => {
          setConnectionStatus('connected');
          setConnectionError(null);
          setReconnectAttempt(0);
        },
        onDisconnect: () => {
          setConnectionStatus('disconnected');
        },
        onError: (err) => {
          setConnectionStatus('error');
          setConnectionError(err.message);
        },
        onConnectionState: (state: ConnectionState, attempt?: number) => {
          setConnectionStatus(state);
          if (attempt !== undefined) setReconnectAttempt(attempt);
        },
      }
    );
    wsClientRef.current = client;
    client.connect();
    return () => {
      client.disconnect();
      wsClientRef.current = null;
    };
  }, [caseId, addNotification]);

  const handleRetry = useCallback(() => {
    setConnectionError(null);
    setConnectionStatus('connecting');
    wsClientRef.current?.disconnect();
    const client = createAgentWebSocket(
      caseId,
      (message: WebSocketMessage) => {
        if (message.type === 'agent_status') {
          setAgentStatuses((prev) => {
            const next = new Map(prev);
            next.set(message.agent_name, {
              status: message.status,
              reasoning: message.reasoning ?? null,
              progress: message.progress ?? 0,
              timestamp: Date.now(),
            });
            return next;
          });
          if (message.status === 'running') {
            addNotification(message.agent_name, message.status, 'started');
          } else if (message.status === 'completed' || message.status === 'skipped') {
            addNotification(message.agent_name, message.status, 'completed');
          } else if (message.status === 'failed') {
            addNotification(message.agent_name, message.status, 'failed');
          }
        } else if (message.type === 'workflow_update') {
          setWorkflowState({
            current_agent: message.current_agent ?? null,
            completed_agents: message.completed_agents ?? [],
            workflow_status: message.workflow_status ?? 'pending',
            error: message.error ?? null,
            progress_percentage: message.progress_percentage ?? 0,
          });
        }
      },
      {
        onConnect: () => {
          setConnectionStatus('connected');
          setConnectionError(null);
          setReconnectAttempt(0);
        },
        onDisconnect: () => setConnectionStatus('disconnected'),
        onError: (err) => {
          setConnectionStatus('error');
          setConnectionError(err.message);
        },
        onConnectionState: (state: ConnectionState, attempt?: number) => {
          setConnectionStatus(state);
          if (attempt !== undefined) setReconnectAttempt(attempt);
        },
      }
    );
    wsClientRef.current = client;
    client.connect();
  }, [caseId, addNotification]);

  const handleReconnect = useCallback(() => {
    setConnectionError(null);
    setConnectionStatus('connecting');
    setReconnectAttempt(0);
    wsClientRef.current?.reconnect();
  }, []);

  const agentList: AgentListItem[] = WORKFLOW_STEPS.map((name) => {
    const entry = agentStatuses.get(name);
    return {
      name,
      status: entry?.status ?? 'pending',
      reasoning: entry?.reasoning ?? null,
      progress: entry?.progress ?? 0,
      timestamp: entry?.timestamp ?? 0,
    };
  });

  const hasAnyActivity =
    agentStatuses.size > 0 ||
    workflowState.completed_agents.length > 0 ||
    workflowState.current_agent != null;

  if (connectionStatus === 'connecting' && !connectionError) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12">
        <LoadingSpinner size="lg" />
        <p className="text-sm text-gray-600">Connecting to agent monitoring…</p>
      </div>
    );
  }

  if (connectionError && connectionStatus === 'error') {
    return (
      <div className="space-y-4">
        <div
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800"
          role="alert"
        >
          <p className="font-medium">Connection error</p>
          <p className="text-sm">{connectionError}</p>
          <Button variant="primary" onClick={handleRetry} className="mt-2">
            Retry connection
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AgentNotificationContainer
        notifications={notifications}
        onDismiss={dismissNotification}
      />

      <Card title="Workflow Progress">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <ConnectionStatusIndicator
            state={connectionStatus as ConnectionState}
            reconnectAttempt={reconnectAttempt}
            onReconnect={handleReconnect}
          />
          {connectionStatus === 'connected' && (
            <span className="text-sm text-gray-600">Live</span>
          )}
          <Badge variant={workflowBadgeVariant(workflowState.workflow_status)}>
            {workflowState.workflow_status}
          </Badge>
        </div>
        <ProgressBar
          progress={workflowState.progress_percentage}
          label={`${workflowState.progress_percentage}%`}
          variant={
            workflowState.workflow_status === 'failed'
              ? 'error'
              : workflowState.workflow_status === 'completed'
                ? 'success'
                : 'primary'
          }
        />
        {workflowState.error && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {workflowState.error}
          </p>
        )}
        <div className="mt-4">
          <AgentWorkflowDiagram
            currentAgent={workflowState.current_agent}
            completedAgents={workflowState.completed_agents}
            workflowStatus={workflowState.workflow_status}
          />
        </div>
        {onRunAgents && (
          <Button
            variant="primary"
            onClick={onRunAgents}
            className="mt-4"
          >
            Run Agents
          </Button>
        )}
      </Card>

      <Card title="Agent reasoning">
        {!hasAnyActivity ? (
          <EmptyState
            title="No agent activity yet"
            description="Click 'Run Agents' to start the workflow."
            action={
              onRunAgents
                ? { label: 'Run Agents', onClick: onRunAgents }
                : undefined
            }
          />
        ) : (
          <AgentList
            agents={agentList}
            currentAgent={workflowState.current_agent}
          />
        )}
      </Card>
    </div>
  );
}
