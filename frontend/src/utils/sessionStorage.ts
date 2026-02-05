/**
 * Persist active session selection per case in localStorage.
 */

const KEY_PREFIX = 'case_active_session_';

export function getActiveSessionForCase(caseId: string): string | null {
  try {
    return localStorage.getItem(KEY_PREFIX + caseId);
  } catch {
    return null;
  }
}

export function setActiveSessionForCase(caseId: string, sessionId: string): void {
  try {
    localStorage.setItem(KEY_PREFIX + caseId, sessionId);
  } catch {
    // ignore quota or disabled storage
  }
}

export function clearActiveSessionForCase(caseId: string): void {
  try {
    localStorage.removeItem(KEY_PREFIX + caseId);
  } catch {
    // ignore
  }
}
