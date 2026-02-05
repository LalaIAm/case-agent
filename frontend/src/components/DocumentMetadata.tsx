/**
 * Detailed metadata display for a generated document.
 */
import { useState, useCallback } from 'react';
import { Card } from './Card';
import { Button } from './Button';
import { DocumentStatusBadge, type DocumentStatus } from './DocumentStatusBadge';
import type { GeneratedDocumentResponse } from '../services/documents';
import {
  formatDocumentType,
  formatGeneratedDate,
  estimatePageCount,
} from '../utils/documentUtils';

const PREVIEW_LENGTH = 200;

interface DocumentMetadataProps {
  document: GeneratedDocumentResponse;
  showFullContent?: boolean;
}

function truncateId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 8)}…`;
}

function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text).catch(() => {});
}

export function DocumentMetadata({
  document: doc,
  showFullContent = false,
}: DocumentMetadataProps) {
  const [showFull, setShowFull] = useState(showFullContent);
  const [showContentModal, setShowContentModal] = useState(false);

  const status: DocumentStatus = doc.has_pdf
    ? 'pdf_ready'
    : 'no_pdf';

  const charCount = doc.content?.length ?? 0;
  const wordCount = doc.content
    ? doc.content.trim().split(/\s+/).filter(Boolean).length
    : 0;
  const pageEstimate = estimatePageCount(doc.content ?? '');

  const preview =
    doc.content && doc.content.length > PREVIEW_LENGTH
      ? doc.content.slice(0, PREVIEW_LENGTH) + '…'
      : doc.content ?? '';

  const handleCopyId = useCallback(() => {
    copyToClipboard(doc.id);
  }, [doc.id]);

  const handleCopyCaseId = useCallback(() => {
    copyToClipboard(doc.case_id);
  }, [doc.case_id]);

  return (
    <>
      <Card title="Document details" className="space-y-4">
        <div className="grid gap-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-gray-500">Document ID</span>
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">
              {truncateId(doc.id)}
            </code>
            <button
              type="button"
              onClick={handleCopyId}
              className="text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Copy document ID"
            >
              Copy
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-gray-500">Case ID</span>
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">
              {truncateId(doc.case_id)}
            </code>
            <button
              type="button"
              onClick={handleCopyCaseId}
              className="text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Copy case ID"
            >
              Copy
            </button>
          </div>
          <div>
            <span className="font-medium text-gray-500">Document type</span>
            <p className="mt-0.5">{formatDocumentType(doc.document_type)}</p>
          </div>
          <div>
            <span className="font-medium text-gray-500">Version</span>
            <p className="mt-0.5">v{doc.version}</p>
          </div>
          <div>
            <span className="font-medium text-gray-500">Generated</span>
            <p className="mt-0.5">{formatGeneratedDate(doc.generated_at)}</p>
          </div>
          <div>
            <span className="font-medium text-gray-500">PDF status</span>
            <div className="mt-1">
              <DocumentStatusBadge status={status} />
            </div>
          </div>
          <div>
            <span className="font-medium text-gray-500">Statistics</span>
            <p className="mt-0.5 text-gray-600">
              {charCount.toLocaleString()} characters · {wordCount.toLocaleString()}{' '}
              words · ~{pageEstimate} page{pageEstimate !== 1 ? 's' : ''}
            </p>
          </div>
          <div>
            <span className="font-medium text-gray-500">Content preview</span>
            <div className="mt-1">
              <p className="whitespace-pre-wrap break-words text-gray-600">
                {showFull ? doc.content ?? '' : preview}
              </p>
              {doc.content && doc.content.length > PREVIEW_LENGTH && (
                <Button
                  variant="secondary"
                  className="mt-2"
                  onClick={() => setShowFull((s) => !s)}
                >
                  {showFull ? 'Show less' : 'Show more'}
                </Button>
              )}
            </div>
            {doc.content && (
              <Button
                variant="secondary"
                className="mt-2"
                onClick={() => setShowContentModal(true)}
              >
                View full content
              </Button>
            )}
          </div>
        </div>
      </Card>

      {showContentModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Full document content"
        >
          <div className="flex h-full max-h-[90vh] w-full max-w-3xl flex-col rounded-lg border border-gray-200 bg-white shadow-lg">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
              <h3 className="text-lg font-medium">Full content</h3>
              <Button
                variant="secondary"
                onClick={() => setShowContentModal(false)}
              >
                Close
              </Button>
            </div>
            <textarea
              readOnly
              className="flex-1 resize-none border-0 p-4 font-mono text-sm focus:ring-0"
              value={doc.content ?? ''}
              aria-label="Full document content"
            />
          </div>
        </div>
      )}
    </>
  );
}
