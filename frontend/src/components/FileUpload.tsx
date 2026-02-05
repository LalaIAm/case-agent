/**
 * Drag-and-drop file upload for case documents with progress and error handling.
 */
import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  uploadDocument,
  getDocuments,
  deleteDocument,
  type DocumentResponse,
} from '../services/documents';
import { ProgressBar } from './ProgressBar';
import { Button } from './Button';

const MAX_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPT = {
  'application/pdf': ['.pdf'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
} as const;

interface FileUploadProps {
  caseId: string;
  onUploadComplete?: (document: DocumentResponse) => void;
}

export function FileUpload({ caseId, onUploadComplete }: FileUploadProps) {
  const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(
    () => new Map()
  );
  const [uploadErrors, setUploadErrors] = useState<Map<string, string>>(
    () => new Map()
  );
  const [uploadedFiles, setUploadedFiles] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      const list = await getDocuments(caseId);
      setUploadedFiles(list);
    } catch (e) {
      console.error('Failed to load documents', e);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleUpload = useCallback(
    async (file: File) => {
      const key = `${file.name}-${Date.now()}`;
      setUploadProgress((prev) => new Map(prev).set(key, 0));
      setUploadErrors((prev) => {
        const next = new Map(prev);
        next.delete(file.name);
        return next;
      });
      try {
        const doc = await uploadDocument(caseId, file, (progress) => {
          setUploadProgress((prev) => new Map(prev).set(key, progress));
        });
        setUploadProgress((prev) => {
          const next = new Map(prev);
          next.delete(key);
          return next;
        });
        setUploadedFiles((prev) => [doc, ...prev]);
        onUploadComplete?.(doc);
      } catch (err: unknown) {
        const message =
          err && typeof err === 'object' && 'response' in err
            ? String((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Upload failed')
            : err instanceof Error
              ? err.message
              : 'Upload failed';
        setUploadProgress((prev) => {
          const next = new Map(prev);
          next.delete(key);
          return next;
        });
        setUploadErrors((prev) => new Map(prev).set(key, message));
      }
    },
    [caseId, onUploadComplete]
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => handleUpload(file));
    },
    [handleUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    multiple: true,
    onDropRejected: (rejections) => {
      rejections.forEach(({ file, errors }) => {
        const msg = errors.map((e) => e.message).join('; ');
        setUploadErrors((prev) =>
          new Map(prev).set(file.name, msg || 'File rejected')
        );
      });
    },
  });

  const handleRetry = useCallback(
    (key: string) => {
      setRetrying(key);
      setUploadErrors((prev) => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
      setRetrying(null);
      // User can drag the same file again to retry; we don't have the File object stored
    },
    []
  );

  const handleDelete = useCallback(
    async (documentId: string) => {
      try {
        await deleteDocument(documentId);
        setUploadedFiles((prev) => prev.filter((d) => d.id !== documentId));
      } catch (e) {
        console.error('Delete failed', e);
      }
    },
    []
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      dateStyle: 'short',
      timeStyle: 'short',
    });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-gray-500 dark:hover:bg-gray-700/50'
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-center text-sm text-gray-600 dark:text-gray-400">
          Drag & drop files here, or click to select
        </p>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
          PDF, PNG, JPG up to {MAX_SIZE / (1024 * 1024)} MB
        </p>
      </div>

      {uploadProgress.size > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Uploading
          </p>
          {Array.from(uploadProgress.entries()).map(([key, progress]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-sm text-gray-600 dark:text-gray-400">
                {key.replace(/-\d+$/, '')}
              </span>
              <div className="w-32 flex-shrink-0">
                <ProgressBar progress={progress} variant="primary" />
              </div>
            </div>
          ))}
        </div>
      )}

      {uploadErrors.size > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">
            Errors
          </p>
          {Array.from(uploadErrors.entries()).map(([key, message]) => (
            <div
              key={key}
              className="flex items-center justify-between gap-2 rounded-md bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300"
            >
              <span className="min-w-0 flex-1 truncate">
                {key.replace(/-\d+$/, '')}: {message}
              </span>
              <Button
                type="button"
                variant="secondary"
                onClick={() => handleRetry(key)}
                disabled={retrying === key}
              >
                Retry
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Documents
        </p>
        {loading ? (
          <p className="text-sm text-gray-500 dark:text-gray-500">
            Loading…
          </p>
        ) : uploadedFiles.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-500">
            No documents yet
          </p>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-md border border-gray-200 dark:divide-gray-700 dark:border-gray-700">
            {uploadedFiles.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-2 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <span className="truncate font-medium text-gray-900 dark:text-gray-100">
                    {doc.filename}
                  </span>
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-500">
                    {formatSize(doc.file_size)} · {formatDate(doc.uploaded_at)}
                  </span>
                  <span className="ml-2">
                    {doc.processed ? (
                      <span className="inline-flex items-center rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-800 dark:bg-green-900/30 dark:text-green-300">
                        Processed
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                        Processing…
                      </span>
                    )}
                  </span>
                </div>
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => handleDelete(doc.id)}
                  className="flex-shrink-0"
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
