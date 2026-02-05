/**
 * Case types matching backend Pydantic schemas.
 */
export interface Case {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface CaseCreate {
  title: string;
  description?: string | null;
}

export interface CaseUpdate {
  title?: string;
  description?: string | null;
  status?: string;
}

export interface CaseSession {
  id: string;
  case_id: string;
  session_number: number;
  started_at: string;
  completed_at: string | null;
  status: string;
}

export interface DocumentInCase {
  id: string;
  case_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  processed: boolean;
}

export interface CaseWithDetails extends Case {
  sessions: CaseSession[];
  documents: DocumentInCase[];
}
