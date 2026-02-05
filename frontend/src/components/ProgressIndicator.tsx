/**
 * Progress indicator: determinate bar, indeterminate, or step-based.
 */
interface ProgressIndicatorProps {
  /** 0–100 for determinate; null for indeterminate */
  progress?: number | null;
  /** Current step label (e.g. "Step 2 of 5") */
  stepLabel?: string;
  /** Estimated time remaining (e.g. "~2 min") */
  estimatedTime?: string;
  className?: string;
}

export function ProgressIndicator({
  progress = null,
  stepLabel,
  estimatedTime,
  className = '',
}: ProgressIndicatorProps) {
  const isIndeterminate = progress == null;

  return (
    <div className={`space-y-2 ${className}`} role="progressbar" aria-valuenow={progress ?? undefined} aria-valuemin={0} aria-valuemax={100} aria-label={stepLabel ?? 'Progress'}>
      {(stepLabel || estimatedTime) && (
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          {stepLabel && <span>{stepLabel}</span>}
          {estimatedTime && <span>{estimatedTime}</span>}
        </div>
      )}
      <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        {isIndeterminate ? (
          <div className="h-full w-1/3 rounded-full bg-blue-600 animate-pulse-soft" />
        ) : (
          <div
            className="h-full rounded-full bg-blue-600 transition-[width] duration-300"
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        )}
      </div>
    </div>
  );
}
