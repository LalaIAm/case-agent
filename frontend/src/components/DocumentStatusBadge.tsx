/**
 * Document status indicator: PDF Ready, Generating, Failed, No PDF.
 */
import { LoadingSpinner } from './LoadingSpinner';

export type DocumentStatus = 'pdf_ready' | 'generating' | 'failed' | 'no_pdf';

interface DocumentStatusBadgeProps {
  status: DocumentStatus;
  onRetry?: () => void;
  title?: string;
}

const statusConfig: Record<
  DocumentStatus,
  { label: string; className: string; showSpinner?: boolean }
> = {
  pdf_ready: {
    label: 'PDF Ready',
    className: 'bg-green-100 text-green-800',
  },
  generating: {
    label: 'Generating PDF',
    className: 'bg-amber-100 text-amber-800',
    showSpinner: true,
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-800',
  },
  no_pdf: {
    label: 'No PDF',
    className: 'bg-gray-100 text-gray-600',
  },
};

export function DocumentStatusBadge({
  status,
  onRetry,
  title,
}: DocumentStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
      title={title ?? config.label}
      role="status"
      aria-label={config.label}
    >
      {config.showSpinner && (
        <LoadingSpinner size="sm" className="flex-shrink-0" />
      )}
      {config.label}
      {status === 'failed' && onRetry && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRetry();
          }}
          className="ml-1 rounded px-1 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500"
          aria-label="Retry PDF generation"
        >
          Retry
        </button>
      )}
    </span>
  );
}
