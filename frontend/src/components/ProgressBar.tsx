/**
 * Reusable progress bar with optional label and variant styling.
 */
interface ProgressBarProps {
  progress: number;
  label?: string;
  variant?: 'primary' | 'success' | 'error';
}

const variantClasses = {
  primary: 'bg-blue-600',
  success: 'bg-green-600',
  error: 'bg-red-600',
};

export function ProgressBar({
  progress,
  label,
  variant = 'primary',
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, progress));
  return (
    <div className="w-full">
      {label != null && (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {label}
        </span>
      )}
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className={`h-full transition-all duration-300 ${variantClasses[variant]}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
