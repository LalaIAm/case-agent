/**
 * API client with JWT auth and auth helpers.
 */
import axios, { AxiosError } from 'axios';

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const TOKEN_KEY = 'auth_token';

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      const path = window.location.pathname;
      if (path !== '/login' && path !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);
  const { data } = await api.post<LoginResponse>('/api/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function register(email: string, password: string): Promise<void> {
  await api.post<UserResponse>('/api/auth/register', {
    email,
    password,
  });
  const loginData = await login(email, password);
  setStoredToken(loginData.access_token);
}

export async function logout(): Promise<void> {
  try {
    await api.post('/api/auth/logout');
  } finally {
    clearStoredToken();
  }
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  const token = getStoredToken();
  if (!token) return null;
  const { data } = await api.get<UserResponse>('/api/auth/me');
  return data;
}
