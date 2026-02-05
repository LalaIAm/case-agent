/**
 * Reusable skeleton placeholders with pulse animation.
 */
interface SkeletonLoaderProps {
  className?: string;
  variant?: 'text' | 'card' | 'list' | 'table';
}

function SkeletonBox({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`}
      aria-hidden
    />
  );
}

export function SkeletonLoader({ className = '', variant = 'text' }: SkeletonLoaderProps) {
  if (variant === 'text') {
    return (
      <div className={`space-y-2 ${className}`}>
        <SkeletonBox className="h-4 w-full" />
        <SkeletonBox className="h-4 w-5/6" />
        <SkeletonBox className="h-4 w-4/6" />
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className={`rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3 ${className}`}>
        <SkeletonBox className="h-5 w-3/4" />
        <SkeletonBox className="h-4 w-full" />
        <SkeletonBox className="h-4 w-full" />
        <SkeletonBox className="h-8 w-24" />
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className={`space-y-2 ${className}`}>
        {[1, 2, 3, 4, 5].map((i) => (
          <SkeletonBox key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={`space-y-2 ${className}`}>
        <SkeletonBox className="h-10 w-full" />
        {[1, 2, 3, 4].map((i) => (
          <SkeletonBox key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return <SkeletonBox className={className} />;
}
