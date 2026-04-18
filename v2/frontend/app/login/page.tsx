"use client";

import type { CSSProperties, FormEvent } from "react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { buildApiUrl, readStoredAuthNotice, writeStoredAuthNotice } from "../../lib/api";
import { resolveDefaultPath } from "../../lib/navigation";
import { isPreviewModeBrowser } from "../../lib/preview";

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

type LoginPilotStatusPayload = {
  localSetupSource?: "backend" | "frontend_local_doctor" | null;
  frontend?: {
    proxyConfigured?: boolean;
    backendReachable?: boolean;
    detail?: string;
    targetBaseUrl?: string | null;
    pilotHttpStatus?: number | null;
    pilotErrorDetail?: string | null;
  };
  backend?: {
    required_missing_env_vars?: string[];
    next_actions?: string[];
    pilot_accounts?: Array<{
      email: string;
      full_name: string;
      role: string;
      has_phone: boolean;
      must_change_password: boolean;
      default_password_active: boolean;
    }>;
  } | null;
  localSetup?: {
    ready?: boolean;
    backend_env_exists?: boolean;
    frontend_env_exists?: boolean;
    database_url_present?: boolean;
    runtime_database_url_present?: boolean;
    backend_env_database_url_present?: boolean;
    backend_restart_required?: boolean;
    backend_restart_reason?: string | null;
    default_auth_password_present?: boolean;
    default_auth_password_is_default?: boolean;
    frontend_env_needs_sync?: boolean;
    suggested_frontend_url?: string | null;
    suggested_api_url?: string | null;
    suggested_bootstrap_command?: string | null;
    suggested_bootstrap_with_db_command?: string | null;
    suggested_frontend_env_command?: string | null;
    suggested_scaffold_command?: string | null;
    suggested_env_write_command?: string | null;
    suggested_current_app_env_command?: string | null;
    suggested_backend_start_command?: string | null;
    suggested_backend_restart_command?: string | null;
    current_app_seed_detected?: boolean;
    current_app_seed_sources?: string[];
    current_app_seed_placeholders?: string[];
    blocking_items?: string[];
    warnings?: string[];
    next_actions?: string[];
    decision_status?: string;
    decision_headline?: string;
    decision_detail?: string;
    decision_command?: string | null;
  } | null;
};

type LocalLoginHint = {
  title: string;
  detail: string;
  command?: string;
};

type LocalReadyLogin = {
  accounts: Array<{
    email: string;
    full_name: string;
    role: string;
    mustChangePassword: boolean;
    defaultPasswordActive: boolean;
  }>;
  defaultPasswordPresent: boolean;
  defaultPasswordIsDefault: boolean;
};

function extractInlineCommand(value: string | undefined): string | null {
  if (!value) {
    return null;
  }
  const match = value.match(/`([^`]+)`/);
  return match?.[1] ?? null;
}

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
  const [authModesUnavailable, setAuthModesUnavailable] = useState(false);
  const [authPanelMode, setAuthPanelMode] = useState<"sms" | "recovery">("sms");
  const [phone, setPhone] = useState("");
  const [loginCode, setLoginCode] = useState("");
  const [recoveryNewPassword, setRecoveryNewPassword] = useState("");
  const [recoveryConfirmPassword, setRecoveryConfirmPassword] = useState("");
  const [smsSubmitting, setSmsSubmitting] = useState(false);
  const [smsError, setSmsError] = useState("");
  const [smsMessage, setSmsMessage] = useState("");
  const [maskedPhone, setMaskedPhone] = useState("");
  const [localPilotStatus, setLocalPilotStatus] = useState<LoginPilotStatusPayload | null>(null);
  const [copiedLocalHintCommand, setCopiedLocalHintCommand] = useState(false);
  const recoveryPanelRef = useRef<HTMLDivElement | null>(null);
  const recoveryPhoneInputRef = useRef<HTMLInputElement | null>(null);

  const nextPath = useMemo(() => searchParams.get("next") || "", [searchParams]);
  const runningOnLocalhost = useMemo(
    () =>
      typeof window !== "undefined" &&
      (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"),
    [],
  );

  useEffect(() => {
    if (!loading && user) {
      router.replace(user.must_change_password ? "/account" : nextPath || resolveDefaultPath(user.allowed_actions));
    }
  }, [loading, user, router, nextPath]);

  useEffect(() => {
    let active = true;

    async function loadAuthModes() {
      if (isPreviewModeBrowser()) {
        if (active) {
          setSmsLoginEnabled(true);
          setAuthModesUnavailable(false);
        }
        return;
      }
      try {
        const response = await fetch(buildApiUrl("/auth/modes"), { cache: "no-store" });
        if (!response.ok) {
          if (active) {
            setSmsLoginEnabled(false);
            setAuthModesUnavailable(true);
          }
          return;
        }
        const payload = (await response.json().catch(() => null)) as { sms_login?: boolean } | null;
        if (active) {
          setSmsLoginEnabled(Boolean(payload?.sms_login));
          setAuthModesUnavailable(false);
        }
      } catch {
        if (active) {
          setSmsLoginEnabled(false);
          setAuthModesUnavailable(true);
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

  useEffect(() => {
    if (!runningOnLocalhost || isPreviewModeBrowser()) {
      return;
    }
    let active = true;

    async function loadLocalPilotStatus() {
      try {
        const response = await fetch("/api/pilot-status", { cache: "no-store" });
        if (!response.ok) {
          return;
        }
        const payload = (await response.json().catch(() => null)) as LoginPilotStatusPayload | null;
        if (active && payload) {
          setLocalPilotStatus(payload);
        }
      } catch {
        if (active) {
          setLocalPilotStatus(null);
        }
      }
    }

    void loadLocalPilotStatus();
    return () => {
      active = false;
    };
  }, [runningOnLocalhost]);

  useEffect(() => {
    if (!smsLoginEnabled || authPanelMode !== "recovery") {
      return;
    }
    const frameId = window.requestAnimationFrame(() => {
      recoveryPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      recoveryPhoneInputRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [authPanelMode, smsLoginEnabled]);

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
      setError(authError instanceof Error ? authError.message : "Giriş yapilamadi.");
    } finally {
      setSubmitting(false);
    }
  }

  async function requestPasswordResetCode(phoneValue: string): Promise<{ message: string; masked_phone: string }> {
    if (isPreviewModeBrowser()) {
      return {
        message: "Preview modunda şifre kurtarma kodu hazırlandı.",
        masked_phone: phoneValue || "05xxxxxxxxx",
      };
    }
    const response = await fetch(buildApiUrl("/auth/request-password-reset-code"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ phone: phoneValue }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string; masked_phone?: string }
      | null;

    if (!response.ok || !payload?.message || !payload?.masked_phone) {
      throw new Error(payload?.detail || "Şifre sıfırlama kodu gonderilemedi.");
    }

    return {
      message: payload.message,
      masked_phone: payload.masked_phone,
    };
  }

  async function resetPasswordWithCode(
    phoneValue: string,
    codeValue: string,
    nextPassword: string,
  ): Promise<{ message: string }> {
    if (isPreviewModeBrowser()) {
      return { message: "Preview modunda şifre sıfırlama tamamlandı. Yeni şifrenle giriş yapabilirsin." };
    }
    const response = await fetch(buildApiUrl("/auth/reset-password-with-code"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        phone: phoneValue,
        code: codeValue,
        new_password: nextPassword,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok || !payload?.message) {
      throw new Error(payload?.detail || "Şifre sifirlanamadi.");
    }

    return { message: payload.message };
  }

  async function handleSendCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSmsSubmitting(true);
    setSmsError("");
    setNotice("");
    try {
      const payload =
        authPanelMode === "recovery" ? await requestPasswordResetCode(phone) : await requestPhoneCode(phone);
      setMaskedPhone(payload.masked_phone);
      setSmsMessage(
        authPanelMode === "recovery"
          ? "Kimligini doğrulaman için kod hazır. Aynı kartta yeni şifreni belirleyip hesabına geri dönebilirsin."
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
    if (authPanelMode === "recovery" && recoveryNewPassword !== recoveryConfirmPassword) {
      setSmsError("Yeni şifre ve tekrar şifresi aynı olmalı.");
      return;
    }
    setSmsSubmitting(true);
    setSmsError("");
    setNotice("");
    try {
      if (authPanelMode === "recovery") {
        const recoveryPhone = phone.trim();
        const nextPassword = recoveryNewPassword;
        const payload = await resetPasswordWithCode(recoveryPhone, loginCode, nextPassword);
        setIdentity((currentIdentity) => currentIdentity.trim() || recoveryPhone);
        setPassword("");
        setNotice(payload.message);
        setSmsMessage("");
        setMaskedPhone("");
        setLoginCode("");
        setRecoveryNewPassword("");
        setRecoveryConfirmPassword("");
        setPhone("");
        switchAuthPanelMode("sms");

        const loggedInUser = await login(recoveryPhone, nextPassword);
        router.replace(
          loggedInUser.must_change_password ? "/account" : nextPath || resolveDefaultPath(loggedInUser.allowed_actions),
        );
        return;
      }
      const loggedInUser = await verifyPhoneCode(phone, loginCode);
      router.replace(
        loggedInUser.must_change_password ? "/account" : nextPath || resolveDefaultPath(loggedInUser.allowed_actions),
      );
    } catch (verifyError) {
      setSmsError(verifyError instanceof Error ? verifyError.message : "SMS kodu doğrulanamadı.");
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
    setRecoveryNewPassword("");
    setRecoveryConfirmPassword("");
  }

  async function copyLocalHintCommand(command: string) {
    try {
      await navigator.clipboard.writeText(command);
      setCopiedLocalHintCommand(true);
      window.setTimeout(() => setCopiedLocalHintCommand(false), 1800);
    } catch {
      setCopiedLocalHintCommand(false);
    }
  }

  function fillLocalCredentials(account: LocalReadyLogin["accounts"][number]) {
    setIdentity(account.email);
    if (localReadyLogin?.defaultPasswordPresent && localReadyLogin.defaultPasswordIsDefault && account.defaultPasswordActive) {
      setPassword("123456");
    } else {
      setPassword("");
    }
    setError("");
    setNotice(
      localReadyLogin?.defaultPasswordIsDefault && account.defaultPasswordActive
        ? "Yerel sqlite hesabı forma dolduruldu. Bu hesapta varsayılan yerel şifre şu an 123456."
        : account.mustChangePassword
          ? "Yerel sqlite hesabı forma dolduruldu. Bu hesap geçici şifre bekliyor; güncel şifreyi biliyorsan elle girmen gerekecek."
          : "Yerel sqlite hesabı forma dolduruldu. Bu hesapta varsayılan şifre artık aktif görünmüyor; en son belirlenen şifreyi kullanman gerekecek.",
    );
  }

  const localLoginHint = useMemo<LocalLoginHint | null>(() => {
    if (!runningOnLocalhost || isPreviewModeBrowser()) {
      return null;
    }

    const frontendStatus = localPilotStatus?.frontend;
    const localSetup = localPilotStatus?.localSetup;
    if (!frontendStatus) {
      return null;
    }

    if (localSetup?.frontend_env_needs_sync && localSetup.suggested_frontend_env_command) {
      return {
        title: "Ön yüz ortam dosyası yerel hedefle yeniden hizalanmalı.",
        detail:
          "Doctor şu an ön yüz geçiş ayarının canlı yerel API önerisiyle aynı olmadığını görüyor. `.env.local` dosyasını tek komutla doğru hedefe çekebiliriz.",
        command: localSetup.suggested_frontend_env_command,
      };
    }

    if (!frontendStatus.proxyConfigured && localSetup?.suggested_frontend_env_command) {
      return {
        title: "Ön yüz geçiş ortamı henüz hazır değil.",
        detail:
          "Giriş ekranı çalışıyor ama arka uç hedefi ön yüz tarafında eksik. Doctor yerel API adresine göre `.env.local` dosyasını tek komutla yeniden yazabilir.",
        command: localSetup.suggested_frontend_env_command,
      };
    }

    if (!frontendStatus.backendReachable) {
      return {
        title: "Yerel arka uç henüz ayakta değil.",
        detail:
          "Ön yüz 127.0.0.1:8000 hedefini bulamıyor. Bu durumda giriş ve şifre kurtarma çalışmaz; tanıtım için ön izleme, gerçek deneme için arka uç gerekir.",
        command: localSetup?.suggested_backend_start_command || "cd v2/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      };
    }

    if (localSetup) {
      const blockingItems = localSetup.blocking_items ?? [];
      const nextActions = localSetup.next_actions ?? [];
      const backendNeedsRestartForEnv = Boolean(localSetup.backend_restart_required) || (
        localPilotStatus?.localSetupSource !== "backend" &&
        localSetup.database_url_present &&
        frontendStatus.pilotHttpStatus === 503 &&
        (frontendStatus.pilotErrorDetail?.includes("DATABASE_URL") || frontendStatus.detail?.includes("DATABASE_URL"))
      );
      const setupSourceDetail =
        localPilotStatus?.localSetupSource === "frontend_local_doctor"
          ? " Teşhis ön yüz tarafında taze doctor yedeğiyle üretildi; arka ucu yeniden başlatınca uç nokta da aynı seviyeye gelir."
          : "";

      if (backendNeedsRestartForEnv) {
        return {
          title: "Arka uç ortamı yazıldı ama çalışan süreç yeniden başlatılmalı.",
          detail:
            (localSetup.backend_restart_reason ||
              "Doctor `backend/.env` tarafında veritabanı bağlantısını görüyor; buna rağmen çalışan arka uç hâlâ `DATABASE_URL` eksiği dönüyor. Bu genelde ortam yazıldıktan sonra uvicorn süreci yeniden başlatılmadığında olur.") +
            setupSourceDetail,
          command:
            localSetup.suggested_backend_restart_command ||
            localSetup.suggested_backend_start_command ||
            "cd v2/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
        };
      }

      if (localSetup.decision_headline) {
        const targetDetail =
          localSetup.suggested_frontend_url || localSetup.suggested_api_url
            ? ` Doctor hedefleri ön yüz=${localSetup.suggested_frontend_url || "bilinmiyor"} ve api=${localSetup.suggested_api_url || "bilinmiyor"} olarak görüyor.`
            : "";
        return {
          title: localSetup.decision_headline,
          detail:
            (localSetup.decision_detail || blockingItems[0] || "Yerel kurulumda doctor tarafında yeni bir eylem önerisi var.") +
            targetDetail +
            setupSourceDetail,
          command:
            localSetup.decision_command ||
            extractInlineCommand(nextActions[0]) ||
            localSetup.suggested_bootstrap_command ||
            localSetup.suggested_backend_start_command ||
            undefined,
        };
      }

      if (blockingItems.length > 0) {
        return {
          title: "Yerel kurulumda hâlâ bir blokaj var.",
          detail: `${blockingItems[0]}${setupSourceDetail}`,
          command: extractInlineCommand(nextActions[0]) || "python v2/scripts/local_v2_doctor.py",
        };
      }
    }

    const requiredMissing = localPilotStatus?.backend?.required_missing_env_vars ?? [];
    const pilotErrorDetail = frontendStatus.pilotErrorDetail || "";
    const databaseMissing =
      requiredMissing.includes("CK_V2_DATABASE_URL") || pilotErrorDetail.includes("DATABASE_URL");

    if (databaseMissing) {
      return {
        title: "Arka uç ayakta ama veritabanı ortamı eksik.",
        detail:
          "API cevap veriyor fakat `DATABASE_URL` olmadığı için gerçek giriş tamamlanamaz. Doctor komutuyla eksik ortamı görüp `backend/.env` dosyasını hazırlayabiliriz.",
        command: "python v2/scripts/local_v2_doctor.py",
      };
    }

    if (frontendStatus.pilotHttpStatus && !localPilotStatus?.backend) {
      return {
        title: "Arka uç ayakta ama hazırlık katmanı henüz temiz değil.",
        detail: frontendStatus.pilotErrorDetail || frontendStatus.detail || "Pilot durumu tam dönemedi.",
      };
    }

    return null;
  }, [localPilotStatus, runningOnLocalhost]);

  const localReadyLogin = useMemo<LocalReadyLogin | null>(() => {
    if (!runningOnLocalhost || isPreviewModeBrowser()) {
      return null;
    }

    const localSetup = localPilotStatus?.localSetup;
    const frontendStatus = localPilotStatus?.frontend;
    const pilotAccounts = localPilotStatus?.backend?.pilot_accounts ?? [];
    const sqliteFallbackReady =
      (localSetup?.warnings ?? []).some((item) => item.toLowerCase().includes("sqlite fallback")) ||
      (localSetup?.decision_headline ?? "").toLowerCase().includes("sqlite");

    if (!sqliteFallbackReady || !frontendStatus?.backendReachable || pilotAccounts.length === 0) {
      return null;
    }

    return {
      accounts: pilotAccounts.slice(0, 3).map((account) => ({
        email: account.email,
        full_name: account.full_name,
        role: account.role,
        mustChangePassword: Boolean(account.must_change_password),
        defaultPasswordActive: Boolean(account.default_password_active),
      })),
      defaultPasswordPresent: Boolean(localSetup?.default_auth_password_present),
      defaultPasswordIsDefault: Boolean(localSetup?.default_auth_password_is_default),
    };
  }, [localPilotStatus, runningOnLocalhost]);

  const recoveryModeActive = authPanelMode === "recovery";
  const smsPanelActive = smsLoginEnabled && authPanelMode === "sms";
  const supportPanelVisible = smsLoginEnabled || authModesUnavailable;
  const supportCardTitle = recoveryModeActive ? "Şifre kurtarma" : smsPanelActive ? "SMS ile giriş" : "Destek akışı";
  const supportCardBody = recoveryModeActive
    ? "Kayıtlı telefonunla kod al, yeni şifreni belirle ve girişe dön."
    : smsPanelActive
      ? "Tek kullanımlık kodla hızlı doğrulama yap."
      : "İhtiyaç olursa SMS veya şifre kurtarma akışı buradan açılır.";

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "24px",
        display: "grid",
        placeItems: "center",
        background:
          "radial-gradient(circle at top left, rgba(18, 59, 116, 0.08), transparent 26%), linear-gradient(180deg, #f7f2e8 0%, #f2ece1 100%)",
      }}
    >
      <section
        style={{
          width: "min(1040px, 100%)",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "18px",
          alignItems: "start",
        }}
      >
        <article
          style={{
            padding: "30px",
            borderRadius: "34px",
            background: "linear-gradient(160deg, rgba(20, 35, 58, 0.98), rgba(28, 58, 97, 0.96))",
            boxShadow: "var(--shadow-deep)",
            color: "#fff7ea",
            position: "relative",
            overflow: "hidden",
            display: "grid",
            gap: "24px",
            minHeight: "100%",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "auto auto -110px -80px",
              width: "240px",
              height: "240px",
              borderRadius: "999px",
              background: "radial-gradient(circle, rgba(244, 175, 74, 0.28), transparent 70%)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: "20px 22px auto auto",
              width: "160px",
              height: "160px",
              borderRadius: "999px",
              background: "radial-gradient(circle, rgba(255,255,255,0.08), transparent 72%)",
            }}
          />

          <div style={{ position: "relative", display: "grid", gap: "18px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                flexWrap: "wrap",
              }}
            >
              <div
                style={{
                  width: "58px",
                  height: "58px",
                  borderRadius: "20px",
                  background: "linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06))",
                  border: "1px solid rgba(255,255,255,0.14)",
                  display: "grid",
                  placeItems: "center",
                  boxShadow: "0 18px 34px rgba(10, 20, 35, 0.24)",
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "14px",
                    background: "linear-gradient(180deg, #f6d6a9, #c9852b)",
                    display: "grid",
                    placeItems: "center",
                    color: "#1d2f4b",
                    fontWeight: 900,
                    fontSize: "0.98rem",
                    letterSpacing: "0.08em",
                    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.3)",
                  }}
                >
                  CK
                </div>
              </div>
              <div style={{ display: "grid", gap: "4px" }}>
                <div
                  style={{
                    color: "#f2cf9e",
                    fontSize: "0.7rem",
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    fontWeight: 800,
                  }}
                >
                  Çat Kapında
                </div>
                <div
                  style={{
                    ...serifTitleStyle,
                    fontSize: "1.28rem",
                    lineHeight: 0.96,
                    fontWeight: 700,
                    color: "#fff7ea",
                  }}
                >
                  CRM
                </div>
              </div>
            </div>
            <div
              style={{
                display: "inline-flex",
                width: "fit-content",
                padding: "6px 11px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#f2cf9e",
                fontSize: "0.66rem",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                fontWeight: 800,
              }}
            >
              operasyon merkezi
            </div>
            <div style={{ display: "grid", gap: "10px" }}>
              <h1
                style={{
                  ...serifTitleStyle,
                  margin: 0,
                  fontSize: "clamp(2.5rem, 5vw, 3.7rem)",
                  lineHeight: 0.94,
                  fontWeight: 700,
                  maxWidth: "11ch",
                }}
              >
                Çat Kapında CRM
              </h1>
              <p
                style={{
                  margin: 0,
                  maxWidth: "48ch",
                  color: "rgba(255, 247, 234, 0.76)",
                  lineHeight: 1.68,
                  fontSize: "0.96rem",
                }}
              >
                Çat Kapında CRM; restoran, saha ekipleri ve merkez operasyon için günlük yönetimi tek
                ekranda toplar. Kadro, puantaj, ekipman, kesinti ve finansal görünüm aynı veri akışından
                beslenir.
              </p>
            </div>
          </div>

          <div
            style={{
              position: "relative",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "12px",
            }}
          >
            {[
              ["Şube Operasyonu", "Restoran durumu, aktif kadro ve günlük saha akışı tek merkezden izlenir."],
              ["Personel ve Ekipman", "Kurye, araç, zimmet ve geçmiş hareketler bağlı operasyon kaydıyla tutulur."],
              ["Rapor ve Finans", "Hakediş, maliyet ve operasyon farkı aynı karar yüzeyinde okunur."],
            ].map(([title, text]) => (
              <article
                key={title}
                style={{
                  padding: "15px 14px",
                  borderRadius: "18px",
                  background: "rgba(255,255,255,0.07)",
                  border: "1px solid rgba(255,255,255,0.09)",
                  display: "grid",
                  gap: "6px",
                }}
              >
                <div style={{ color: "#fff4e5", fontWeight: 800, fontSize: "0.9rem" }}>{title}</div>
                <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.55, fontSize: "0.86rem" }}>
                  {text}
                </div>
              </article>
            ))}
          </div>

          <div
            style={{
              position: "relative",
              display: "grid",
              gap: "10px",
              alignContent: "start",
            }}
          >
            {[
              "Şube, personel, puantaj ve rapor modülleri aynı operasyon omurgasında birlikte çalışır.",
              "Saha hareketleri ile merkez kararları aynı CRM içinde birbirine bağlı görünür.",
              "Yönetici ekipleri günlük operasyonu, kapasiteyi ve finansal resmi aynı yerden takip eder.",
            ].map((item) => (
              <div
                key={item}
                style={{
                  display: "flex",
                  gap: "10px",
                  alignItems: "start",
                  padding: "12px 14px",
                  borderRadius: "16px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "999px",
                    marginTop: "7px",
                    background: "#f2cf9e",
                    flexShrink: 0,
                  }}
                />
                <div style={{ color: "rgba(255,247,234,0.78)", lineHeight: 1.58, fontSize: "0.9rem" }}>{item}</div>
              </div>
            ))}
          </div>
        </article>

        <div style={{ display: "grid", gap: "14px", alignContent: "start" }}>
          <section
            style={{
              ...paperCardStyle,
              padding: "24px",
              display: "grid",
              gap: "12px",
              background: "linear-gradient(180deg, rgba(255,253,247,0.99), rgba(249,245,237,0.97))",
            }}
          >
            <div style={{ display: "grid", gap: "6px" }}>
              <div style={eyebrowStyle}>Giriş</div>
              <h2
                style={{
                  ...serifTitleStyle,
                  margin: 0,
                  fontSize: "1.72rem",
                  lineHeight: 0.98,
                  fontWeight: 700,
                }}
              >
                Hesabınla devam et
              </h2>
              <p style={cardBodyStyle}>
                E-posta ya da telefon ve şifrenle oturumu aç. Gerekirse aşağıdaki karttan SMS veya şifre
                kurtarma akışına geçebilirsin.
              </p>
            </div>

            {localLoginHint ? (
              <div style={{ ...infoBannerStyle, padding: "12px 14px", fontSize: "0.9rem" }}>
                <div style={{ display: "grid", gap: "6px", maxWidth: "54ch" }}>
                  <strong>{localLoginHint.title}</strong>
                  <span>{localLoginHint.detail}</span>
                  {localLoginHint.command ? <code style={inlineCodeStyle}>{localLoginHint.command}</code> : null}
                </div>
                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  {localLoginHint.command ? (
                    <button
                      type="button"
                      onClick={() => void copyLocalHintCommand(localLoginHint.command!)}
                      style={infoBannerButtonStyle}
                    >
                      {copiedLocalHintCommand ? "Komut Kopyalandı" : "Komutu Kopyala"}
                    </button>
                  ) : null}
                  <Link href="/status" style={infoBannerLinkStyle}>
                    Durum
                  </Link>
                  <Link href="/preview" style={secondaryInfoBannerLinkStyle}>
                    Ön İzleme
                  </Link>
                </div>
              </div>
            ) : authModesUnavailable ? (
              <div style={{ ...infoBannerStyle, padding: "12px 14px", fontSize: "0.9rem" }}>
                <div style={{ display: "grid", gap: "5px" }}>
                  <strong>Bu ekran gerçek v2 giriş yüzeyi.</strong>
                  <span>Arka uç bağlı değilse SMS ve kurtarma akışları çalışmaz; sadece ön yüzü gezebilirsin.</span>
                </div>
                {runningOnLocalhost ? (
                  <Link href="/preview" style={infoBannerLinkStyle}>
                    Ön İzlemeye Git
                  </Link>
                ) : null}
              </div>
            ) : null}

            {localReadyLogin ? (
              <div
                style={{
                  borderRadius: "18px",
                  border: "1px solid rgba(15, 95, 215, 0.12)",
                  background: "linear-gradient(180deg, rgba(239,246,255,0.94), rgba(255,255,255,0.98))",
                  padding: "14px",
                  display: "grid",
                  gap: "10px",
                }}
              >
                <div style={{ display: "grid", gap: "4px" }}>
                  <strong style={{ color: "#0f3f91" }}>Yerel giriş hazır</strong>
                  <span style={{ color: "#4f6283", lineHeight: 1.58, fontSize: "0.9rem" }}>
                    Bu makinede sqlite destekli örnek hesaplarla akışı hızlıca deneyebiliriz.
                  </span>
                </div>
                <div style={{ display: "grid", gap: "8px" }}>
                  {localReadyLogin.accounts.map((account) => (
                    <div
                      key={account.email}
                      style={{
                        borderRadius: "14px",
                        border: "1px solid rgba(15, 95, 215, 0.1)",
                        background: "rgba(255,255,255,0.84)",
                        padding: "11px 12px",
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <div style={{ display: "grid", gap: "2px" }}>
                        <strong style={{ color: "#16274a" }}>{account.full_name}</strong>
                        <span style={{ color: "#5f7294", fontSize: "0.88rem" }}>
                          {account.role} · {account.email}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => fillLocalCredentials(account)}
                        style={{
                          borderRadius: "10px",
                          border: "1px solid rgba(15, 95, 215, 0.16)",
                          background: "rgba(15, 95, 215, 0.08)",
                          color: "#0f3f91",
                          fontWeight: 800,
                          padding: "8px 12px",
                          cursor: "pointer",
                        }}
                      >
                        Formu Doldur
                      </button>
                    </div>
                  ))}
                </div>
                <div style={{ color: "#4f6283", lineHeight: 1.58, fontSize: "0.88rem" }}>
                  {localReadyLogin.defaultPasswordIsDefault &&
                  localReadyLogin.accounts.some((account) => account.defaultPasswordActive)
                    ? "Varsayılan şifre aktif hesaplarda yerel parola 123456 olabilir."
                    : localReadyLogin.defaultPasswordPresent
                      ? "Şifre daha önce değişmiş olabilir; güncel parolayı elle girmen gerekir."
                      : "Şifre tanımlı görünmüyor; backend/.env tarafını kontrol et."}
                </div>
              </div>
            ) : null}

            {notice ? <div style={noticeStyle}>{notice}</div> : null}

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
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
                <span style={labelTitleStyle}>Şifre</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Şifreni gir"
                  style={fieldStyle}
                />
              </label>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "10px",
                  alignItems: "center",
                  flexWrap: "wrap",
                  color: "var(--muted)",
                  fontSize: "0.9rem",
                }}
              >
                <span>Yetkine uygun modüle yönlendirilirsin.</span>
                {smsLoginEnabled ? (
                  <button type="button" onClick={() => switchAuthPanelMode("recovery")} style={inlineLinkButtonStyle}>
                    Şifremi unuttum
                  </button>
                ) : authModesUnavailable && runningOnLocalhost ? (
                  <Link href="/preview" style={inlinePreviewLinkStyle}>
                    Ön izlemeyi aç
                  </Link>
                ) : null}
              </div>

              {error ? <div style={errorStyle}>{error}</div> : null}

              <button type="submit" disabled={submitting || loading} style={primaryButtonStyle(submitting || loading)}>
                {submitting ? "Giriş yapılıyor..." : "Giriş Yap"}
              </button>
            </form>
          </section>

          {supportPanelVisible ? (
            <section
              style={{
                ...paperCardStyle,
                padding: "20px",
                display: "grid",
                gap: "14px",
                background:
                  recoveryModeActive
                    ? "linear-gradient(180deg, rgba(24,42,68,0.98), rgba(32,56,86,0.96))"
                    : "linear-gradient(180deg, rgba(248,250,255,0.98), rgba(255,252,246,0.96))",
                color: recoveryModeActive ? "#fff7ea" : "var(--text)",
                border: recoveryModeActive
                  ? "1px solid rgba(15,95,215,0.18)"
                  : "1px solid rgba(15,95,215,0.12)",
              }}
            >
              <div style={{ display: "grid", gap: "10px" }}>
                <div
                  style={{
                    display: "inline-flex",
                    padding: "6px",
                    borderRadius: "999px",
                    background: recoveryModeActive ? "rgba(255,255,255,0.08)" : "rgba(15,95,215,0.08)",
                    border: recoveryModeActive
                      ? "1px solid rgba(255,255,255,0.08)"
                      : "1px solid rgba(15,95,215,0.12)",
                    gap: "6px",
                    width: "fit-content",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => switchAuthPanelMode("sms")}
                    style={supportToggleStyle(smsPanelActive, recoveryModeActive)}
                  >
                    SMS ile Giriş
                  </button>
                  <button
                    type="button"
                    onClick={() => switchAuthPanelMode("recovery")}
                    style={supportToggleStyle(recoveryModeActive, recoveryModeActive)}
                  >
                    Şifre Kurtarma
                  </button>
                </div>
                <div
                  style={{
                    color: recoveryModeActive ? "#f2cf9e" : "#0f5fd7",
                    fontWeight: 800,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    fontSize: "0.72rem",
                  }}
                >
                  {supportCardTitle}
                </div>
                <h2
                  style={{
                    ...serifTitleStyle,
                    margin: 0,
                    fontSize: "1.45rem",
                    lineHeight: 0.98,
                    fontWeight: 700,
                  }}
                >
                  {recoveryModeActive
                    ? "Telefon koduyla şifreni yenile."
                    : smsPanelActive
                      ? "Tek kullanımlık kodla hızlı doğrulama."
                      : "İhtiyaç olduğunda destek akışına geç."}
                </h2>
                <p
                  style={{
                    margin: 0,
                    color: recoveryModeActive ? "rgba(255,247,234,0.72)" : "var(--muted)",
                    lineHeight: 1.58,
                    fontSize: "0.92rem",
                  }}
                >
                  {supportCardBody}
                </p>
              </div>

              {recoveryModeActive ? (
                <>
                  <form onSubmit={handleSendCode} style={{ display: "grid", gap: "12px" }}>
                    <label style={labelStyle}>
                      <span style={{ ...labelTitleStyle, color: "#fff4e5" }}>Kayitli Telefon</span>
                      <input
                        ref={recoveryPhoneInputRef}
                        value={phone}
                        onChange={(event) => setPhone(event.target.value)}
                        placeholder="05xxxxxxxxx"
                        style={darkFieldStyle}
                      />
                    </label>
                    <button
                      type="submit"
                      disabled={smsSubmitting || !phone.trim()}
                      style={secondaryButtonStyle(smsSubmitting || !phone.trim())}
                    >
                      {smsSubmitting ? "Kod hazırlanıyor..." : "Doğrulama Kodu Gönder"}
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
                    <label style={labelStyle}>
                      <span style={{ ...labelTitleStyle, color: "#fff4e5" }}>Yeni Sifre</span>
                      <input
                        type="password"
                        value={recoveryNewPassword}
                        onChange={(event) => setRecoveryNewPassword(event.target.value)}
                        placeholder="En az 6 karakter"
                        style={darkFieldStyle}
                      />
                    </label>
                    <label style={labelStyle}>
                      <span style={{ ...labelTitleStyle, color: "#fff4e5" }}>Yeni Sifre Tekrar</span>
                      <input
                        type="password"
                        value={recoveryConfirmPassword}
                        onChange={(event) => setRecoveryConfirmPassword(event.target.value)}
                        placeholder="Yeni sifreni tekrar gir"
                        style={darkFieldStyle}
                      />
                    </label>

                    {smsError ? <div style={darkErrorStyle}>{smsError}</div> : null}

                    <button
                      type="submit"
                      disabled={
                        smsSubmitting ||
                        !loginCode.trim() ||
                        !recoveryNewPassword.trim() ||
                        !recoveryConfirmPassword.trim()
                      }
                      style={goldButtonStyle(
                        smsSubmitting ||
                          !loginCode.trim() ||
                          !recoveryNewPassword.trim() ||
                          !recoveryConfirmPassword.trim(),
                      )}
                    >
                      {smsSubmitting ? "Kod doğrulanıyor..." : "Şifreyi Yenile"}
                    </button>
                  </form>
                </>
              ) : smsPanelActive ? (
                <>
                  <form onSubmit={handleSendCode} style={{ display: "grid", gap: "12px" }}>
                    <label style={labelStyle}>
                      <span style={labelTitleStyle}>Telefon</span>
                      <input
                        ref={recoveryPhoneInputRef}
                        value={phone}
                        onChange={(event) => setPhone(event.target.value)}
                        placeholder="05xxxxxxxxx"
                        style={fieldStyle}
                      />
                    </label>
                    <button
                      type="submit"
                      disabled={smsSubmitting || !phone.trim()}
                      style={ghostButtonStyle(smsSubmitting || !phone.trim())}
                    >
                      {smsSubmitting ? "Kod hazırlanıyor..." : "SMS Kodu Gönder"}
                    </button>
                  </form>

                  {smsMessage ? (
                    <div style={noticeStyle}>
                      {smsMessage}
                      {maskedPhone ? ` (${maskedPhone})` : ""}
                    </div>
                  ) : null}

                  <form onSubmit={handleVerifyCode} style={{ display: "grid", gap: "12px" }}>
                    <label style={labelStyle}>
                      <span style={labelTitleStyle}>6 Haneli Kod</span>
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

                    <button
                      type="submit"
                      disabled={smsSubmitting || !loginCode.trim()}
                      style={primaryButtonStyle(smsSubmitting || !loginCode.trim())}
                    >
                      {smsSubmitting ? "Kod doğrulanıyor..." : "Kodu Doğrula"}
                    </button>
                  </form>
                </>
              ) : (
                <div
                  style={{
                    padding: "14px 16px",
                    borderRadius: "18px",
                    background: "rgba(15,95,215,0.06)",
                    border: "1px solid rgba(15,95,215,0.1)",
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  <div style={{ color: "#0f5fd7", fontWeight: 800 }}>Ek Giriş Seçenekleri</div>
                  <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                    SMS girişi ve şifre kurtarma aynı alanda hazır. İhtiyaç olduğunda yukarıdaki düğmelerden ilgili akışa geçebilirsin.
                  </div>
                  {authModesUnavailable && runningOnLocalhost ? (
                    <Link href="/preview" style={recoveryFallbackLinkStyle}>
                      Yerel ön izlemeyi aç
                    </Link>
                  ) : null}
                </div>
              )}
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
          Giriş masası hazırlanıyor.
        </div>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
          Oturum modlari ve yönlendirme bilgileri yükleniyor. Hazır oldugunda seni doğrudan yeni
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

const infoBannerStyle = {
  padding: "14px 16px",
  borderRadius: "18px",
  border: "1px solid rgba(15,95,215,0.14)",
  background: "linear-gradient(180deg, rgba(239,246,255,0.98), rgba(255,250,244,0.96))",
  color: "var(--text)",
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "start",
  flexWrap: "wrap",
  lineHeight: 1.6,
  fontSize: "0.92rem",
} satisfies CSSProperties;

const infoBannerLinkStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "10px 14px",
  borderRadius: "999px",
  background: "rgba(15,95,215,0.1)",
  border: "1px solid rgba(15,95,215,0.14)",
  color: "#0f5fd7",
  fontWeight: 800,
  textDecoration: "none",
  whiteSpace: "nowrap",
} satisfies CSSProperties;

const secondaryInfoBannerLinkStyle = {
  ...infoBannerLinkStyle,
  background: "rgba(255,255,255,0.78)",
  color: "var(--text)",
} satisfies CSSProperties;

const infoBannerButtonStyle = {
  ...infoBannerLinkStyle,
  cursor: "pointer",
} satisfies CSSProperties;

const inlineCodeStyle = {
  display: "inline-flex",
  width: "fit-content",
  padding: "8px 10px",
  borderRadius: "12px",
  background: "rgba(16, 24, 40, 0.08)",
  border: "1px solid rgba(16, 24, 40, 0.08)",
  color: "var(--text)",
  fontSize: "0.84rem",
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

const inlineLinkButtonStyle = {
  padding: 0,
  border: "none",
  background: "transparent",
  color: "#0f5fd7",
  fontWeight: 800,
  fontSize: "0.92rem",
  cursor: "pointer",
} satisfies CSSProperties;

const inlinePreviewLinkStyle = {
  color: "#0f5fd7",
  fontWeight: 800,
  fontSize: "0.92rem",
  textDecoration: "none",
} satisfies CSSProperties;

function supportToggleStyle(active: boolean, darkMode: boolean): CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: "999px",
    border: "none",
    background: active
      ? darkMode
        ? "rgba(241,194,143,0.96)"
        : "rgba(15,95,215,0.12)"
      : "transparent",
    color: active ? (darkMode ? "#2f1b09" : "#0f5fd7") : darkMode ? "rgba(255,247,234,0.78)" : "var(--muted)",
    fontWeight: 800,
    fontSize: "0.82rem",
    cursor: "pointer",
  };
}

function heroQuickActionStyle(active: boolean): CSSProperties {
  return {
    padding: "13px 16px",
    borderRadius: "999px",
    border: active ? "1px solid rgba(241,194,143,0.24)" : "1px solid rgba(255,255,255,0.14)",
    background: active
      ? "linear-gradient(135deg, rgba(241,194,143,0.98), rgba(185,116,41,0.96))"
      : "rgba(255,255,255,0.08)",
    color: active ? "#2f1b09" : "#fff4e5",
    fontWeight: 900,
    fontSize: "0.92rem",
    cursor: "pointer",
    boxShadow: active ? "0 16px 30px rgba(185,116,41,0.18)" : "none",
  };
}

function heroSecondaryActionStyle(active: boolean): CSSProperties {
  return {
    padding: "13px 16px",
    borderRadius: "999px",
    border: "1px solid rgba(255,255,255,0.12)",
    background: active ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.06)",
    color: "#fff4e5",
    fontWeight: 800,
    fontSize: "0.9rem",
    cursor: "pointer",
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

function recoveryCtaStyle(active: boolean): CSSProperties {
  return {
    padding: "14px 18px",
    borderRadius: "18px",
    border: active ? "1px solid rgba(15,95,215,0.18)" : "1px solid rgba(15,95,215,0.14)",
    background: active
      ? "linear-gradient(135deg, rgba(15,95,215,0.12), rgba(255,255,255,0.9))"
      : "rgba(255,255,255,0.92)",
    color: "#0f5fd7",
    fontWeight: 900,
    fontSize: "0.94rem",
    cursor: "pointer",
    boxShadow: active ? "0 16px 30px rgba(15,95,215,0.14)" : "none",
  };
}

const recoveryFallbackLinkStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid rgba(15,95,215,0.12)",
  background: "rgba(15,95,215,0.08)",
  color: "#0f5fd7",
  fontWeight: 800,
  textDecoration: "none",
} satisfies CSSProperties;
