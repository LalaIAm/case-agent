/**
 * Intake page: create new case and upload evidence.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/Header';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Textarea } from '../components/Textarea';
import { Button } from '../components/Button';
import { FileUpload } from '../components/FileUpload';
import { createCase } from '../services/cases';
import type { Case } from '../types/case';

export function IntakePage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [titleError, setTitleError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [createdCase, setCreatedCase] = useState<Case | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setTitleError(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setTitleError('Title is required');
      return;
    }
    if (trimmedTitle.length > 500) {
      setTitleError('Title must be 500 characters or less');
      return;
    }

    setLoading(true);
    try {
      const c = await createCase({
        title: trimmedTitle,
        description: description.trim() || null,
      });
      setCreatedCase(c);
    } catch (err: unknown) {
      const message =
        err && typeof err === 'object' && 'response' in err
          ? String(
              (err as { response?: { data?: { detail?: string } } }).response
                ?.data?.detail ?? 'Failed to create case'
            )
          : err instanceof Error
            ? err.message
            : 'Failed to create case';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handleContinue() {
    if (createdCase) {
      navigate(`/cases/${createdCase.id}`);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">
          Start New Case
        </h1>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <Card title="Case Information">
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Case Title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setTitleError(null);
                }}
                error={titleError ?? undefined}
                placeholder="Brief description of your case"
                maxLength={500}
                required
              />
              <Textarea
                label="Description (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                placeholder="Additional details about your case..."
              />
              {error && (
                <p className="text-sm text-red-600" role="alert">
                  {error}
                </p>
              )}
              <Button
                type="submit"
                variant="primary"
                disabled={loading}
              >
                {loading ? 'Creating…' : 'Create Case'}
              </Button>
            </form>
          </Card>

          {createdCase && (
            <Card title="Upload Evidence">
              <p className="mb-4 text-sm text-gray-600">
                Case <strong>{createdCase.title}</strong> created. Upload
                evidence documents (PDF, PNG, JPG).
              </p>
              <FileUpload
                caseId={createdCase.id}
                onUploadComplete={() => {}}
              />
              <div className="mt-4 flex gap-2">
                <Button variant="primary" onClick={handleContinue}>
                  Continue to Case
                </Button>
              </div>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
