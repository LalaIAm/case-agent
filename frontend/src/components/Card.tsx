/**
 * Reusable card with optional header.
 */
interface CardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function Card({ children, title, className = '' }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-6 shadow-sm ${className}`}
    >
      {title && (
        <h3 className="mb-4 text-lg font-medium text-gray-900">{title}</h3>
      )}
      {children}
    </div>
  );
}
