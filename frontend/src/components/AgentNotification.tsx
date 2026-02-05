/**
 * Toast notification for agent events: started (blue), completed (green), failed (red).
 * Auto-dismiss 5s, manual dismiss, slide-in/slide-out, top-right.
 */
import { useEffect, useState } from 'react';

export type AgentNotificationVariant = 'started' | 'completed' | 'failed';

export interface AgentNotificationItem {
  id: string;
  agentName: string;
  status: string;
  variant: AgentNotificationVariant;
  message: string;
}

interface AgentNotificationProps {
  item: AgentNotificationItem;
  onDismiss: (id: string) => void;
  autoDismissMs?: number;
}

const variantStyles: Record<
  AgentNotificationVariant,
  { bg: string; border: string; icon: string }
> = {
  started: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'text-blue-600',
  },
  completed: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: 'text-green-600',
  },
  failed: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: 'text-red-600',
  },
};

export function AgentNotification({
  item,
  onDismiss,
  autoDismissMs = 5000,
}: AgentNotificationProps) {
  const [visible, setVisible] = useState(false);
  const { variant, message, agentName, id } = item;
  const styles = variantStyles[variant];

  useEffect(() => {
    const t = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss(id), 300);
    }, autoDismissMs);
    return () => clearTimeout(timer);
  }, [id, autoDismissMs, onDismiss]);

  const handleDismiss = () => {
    setVisible(false);
    setTimeout(() => onDismiss(id), 300);
  };

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg transition-all duration-300 ${
        styles.bg
      } ${styles.border} ${visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}`}
    >
      <span className={`text-lg ${styles.icon}`} aria-hidden>
        {variant === 'failed' ? '✕' : variant === 'completed' ? '✓' : '●'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-gray-900">{agentName}</p>
        <p className="text-sm text-gray-700">{message}</p>
      </div>
      <button
        type="button"
        onClick={handleDismiss}
        className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-200 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export interface AgentNotificationContainerProps {
  notifications: AgentNotificationItem[];
  onDismiss: (id: string) => void;
}

export function AgentNotificationContainer({
  notifications,
  onDismiss,
}: AgentNotificationContainerProps) {
  if (notifications.length === 0) return null;
  return (
    <div
      className="fixed right-4 top-4 z-50 flex max-w-sm flex-col gap-2"
      aria-live="polite"
    >
      {notifications.map((item) => (
        <AgentNotification
          key={item.id}
          item={item}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}
