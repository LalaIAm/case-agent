/**
 * Reusable validation functions for forms.
 */

export type Validator<T = string> = (value: T) => string | undefined;

export const required: Validator = (value) => {
  if (value == null || String(value).trim() === '') return 'This field is required';
  return undefined;
};

export const minLength = (min: number): Validator => (value) => {
  const s = value == null ? '' : String(value);
  if (s.length < min) return `Must be at least ${min} characters`;
  return undefined;
};

export const maxLength = (max: number): Validator => (value) => {
  const s = value == null ? '' : String(value);
  if (s.length > max) return `Must be at most ${max} characters`;
  return undefined;
};

export const pattern = (regex: RegExp, message: string): Validator => (value) => {
  const s = value == null ? '' : String(value);
  if (!regex.test(s)) return message;
  return undefined;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const email: Validator = (value) => {
  const s = value == null ? '' : String(value).trim();
  if (!s) return 'Email is required';
  if (!EMAIL_REGEX.test(s)) return 'Please enter a valid email address';
  return undefined;
};

export function compose<T>(...validators: Validator<T>[]): Validator<T> {
  return (value) => {
    for (const v of validators) {
      const err = v(value);
      if (err) return err;
    }
    return undefined;
  };
}

export type AsyncValidator<T = string> = (value: T) => Promise<string | undefined>;
