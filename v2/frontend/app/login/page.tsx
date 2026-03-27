"use client";

import type { CSSProperties, FormEvent } from "react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { buildApiUrl } from "../../lib/api";
import { resolveDefaultPath } from "../../lib/navigation";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading, login, requestPhoneCode, verifyPhoneCode } = useAuth();

  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [smsLoginEnabled, setSmsLoginEnabled] = useState(false);
  const [phone, setPhone] = useState("");
  const [loginCode, setLoginCode] = useState("");
  const [smsSubmitting, setSmsSubmitting] = useState(false);
  const [smsError, setSmsError] = useState("");
  const [smsMessage, setSmsMessage] = useState("");
  const [maskedPhone, setMaskedPhone] = useState("");

  const nextPath = useMemo(() => searchParams.get("next") || "", [searchParams]);

  useEffect(() => {
    if (!loading && user) {
      router.replace(user.must_change_password ? "/account" : nextPath || resolveDefaultPath(user.allowed_actions));
    }
  }, [loading, user, router, nextPath]);

  useEffect(() => {
    let active = true;

    async function loadAuthModes() {
      try {
        const response = await fetch(buildApiUrl("/auth/modes"), { cache: "no-store" });
        const payload = (await response.json().catch(() => null)) as { sms_login?: boolean } | null;
        if (active) {
          setSmsLoginEnabled(Boolean(payload?.sms_login));
        }
      } catch {
        if (active) {
          setSmsLoginEnabled(false);
        }
      }
    }

    void loadAuthModes();
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const loggedInUser = await login(identity, password);
      router.replace(
        loggedInUser.must_change_password ? "/account" : nextPath || resolveDefaultPath(loggedInUser.allowed_actions),
      );
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Giris yapilamadi.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSendCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSmsSubmitting(true);
    setSmsError("");
    try {
      const payload = await requestPhoneCode(phone);
      setMaskedPhone(payload.masked_phone);
      setSmsMessage(payload.message);
    } catch (requestError) {
      setSmsError(requestError instanceof Error ? requestError.message : "SMS kodu gonderilemedi.");
    } finally {
      setSmsSubmitting(false);
    }
  }

  async function handleVerifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSmsSubmitting(true);
    setSmsError("");
    try {
      const loggedInUser = await verifyPhoneCode(phone, loginCode);
      router.replace(
        loggedInUser.must_change_password ? "/account" : nextPath || resolveDefaultPath(loggedInUser.allowed_actions),
      );
    } catch (verifyError) {
      setSmsError(verifyError instanceof Error ? verifyError.message : "SMS kodu dogrulanamadi.");
    } finally {
      setSmsSubmitting(false);
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
          width: "min(1120px, 100%)",
          display: "grid",
          gap: "18px",
          gridTemplateColumns: "minmax(0, 1.1fr) minmax(340px, 0.9fr)",
          alignItems: "start",
        }}
      >
        <div
          style={{
            padding: "36px",
            borderRadius: "32px",
            background: "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,248,255,0.94))",
            border: "1px solid rgba(40, 92, 196, 0.10)",
            boxShadow: "0 32px 80px rgba(22, 42, 74, 0.08)",
            minHeight: "100%",
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
            Cat Kapinda v2
          </div>

          <h1
            style={{
              margin: "18px 0 10px",
              fontSize: "clamp(2.2rem, 4vw, 3.4rem)",
              lineHeight: 0.96,
              letterSpacing: "-0.04em",
            }}
          >
            Yeni operasyon paneline hos geldin.
          </h1>

          <p
            style={{
              margin: 0,
              maxWidth: "58ch",
              color: "var(--muted)",
              lineHeight: 1.8,
              fontSize: "1rem",
            }}
          >
            Artik menu gecisleri, formlar ve yetki akislari daha modern bir yapida ilerliyor.
            Istersen e-posta/sifre ile, istersen telefon ve SMS kodu ile giris yapabilirsin.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "14px",
              marginTop: "28px",
            }}
          >
            {[
              ["Puantaj", "Giris, duzeltme ve yonetim tek akista."],
              ["Personel", "Kayit olusturma ve duzenleme yeni hat uzerinde."],
              ["Kesintiler", "Filo ve finans kurallariyla uyumlu yonetim."],
            ].map(([title, text]) => (
              <div
                key={title}
                style={{
                  padding: "18px",
                  borderRadius: "24px",
                  border: "1px solid rgba(40, 92, 196, 0.08)",
                  background: "rgba(255,255,255,0.88)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div style={{ fontWeight: 800 }}>{title}</div>
                <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>{text}</div>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gap: "18px",
          }}
        >
          <section style={cardStyle}>
            <div>
              <div style={eyebrowStyle}>Sifre ile Giris</div>
              <h2 style={cardTitleStyle}>E-posta veya telefon</h2>
              <p style={cardBodyStyle}>Mevcut sifrenle dogrudan giris yap.</p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
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

              {error ? <div style={errorStyle}>{error}</div> : null}

              <button type="submit" disabled={submitting || loading} style={primaryButtonStyle(submitting || loading)}>
                {submitting ? "Giris Yapiliyor..." : "Giris Yap"}
              </button>
            </form>
          </section>

          {smsLoginEnabled ? (
            <section style={cardStyle}>
              <div>
                <div style={eyebrowStyle}>SMS ile Giris</div>
                <h2 style={cardTitleStyle}>Telefonuna tek kullanimlik kod gelsin</h2>
                <p style={cardBodyStyle}>
                  Bolge muduru ve izinli yonetici numaralari bu akisi kullanabilir.
                </p>
              </div>

              <form onSubmit={handleSendCode} style={{ display: "grid", gap: "12px" }}>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Telefon</span>
                  <input
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="05xxxxxxxxx"
                    style={fieldStyle}
                  />
                </label>
                <button type="submit" disabled={smsSubmitting} style={secondaryButtonStyle(smsSubmitting)}>
                  {smsSubmitting ? "Kod Hazirlaniyor..." : "SMS Kodu Gonder"}
                </button>
              </form>

              {smsMessage ? (
                <div style={successStyle}>
                  {smsMessage}
                  {maskedPhone ? ` (${maskedPhone})` : ""}
                </div>
              ) : null}

              <form onSubmit={handleVerifyCode} style={{ display: "grid", gap: "12px" }}>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>6 Haneli Kod</span>
                  <input
                    value={loginCode}
                    onChange={(event) => setLoginCode(event.target.value)}
                    placeholder="000000"
                    style={fieldStyle}
                    inputMode="numeric"
                    maxLength={6}
                  />
                </label>

                {smsError ? <div style={errorStyle}>{smsError}</div> : null}

                <button type="submit" disabled={smsSubmitting || !loginCode.trim()} style={primaryButtonStyle(smsSubmitting || !loginCode.trim())}>
                  {smsSubmitting ? "Kod Dogrulaniyor..." : "Kodu Dogrula"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}

function LoginPageFallback() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "24px",
      }}
    >
      <section style={cardStyle}>Giris hazirlaniyor...</section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}

const fieldStyle = {
  width: "100%",
  padding: "14px 16px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.96)",
  color: "var(--text)",
  fontSize: "0.98rem",
} satisfies CSSProperties;

const cardStyle = {
  padding: "28px",
  borderRadius: "28px",
  background: "var(--surface-strong)",
  border: "1px solid var(--line)",
  boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
  display: "grid",
  gap: "16px",
} satisfies CSSProperties;

const eyebrowStyle = {
  color: "var(--accent)",
  fontWeight: 800,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  fontSize: "0.76rem",
} satisfies CSSProperties;

const cardTitleStyle = {
  margin: "8px 0 6px",
  fontSize: "1.4rem",
  lineHeight: 1.1,
} satisfies CSSProperties;

const cardBodyStyle = {
  margin: 0,
  color: "var(--muted)",
  lineHeight: 1.7,
  fontSize: "0.95rem",
} satisfies CSSProperties;

const errorStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(207, 65, 65, 0.08)",
  color: "#b73636",
  border: "1px solid rgba(207, 65, 65, 0.12)",
} satisfies CSSProperties;

const successStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(51, 122, 88, 0.09)",
  color: "#2d7f58",
  border: "1px solid rgba(51, 122, 88, 0.14)",
} satisfies CSSProperties;

function primaryButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "14px 18px",
    borderRadius: "16px",
    border: "none",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 800,
    fontSize: "1rem",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}

function secondaryButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "13px 16px",
    borderRadius: "16px",
    border: "1px solid rgba(40, 92, 196, 0.16)",
    background: "rgba(40, 92, 196, 0.06)",
    color: "var(--accent)",
    fontWeight: 800,
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}
