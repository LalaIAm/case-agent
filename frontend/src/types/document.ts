/**
 * Document types matching backend DocumentRead and upload flow.
 */
export interface Document {
  id: string;
  case_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  processed: boolean;
}

export interface UploadProgress {
  filename: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}
