/**
 * Dashboard listing all cases for the current user.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/Header';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { EmptyState } from '../components/EmptyState';
import { getCases } from '../services/cases';
import type { Case } from '../types/case';

type StatusFilter = 'all' | 'draft' | 'active' | 'completed';

function getBadgeVariant(
  status: string
): 'draft' | 'active' | 'completed' | 'error' {
  const s = status.toLowerCase();
  if (s === 'draft') return 'draft';
  if (s === 'active') return 'active';
  if (s === 'completed') return 'completed';
  return 'draft';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function CaseDashboard() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<StatusFilter>('all');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params =
          filter === 'all'
            ? undefined
            : { status: filter };
        const list = await getCases(params);
        setCases(list);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Unable to load cases'
        );
        setCases([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [filter]);

  const tabs: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'draft', label: 'Draft' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-2xl font-semibold text-gray-900">My Cases</h1>
          <Button
            variant="primary"
            onClick={() => navigate('/intake')}
          >
            New Case
          </Button>
        </div>

        <div className="mb-6 flex gap-2 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setFilter(tab.value)}
              className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                filter === tab.value
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : cases.length === 0 ? (
          <EmptyState
            title="No cases yet"
            description="Create your first case to get started."
            action={{
              label: 'New Case',
              onClick: () => navigate('/intake'),
            }}
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {cases.map((c) => (
              <div
                key={c.id}
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/cases/${c.id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(`/cases/${c.id}`);
                  }
                }}
                className="cursor-pointer rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-all hover:border-gray-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <h3 className="truncate text-lg font-medium text-gray-900">
                  {c.title}
                </h3>
                {c.description && (
                  <p className="mt-1 line-clamp-3 text-sm text-gray-500">
                    {c.description}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge variant={getBadgeVariant(c.status)}>
                    {c.status}
                  </Badge>
                  <span className="text-xs text-gray-400">
                    {formatDate(c.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
