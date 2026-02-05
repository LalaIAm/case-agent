/**
 * Case detail page with tabs: Overview, Documents, Agent Status, Generated Documents.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '../components/Header';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { FileUpload } from '../components/FileUpload';
import {
  getCaseDetails,
  updateCase,
  deleteCase,
  createSession,
} from '../services/cases';
import {
  getGeneratedDocuments,
  generateDocumentPdf,
  downloadGeneratedDocument,
  regenerateDocument,
  deleteGeneratedDocument,
  downloadDocument,
  deleteDocument,
  type GeneratedDocumentResponse,
} from '../services/documents';
import { getAgentStatus, executeAgents } from '../services/agents';
import { AdvisorTab } from '../components/AdvisorTab';
import { AgentStatus } from '../components/AgentStatus';
import { DocumentList } from '../components/DocumentList';
import { DocumentViewer } from '../components/DocumentViewer';
import { DocumentComparison } from '../components/DocumentComparison';
import { ConfirmDialog } from '../components/ConfirmDialog';
import type { CaseWithDetails, CaseSession } from '../types/case';

type TabId = 'overview' | 'documents' | 'agent-status' | 'advisor' | 'generated';

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
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function formatDocType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseDetails, setCaseDetails] = useState<CaseWithDetails | null>(null);
  const [sessions, setSessions] = useState<CaseSession[]>([]);
  const [initialAgentStatus, setInitialAgentStatus] = useState<{
    progress_percentage: number;
    workflow_status: string;
    current_agent: string | null;
  } | null>(null);
  const [generatedDocs, setGeneratedDocs] = useState<GeneratedDocumentResponse[]>(
    []
  );
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState(false);
  const [editDesc, setEditDesc] = useState(false);
  const [titleValue, setTitleValue] = useState('');
  const [titleError, setTitleError] = useState<string | null>(null);
  const [descValue, setDescValue] = useState('');
  const [generatingPdf, setGeneratingPdf] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<GeneratedDocumentResponse | null>(null);
  const [comparingDocuments, setComparingDocuments] = useState<
    [GeneratedDocumentResponse, GeneratedDocumentResponse] | null
  >(null);
  const [confirmState, setConfirmState] = useState<{
    open: boolean;
    title: string;
    message: string;
    confirmText: string;
    variant: 'danger' | 'warning' | 'info';
    onConfirm: () => void;
  } | null>(null);

  const loadCase = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const details = await getCaseDetails(caseId);
      setCaseDetails(details);
      setTitleValue(details.title);
      setDescValue(details.description ?? '');
      setSessions(details.sessions);
    } catch (err: unknown) {
      const status =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { status?: number } }).response?.status
          : 0;
      if (status === 403) {
        navigate('/', { replace: true });
        return;
      }
      if (status === 404) {
        setError('Case not found');
        return;
      }
      setError(
        err instanceof Error ? err.message : 'Unable to load case'
      );
    } finally {
      setLoading(false);
    }
  }, [caseId, navigate]);

  const loadInitialAgentStatus = useCallback(async () => {
    if (!caseId) return;
    try {
      const status = await getAgentStatus(caseId);
      setInitialAgentStatus({
        progress_percentage: status.progress_percentage,
        workflow_status: status.workflow_status,
        current_agent: status.current_agent,
      });
    } catch {
      setInitialAgentStatus(null);
    }
  }, [caseId]);

  const loadGeneratedDocs = useCallback(async () => {
    if (!caseId) return;
    try {
      const list = await getGeneratedDocuments(caseId);
      setGeneratedDocs(list);
    } catch {
      setGeneratedDocs([]);
    }
  }, [caseId]);

  useEffect(() => {
    loadCase();
  }, [loadCase]);

  useEffect(() => {
    if (activeTab === 'agent-status') loadInitialAgentStatus();
    if (activeTab === 'generated') loadGeneratedDocs();
  }, [activeTab, loadInitialAgentStatus, loadGeneratedDocs]);

  async function handleSaveTitle() {
    setTitleError(null);
    if (!caseId || !caseDetails) {
      setEditTitle(false);
      return;
    }
    const trimmed = titleValue.trim();
    if (trimmed === caseDetails.title) {
      setEditTitle(false);
      return;
    }
    if (trimmed.length === 0) {
      setTitleError('Title cannot be empty.');
      return;
    }
    if (trimmed.length > 500) {
      setTitleError('Title must be 500 characters or less.');
      return;
    }
    try {
      const updated = await updateCase(caseId, { title: trimmed });
      setCaseDetails((prev) => (prev ? { ...prev, ...updated } : null));
      setTitleValue(trimmed);
      setEditTitle(false);
    } catch (err: unknown) {
      const msg =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data
          ? typeof (err.response.data as { detail: unknown }).detail === 'string'
            ? (err.response.data as { detail: string }).detail
            : Array.isArray((err.response.data as { detail: unknown }).detail)
              ? (err.response.data as { detail: string[] }).detail.join('. ')
              : 'Update failed. Please try again.'
          : err instanceof Error
            ? err.message
            : 'Update failed. Please try again.';
      setTitleError(msg);
    }
  }

  async function handleSaveDesc() {
    if (!caseId || !caseDetails) {
      setEditDesc(false);
      return;
    }
    try {
      const updated = await updateCase(caseId, {
        description: descValue.trim() || null,
      });
      setCaseDetails((prev) => (prev ? { ...prev, ...updated } : null));
      setEditDesc(false);
    } catch {
      // Keep edit mode
    }
  }

  async function handleDelete() {
    if (!caseId || !window.confirm('Delete this case? This cannot be undone.'))
      return;
    try {
      await deleteCase(caseId);
      navigate('/', { replace: true });
    } catch {
      setError('Failed to delete case');
    }
  }

  async function handleNewSession() {
    if (!caseId) return;
    try {
      const session = await createSession(caseId);
      setSessions((prev) => [...prev, session]);
      await loadCase();
      if (activeTab === 'generated') loadGeneratedDocs();
    } catch {
      setError('Failed to create session');
    }
  }

  async function handleRunAgents() {
    if (!caseId) return;
    try {
      await executeAgents(caseId);
    } catch {
      setError('Failed to start agents');
    }
  }

  async function handleGeneratePdf(doc: GeneratedDocumentResponse) {
    setGeneratingPdf(doc.id);
    try {
      setError(null);
      const updated = await generateDocumentPdf(doc.id);
      setGeneratedDocs((prev) =>
        prev.map((d) => (d.id === doc.id ? { ...d, ...updated } : d))
      );
      setSelectedDocument((prev) =>
        prev?.id === doc.id
          ? {
              ...prev,
              ...updated,
              has_pdf: updated.file_path != null || updated.pdf_generated,
            }
          : prev
      );
    } catch {
      setError('Failed to generate PDF');
    } finally {
      setGeneratingPdf(null);
    }
  }

  async function handleDownload(doc: GeneratedDocumentResponse) {
    try {
      setError(null);
      const filename = `${doc.document_type}_v${doc.version}.pdf`;
      await downloadGeneratedDocument(doc.id, filename);
    } catch {
      setError('Failed to download PDF');
    }
  }

  function handleViewDocument(doc: GeneratedDocumentResponse) {
    setSelectedDocument(doc);
  }

  function handleCompareVersions(
    doc1: GeneratedDocumentResponse,
    doc2: GeneratedDocumentResponse
  ) {
    setComparingDocuments([doc1, doc2]);
    setSelectedDocument(null);
  }

  function handleRegenerateClick(doc: GeneratedDocumentResponse) {
    setConfirmState({
      open: true,
      title: 'Regenerate document',
      message: `This will create a new version (v${doc.version + 1}) of "${formatDocType(doc.document_type)}" and generate its PDF. Continue?`,
      confirmText: 'Regenerate',
      variant: 'warning',
      onConfirm: () => {
        setConfirmState(null);
        handleRegenerateDocument(doc.id);
      },
    });
  }

  async function handleRegenerateDocument(documentId: string) {
    if (!caseId) return;
    try {
      setError(null);
      const newDoc = await regenerateDocument(documentId);
      await loadGeneratedDocs();
      setSelectedDocument((prev) =>
        prev?.id === documentId ? newDoc : prev
      );
    } catch {
      setError('Failed to regenerate document');
    }
  }

  function handleDeleteGeneratedDocClick(doc: GeneratedDocumentResponse) {
    setConfirmState({
      open: true,
      title: 'Delete document',
      message: `Delete "${formatDocType(doc.document_type)}" v${doc.version}? This cannot be undone.`,
      confirmText: 'Delete',
      variant: 'danger',
      onConfirm: () => {
        setConfirmState(null);
        handleDeleteGeneratedDoc(doc.id);
      },
    });
  }

  async function handleDeleteGeneratedDoc(documentId: string) {
    if (!caseId) return;
    try {
      setError(null);
      await deleteGeneratedDocument(documentId);
      await loadGeneratedDocs();
      if (selectedDocument?.id === documentId) setSelectedDocument(null);
    } catch {
      setError('Failed to delete document');
    }
  }

  async function handleDownloadUploadedDoc(doc: {
    id: string;
    filename: string;
  }) {
    try {
      setError(null);
      await downloadDocument(doc.id, doc.filename);
    } catch {
      setError('Failed to download document');
    }
  }

  async function handleDeleteUploadedDoc(doc: { id: string }) {
    try {
      setError(null);
      setDeletingDocId(doc.id);
      await deleteDocument(doc.id);
      await loadCase();
      if (activeTab === 'generated') loadGeneratedDocs();
    } catch {
      setError('Failed to delete document');
    } finally {
      setDeletingDocId(null);
    }
  }

  if (!caseId) return null;

  if (loading && !caseDetails) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="flex items-center justify-center py-24">
          <LoadingSpinner size="lg" />
        </main>
      </div>
    );
  }

  if (error && !caseDetails) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <p className="text-red-600">{error}</p>
          <Button variant="secondary" onClick={() => navigate('/')} className="mt-4">
            Back to Dashboard
          </Button>
        </main>
      </div>
    );
  }

  if (!caseDetails) return null;

  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'documents', label: 'Documents' },
    { id: 'agent-status', label: 'Agent Status' },
    { id: 'advisor', label: 'Case Advisor' },
    { id: 'generated', label: 'Generated Documents' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <nav className="mb-4 text-sm text-gray-500">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="hover:text-gray-700"
          >
            Dashboard
          </button>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{caseDetails.title}</span>
        </nav>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            {editTitle ? (
              <div className="flex flex-col gap-1">
                <input
                  type="text"
                  value={titleValue}
                  onChange={(e) => setTitleValue(e.target.value)}
                  onBlur={handleSaveTitle}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                  className="rounded border border-gray-300 px-2 py-1 text-xl font-semibold"
                  autoFocus
                  aria-label="Case title"
                  {...(titleError ? { 'aria-invalid': 'true' as const } : {})}
                  aria-describedby={titleError ? 'title-error' : undefined}
                />
                {titleError && (
                  <p id="title-error" className="text-sm text-red-600" role="alert">
                    {titleError}
                  </p>
                )}
              </div>
            ) : (
              <h1
                className="cursor-pointer text-2xl font-semibold text-gray-900 hover:text-blue-600"
                onClick={() => {
                  setTitleError(null);
                  setEditTitle(true);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setTitleError(null);
                    setEditTitle(true);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                {caseDetails.title}
              </h1>
            )}
            <div className="mt-1 flex items-center gap-2">
              <Badge variant={getBadgeVariant(caseDetails.status)}>
                {caseDetails.status}
              </Badge>
              <span className="text-sm text-gray-500">
                Created {formatDate(caseDetails.created_at)}
              </span>
              {caseDetails.updated_at && (
                <span className="text-sm text-gray-500">
                  · Updated {formatDate(caseDetails.updated_at)}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleNewSession}>
              New Session
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <div className="mb-6 border-b border-gray-200">
          <div className="flex gap-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`border-b-2 px-4 py-2 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <Card title="Description">
              {editDesc ? (
                <div className="space-y-2">
                  <textarea
                    value={descValue}
                    onChange={(e) => setDescValue(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-gray-300 px-3 py-2"
                    aria-label="Case description"
                  />
                  <div className="flex gap-2">
                    <Button variant="primary" onClick={handleSaveDesc}>
                      Save
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setDescValue(caseDetails.description ?? '');
                        setEditDesc(false);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-gray-600">
                    {caseDetails.description || 'No description.'}
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => setEditDesc(true)}
                    className="mt-2"
                  >
                    Edit
                  </Button>
                </div>
              )}
            </Card>
            <Card title="Sessions">
              <ul className="space-y-2">
                {sessions.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded border border-gray-200 px-4 py-2"
                  >
                    <span>
                      Session {s.session_number} · {s.status} ·{' '}
                      {formatDate(s.started_at)}
                    </span>
                  </li>
                ))}
              </ul>
              <Button
                variant="secondary"
                onClick={handleNewSession}
                className="mt-4"
              >
                Start New Session
              </Button>
            </Card>
          </div>
        )}

        {activeTab === 'documents' && (
          <Card title="Documents">
            <FileUpload caseId={caseId} onUploadComplete={loadCase} />
            {caseDetails.documents.length > 0 ? (
              <ul className="mt-6 space-y-2" aria-label="Uploaded documents">
                {caseDetails.documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex flex-wrap items-center justify-between gap-4 rounded border border-gray-200 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <span className="font-medium text-gray-900">
                        {doc.filename}
                      </span>
                      <span className="ml-2 text-sm text-gray-500">
                        {formatFileSize(doc.file_size)} ·{' '}
                        {formatDate(doc.uploaded_at)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => handleDownloadUploadedDoc(doc)}
                      >
                        Download
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => handleDeleteUploadedDoc(doc)}
                        disabled={deletingDocId === doc.id}
                      >
                        {deletingDocId === doc.id ? 'Deleting…' : 'Delete'}
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-6 text-sm text-gray-500">
                No documents uploaded yet. Add files above.
              </p>
            )}
          </Card>
        )}

        {activeTab === 'agent-status' && (
          <AgentStatus
            caseId={caseId}
            initialStatus={initialAgentStatus ?? undefined}
            onRunAgents={handleRunAgents}
          />
        )}

        {activeTab === 'advisor' && <AdvisorTab caseId={caseId} />}

        {activeTab === 'generated' && (
          <Card title="Generated Documents">
            <DocumentList
              documents={generatedDocs}
              onViewDocument={handleViewDocument}
              onGeneratePdf={handleGeneratePdf}
              onDownload={handleDownload}
              onRegenerate={handleRegenerateClick}
              onDelete={handleDeleteGeneratedDocClick}
              generatingPdfId={generatingPdf}
            />
          </Card>
        )}

        {selectedDocument && (
          <DocumentViewer
            documentId={selectedDocument.id}
            documentType={selectedDocument.document_type}
            version={selectedDocument.version}
            generatedAt={selectedDocument.generated_at}
            hasPdf={selectedDocument.has_pdf ?? false}
            content={selectedDocument.content ?? ''}
            caseId={caseId}
            document={selectedDocument}
            onRegenerate={() => handleRegenerateClick(selectedDocument)}
            onDownload={() => handleDownload(selectedDocument)}
            onClose={() => setSelectedDocument(null)}
            onSelectVersion={(doc) => setSelectedDocument(doc)}
            onCompare={handleCompareVersions}
          />
        )}

        {comparingDocuments && (
          <DocumentComparison
            documents={comparingDocuments}
            onClose={() => setComparingDocuments(null)}
          />
        )}

        {confirmState && (
          <ConfirmDialog
            open={confirmState.open}
            title={confirmState.title}
            message={confirmState.message}
            confirmText={confirmState.confirmText}
            cancelText="Cancel"
            variant={confirmState.variant}
            onConfirm={confirmState.onConfirm}
            onCancel={() => setConfirmState(null)}
          />
        )}
      </main>
    </div>
  );
}
