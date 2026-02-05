/**
 * WebSocket client for real-time agent status. Connects to backend /ws/agents/{case_id}
 * with JWT in query, heartbeat, exponential backoff reconnection, and close-code handling.
 */
import { getStoredToken } from './api';
import type { WebSocketMessage } from '../types/websocket';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000';
const HEARTBEAT_INTERVAL_MS = 25000;
const PONG_TIMEOUT_MS = 10000;

export interface AgentWebSocketCallbacks {
  onMessage: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export class AgentWebSocketClient {
  private caseId: string;
  private callbacks: AgentWebSocketCallbacks;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelays = [1000, 2000, 4000, 8000, 16000];
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private pongTimeout: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  constructor(caseId: string, callbacks: AgentWebSocketCallbacks) {
    this.caseId = caseId;
    this.callbacks = callbacks;
  }

  connect(): void {
    this.intentionalClose = false;
    const token = getStoredToken();
    if (!token) {
      this.callbacks.onError?.(new Error('No auth token'));
      return;
    }
    const base = WS_BASE.replace(/^http/, 'ws');
    const url = `${base}/ws/agents/${this.caseId}?token=${encodeURIComponent(token)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.callbacks.onConnect?.();
    };

    this.ws.onmessage = (event) => {
      this.resetPongTimeout();
      const data = event.data;
      if (typeof data !== 'string') return;
      const trimmed = data.trim();
      if (trimmed === 'pong') return;
      try {
        const parsed = JSON.parse(trimmed) as { type?: string };
        if (parsed.type === 'ping') return;
        this.callbacks.onMessage(parsed as WebSocketMessage);
      } catch {
        // ignore non-JSON
      }
    };

    this.ws.onerror = () => {
      this.callbacks.onError?.(new Error('WebSocket error'));
    };

    this.ws.onclose = (event) => {
      this.stopHeartbeat();
      this.clearPongTimeout();
      this.ws = null;

      if (this.intentionalClose) {
        this.callbacks.onDisconnect?.();
        return;
      }
      if (event.code === 4001) {
        this.callbacks.onError?.(new Error('Invalid or expired token'));
        window.location.href = '/login';
        return;
      }
      if (event.code === 4003) {
        this.callbacks.onError?.(new Error('You do not have access to this case'));
        this.callbacks.onDisconnect?.();
        return;
      }
      if (event.code === 1000) {
        this.callbacks.onDisconnect?.();
        return;
      }
      this.callbacks.onDisconnect?.();
      this.reconnect();
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.stopHeartbeat();
    this.clearPongTimeout();
    if (this.ws) {
      this.ws.close(1000);
      this.ws = null;
    }
    this.callbacks.onDisconnect?.();
  }

  private reconnect(): void {
    if (this.intentionalClose || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }
    const delay = this.reconnectDelays[this.reconnectAttempts] ?? 16000;
    this.reconnectAttempts += 1;
    setTimeout(() => this.connect(), delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
        this.resetPongTimeout();
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private resetPongTimeout(): void {
    this.clearPongTimeout();
    this.pongTimeout = setTimeout(() => {
      this.pongTimeout = null;
      if (this.ws) {
        this.ws.close();
        this.ws = null;
        this.reconnect();
      }
    }, PONG_TIMEOUT_MS);
  }

  private clearPongTimeout(): void {
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
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
