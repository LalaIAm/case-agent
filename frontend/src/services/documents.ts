/**
 * Document upload and management API.
 */
import { api } from './api';

const BASE = '/api/documents';

export interface DocumentResponse {
  id: string;
  case_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  processed: boolean;
}

export async function uploadDocument(
  caseId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<DocumentResponse>(
    `${BASE}/cases/${caseId}/documents/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event) => {
        if (event.total != null && event.total > 0 && onProgress) {
          const progress = Math.round((event.loaded * 100) / event.total);
          onProgress(progress);
        }
      },
    }
  );
  return data;
}

export async function getDocuments(caseId: string): Promise<DocumentResponse[]> {
  const { data } = await api.get<DocumentResponse[]>(
    `${BASE}/cases/${caseId}/documents`
  );
  return data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`${BASE}/documents/${documentId}`);
}

export async function downloadDocument(
  documentId: string,
  filename: string
): Promise<void> {
  const { data } = await api.get<Blob>(
    `${BASE}/documents/${documentId}/download`,
    { responseType: 'blob' }
  );
  const url = window.URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'document';
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}

export interface GeneratedDocumentResponse {
  id: string;
  case_id: string;
  document_type: string;
  content: string;
  file_path: string | null;
  version: number;
  generated_at: string;
  has_pdf?: boolean;
  download_url?: string | null;
}

export async function getGeneratedDocuments(
  caseId: string
): Promise<GeneratedDocumentResponse[]> {
  const { data } = await api.get<GeneratedDocumentResponse[]>(
    `${BASE}/cases/${caseId}/generated`
  );
  return data;
}

export interface DocumentGenerationResponse extends GeneratedDocumentResponse {
  pdf_generated: boolean;
  generation_time_ms?: number;
}

export async function generateDocumentPdf(
  documentId: string
): Promise<DocumentGenerationResponse> {
  const { data } = await api.post<DocumentGenerationResponse>(
    `${BASE}/generated/${documentId}/generate-pdf`
  );
  return data;
}

export async function downloadGeneratedDocument(
  documentId: string,
  filename: string
): Promise<void> {
  const { data } = await api.get<Blob>(
    `${BASE}/generated/${documentId}/download`,
    { responseType: 'blob' }
  );
  const url = window.URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'document.pdf';
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}
