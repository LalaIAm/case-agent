/**
 * Full-screen loading overlay with spinner and message. Blocks interaction.
 */
interface LoadingOverlayProps {
  message?: string;
  show: boolean;
}

export function LoadingOverlay({ message = 'Loading...', show }: LoadingOverlayProps) {
  if (!show) return null;

  return (
    <div
      className="fixed inset-0 z-[9998] flex flex-col items-center justify-center bg-black/30 backdrop-blur-sm"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex flex-col items-center gap-4 rounded-lg bg-white dark:bg-gray-800 px-8 py-6 shadow-xl">
        <div
          className="h-10 w-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"
          aria-hidden
        />
        <p className="text-gray-700 dark:text-gray-200 font-medium">{message}</p>
      </div>
    </div>
  );
}
