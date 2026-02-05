/**
 * Client-side error tracking. Log to console in development; can send to Sentry/LogRocket in production.
 */
export function initErrorTracking(): void {
  if (import.meta.env.PROD && import.meta.env.VITE_ENABLE_ERROR_TRACKING === 'true') {
    // Placeholder for Sentry/LogRocket init using VITE_SENTRY_DSN
    // e.g. Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN, ... })
  }
}

export function captureException(error: unknown, context?: Record<string, unknown>): void {
  if (import.meta.env.DEV) {
    console.error('Error captured:', error, context);
    return;
  }
  if (import.meta.env.VITE_ENABLE_ERROR_TRACKING === 'true') {
    // Sentry.captureException(error, { extra: context });
  }
}

export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info'): void {
  if (import.meta.env.DEV) {
    if (level === 'error') console.error(message);
    else if (level === 'warning') console.warn(message);
    else console.log(message);
    return;
  }
  if (import.meta.env.VITE_ENABLE_ERROR_TRACKING === 'true') {
    // Sentry.captureMessage(message, level);
  }
}
