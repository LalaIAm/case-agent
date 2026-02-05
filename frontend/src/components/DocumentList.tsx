/**
 * Grid/list of generated documents with sorting, filtering, and actions.
 */
import { useState, useMemo } from 'react';
import { Button } from './Button';
import { DocumentStatusBadge, type DocumentStatus } from './DocumentStatusBadge';
import type { GeneratedDocumentResponse } from '../services/documents';
import {
  formatDocumentType,
  formatGeneratedDate,
  getDocumentTypeIcon,
  getDocumentTypeColor,
  getVersionBadgeColor,
} from '../utils/documentUtils';

export type SortField = 'date' | 'type' | 'version';
export type SortOrder = 'asc' | 'desc';

export interface DocumentListProps {
  documents: GeneratedDocumentResponse[];
  onViewDocument: (doc: GeneratedDocumentResponse) => void;
  onGeneratePdf: (doc: GeneratedDocumentResponse) => void;
  onDownload: (doc: GeneratedDocumentResponse) => void;
  onRegenerate: (doc: GeneratedDocumentResponse) => void;
  onDelete?: (doc: GeneratedDocumentResponse) => void;
  generatingPdfId: string | null;
}

export function DocumentList({
  documents,
  onViewDocument,
  onGeneratePdf,
  onDownload,
  onRegenerate,
  onDelete,
  generatingPdfId,
}: DocumentListProps) {
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filterType, setFilterType] = useState<string>('');
  const [filterHasPdf, setFilterHasPdf] = useState<'all' | 'yes' | 'no'>('all');

  const filteredAndSorted = useMemo(() => {
    let list = [...documents];
    if (filterType) {
      list = list.filter((d) => d.document_type === filterType);
    }
    if (filterHasPdf === 'yes') list = list.filter((d) => d.has_pdf);
    if (filterHasPdf === 'no') list = list.filter((d) => !d.has_pdf);
    list.sort((a, b) => {
      let cmp = 0;
      if (sortBy === 'date') {
        cmp = new Date(a.generated_at).getTime() - new Date(b.generated_at).getTime();
      } else if (sortBy === 'type') {
        cmp = a.document_type.localeCompare(b.document_type);
      } else {
        cmp = a.version - b.version;
      }
      return sortOrder === 'desc' ? -cmp : cmp;
    });
    return list;
  }, [documents, filterType, filterHasPdf, sortBy, sortOrder]);

  const types = useMemo(() => {
    const set = new Set(documents.map((d) => d.document_type));
    return Array.from(set);
  }, [documents]);

  if (documents.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
        <p className="text-gray-500">
          No generated documents yet. Run the drafting agent first to generate documents.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">Sort by</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            aria-label="Sort by"
          >
            <option value="date">Date</option>
            <option value="type">Type</option>
            <option value="version">Version</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
          className="text-sm text-blue-600 hover:underline"
          aria-label={`Sort ${sortOrder === 'desc' ? 'ascending' : 'descending'}`}
        >
          {sortOrder === 'desc' ? 'Newest first' : 'Oldest first'}
        </button>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">Type</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            aria-label="Filter by type"
          >
            <option value="">All</option>
            {types.map((t) => (
              <option key={t} value={t}>{formatDocumentType(t)}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">PDF</span>
          <select
            value={filterHasPdf}
            onChange={(e) => setFilterHasPdf(e.target.value as 'all' | 'yes' | 'no')}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            aria-label="Filter by PDF status"
          >
            <option value="all">All</option>
            <option value="yes">PDF ready</option>
            <option value="no">No PDF</option>
          </select>
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-200 text-sm">
          <thead>
            <tr className="bg-gray-50">
              <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-700">Type</th>
              <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-700">Version</th>
              <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-700">Generated</th>
              <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-700">Status</th>
              <th className="border border-gray-200 px-3 py-2 text-right font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSorted.map((doc) => {
              const status: DocumentStatus = generatingPdfId === doc.id
                ? 'generating'
                : doc.has_pdf
                  ? 'pdf_ready'
                  : 'no_pdf';
              return (
                <tr key={doc.id} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="border border-gray-200 px-3 py-2">
                    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${getDocumentTypeColor(doc.document_type)}`}>
                      {getDocumentTypeIcon(doc.document_type)} {formatDocumentType(doc.document_type)}
                    </span>
                  </td>
                  <td className="border border-gray-200 px-3 py-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${getVersionBadgeColor(doc.version)}`}>
                      v{doc.version}
                    </span>
                  </td>
                  <td className="border border-gray-200 px-3 py-2 text-gray-600">
                    {formatGeneratedDate(doc.generated_at)}
                  </td>
                  <td className="border border-gray-200 px-3 py-2">
                    <DocumentStatusBadge status={status} />
                  </td>
                  <td className="border border-gray-200 px-3 py-2 text-right">
                    <div className="flex flex-wrap justify-end gap-1">
                      <Button variant="secondary" className="!py-1 !text-xs" onClick={() => onViewDocument(doc)}>
                        View
                      </Button>
                      {doc.has_pdf ? (
                        <Button variant="secondary" className="!py-1 !text-xs" onClick={() => onDownload(doc)}>
                          Download
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          className="!py-1 !text-xs"
                          onClick={() => onGeneratePdf(doc)}
                          disabled={generatingPdfId === doc.id}
                        >
                          {generatingPdfId === doc.id ? 'Generating…' : 'Generate PDF'}
                        </Button>
                      )}
                      <Button variant="secondary" className="!py-1 !text-xs" onClick={() => onRegenerate(doc)}>
                        Regenerate
                      </Button>
                      {onDelete && (
                        <Button variant="danger" className="!py-1 !text-xs" onClick={() => onDelete(doc)}>
                          Delete
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
