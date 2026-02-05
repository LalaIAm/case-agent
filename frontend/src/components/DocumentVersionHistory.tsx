/**
 * Timeline of versions for a document type with View and Compare actions.
 */
import { useState, useEffect, useCallback } from 'react';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';
import { getGeneratedDocuments, type GeneratedDocumentResponse } from '../services/documents';
import { formatGeneratedDate, getVersionBadgeColor } from '../utils/documentUtils';

export interface DocumentVersionHistoryProps {
  caseId: string;
  documentType: string;
  currentVersion: number;
  currentDocumentId: string;
  onSelectVersion?: (doc: GeneratedDocumentResponse) => void;
  onCompare?: (doc1: GeneratedDocumentResponse, doc2: GeneratedDocumentResponse) => void;
}

export function DocumentVersionHistory({
  caseId,
  documentType,
  currentVersion: _currentVersion,
  currentDocumentId,
  onSelectVersion,
  onCompare,
}: DocumentVersionHistoryProps) {
  const [documents, setDocuments] = useState<GeneratedDocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await getGeneratedDocuments(caseId);
      const filtered = list
        .filter((d) => d.document_type === documentType)
        .sort((a, b) => b.version - a.version);
      setDocuments(filtered);
    } catch {
      setError('Failed to load versions');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [caseId, documentType]);

  useEffect(() => {
    load();
  }, [load]);

  const currentDoc = documents.find((d) => d.id === currentDocumentId);
  const totalChars = documents.reduce((sum, d) => sum + (d.content?.length ?? 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <LoadingSpinner size="sm" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        {error}
        <Button variant="secondary" className="mt-2" onClick={load}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-900">Version history</h3>
      <p className="text-xs text-gray-500">
        {documents.length} version{documents.length !== 1 ? 's' : ''} · ~{(totalChars / 1024).toFixed(1)} KB text
      </p>
      <ul className="space-y-2" role="list">
        {documents.map((doc) => {
          const isCurrent = doc.id === currentDocumentId;
          return (
            <li
              key={doc.id}
              className={`rounded border p-2 text-sm ${isCurrent ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'}`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${getVersionBadgeColor(doc.version)}`}>
                  v{doc.version}
                </span>
                {isCurrent && (
                  <span className="text-xs font-medium text-blue-700">Current</span>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-500">{formatGeneratedDate(doc.generated_at)}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Button
                  variant="secondary"
                  className="!py-1 !text-xs"
                  onClick={() => onSelectVersion?.(doc)}
                >
                  View
                </Button>
                {currentDoc && doc.id !== currentDoc.id && onCompare && (
                  <Button
                    variant="secondary"
                    className="!py-1 !text-xs"
                    onClick={() => onCompare(currentDoc, doc)}
                  >
                    Compare
                  </Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {documents.length === 0 && (
        <p className="text-sm text-gray-500">No versions yet.</p>
      )}
    </div>
  );
}
