/**
 * Sanitize user input: trim, normalize line endings, safe filenames.
 */

/** Trim whitespace from string. */
export function trim(value: string): string {
  return value.replace(/^\s+|\s+$/g, '');
}

/** Normalize line endings to \\n. */
export function normalizeLineEndings(value: string): string {
  return value.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

/** Remove or replace characters that are unsafe in filenames. */
const UNSAFE_FILENAME = /[<>:"/\\|?*\x00-\x1f]/g;
export function sanitizeFilename(name: string): string {
  return name.replace(UNSAFE_FILENAME, '_').trim() || 'file';
}

/** Sanitize text input: trim and normalize line endings. */
export function sanitizeText(value: string): string {
  return normalizeLineEndings(trim(value));
}
