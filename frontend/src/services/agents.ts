/**
 * Agent execution and status API.
 */
import { api } from './api';

const BASE = '/api/agents';

export interface AgentRun {
  id: string;
  case_id: string;
  agent_name: string;
  status: string;
  reasoning: string | null;
  result: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface AgentStatusResponse {
  case_id: string;
  current_agent: string | null;
  workflow_status: string;
  progress_percentage: number;
  agent_runs: AgentRun[];
}

export async function getAgentStatus(
  caseId: string
): Promise<AgentStatusResponse> {
  const { data } = await api.get<AgentStatusResponse>(
    `${BASE}/status/${caseId}`
  );
  return data;
}

export async function getAgentRuns(caseId: string): Promise<AgentRun[]> {
  const { data } = await api.get<AgentRun[]>(`${BASE}/cases/${caseId}/runs`);
  return data;
}

export async function executeAgents(
  caseId: string,
  options?: { agentName?: string; forceRestart?: boolean }
): Promise<{ status: string; message: string; case_id: string }> {
  const body: {
    case_id: string;
    agent_name?: string | null;
    force_restart: boolean;
  } = {
    case_id: caseId,
    force_restart: options?.forceRestart ?? false,
  };
  if (options?.agentName != null) {
    body.agent_name = options.agentName;
  }
  const { data } = await api.post<{
    status: string;
    message: string;
    case_id: string;
  }>(`${BASE}/execute`, body);
  return data;
}
