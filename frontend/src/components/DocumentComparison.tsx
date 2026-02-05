/**
 * Side-by-side comparison of two document versions with PDF preview and text diff.
 */
import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Button } from './Button';
import type { GeneratedDocumentResponse } from '../services/documents';
import { formatDocumentType } from '../utils/documentUtils';
import { api } from '../services/api';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import '../styles/documentViewer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const BASE = '/api/documents';

/** Simple character-level diff: returns HTML-safe spans for left and right. */
function simpleTextDiff(left: string, right: string): { leftHtml: string; rightHtml: string } {
  const l = left || '';
  const r = right || '';
  const maxLen = Math.max(l.length, r.length);
  let leftHtml = '';
  let rightHtml = '';
  for (let i = 0; i < maxLen; i++) {
    const a = l[i] ?? '';
    const b = r[i] ?? '';
    if (a === b) {
      leftHtml += escapeHtml(a);
      rightHtml += escapeHtml(b);
    } else {
      if (a) leftHtml += `<span class="bg-red-200">${escapeHtml(a)}</span>`;
      if (b) rightHtml += `<span class="bg-green-200">${escapeHtml(b)}</span>`;
    }
  }
  return { leftHtml, rightHtml };
}

function escapeHtml(s: string): string {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

export interface DocumentComparisonProps {
  documents: [GeneratedDocumentResponse, GeneratedDocumentResponse];
  onClose: () => void;
}

export function DocumentComparison({ documents: [docA, docB], onClose }: DocumentComparisonProps) {
  const [pdfUrlA, setPdfUrlA] = useState<string | null>(null);
  const [pdfUrlB, setPdfUrlB] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'pdf' | 'text'>('pdf');
  const [syncScroll, setSyncScroll] = useState(true);

  useEffect(() => {
    let urlA: string | null = null;
    let urlB: string | null = null;
    if (docA.has_pdf) {
      api.get<Blob>(`${BASE}/generated/${docA.id}/download`, { responseType: 'blob' })
        .then(({ data }) => {
          urlA = URL.createObjectURL(data);
          setPdfUrlA(urlA);
        });
    }
    if (docB.has_pdf) {
      api.get<Blob>(`${BASE}/generated/${docB.id}/download`, { responseType: 'blob' })
        .then(({ data }) => {
          urlB = URL.createObjectURL(data);
          setPdfUrlB(urlB);
        });
    }
    return () => {
      if (urlA) URL.revokeObjectURL(urlA);
      if (urlB) URL.revokeObjectURL(urlB);
    };
  }, [docA.id, docB.id, docA.has_pdf, docB.has_pdf]);

  const bothHavePdf = docA.has_pdf && docB.has_pdf;
  const { leftHtml, rightHtml } = simpleTextDiff(docA.content ?? '', docB.content ?? '');

  return (
    <div
      className="document-viewer-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Compare document versions"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="document-viewer-container max-h-[95vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="no-print flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-4 py-3">
          <h2 className="text-lg font-medium">Compare versions</h2>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="comparison-view"
                checked={viewMode === 'pdf'}
                onChange={() => setViewMode('pdf')}
                disabled={!bothHavePdf}
              />
              PDF
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="comparison-view"
                checked={viewMode === 'text'}
                onChange={() => setViewMode('text')}
              />
              Text diff
            </label>
            {viewMode === 'pdf' && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={syncScroll}
                  onChange={(e) => setSyncScroll(e.target.checked)}
                />
                Sync scroll
              </label>
            )}
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </div>
        </header>

        <div className="document-comparison-panels flex-1 overflow-auto p-4">
          <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
            <div className="bg-white px-3 py-2 border-b border-gray-200 text-sm font-medium">
              {formatDocumentType(docA.document_type)} v{docA.version} · {new Date(docA.generated_at).toLocaleString()}
            </div>
            <div className="flex-1 min-h-[400px] overflow-auto p-2">
              {viewMode === 'pdf' && docA.has_pdf && pdfUrlA && (
                <Document file={pdfUrlA}>
                  <Page pageNumber={1} scale={1} />
                </Document>
              )}
              {viewMode === 'text' && (
                <pre className="whitespace-pre-wrap break-words font-mono text-xs p-2" dangerouslySetInnerHTML={{ __html: leftHtml }} />
              )}
              {viewMode === 'pdf' && !docA.has_pdf && (
                <p className="text-gray-500 p-4">PDF not generated for this version.</p>
              )}
            </div>
          </div>
          <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
            <div className="bg-white px-3 py-2 border-b border-gray-200 text-sm font-medium">
              {formatDocumentType(docB.document_type)} v{docB.version} · {new Date(docB.generated_at).toLocaleString()}
            </div>
            <div className="flex-1 min-h-[400px] overflow-auto p-2">
              {viewMode === 'pdf' && docB.has_pdf && pdfUrlB && (
                <Document file={pdfUrlB}>
                  <Page pageNumber={1} scale={1} />
                </Document>
              )}
              {viewMode === 'text' && (
                <pre className="whitespace-pre-wrap break-words font-mono text-xs p-2" dangerouslySetInnerHTML={{ __html: rightHtml }} />
              )}
              {viewMode === 'pdf' && !docB.has_pdf && (
                <p className="text-gray-500 p-4">PDF not generated for this version.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
