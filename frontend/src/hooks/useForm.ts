/**
 * Form state with validation, dirty/touched, and submit handling.
 */
import React, { useCallback, useState } from 'react';
import type { Validator } from '../utils/validators';

export interface FieldConfig<T = string> {
  initialValue: T;
  validate?: Validator<T>;
}

export interface FieldState<T = string> {
  value: T;
  error: string | undefined;
  touched: boolean;
  dirty: boolean;
}

export function useForm<T extends Record<string, unknown>>(
  initialValues: T,
  validators?: Partial<{ [K in keyof T]: Validator<T[K]> }>,
  onSubmit?: (values: T) => void | Promise<void>
) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [dirty, setDirty] = useState(false);

  const setFieldValue = useCallback(
    <K extends keyof T>(name: K, value: T[K]) => {
      setValues((prev) => ({ ...prev, [name]: value }));
      setDirty(true);
      const validate = validators?.[name];
      if (validate) {
        const err = validate(value);
        setErrors((prev) => (err ? { ...prev, [name]: err } : { ...prev, [name]: undefined }));
      }
    },
    [validators]
  );

  const setFieldTouched = useCallback(<K extends keyof T>(name: K, t: boolean = true) => {
    setTouched((prev) => ({ ...prev, [name]: t }));
    const validate = validators?.[name];
    if (validate && values[name] !== undefined) {
      const err = validate(values[name]);
      setErrors((prev) => (err ? { ...prev, [name]: err } : { ...prev, [name]: undefined }));
    }
  }, [validators, values]);

  const validateAll = useCallback((): boolean => {
    if (!validators) return true;
    const next: Partial<Record<keyof T, string>> = {};
    let valid = true;
    for (const key of Object.keys(validators) as (keyof T)[]) {
      const v = validators[key];
      if (v) {
        const err = v(values[key]);
        if (err) {
          next[key] = err;
          valid = false;
        }
      }
    }
    setErrors(next);
    setTouched(Object.keys(validators).reduce((acc, k) => ({ ...acc, [k]: true }), {} as Partial<Record<keyof T, boolean>>));
    return valid;
  }, [validators, values]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!validateAll()) return;
      onSubmit?.(values);
    },
    [validateAll, onSubmit, values]
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setDirty(false);
  }, [initialValues]);

  const getFieldProps = useCallback(
    <K extends keyof T>(name: K) => ({
      value: values[name],
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        setFieldValue(name, e.target.value as T[K]),
      onBlur: () => setFieldTouched(name),
      error: errors[name],
      touched: touched[name],
    }),
    [values, errors, touched, setFieldValue, setFieldTouched]
  );

  return {
    values,
    errors,
    touched,
    dirty,
    setFieldValue,
    setFieldTouched,
    validateAll,
    handleSubmit,
    reset,
    getFieldProps,
  };
}
