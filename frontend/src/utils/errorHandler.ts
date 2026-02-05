/**
 * Centralized error parsing and user-friendly messages from API errors.
 */
import { AxiosError } from 'axios';

export interface ApiErrorBody {
  error?: {
    type?: string;
    message?: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

/**
 * Extract a user-friendly message from an API error response.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ApiErrorBody | undefined;
    const msg = data?.error?.message;
    if (typeof msg === 'string' && msg) return msg;
    if (error.response?.status === 422) return 'Validation failed. Please check your input.';
    if (error.response?.status === 429) return 'Too many requests. Please wait a moment and try again.';
    if (error.response?.status === 403) return 'You do not have permission to perform this action.';
    if (error.response?.status === 404) return 'The requested resource was not found.';
    if (error.response?.status && error.response.status >= 500) return 'Something went wrong on the server. Please try again.';
    if (error.code === 'ECONNABORTED') return 'Request timed out. Please try again.';
    if (error.code === 'ERR_NETWORK') return 'Network error. Please check your connection.';
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}

/**
 * Get error code or type for programmatic handling.
 */
export function getErrorCode(error: unknown): string | undefined {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ApiErrorBody | undefined;
    return data?.error?.type ?? undefined;
  }
  return undefined;
}

/**
 * Get request ID for support/debugging.
 */
export function getRequestId(error: unknown): string | undefined {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ApiErrorBody | undefined;
    return data?.error?.request_id;
  }
  return undefined;
}

/**
 * Get field-level validation errors (for 422).
 */
export function getValidationErrors(error: unknown): Array<{ loc: unknown; msg: string }> {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ApiErrorBody | undefined;
    const fields = (data?.error?.details as { fields?: Array<{ loc: unknown; msg: string }> })?.fields;
    return Array.isArray(fields) ? fields : [];
  }
  return [];
}
