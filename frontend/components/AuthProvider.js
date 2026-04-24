"use client";
/**
 * Global auth state via React Context.
 * Provides login, register, logout + current user to all components.
 */
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getStoredUser, logout as apiLogout, login as apiLogin, register as apiRegister } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = getStoredUser();
    if (stored) setUser(stored);
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    setUser({ user_id: data.user_id, email: data.email });
    return data;
  }, []);

  const registerUser = useCallback(async (email, password) => {
    const data = await apiRegister(email, password);
    setUser({ user_id: data.user_id, email: data.email });
    return data;
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register: registerUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
