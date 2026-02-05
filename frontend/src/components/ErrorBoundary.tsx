/**
 * React error boundary: catches render errors and displays a fallback with recovery actions.
 * Logs to console in development; can send to error tracking in production.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { captureException } from '../utils/errorTracking';

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, State> {
  state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
    captureException(error, { componentStack: errorInfo.componentStack });
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  toggleDetails = (): void => {
    this.setState((s) => ({ showDetails: !s.showDetails }));
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      const { error, errorInfo, showDetails } = this.state;
      return (
        <div
          className="min-h-[40vh] flex flex-col items-center justify-center p-6 bg-gray-50 dark:bg-gray-900"
          role="alert"
          aria-live="assertive"
        >
          <div className="max-w-lg w-full rounded-lg border border-red-200 dark:border-red-800 bg-white dark:bg-gray-800 shadow p-6">
            <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-2">
              Something went wrong
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              We're sorry. You can try reloading the page or go back to the dashboard.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={this.handleRetry}
                className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Try again
              </button>
              <button
                type="button"
                onClick={this.handleGoHome}
                className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Go to dashboard
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Reload page
              </button>
            </div>
            <div className="mt-4">
              <button
                type="button"
                onClick={this.toggleDetails}
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {showDetails ? 'Hide' : 'Show'} error details
              </button>
              {showDetails && (
                <pre className="mt-2 p-3 text-xs bg-gray-100 dark:bg-gray-900 rounded overflow-auto max-h-48">
                  {error.toString()}
                  {errorInfo?.componentStack}
                </pre>
              )}
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
