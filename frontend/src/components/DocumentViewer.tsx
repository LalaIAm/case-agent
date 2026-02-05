/**
 * Main document viewing component: metadata sidebar, PDF preview, version history.
 */
import { useState, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Button } from './Button';
import { DocumentVersionHistory } from './DocumentVersionHistory';
import { DocumentStatusBadge } from './DocumentStatusBadge';
import type { GeneratedDocumentResponse } from '../services/documents';
import { formatDocumentType } from '../utils/documentUtils';
import { api } from '../services/api';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import '../styles/documentViewer.css';

// PDF.js worker for react-pdf
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const BASE = '/api/documents';

export interface DocumentViewerProps {
  documentId: string;
  documentType: string;
  version: number;
  generatedAt: string;
  hasPdf: boolean;
  content: string;
  caseId: string;
  document: GeneratedDocumentResponse;
  onRegenerate: () => void;
  onDownload: () => void;
  onClose: () => void;
  onSelectVersion?: (doc: GeneratedDocumentResponse) => void;
  onCompare?: (doc1: GeneratedDocumentResponse, doc2: GeneratedDocumentResponse) => void;
}

const MIN_SCALE = 0.5;
const MAX_SCALE = 2.5;
const SCALE_STEP = 0.25;

export function DocumentViewer({
  documentId,
  documentType,
  version,
  generatedAt,
  hasPdf,
  content,
  caseId,
  document: _doc,
  onRegenerate,
  onDownload,
  onClose,
  onSelectVersion,
  onCompare,
}: DocumentViewerProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.25);
  const [loadingPdf, setLoadingPdf] = useState(hasPdf);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (!hasPdf) {
      setLoadingPdf(false);
      setPdfUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    setPdfError(null);
    setLoadingPdf(true);
    api
      .get<Blob>(`${BASE}/generated/${documentId}/download`, {
        responseType: 'blob',
      })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        setPdfUrl(objectUrl);
      })
      .catch(() => {
        setPdfError('Failed to load PDF');
      })
      .finally(() => {
        setLoadingPdf(false);
      });
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, hasPdf]);

  const onDocumentLoadSuccess = useCallback(({ numPages: n }: { numPages: number }) => {
    setNumPages(n);
    setPageNumber(1);
  }, []);

  const zoomIn = () => setScale((s) => Math.min(MAX_SCALE, s + SCALE_STEP));
  const zoomOut = () => setScale((s) => Math.max(MIN_SCALE, s - SCALE_STEP));
  const fitWidth = () => setScale(1.25);
  const resetZoom = () => setScale(1);

  const goPrevPage = () => setPageNumber((p) => Math.max(1, p - 1));
  const goNextPage = () => setPageNumber((p) => Math.min(numPages ?? 1, p + 1));

  const handlePrint = () => window.print();

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') goPrevPage();
      if (e.key === 'ArrowRight') goNextPage();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, numPages]);

  const fileSizeEstimate = content.length * 2;

  return (
    <div
      className="document-viewer-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-viewer-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className={`document-viewer-container ${fullscreen ? 'fixed inset-4 m-0 max-h-none w-auto' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="no-print flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-3">
          <h2 id="document-viewer-title" className="text-lg font-medium text-gray-900">
            {formatDocumentType(documentType)} — v{version}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={onDownload} disabled={!hasPdf}>
              Download PDF
            </Button>
            <Button variant="primary" onClick={onRegenerate}>
              Regenerate Document
            </Button>
            <button
              type="button"
              onClick={() => setFullscreen((f) => !f)}
              className="rounded-md border border-gray-300 px-2 py-1 text-sm hover:bg-gray-50"
              aria-label={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            </button>
            <Button variant="secondary" onClick={handlePrint} disabled={!hasPdf}>
              Print
            </Button>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </header>

        <div className="flex flex-1 min-h-0 flex-col md:flex-row">
          {/* Left: metadata */}
          <aside className="no-print w-full border-b border-gray-200 bg-gray-50 p-4 md:w-64 md:border-b-0 md:border-r md:max-h-[70vh] md:overflow-y-auto">
            <div className="space-y-2 text-sm">
              <p><span className="font-medium text-gray-500">Version</span> v{version}</p>
              <p><span className="font-medium text-gray-500">Generated</span> {new Date(generatedAt).toLocaleString()}</p>
              <p>
                <span className="font-medium text-gray-500">Status</span>{' '}
                <DocumentStatusBadge status={hasPdf ? 'pdf_ready' : 'no_pdf'} />
              </p>
              <p>
                <span className="font-medium text-gray-500">Est. size</span>{' '}
                ~{(fileSizeEstimate / 1024).toFixed(1)} KB
              </p>
            </div>
          </aside>

          {/* Center: PDF preview */}
          <div className="flex flex-1 flex-col min-h-0">
            <div className="no-print flex flex-wrap items-center gap-2 border-b border-gray-200 bg-white px-2 py-2">
              <div className="document-zoom-controls">
                <button type="button" onClick={zoomOut} aria-label="Zoom out">−</button>
                <span className="min-w-[4rem] text-center text-sm">{Math.round(scale * 100)}%</span>
                <button type="button" onClick={zoomIn} aria-label="Zoom in">+</button>
                <button type="button" onClick={resetZoom} className="ml-1" aria-label="Reset zoom">100%</button>
                <button type="button" onClick={fitWidth} aria-label="Fit width">Fit width</button>
              </div>
              {numPages != null && (
                <div className="flex items-center gap-1">
                  <button type="button" onClick={goPrevPage} disabled={pageNumber <= 1} aria-label="Previous page">Prev</button>
                  <span className="text-sm">
                    Page <input
                      type="number"
                      min={1}
                      max={numPages}
                      value={pageNumber}
                      onChange={(e) => setPageNumber(Math.max(1, Math.min(numPages, parseInt(e.target.value, 10) || 1)))}
                      className="w-12 rounded border border-gray-300 px-1 text-center"
                      aria-label="Page number"
                    /> of {numPages}
                  </span>
                  <button type="button" onClick={goNextPage} disabled={pageNumber >= numPages} aria-label="Next page">Next</button>
                </div>
              )}
            </div>
            <div className="pdf-preview-wrapper flex-1">
              {loadingPdf && (
                <div className="pdf-loading-skeleton" role="status" aria-label="Loading PDF" />
              )}
              {pdfError && (
                <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">
                  {pdfError}. You can still download or regenerate the document.
                </div>
              )}
              {!loadingPdf && pdfUrl && !pdfError && (
                <Document
                  file={pdfUrl}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={() => setPdfError('Failed to render PDF')}
                  loading=""
                >
                  <Page
                    pageNumber={pageNumber}
                    scale={scale}
                    renderTextLayer
                    renderAnnotationLayer
                  />
                </Document>
              )}
              {!hasPdf && !loadingPdf && (
                <div className="rounded border border-amber-200 bg-amber-50 p-4 text-amber-800">
                  PDF not generated yet. Use &quot;Generate PDF&quot; from the list or regenerate this document.
                </div>
              )}
            </div>
          </div>

          {/* Right: version history */}
          <aside className="no-print w-full border-t border-gray-200 bg-gray-50 p-4 md:w-56 md:border-t-0 md:border-l md:max-h-[70vh] md:overflow-y-auto">
            <DocumentVersionHistory
              caseId={caseId}
              documentType={documentType}
              currentVersion={version}
              currentDocumentId={documentId}
              onSelectVersion={onSelectVersion}
              onCompare={onCompare}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
