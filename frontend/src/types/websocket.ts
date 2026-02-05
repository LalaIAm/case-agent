/**
 * WebSocket message types matching backend AgentStatusMessage and WorkflowUpdateMessage.
 */

export interface AgentStatusMessage {
  type: 'agent_status';
  case_id: string;
  agent_name: string;
  status: string;
  reasoning: string | null;
  progress: number;
}

export interface WorkflowUpdateMessage {
  type: 'workflow_update';
  case_id: string;
  current_agent: string | null;
  completed_agents: string[];
  workflow_status: string;
  error: string | null;
  progress_percentage: number;
}

export type WebSocketMessage = AgentStatusMessage | WorkflowUpdateMessage;

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
