"use client";

import type { CSSProperties, FormEvent } from "react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { buildApiUrl, readStoredAuthNotice, writeStoredAuthNotice } from "../../lib/api";
import { resolveDefaultPath } from "../../lib/navigation";

const serifTitleStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const paperCardStyle = {
  borderRadius: "30px",
  border: "1px solid var(--line)",
  background: "var(--surface-raised)",
  boxShadow: "var(--shadow-soft)",
} as const;

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading, login, requestPhoneCode, verifyPhoneCode } = useAuth();

  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [smsLoginEnabled, setSmsLoginEnabled] = useState(false);
  const [authPanelMode, setAuthPanelMode] = useState<"sms" | "recovery">("sms");
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

  useEffect(() => {
    const nextNotice = readStoredAuthNotice();
    if (!nextNotice) {
      return;
    }
    setNotice(nextNotice);
    writeStoredAuthNotice("");
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setNotice("");
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
    setNotice("");
    try {
      const payload = await requestPhoneCode(phone);
      setMaskedPhone(payload.masked_phone);
      setSmsMessage(
        authPanelMode === "recovery"
          ? "Kimligini dogrulaman icin kod hazir. Kodla devam edip sifreni guvenlik ekranindan guncelleyebilirsin."
          : payload.message,
      );
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
    setNotice("");
    try {
      const loggedInUser = await verifyPhoneCode(phone, loginCode);
      if (authPanelMode === "recovery") {
        writeStoredAuthNotice("SMS ile kimligini dogruladin. Guvenlik icin sifreni simdi guncelle.");
        router.replace("/account");
        return;
      }
      router.replace(
        loggedInUser.must_change_password ? "/account" : nextPath || resolveDefaultPath(loggedInUser.allowed_actions),
      );
    } catch (verifyError) {
      setSmsError(verifyError instanceof Error ? verifyError.message : "SMS kodu dogrulanamadi.");
    } finally {
      setSmsSubmitting(false);
    }
  }

  function switchAuthPanelMode(mode: "sms" | "recovery") {
    setAuthPanelMode(mode);
    setSmsError("");
    setSmsMessage("");
    setMaskedPhone("");
    setLoginCode("");
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "24px",
        display: "grid",
        placeItems: "center",
      }}
    >
      <section
        style={{
          width: "min(1180px, 100%)",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "20px",
          alignItems: "stretch",
        }}
      >
        <article
          style={{
            padding: "34px",
            borderRadius: "36px",
            background:
              "linear-gradient(145deg, rgba(22, 38, 58, 0.98), rgba(38, 58, 82, 0.96))",
            boxShadow: "var(--shadow-deep)",
            color: "#fff7ea",
            position: "relative",
            overflow: "hidden",
            display: "grid",
            gap: "24px",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "auto auto -120px -80px",
              width: "280px",
              height: "280px",
              borderRadius: "999px",
              background: "radial-gradient(circle, rgba(185,116,41,0.35), transparent 70%)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: "36px 34px auto auto",
              width: "180px",
              height: "180px",
              borderRadius: "999px",
              background: "radial-gradient(circle, rgba(255,255,255,0.1), transparent 72%)",
            }}
          />

          <div style={{ position: "relative", display: "grid", gap: "18px" }}>
            <div
              style={{
                display: "inline-flex",
                width: "fit-content",
                padding: "7px 12px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#f2cf9e",
                fontSize: "0.74rem",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                fontWeight: 800,
              }}
            >
              v2 pilot giris masasi
            </div>
            <div style={{ display: "grid", gap: "12px" }}>
              <h1
                style={{
                  ...serifTitleStyle,
                  margin: 0,
                  fontSize: "clamp(2.8rem, 6vw, 5rem)",
                  lineHeight: 0.9,
                  fontWeight: 700,
                  maxWidth: "8ch",
                }}
              >
                Yeni operasyon paneline giris.
              </h1>
              <p
                style={{
                  margin: 0,
                  maxWidth: "58ch",
                  color: "rgba(255, 247, 234, 0.76)",
                  lineHeight: 1.8,
                  fontSize: "1rem",
                }}
              >
                Bu yuzeyi yalnizca kimlik dogrulama icin degil, yeni sistemin karakterini ilk
                andan hissettirmek icin kurduk. Sifreyle giris, SMS akisi ve yonlendirme tek
                editorial yuzeyde toplanmis durumda.
              </p>
            </div>
          </div>

          <div
            style={{
              position: "relative",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "14px",
            }}
          >
            {[
              ["Giris Hatti", "Sifre ve SMS akisi ayni kontrol masasi icinde."],
              ["Yetki", "Rol bazli yonlendirme giris sonrasi otomatik isliyor."],
              ["Pilot Akis", "Giris yapan ekip ilgili modullere temiz sekilde dusuyor."],
            ].map(([title, text]) => (
              <article
                key={title}
                style={{
                  padding: "18px 16px",
                  borderRadius: "22px",
                  background: "rgba(255,255,255,0.07)",
                  border: "1px solid rgba(255,255,255,0.09)",
                  backdropFilter: "blur(10px)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div style={{ color: "#fff4e5", fontWeight: 800 }}>{title}</div>
                <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.65, fontSize: "0.92rem" }}>
                  {text}
                </div>
              </article>
            ))}
          </div>

          <div
            style={{
              position: "relative",
              display: "grid",
              gridTemplateColumns: "1.2fr 0.8fr",
              gap: "14px",
            }}
          >
            <article
              style={{
                padding: "20px",
                borderRadius: "24px",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.1)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div
                style={{
                  color: "#f2cf9e",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  fontSize: "0.72rem",
                  letterSpacing: "0.08em",
                }}
              >
                Ilk bakista
              </div>
              <div
                style={{
                  ...serifTitleStyle,
                  fontSize: "1.8rem",
                  lineHeight: 0.96,
                  fontWeight: 700,
                }}
              >
                Hızlı giris, temiz yonlendirme, daha az surtunme.
              </div>
              <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.7 }}>
                Login sonrasi ekranlar artik beyazlayip yeniden yukleniyormus gibi his
                vermesin diye yapinin geri kalanini da ayni dille tasiyoruz.
              </div>
            </article>

            <article
              style={{
                padding: "20px",
                borderRadius: "24px",
                background: "linear-gradient(180deg, rgba(185,116,41,0.24), rgba(255,255,255,0.06))",
                border: "1px solid rgba(241,194,143,0.2)",
                display: "grid",
                gap: "6px",
                alignContent: "start",
              }}
            >
              <div style={{ color: "#f6ddbb", fontSize: "0.74rem", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 800 }}>
                Hazir Moduller
              </div>
              <div style={{ ...serifTitleStyle, fontSize: "2.4rem", lineHeight: 0.9, fontWeight: 700 }}>
                10+
              </div>
              <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                Puantaj, personel, kesintiler, raporlar ve daha fazlasi ayni pilot omurgasinda.
              </div>
            </article>
          </div>
        </article>

        <div style={{ display: "grid", gap: "18px", alignContent: "start" }}>
          <section
            style={{
              ...paperCardStyle,
              padding: "26px",
              display: "grid",
              gap: "18px",
              background:
                "linear-gradient(180deg, rgba(255,253,247,0.99), rgba(247,241,230,0.96))",
            }}
          >
            <div style={{ display: "grid", gap: "8px" }}>
              <div style={eyebrowStyle}>Sifre ile Giris</div>
              <h2
                style={{
                  ...serifTitleStyle,
                  margin: 0,
                  fontSize: "2rem",
                  lineHeight: 0.96,
                  fontWeight: 700,
                }}
              >
                E-posta veya telefonla dogrudan gir.
              </h2>
              <p style={cardBodyStyle}>
                Ofis icin en hizli akis. Giris sonrasi sistem seni yetkine uygun ilk ekrana alir.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
              {notice ? <div style={noticeStyle}>{notice}</div> : null}
              <label style={labelStyle}>
                <span style={labelTitleStyle}>E-posta veya Telefon</span>
                <input
                  value={identity}
                  onChange={(event) => setIdentity(event.target.value)}
                  placeholder="ornek@catkapinda.com veya 05xxxxxxxxx"
                  style={fieldStyle}
                />
              </label>

              <label style={labelStyle}>
                <span style={labelTitleStyle}>Sifre</span>
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

          <section
            style={{
              ...paperCardStyle,
              padding: "24px",
              display: "grid",
              gap: "16px",
              background:
                "linear-gradient(180deg, rgba(240,247,255,0.98), rgba(255,252,246,0.96))",
              border: "1px solid rgba(15,95,215,0.12)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "14px",
                alignItems: "start",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: "8px", maxWidth: "42ch" }}>
                <div style={{ ...eyebrowStyle, color: "#0f5fd7" }}>Sifre Kurtarma</div>
                <h2
                  style={{
                    ...serifTitleStyle,
                    margin: 0,
                    fontSize: "1.85rem",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Sifreni unuttuysan buradan guvenli sekilde geri don.
                </h2>
                <p style={cardBodyStyle}>
                  Kayitli telefon numarana tek kullanimlik kod gonderelim. Kimligini
                  dogruladiginda seni dogrudan guvenlik ekranina alip yeni sifre belirletelim.
                </p>
              </div>

              <div
                style={{
                  minWidth: "160px",
                  padding: "16px",
                  borderRadius: "20px",
                  background: "rgba(15,95,215,0.08)",
                  border: "1px solid rgba(15,95,215,0.12)",
                  display: "grid",
                  gap: "6px",
                }}
              >
                <div
                  style={{
                    color: "#0f5fd7",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    fontSize: "0.72rem",
                    letterSpacing: "0.08em",
                  }}
                >
                  Kurtarma Hatti
                </div>
                <div
                  style={{
                    ...serifTitleStyle,
                    fontSize: "1.7rem",
                    lineHeight: 0.92,
                    fontWeight: 700,
                    color: "var(--text)",
                  }}
                >
                  SMS
                </div>
                <div style={{ color: "var(--muted)", lineHeight: 1.55, fontSize: "0.9rem" }}>
                  Telefon koduyla dogrulama, sonra yeni sifre.
                </div>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "12px",
              }}
            >
              {[
                ["1. Kimlik", "Kayitli telefon numarani gir."],
                ["2. Kod", "Tek kullanimlik SMS kodunu al."],
                ["3. Sifre", "Guvenlik ekraninda yeni sifreni belirle."],
              ].map(([title, text]) => (
                <article
                  key={title}
                  style={{
                    padding: "16px",
                    borderRadius: "18px",
                    border: "1px solid rgba(15,95,215,0.1)",
                    background: "rgba(255,255,255,0.84)",
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <div style={{ color: "#0f5fd7", fontWeight: 800 }}>{title}</div>
                  <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                    {text}
                  </div>
                </article>
              ))}
            </div>

            <div
              style={{
                display: "flex",
                gap: "12px",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
              }}
            >
              <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                {smsLoginEnabled
                  ? "SMS kurtarma hatti aktif. Telefon dogrulamasiyla hesaba geri donebilirsin."
                  : "SMS kurtarma hatti aktif degilse ofis yoneticisiyle iletisime gecerek sifre destegi alabilirsin."}
              </div>

              {smsLoginEnabled ? (
                <button
                  type="button"
                  onClick={() => switchAuthPanelMode("recovery")}
                  style={ghostButtonStyle(false)}
                >
                  Sifremi Unuttum
                </button>
              ) : null}
            </div>
          </section>

          {smsLoginEnabled ? (
            <section
              style={{
                ...paperCardStyle,
                padding: "24px",
                display: "grid",
                gap: "18px",
                background:
                  "linear-gradient(145deg, rgba(27,43,63,0.98), rgba(43,62,85,0.95))",
                color: "#fff7ea",
              }}
            >
              <div style={{ display: "grid", gap: "8px" }}>
                <div
                  style={{
                    display: "inline-flex",
                    width: "fit-content",
                    padding: "6px",
                    borderRadius: "999px",
                    background: "rgba(255,255,255,0.08)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    gap: "6px",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => switchAuthPanelMode("sms")}
                    style={panelToggleStyle(authPanelMode === "sms")}
                  >
                    SMS ile Giris
                  </button>
                  <button
                    type="button"
                    onClick={() => switchAuthPanelMode("recovery")}
                    style={panelToggleStyle(authPanelMode === "recovery")}
                  >
                    Sifremi Unuttum
                  </button>
                </div>
                <div
                  style={{
                    color: "#f2cf9e",
                    fontWeight: 800,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    fontSize: "0.72rem",
                  }}
                >
                  SMS ile Giris
                </div>
                <h2
                  style={{
                    ...serifTitleStyle,
                    margin: 0,
                    fontSize: "1.9rem",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  {authPanelMode === "recovery"
                    ? "Telefon dogrulamasiyla hesabina geri don."
                    : "Tek kullanimlik kodla hizli dogrulama."}
                </h2>
                <p
                  style={{
                    margin: 0,
                    color: "rgba(255,247,234,0.72)",
                    lineHeight: 1.75,
                    fontSize: "0.95rem",
                  }}
                >
                  {authPanelMode === "recovery"
                    ? "Kayitli telefon numarana tek kullanimlik kod gonder. Kimligini dogruladiktan sonra seni dogrudan guvenlik ekranina alip yeni sifre belirletelim."
                    : "Bolge muduru ve izinli yonetici numaralari bu akisi kullanabilir. Kod gonder ve ayni kart icinde dogrulamayi tamamla."}
                </p>
              </div>

              <form onSubmit={handleSendCode} style={{ display: "grid", gap: "12px" }}>
                <label style={labelStyle}>
                  <span style={{ ...labelTitleStyle, color: "#fff4e5" }}>
                    {authPanelMode === "recovery" ? "Kayitli Telefon" : "Telefon"}
                  </span>
                  <input
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="05xxxxxxxxx"
                    style={darkFieldStyle}
                  />
                </label>
                <button type="submit" disabled={smsSubmitting} style={secondaryButtonStyle(smsSubmitting)}>
                  {smsSubmitting
                    ? "Kod Hazirlaniyor..."
                    : authPanelMode === "recovery"
                      ? "Dogrulama Kodu Gonder"
                      : "SMS Kodu Gonder"}
                </button>
              </form>

              {smsMessage ? (
                <div style={successStyle}>
                  {smsMessage}
                  {maskedPhone ? ` (${maskedPhone})` : ""}
                </div>
              ) : null}

              <form onSubmit={handleVerifyCode} style={{ display: "grid", gap: "12px" }}>
                <label style={labelStyle}>
                  <span style={{ ...labelTitleStyle, color: "#fff4e5" }}>6 Haneli Kod</span>
                  <input
                    value={loginCode}
                    onChange={(event) => setLoginCode(event.target.value)}
                    placeholder="000000"
                    style={darkFieldStyle}
                    inputMode="numeric"
                    maxLength={6}
                  />
                </label>

                {smsError ? <div style={darkErrorStyle}>{smsError}</div> : null}

                <button
                  type="submit"
                  disabled={smsSubmitting || !loginCode.trim()}
                  style={goldButtonStyle(smsSubmitting || !loginCode.trim())}
                >
                  {smsSubmitting
                    ? "Kod Dogrulaniyor..."
                    : authPanelMode === "recovery"
                      ? "Kimligimi Dogrula ve Devam Et"
                      : "Kodu Dogrula"}
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
        padding: "24px",
        display: "grid",
        placeItems: "center",
      }}
    >
      <section
        style={{
          ...paperCardStyle,
          width: "min(460px, 100%)",
          padding: "28px",
          display: "grid",
          gap: "16px",
        }}
      >
        <div
          style={{
            height: "10px",
            borderRadius: "999px",
            background: "rgba(185, 116, 41, 0.12)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: "42%",
              height: "100%",
              borderRadius: "999px",
              background: "linear-gradient(90deg, var(--accent-strong), var(--accent))",
            }}
          />
        </div>
        <div
          style={{
            ...serifTitleStyle,
            fontSize: "2rem",
            lineHeight: 0.96,
            fontWeight: 700,
          }}
        >
          Giris masasi hazirlaniyor.
        </div>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
          Oturum modlari ve yonlendirme bilgileri yukleniyor. Hazir oldugunda seni dogrudan yeni
          panele alacagiz.
        </p>
      </section>
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

const labelStyle = {
  display: "grid",
  gap: "8px",
} satisfies CSSProperties;

const labelTitleStyle = {
  fontWeight: 800,
  fontSize: "0.92rem",
} satisfies CSSProperties;

const fieldStyle = {
  width: "100%",
  padding: "15px 16px",
  borderRadius: "18px",
  border: "1px solid rgba(62, 81, 107, 0.14)",
  background: "rgba(255,255,255,0.92)",
  color: "var(--text)",
  fontSize: "0.98rem",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.6)",
} satisfies CSSProperties;

const darkFieldStyle = {
  ...fieldStyle,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(255,255,255,0.08)",
  color: "#fff7ea",
  boxShadow: "none",
} satisfies CSSProperties;

const eyebrowStyle = {
  color: "var(--accent-strong)",
  fontWeight: 800,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  fontSize: "0.74rem",
} satisfies CSSProperties;

const cardBodyStyle = {
  margin: 0,
  color: "var(--muted)",
  lineHeight: 1.75,
  fontSize: "0.95rem",
} satisfies CSSProperties;

const noticeStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(185, 116, 41, 0.1)",
  border: "1px solid rgba(185, 116, 41, 0.18)",
  color: "#8f5a1f",
  fontWeight: 700,
} satisfies CSSProperties;

const errorStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(207,65,65,0.08)",
  color: "#b73636",
  border: "1px solid rgba(207,65,65,0.12)",
} satisfies CSSProperties;

const darkErrorStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(207,65,65,0.14)",
  color: "#ffd9d9",
  border: "1px solid rgba(255,128,128,0.16)",
} satisfies CSSProperties;

const successStyle = {
  padding: "12px 14px",
  borderRadius: "16px",
  background: "rgba(98, 165, 124, 0.16)",
  color: "#dcf4e4",
  border: "1px solid rgba(124, 208, 154, 0.16)",
} satisfies CSSProperties;

function primaryButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "15px 18px",
    borderRadius: "18px",
    border: "none",
    background: "linear-gradient(135deg, var(--accent-strong), var(--accent))",
    color: "#fffaf3",
    fontWeight: 800,
    fontSize: "0.98rem",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
    boxShadow: disabled ? "none" : "0 16px 26px rgba(185, 116, 41, 0.18)",
  };
}

function secondaryButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "14px 16px",
    borderRadius: "18px",
    border: "1px solid rgba(241,194,143,0.18)",
    background: "rgba(255,255,255,0.08)",
    color: "#fff4e5",
    fontWeight: 800,
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}

function goldButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "15px 18px",
    borderRadius: "18px",
    border: "none",
    background: "linear-gradient(135deg, rgba(241,194,143,0.98), rgba(185,116,41,0.96))",
    color: "#2f1b09",
    fontWeight: 900,
    fontSize: "0.98rem",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}

function ghostButtonStyle(disabled: boolean): CSSProperties {
  return {
    padding: "13px 15px",
    borderRadius: "16px",
    border: "1px solid rgba(15,95,215,0.14)",
    background: "rgba(255,255,255,0.9)",
    color: "#0f5fd7",
    fontWeight: 800,
    fontSize: "0.94rem",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}

function panelToggleStyle(active: boolean): CSSProperties {
  return {
    padding: "9px 14px",
    borderRadius: "999px",
    border: "none",
    background: active ? "rgba(241,194,143,0.98)" : "transparent",
    color: active ? "#2f1b09" : "rgba(255,247,234,0.74)",
    fontWeight: 800,
    fontSize: "0.82rem",
    cursor: "pointer",
  };
}
