/**
 * Socket.IO client for real-time agent status. Connects to backend with path /ws/agents,
 * query { caseId, token }; forwards agent_status and workflow_update events.
 * Connection state tracking, exponential backoff reconnection, and status callbacks.
 */
import { io, type Socket } from 'socket.io-client';
import { getStoredToken } from './api';
import type { WebSocketMessage } from '../types/websocket';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'http://localhost:8000';
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY_INITIAL = 1000;
const RECONNECT_DELAY_MAX = 30000;

/** Ensure base URL is HTTP for Socket.IO (it performs its own upgrade). */
function getSocketBase(): string {
  const base = WS_BASE.trim();
  if (base.startsWith('ws://')) return base.replace(/^ws/, 'http');
  if (base.startsWith('wss://')) return base.replace(/^wss/, 'https');
  return base;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface AgentWebSocketCallbacks {
  onMessage: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onConnectionState?: (state: ConnectionState, attempt?: number) => void;
}

export class AgentWebSocketClient {
  private caseId: string;
  private callbacks: AgentWebSocketCallbacks;
  private socket: Socket | null = null;
  private _connectionState: ConnectionState = 'disconnected';
  private _reconnectAttempt = 0;

  constructor(caseId: string, callbacks: AgentWebSocketCallbacks) {
    this.caseId = caseId;
    this.callbacks = callbacks;
  }

  get connectionState(): ConnectionState {
    return this._connectionState;
  }

  get reconnectAttempt(): number {
    return this._reconnectAttempt;
  }

  private setState(state: ConnectionState, attempt?: number): void {
    this._connectionState = state;
    if (attempt !== undefined) this._reconnectAttempt = attempt;
    this.callbacks.onConnectionState?.(state, this._reconnectAttempt);
  }

  connect(): void {
    const token = getStoredToken();
    if (!token) {
      this.callbacks.onError?.(new Error('No auth token'));
      this.setState('error');
      return;
    }

    this.setState('connecting');
    const base = getSocketBase();
    this.socket = io(base, {
      path: '/ws/agents',
      query: { caseId: this.caseId, token },
      reconnection: true,
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
      reconnectionDelay: RECONNECT_DELAY_INITIAL,
      reconnectionDelayMax: RECONNECT_DELAY_MAX,
      timeout: 20000,
    });

    this.socket.on('connect', () => {
      this._reconnectAttempt = 0;
      this.setState('connected');
      this.callbacks.onConnect?.();
    });

    this.socket.on('disconnect', (reason) => {
      this.setState('disconnected');
      this.callbacks.onDisconnect?.();
    });

    this.socket.on('reconnect_attempt', (attempt: number) => {
      this._reconnectAttempt = attempt;
      this.setState('connecting', attempt);
    });

    this.socket.on('reconnect_failed', () => {
      this.setState('error', this._reconnectAttempt);
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

  reconnect(): void {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }
    this._reconnectAttempt = 0;
    this.connect();
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }
    this.setState('disconnected');
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
