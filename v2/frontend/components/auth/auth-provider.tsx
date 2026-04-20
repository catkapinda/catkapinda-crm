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
  apiErrorMessage,
  apiFetch,
  buildApiUrl,
  writeAuthPresenceMarker,
  writeStoredAuthNotice,
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

async function confirmAuthenticatedSession(fallbackUser: AuthUser) {
  const response = await fetch(buildApiUrl("/auth/me"), {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const fallbackMessage =
      "Giriş tamamlandı ama oturum tarayıcıda doğrulanamadı. Lütfen sayfayı yenileyip tekrar dene.";
    const detail = await apiErrorMessage(response, fallbackMessage);
    throw new Error(
      detail === "Giris gerekli." || detail === "Oturum suresi dolmus veya gecersiz." ? fallbackMessage : detail,
    );
  }
  const payload = (await response.json().catch(() => null)) as AuthUser | null;
  return payload?.id ? payload : fallbackUser;
}

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
        writeAuthPresenceMarker(false);
        setUser(null);
        return;
      }
      const payload = (await response.json()) as AuthUser;
      setUser(payload);
    } catch {
      writeAuthPresenceMarker(false);
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
      writeAuthPresenceMarker(false);
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
      credentials: "same-origin",
      body: JSON.stringify({ identity, password }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; access_token?: string; user?: AuthUser }
      | null;

    if (!response.ok || !payload?.user) {
      throw new Error(payload?.detail || "Giriş yapilamadi.");
    }

    try {
      const confirmedUser = await confirmAuthenticatedSession(payload.user);
      writeAuthPresenceMarker(true);
      setUser(confirmedUser);
      return confirmedUser;
    } catch (confirmationError) {
      writeAuthPresenceMarker(false);
      setUser(null);
      throw confirmationError;
    }
  }, []);

  const requestPhoneCode = useCallback(async (phone: string) => {
    if (isPreviewModeBrowser()) {
      return {
        message: "Preview modunda SMS kodu hazırlandı.",
        masked_phone: phone || "05xxxxxxxxx",
      };
    }
    const response = await fetch(buildApiUrl("/auth/request-phone-code"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "same-origin",
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
      credentials: "same-origin",
      body: JSON.stringify({ phone, code }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; access_token?: string; user?: AuthUser }
      | null;

    if (!response.ok || !payload?.user) {
      throw new Error(payload?.detail || "SMS kodu doğrulanamadı.");
    }

    try {
      const confirmedUser = await confirmAuthenticatedSession(payload.user);
      writeAuthPresenceMarker(true);
      setUser(confirmedUser);
      return confirmedUser;
    } catch (confirmationError) {
      writeAuthPresenceMarker(false);
      setUser(null);
      throw confirmationError;
    }
  }, []);

  const logout = useCallback(async () => {
    if (isPreviewModeBrowser()) {
      writeAuthPresenceMarker(false);
      writeStoredAuthNotice("");
      setUser(null);
      return;
    }
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      writeAuthPresenceMarker(false);
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
