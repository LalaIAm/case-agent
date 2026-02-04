/**
 * Auth context: user state, login, register, logout.
 */
import React, { createContext, useCallback, useEffect, useState } from 'react';
import type { User } from '../types/auth';
import {
  clearStoredToken,
  getCurrentUser,
  getStoredToken,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setStoredToken,
} from '../services/api';
import type { AuthContextType } from '../types/auth';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const u = await getCurrentUser();
      setUser(u ? { ...u, id: u.id } : null);
    } catch {
      clearStoredToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await apiLogin(email, password);
      setStoredToken(access_token);
      await loadUser();
    },
    [loadUser]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await apiRegister(email, password);
      await loadUser();
    },
    [loadUser]
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value: AuthContextType = {
    user,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
