/**
 * Login / register page with mode toggle and useForm validation.
 */
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Button } from '../components/Button';
import { useForm } from '../hooks/useForm';
import { email, compose, required, minLength } from '../utils/validators';
import { getErrorMessage } from '../utils/errorHandler';

const initialValues = { email: '', password: '' };

export function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(
    location.pathname === '/register' ? 'register' : 'login'
  );
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const {
    values,
    getFieldProps,
    handleSubmit: formHandleSubmit,
    validateAll,
  } = useForm(
    initialValues,
    {
      email,
      password: compose(required, minLength(8)),
    }
  );

  useEffect(() => {
    setMode(location.pathname === '/register' ? 'register' : 'login');
  }, [location.pathname]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!validateAll()) return;
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(values.email, values.password);
      } else {
        await register(values.email, values.password);
      }
      navigate('/', { replace: true });
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-blue-900 text-center mb-2">
          Minnesota Conciliation Court Case Agent
        </h1>
        <p className="text-gray-600 text-center text-sm mb-6">
          Sign in or create an account
        </p>
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={getFieldProps('email').value}
                onChange={getFieldProps('email').onChange}
                onBlur={getFieldProps('email').onBlur}
                aria-describedby={getFieldProps('email').touched && getFieldProps('email').error ? 'email-error' : undefined}
                className={`w-full rounded-md border px-3 py-2 text-gray-900 focus:outline-none focus:ring-1 ${
                  getFieldProps('email').error && getFieldProps('email').touched
                    ? 'border-red-500 focus:border-red-600 focus:ring-red-600'
                    : 'border-gray-300 focus:border-blue-600 focus:ring-blue-600'
                }`}
                autoComplete="email"
              />
              {getFieldProps('email').touched && getFieldProps('email').error && (
                <p id="email-error" className="mt-1 text-sm text-red-600" role="alert">
                  {getFieldProps('email').error}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={getFieldProps('password').value}
                onChange={getFieldProps('password').onChange}
                onBlur={getFieldProps('password').onBlur}
                aria-describedby={getFieldProps('password').touched && getFieldProps('password').error ? 'password-error' : undefined}
                className={`w-full rounded-md border px-3 py-2 text-gray-900 focus:outline-none focus:ring-1 ${
                  getFieldProps('password').error && getFieldProps('password').touched
                    ? 'border-red-500 focus:border-red-600 focus:ring-red-600'
                    : 'border-gray-300 focus:border-blue-600 focus:ring-blue-600'
                }`}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              {mode === 'register' && (
                <p className="mt-1 text-xs text-gray-500">At least 8 characters</p>
              )}
              {getFieldProps('password').touched && getFieldProps('password').error && (
                <p id="password-error" className="mt-1 text-sm text-red-600" role="alert">
                  {getFieldProps('password').error}
                </p>
              )}
            </div>
            {error && (
              <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </div>
            )}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-gray-600">
            {mode === 'login' ? (
              <>
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('register');
                    setError('');
                    navigate('/register', { replace: true });
                  }}
                  className="font-medium text-blue-600 hover:text-blue-800"
                >
                  Register
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('login');
                    setError('');
                    navigate('/login', { replace: true });
                  }}
                  className="font-medium text-blue-600 hover:text-blue-800"
                >
                  Log in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
