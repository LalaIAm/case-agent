/**
 * Case management API.
 */
import { api } from './api';
import type {
  Case,
  CaseCreate,
  CaseUpdate,
  CaseWithDetails,
  CaseSession,
} from '../types/case';

const BASE = '/api/cases';

export async function createCase(data: CaseCreate): Promise<Case> {
  const { data: caseData } = await api.post<Case>(BASE, data);
  return caseData;
}

export async function getCases(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<Case[]> {
  const { data } = await api.get<Case[]>(BASE, { params });
  return data;
}

export async function getCase(caseId: string): Promise<Case> {
  const { data } = await api.get<Case>(`${BASE}/${caseId}`);
  return data;
}

export async function getCaseDetails(caseId: string): Promise<CaseWithDetails> {
  const { data } = await api.get<CaseWithDetails>(`${BASE}/${caseId}/details`);
  return data;
}

export async function updateCase(
  caseId: string,
  data: CaseUpdate
): Promise<Case> {
  const { data: updated } = await api.put<Case>(`${BASE}/${caseId}`, data);
  return updated;
}

export async function deleteCase(caseId: string): Promise<void> {
  await api.delete(`${BASE}/${caseId}`);
}

export async function getCaseSessions(
  caseId: string
): Promise<CaseSession[]> {
  const { data } = await api.get<CaseSession[]>(`${BASE}/${caseId}/sessions`);
  return data;
}

export async function createSession(
  caseId: string
): Promise<CaseSession> {
  const { data } = await api.post<CaseSession>(`${BASE}/${caseId}/sessions`);
  return data;
}
