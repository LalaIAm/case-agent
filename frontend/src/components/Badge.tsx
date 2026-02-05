/**
 * Color-coded status badges.
 */
type BadgeVariant = 'draft' | 'active' | 'completed' | 'error';

interface BadgeProps {
  children: React.ReactNode;
  variant: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  draft: 'bg-gray-100 text-gray-800',
  active: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
};

export function Badge({ children, variant }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]}`}
    >
      {children}
    </span>
  );
}
