"use client";

import type { CSSProperties, FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";
import { resolveDefaultPath } from "../../lib/navigation";

type ChangePasswordResponse = {
  message: string;
  user: {
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
};

export default function AccountPage() {
  const router = useRouter();
  const { user, updateUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) {
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Yeni sifre ve tekrar sifresi ayni olmali.");
      return;
    }

    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await apiFetch("/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string }
        | ChangePasswordResponse
        | null;
      if (!response.ok || !payload || !("user" in payload)) {
        throw new Error((payload && "detail" in payload && payload.detail) || "Sifre guncellenemedi.");
      }
      updateUser(payload.user);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage(payload.message || "Sifre guncellendi.");
      if (!payload.user.must_change_password) {
        router.replace(resolveDefaultPath(payload.user.allowed_actions));
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sifre guncellenemedi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell activeItem="Profil">
      <section style={{ display: "grid", gap: "18px" }}>
        <div
          style={{
            padding: "24px 26px",
            borderRadius: "28px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
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
            Profil ve Guvenlik
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Hesabini ve giris bilgilerini buradan yonet.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Pilot kullanimda en kritik guvenlik adimi sifrenin guncel ve tekil olmasi. Ilk
            giriste gecici sifre ile geldiysen bunu burada kalici sifreye cevir.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(320px, 420px) minmax(360px, 1fr)",
            gap: "18px",
          }}
        >
          <section
            style={{
              padding: "22px",
              borderRadius: "24px",
              border: "1px solid var(--line)",
              background: "var(--surface-strong)",
              boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
              display: "grid",
              gap: "14px",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Profil Ozeti</h2>
            <InfoRow label="Ad Soyad" value={user?.full_name || "-"} />
            <InfoRow label="Rol" value={user?.role_display || "-"} />
            <InfoRow label="E-posta" value={user?.email || "-"} />
            <InfoRow label="Telefon" value={user?.phone || "-"} />
            <InfoRow label="Oturum" value={user?.expires_at ? `Acik · ${user.expires_at}` : "-"} />
          </section>

          <section
            style={{
              padding: "22px",
              borderRadius: "24px",
              border: "1px solid var(--line)",
              background: "var(--surface-strong)",
              boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
              display: "grid",
              gap: "16px",
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Sifre Guncelle</h2>
              <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
                Yeni sisteme gectigimizde herkesin tekil ve guclu sifre kullanmasi gerekiyor.
              </p>
            </div>

            {user?.must_change_password ? (
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  background: "rgba(255, 196, 59, 0.12)",
                  border: "1px solid rgba(255, 196, 59, 0.24)",
                  color: "#8a5b00",
                  fontWeight: 700,
                }}
              >
                Bu hesap gecici sifre ile acildi. Devam etmeden once sifreni guncelle.
              </div>
            ) : null}

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Mevcut Sifre</span>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="Mevcut sifren"
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Yeni Sifre</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="En az 6 karakter"
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Yeni Sifre Tekrar</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="Yeni sifreyi tekrar gir"
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

              {message ? (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "16px",
                    background: "rgba(44, 138, 84, 0.08)",
                    color: "#1c6c3f",
                    border: "1px solid rgba(44, 138, 84, 0.14)",
                  }}
                >
                  {message}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: "14px 18px",
                  borderRadius: "16px",
                  border: "none",
                  background: "var(--accent)",
                  color: "#fff",
                  fontWeight: 800,
                  fontSize: "1rem",
                  cursor: "pointer",
                  opacity: submitting ? 0.6 : 1,
                }}
              >
                {submitting ? "Kaydediliyor..." : "Sifreyi Guncelle"}
              </button>
            </form>
          </section>
        </div>
      </section>
    </AppShell>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "grid",
        gap: "6px",
        paddingBottom: "12px",
        borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div style={{ fontWeight: 700 }}>{value}</div>
    </div>
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
