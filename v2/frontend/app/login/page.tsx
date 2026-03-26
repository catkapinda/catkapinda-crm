"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { resolveDefaultPath } from "../../lib/navigation";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading, login } = useAuth();

  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const nextPath = useMemo(() => searchParams.get("next") || "", [searchParams]);

  useEffect(() => {
    if (!loading && user) {
      router.replace(nextPath || resolveDefaultPath(user.allowed_actions));
    }
  }, [loading, user, router, nextPath]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(identity, password);
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Giris yapilamadi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "24px",
      }}
    >
      <section
        style={{
          width: "min(520px, 100%)",
          padding: "32px",
          borderRadius: "28px",
          background: "var(--surface-strong)",
          border: "1px solid var(--line)",
          boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          display: "grid",
          gap: "18px",
        }}
      >
        <div>
          <div
            style={{
              display: "inline-flex",
              padding: "7px 12px",
              borderRadius: "999px",
              background: "var(--accent-soft)",
              color: "var(--accent)",
              fontSize: "0.78rem",
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            v2 Giris
          </div>
          <h1
            style={{
              margin: "16px 0 8px",
              fontSize: "clamp(2rem, 4vw, 3rem)",
              lineHeight: 1.02,
            }}
          >
            Cat Kapinda CRM v2
          </h1>
          <p
            style={{
              margin: 0,
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            E-posta veya telefon numaran ile giris yap. Yetkine gore sadece ilgili moduller
            acilir.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gap: "14px",
          }}
        >
          <label style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontWeight: 700 }}>E-posta veya Telefon</span>
            <input
              value={identity}
              onChange={(event) => setIdentity(event.target.value)}
              placeholder="ornek@catkapinda.com veya 05xxxxxxxxx"
              style={fieldStyle}
            />
          </label>

          <label style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontWeight: 700 }}>Sifre</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Sifreni gir"
              style={fieldStyle}
            />
          </label>

          {error ? (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "16px",
                background: "rgba(207, 65, 65, 0.08)",
                color: "#b73636",
                border: "1px solid rgba(207, 65, 65, 0.12)",
              }}
            >
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting || loading}
            style={{
              padding: "14px 18px",
              borderRadius: "16px",
              border: "none",
              background: "var(--accent)",
              color: "#fff",
              fontWeight: 800,
              fontSize: "1rem",
              cursor: "pointer",
              opacity: submitting || loading ? 0.6 : 1,
            }}
          >
            {submitting ? "Giris Yapiliyor..." : "Giris Yap"}
          </button>
        </form>
      </section>
    </main>
  );
}

const fieldStyle = {
  width: "100%",
  padding: "14px 16px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--text)",
  fontSize: "0.98rem",
} satisfies CSSProperties;
