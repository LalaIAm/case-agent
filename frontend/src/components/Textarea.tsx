/**
 * Styled textarea with label and error state.
 */
import type { TextareaHTMLAttributes } from 'react';

interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'className'> {
  label: string;
  error?: string;
  rows?: number;
}

export function Textarea({
  label,
  error,
  rows = 4,
  id,
  ...textareaProps
}: TextareaProps) {
  const textareaId =
    id ?? `textarea-${label.replace(/\s+/g, '-').toLowerCase()}`;
  return (
    <div className="space-y-1">
      <label
        htmlFor={textareaId}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
      </label>
      <textarea
        id={textareaId}
        rows={rows}
        className={`block w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
          error
            ? 'border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 bg-white'
        }`}
        aria-invalid={!!error}
        aria-describedby={error ? `${textareaId}-error` : undefined}
        {...textareaProps}
      />
      {error && (
        <p
          id={`${textareaId}-error`}
          className="text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}
