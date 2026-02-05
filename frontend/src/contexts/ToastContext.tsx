/**
 * Global toast management: showSuccess, showError, showWarning, showInfo.
 * Queue multiple toasts; position top-right.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Toast, type ToastItem, type ToastVariant } from '../components/Toast';

interface ToastContextValue {
  showSuccess: (message: string, duration?: number) => void;
  showError: (message: string, duration?: number) => void;
  showWarning: (message: string, duration?: number) => void;
  showInfo: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let globalToastRef: ToastContextValue | null = null;

function setGlobalToast(value: ToastContextValue | null): void {
  globalToastRef = value;
}

export function getGlobalToast(): ToastContextValue | null {
  return globalToastRef;
}

let nextId = 0;
function generateId(): string {
  return `toast-${++nextId}-${Date.now()}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const show = useCallback((message: string, variant: ToastVariant, duration?: number) => {
    const id = generateId();
    setToasts((prev) => [...prev, { id, message, variant, duration }]);
    return id;
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      showSuccess: (msg, dur) => show(msg, 'success', dur),
      showError: (msg, dur) => show(msg, 'error', dur),
      showWarning: (msg, dur) => show(msg, 'warning', dur),
      showInfo: (msg, dur) => show(msg, 'info', dur),
    }),
    [show]
  );

  useEffect(() => {
    setGlobalToast(value);
    return () => setGlobalToast(null);
  }, [value]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
        aria-label="Notifications"
      >
        <div className="flex flex-col gap-2 pointer-events-auto">
          {toasts.map((t) => (
            <Toast key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
