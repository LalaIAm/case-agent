/**
 * Visual indicator for WebSocket connection status. Shows reconnection attempts and manual reconnect.
 */
import type { ConnectionState } from '../services/websocket';

export interface ConnectionStatusProps {
  state: ConnectionState;
  reconnectAttempt?: number;
  onReconnect?: () => void;
  className?: string;
}

export function ConnectionStatus({
  state,
  reconnectAttempt = 0,
  onReconnect,
  className = '',
}: ConnectionStatusProps) {
  if (state === 'connected') return null;

  const labels: Record<ConnectionState, string> = {
    connecting: reconnectAttempt > 0 ? `Reconnecting (${reconnectAttempt})…` : 'Connecting…',
    connected: '',
    disconnected: 'Disconnected',
    error: 'Connection failed',
  };
  const label = labels[state];
  const isError = state === 'error' || state === 'disconnected';

  return (
    <div
      className={`flex items-center gap-2 rounded px-2 py-1 text-sm ${className}`}
      role="status"
      aria-live="polite"
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          state === 'connecting' ? 'bg-amber-500 animate-pulse' : isError ? 'bg-red-500' : 'bg-gray-400'
        }`}
        aria-hidden
      />
      <span className={isError ? 'text-red-700 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'}>
        {label}
      </span>
      {onReconnect && isError && (
        <button
          type="button"
          onClick={onReconnect}
          className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
        >
          Reconnect
        </button>
      )}
    </div>
  );
}
