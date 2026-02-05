/**
 * Socket.IO client for real-time agent status. Connects to backend with path /ws/agents,
 * query { caseId, token }; forwards agent_status and workflow_update events.
 * Reconnection and heartbeat are handled by socket.io.
 */
import { io, type Socket } from 'socket.io-client';
import { getStoredToken } from './api';
import type { WebSocketMessage } from '../types/websocket';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'http://localhost:8000';

/** Ensure base URL is HTTP for Socket.IO (it performs its own upgrade). */
function getSocketBase(): string {
  const base = WS_BASE.trim();
  if (base.startsWith('ws://')) return base.replace(/^ws/, 'http');
  if (base.startsWith('wss://')) return base.replace(/^wss/, 'https');
  return base;
}

export interface AgentWebSocketCallbacks {
  onMessage: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export class AgentWebSocketClient {
  private caseId: string;
  private callbacks: AgentWebSocketCallbacks;
  private socket: Socket | null = null;

  constructor(caseId: string, callbacks: AgentWebSocketCallbacks) {
    this.caseId = caseId;
    this.callbacks = callbacks;
  }

  connect(): void {
    const token = getStoredToken();
    if (!token) {
      this.callbacks.onError?.(new Error('No auth token'));
      return;
    }

    const base = getSocketBase();
    this.socket = io(base, {
      path: '/ws/agents',
      query: { caseId: this.caseId, token },
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 16000,
      timeout: 20000,
    });

    this.socket.on('connect', () => {
      this.callbacks.onConnect?.();
    });

    this.socket.on('disconnect', () => {
      this.callbacks.onDisconnect?.();
    });

    this.socket.on('error', (err: Error) => {
      this.callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    });

    this.socket.on('connect_error', (err: Error) => {
      this.callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    });

    this.socket.on('agent_status', (payload: WebSocketMessage) => {
      this.callbacks.onMessage(payload);
    });

    this.socket.on('workflow_update', (payload: WebSocketMessage) => {
      this.callbacks.onMessage(payload);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }
    this.callbacks.onDisconnect?.();
  }
}

export function createAgentWebSocket(
  caseId: string,
  onMessage: (msg: WebSocketMessage) => void,
  callbacks?: Partial<Omit<AgentWebSocketCallbacks, 'onMessage'>>
): AgentWebSocketClient {
  const client = new AgentWebSocketClient(caseId, {
    onMessage,
    ...callbacks,
  });
  return client;
}
