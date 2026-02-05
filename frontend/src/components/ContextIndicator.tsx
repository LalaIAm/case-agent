/**
 * Small badges showing which context types were used in a response.
 */
interface ContextIndicatorProps {
  contextUsed: string[];
}

const LABELS: Record<string, string> = {
  fact: 'Facts',
  facts: 'Facts',
  evidence: 'Evidence',
  strategy: 'Strategy',
  rule: 'Rules',
  rules: 'Rules',
  question: 'Questions',
};

function label(type: string): string {
  return LABELS[type] ?? type;
}

export function ContextIndicator({ contextUsed }: ContextIndicatorProps) {
  if (!contextUsed?.length) return null;
  const unique = [...new Set(contextUsed)];

  return (
    <div
      className="mt-1 flex flex-wrap gap-1"
      title={`Context used: ${unique.length} type(s)`}
    >
      {unique.map((t) => (
        <span
          key={t}
          className="rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600"
        >
          {label(t)}
        </span>
      ))}
    </div>
  );
}
