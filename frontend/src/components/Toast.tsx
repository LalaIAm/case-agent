/**
 * Toast notification: success, error, warning, info. Auto-dismiss, manual dismiss, stacked.
 */
import { useEffect } from 'react';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

const variantStyles: Record<ToastVariant, string> = {
  success: 'bg-green-600 text-white border-green-700',
  error: 'bg-red-600 text-white border-red-700',
  warning: 'bg-amber-600 text-white border-amber-700',
  info: 'bg-blue-600 text-white border-blue-700',
};

const variantIcons: Record<ToastVariant, string> = {
  success: '✓',
  error: '✕',
  warning: '!',
  info: 'i',
};

export function Toast({ toast, onDismiss }: ToastProps) {
  const duration = toast.duration ?? 5000;

  useEffect(() => {
    if (duration <= 0) return;
    const t = setTimeout(() => onDismiss(toast.id), duration);
    return () => clearTimeout(t);
  }, [toast.id, duration, onDismiss]);

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg min-w-[280px] max-w-md animate-toast-in ${variantStyles[toast.variant]}`}
    >
      <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-white/20 text-sm font-bold">
        {variantIcons[toast.variant]}
      </span>
      <p className="flex-1 text-sm font-medium">{toast.message}</p>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="flex-shrink-0 p-1 rounded hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
        aria-label="Dismiss"
      >
        <span aria-hidden>×</span>
      </button>
    </div>
  );
}
