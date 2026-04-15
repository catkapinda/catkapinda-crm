"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import {
  AUTH_UNAUTHORIZED_EVENT,
  apiFetch,
  buildApiUrl,
  writeStoredAuthNotice,
  writeStoredAuthToken,
} from "../../lib/api";
import { isPreviewModeBrowser, PREVIEW_USER } from "../../lib/preview";

export type AuthUser = {
  id: number;
  identity: string;
  email: string;
  phone: string;
  full_name: string;
  role: string;
  role_display: string;
  must_change_password: boolean;
  allowed_actions: string[];
  expires_at: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (identity: string, password: string) => Promise<AuthUser>;
  requestPhoneCode: (phone: string) => Promise<{ message: string; masked_phone: string }>;
  verifyPhoneCode: (phone: string, code: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateUser: (user: AuthUser) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (isPreviewModeBrowser()) {
      setUser(PREVIEW_USER);
      return;
    }
    try {
      const response = await apiFetch("/auth/me");
      if (!response.ok) {
        writeStoredAuthToken("");
        setUser(null);
        return;
      }
      const payload = (await response.json()) as AuthUser;
      setUser(payload);
    } catch {
      writeStoredAuthToken("");
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function boot() {
      try {
        await refreshUser();
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void boot();
    return () => {
      active = false;
    };
  }, [refreshUser]);

  useEffect(() => {
    function handleUnauthorized() {
      writeStoredAuthToken("");
      setUser(null);
      setLoading(false);
    }

    if (typeof window === "undefined") {
      return;
    }
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (identity: string, password: string) => {
    if (isPreviewModeBrowser()) {
      setUser(PREVIEW_USER);
      return PREVIEW_USER;
    }
    const response = await fetch(buildApiUrl("/auth/login"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ identity, password }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; access_token?: string; user?: AuthUser }
      | null;

    if (!response.ok || !payload?.access_token || !payload.user) {
      throw new Error(payload?.detail || "Giris yapilamadi.");
    }

    writeStoredAuthToken(payload.access_token);
    setUser(payload.user);
    return payload.user;
  }, []);

  const requestPhoneCode = useCallback(async (phone: string) => {
    if (isPreviewModeBrowser()) {
      return {
        message: "Preview modunda SMS kodu hazirlandi.",
        masked_phone: phone || "05xxxxxxxxx",
      };
    }
    const response = await fetch(buildApiUrl("/auth/request-phone-code"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ phone }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string; masked_phone?: string }
      | null;

    if (!response.ok || !payload?.message || !payload?.masked_phone) {
      throw new Error(payload?.detail || "SMS kodu gonderilemedi.");
    }

    return {
      message: payload.message,
      masked_phone: payload.masked_phone,
    };
  }, []);

  const verifyPhoneCode = useCallback(async (phone: string, code: string) => {
    if (isPreviewModeBrowser()) {
      setUser(PREVIEW_USER);
      return PREVIEW_USER;
    }
    const response = await fetch(buildApiUrl("/auth/verify-phone-code"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ phone, code }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; access_token?: string; user?: AuthUser }
      | null;

    if (!response.ok || !payload?.access_token || !payload.user) {
      throw new Error(payload?.detail || "SMS kodu dogrulanamadi.");
    }

    writeStoredAuthToken(payload.access_token);
    setUser(payload.user);
    return payload.user;
  }, []);

  const logout = useCallback(async () => {
    if (isPreviewModeBrowser()) {
      writeStoredAuthToken("");
      writeStoredAuthNotice("");
      setUser(null);
      return;
    }
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      writeStoredAuthToken("");
      writeStoredAuthNotice("");
      setUser(null);
    }
  }, []);

  const updateUser = useCallback((nextUser: AuthUser) => {
    setUser(nextUser);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login,
      requestPhoneCode,
      verifyPhoneCode,
      logout,
      refreshUser,
      updateUser,
    }),
    [user, loading, login, requestPhoneCode, verifyPhoneCode, logout, refreshUser, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
