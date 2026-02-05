/**
 * Shared document utilities: formatting, icons, colors, estimates.
 */

export function formatDocumentType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function getDocumentTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    statement_of_claim: '📄',
    hearing_script: '📋',
    legal_advice: '⚖️',
  };
  return icons[type] ?? '📑';
}

export function getDocumentTypeColor(type: string): string {
  const colors: Record<string, string> = {
    statement_of_claim: 'bg-blue-100 text-blue-800',
    hearing_script: 'bg-amber-100 text-amber-800',
    legal_advice: 'bg-emerald-100 text-emerald-800',
  };
  return colors[type] ?? 'bg-gray-100 text-gray-800';
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Rough estimate: ~3000 chars per page for typical legal text. */
export function estimatePageCount(content: string): number {
  if (!content || !content.trim()) return 0;
  return Math.max(1, Math.ceil(content.length / 3000));
}

export function getVersionBadgeColor(version: number): string {
  if (version === 1) return 'bg-blue-100 text-blue-800';
  return 'bg-green-100 text-green-800';
}

export function formatGeneratedDate(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;

  return date.toLocaleDateString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}
