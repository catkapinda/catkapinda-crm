"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch, readStoredAuthNotice, writeStoredAuthNotice } from "../../lib/api";
import { resolveDefaultPath } from "../../lib/navigation";
import { isPreviewModeBrowser } from "../../lib/preview";

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

type BackupStatusResponse = {
  module: string;
  status: string;
  active_backend: string;
  active_backend_label: string;
  can_download_archive: boolean;
  archive_download_label: string;
  suggested_archive_name: string;
  can_download_sqlite_file: boolean;
  sqlite_download_label: string;
  suggested_sqlite_name?: string | null;
  sqlite_download_note: string;
  can_import_sqlite_backup: boolean;
  import_title: string;
  import_note: string;
};

type BackupImportResponse = {
  message: string;
  imported_anything: boolean;
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const fieldStyle = {
  width: "100%",
  padding: "14px 16px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--text)",
  fontSize: "0.98rem",
} satisfies CSSProperties;

function formatExpiry(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function parseApiError(detail: unknown, fallback: string) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  return fallback;
}

function resolveDownloadName(response: Response, fallback: string) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename=\"([^\"]+)\"/i);
  return match?.[1] || fallback;
}

function triggerBrowserDownload(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

function narrativeCard({
  eyebrow,
  title,
  body,
  tone = "paper",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "paper" | "ink" | "accent";
}) {
  const palette =
    tone === "ink"
      ? {
          background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
          border: "1px solid rgba(255,255,255,0.08)",
          title: "#fff7ea",
          body: "rgba(255,247,234,0.72)",
          eyebrow: "rgba(255,247,234,0.62)",
        }
      : tone === "accent"
        ? {
            background: "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
            border: "1px solid rgba(185,116,41,0.18)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--accent-strong)",
          }
        : {
            background: "rgba(255,255,255,0.84)",
            border: "1px solid var(--line)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--muted)",
          };

  return (
    <article
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        background: palette.background,
        border: palette.border,
        boxShadow: tone === "ink" ? "var(--shadow-deep)" : "var(--shadow-soft)",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{
          color: palette.eyebrow,
          fontSize: "0.74rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          ...serifStyle,
          color: palette.title,
          fontSize: "1.45rem",
          lineHeight: 0.98,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: palette.body,
          fontSize: "0.93rem",
          lineHeight: 1.65,
        }}
      >
        {body}
      </div>
    </article>
  );
}

export default function AccountPage() {
  const router = useRouter();
  const { user, updateUser } = useAuth();
  const isPreview = isPreviewModeBrowser();
  const canManageBackup = Boolean(user?.allowed_actions.includes("backup.manage"));
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [backupStatus, setBackupStatus] = useState<BackupStatusResponse | null>(null);
  const [backupBusy, setBackupBusy] = useState<"" | "archive" | "sqlite" | "import">("");
  const [backupMessage, setBackupMessage] = useState("");
  const [backupError, setBackupError] = useState("");
  const [sqliteImportFile, setSqliteImportFile] = useState<File | null>(null);

  useEffect(() => {
    const nextNotice = readStoredAuthNotice();
    if (!nextNotice) {
      return;
    }
    setNotice(nextNotice);
    writeStoredAuthNotice("");
  }, []);

  useEffect(() => {
    if (!canManageBackup) {
      setBackupStatus(null);
      return;
    }

    if (isPreview) {
      setBackupStatus({
        module: "backups",
        status: "active",
        active_backend: "sqlite",
        active_backend_label: "Yerel veritabanı",
        can_download_archive: false,
        archive_download_label: "Tüm tabloları yedek olarak indir",
        suggested_archive_name: "catkapinda_tam_yedek_preview.zip",
        can_download_sqlite_file: false,
        sqlite_download_label: "SQLite veritabanı dosyasını indir",
        suggested_sqlite_name: "catkapinda_crm_preview.db",
        sqlite_download_note: "Yerel kontrol modunda gerçek dosya indirme açılmıyor.",
        can_import_sqlite_backup: false,
        import_title: "SQLite yedeğini içe aktar",
        import_note: "Yerel kontrol modunda içe aktarma kapalı tutulur.",
      });
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const response = await apiFetch("/backups/status");
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string }
          | BackupStatusResponse
          | null;
        if (!response.ok || !payload || !("module" in payload)) {
          throw new Error(parseApiError(payload && "detail" in payload ? payload.detail : "", "Yedek durumu okunamadı."));
        }
        if (!cancelled) {
          setBackupStatus(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setBackupError(loadError instanceof Error ? loadError.message : "Yedek durumu okunamadı.");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [canManageBackup, isPreview]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) {
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Yeni şifre ve tekrar şifresi aynı olmalı.");
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
        throw new Error((payload && "detail" in payload && payload.detail) || "Şifre güncellenemedi.");
      }
      updateUser(payload.user);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage(payload.message || "Şifre güncellendi.");
      if (!payload.user.must_change_password) {
        router.replace(resolveDefaultPath(payload.user.allowed_actions));
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Şifre güncellenemedi.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBackupDownload(kind: "archive" | "sqlite") {
    if (isPreview) {
      setBackupError("Ön izleme modunda gerçek dosya indirme açılmıyor.");
      return;
    }
    setBackupBusy(kind);
    setBackupError("");
    setBackupMessage("");
    try {
      const path = kind === "archive" ? "/backups/archive" : "/backups/sqlite-file";
      const fallbackName =
        kind === "archive"
          ? backupStatus?.suggested_archive_name || "catkapinda_tam_yedek.zip"
          : backupStatus?.suggested_sqlite_name || "catkapinda_crm.db";
      const response = await apiFetch(path);
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(parseApiError(payload?.detail, "Yedek indirilemedi."));
      }
      const blob = await response.blob();
      triggerBrowserDownload(blob, resolveDownloadName(response, fallbackName));
      setBackupMessage(kind === "archive" ? "Tam yedek indirildi." : "SQLite dosyası indirildi.");
    } catch (downloadError) {
      setBackupError(downloadError instanceof Error ? downloadError.message : "Yedek indirilemedi.");
    } finally {
      setBackupBusy("");
    }
  }

  async function handleSqliteImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sqliteImportFile) {
      setBackupError("Önce bir `.db` dosyası seçmelisin.");
      return;
    }
    if (isPreview) {
      setBackupError("Ön izleme modunda içe aktarma kapalı.");
      return;
    }
    setBackupBusy("import");
    setBackupError("");
    setBackupMessage("");
    try {
      const response = await apiFetch("/backups/import-sqlite", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Backup-File-Name": sqliteImportFile.name,
        },
        body: sqliteImportFile,
      });
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string }
        | BackupImportResponse
        | null;
      if (!response.ok || !payload || !("message" in payload)) {
        throw new Error(parseApiError(payload && "detail" in payload ? payload.detail : "", "SQLite yedeği içe aktarılamadı."));
      }
      setBackupMessage(payload.message || "SQLite yedeği işlendi.");
      setSqliteImportFile(null);
      const statusResponse = await apiFetch("/backups/status");
      const statusPayload = (await statusResponse.json().catch(() => null)) as BackupStatusResponse | null;
      if (statusResponse.ok && statusPayload) {
        setBackupStatus(statusPayload);
      }
    } catch (importError) {
      setBackupError(importError instanceof Error ? importError.message : "SQLite yedeği içe aktarılamadı.");
    } finally {
      setBackupBusy("");
    }
  }

  const securityDeck = useMemo(() => {
    if (!user) {
      return [];
    }

    const hasContact = Boolean(user.email || user.phone);
    const sessionReady = Boolean(user.expires_at);

    return [
      {
        eyebrow: "Güvenlik Kararı",
        title: user.must_change_password ? "Geçici şifre hâlâ aktif." : "Hesap sabit güvenlikte görünüyor.",
        body: user.must_change_password
          ? "Bu hesap ilk kurulum şifresiyle açılmış. Kalıcı şifreye geçiş tamamlanmadan hesap güvenliği tamamlanmış sayılmaz."
          : "Şifre değişimi tamamlanmış durumda. Bundan sonra odak, hesabın tekil ve güncel bir erişim hattında kalması.",
        tone: user.must_change_password ? "ink" : "paper",
      },
      {
        eyebrow: "Kimlik Hattı",
        title: hasContact ? "Hesap iletişim bilgisi kayıtlı." : "İletişim bilgisi eksik görünüyor.",
        body: hasContact
          ? `${user.email ? "E-posta" : "E-posta yok"}${user.email && user.phone ? " ve " : ""}${user.phone ? "telefon" : ""} bu hesapta görünür. Bu, pilot geçişte destek ve kurtarma adımlarını kolaylaştırır.`
          : "Bu hesapta görünen e-posta ya da telefon yok. Destek ve kimlik teyidi için iletişim izini güçlendirmek gerekir.",
        tone: hasContact ? "paper" : "accent",
      },
      {
        eyebrow: "Oturum Nabzı",
        title: sessionReady ? "Erişim zamanı okunabiliyor." : "Oturum izi eksik görünüyor.",
        body: sessionReady
          ? `${formatExpiry(user.expires_at)} oturum sınırı olarak görünüyor.`
          : "Bu hesap için okunabilir bir oturum bitiş bilgisi yok. Güvenlik akışını gözden geçirmek faydalı olur.",
        tone: sessionReady ? "accent" : "paper",
      },
    ] as const;
  }, [user]);

  return (
    <AppShell activeItem="Profil">
      <section style={{ display: "grid", gap: "18px" }}>
        <div
          style={{
            padding: "28px",
            borderRadius: "30px",
            background: "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
            display: "grid",
            gap: "18px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.35fr) minmax(280px, 0.9fr)",
              gap: "18px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "16px",
                alignContent: "start",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
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
                Profil ve Güvenlik
              </div>
              <div style={{ display: "grid", gap: "10px", maxWidth: "72ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(2.2rem, 4vw, 3.6rem)",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Hesap güvenliği ve kimlik bilgileri
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "74ch",
                    color: "var(--muted)",
                    lineHeight: 1.76,
                    fontSize: "1.02rem",
                  }}
                >
                  Güçlü şifre, güncel iletişim bilgisi ve okunabilir oturum kaydı hesabın güvenli
                  kalması için birlikte takip edilir.
                </p>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Kimlik ve şifre aynı hatta
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Geçici şifre riski görünür
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gap: "12px",
              }}
            >
              <article
                style={{
                  padding: "18px 18px 16px",
                  borderRadius: "24px",
                  background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    alignItems: "start",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "6px" }}>
                    <div
                      style={{
                        color: "rgba(255,247,234,0.62)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Güvenlik Nabzı
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {user?.must_change_password ? "geçici şifre açık" : "hesap sabit hatta"}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "7px 10px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.8rem",
                      fontWeight: 800,
                    }}
                  >
                    Güvenlik Masası
                  </div>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "10px",
                  }}
                >
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Rol
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {user?.role_display || "-"}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Oturum
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {user?.expires_at ? "izlenebilir" : "eksik"}
                    </div>
                  </div>
                </div>
              </article>

              <article
                style={{
                  padding: "16px 18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.74rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Okuma Notu
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  Bu ekranda önce geçici şifre durumuna, sonra hesap kimlik kanallarına ve en
                  son oturum izine bakmak en sağlıklı profil okumasını verir.
                </div>
              </article>
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "14px",
          }}
        >
          {securityDeck.map((item) => (
            <div key={`${item.eyebrow}-${item.title}`}>{narrativeCard(item)}</div>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(320px, 420px) minmax(360px, 1fr)",
            gap: "18px",
            alignItems: "start",
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
            <div style={{ display: "grid", gap: "6px" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Profil Özeti</h2>
              <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
                Hesabın kimlik, rol ve oturum izini tek yerde oku.
              </p>
            </div>
            <InfoRow label="Ad Soyad" value={user?.full_name || "-"} />
            <InfoRow label="Rol" value={user?.role_display || "-"} />
            <InfoRow label="E-posta" value={user?.email || "-"} />
            <InfoRow label="Telefon" value={user?.phone || "-"} />
            <InfoRow label="Oturum" value={user?.expires_at ? `Açık · ${formatExpiry(user.expires_at)}` : "-"} />
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
            <div style={{ display: "grid", gap: "6px" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Şifre Güncelle</h2>
              <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
                Yeni sisteme geçtiğimizde herkesin tekil ve güçlü şifre kullanması gerekiyor.
              </p>
            </div>

            {notice ? (
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  background: "rgba(15, 95, 215, 0.08)",
                  color: "#0f5fd7",
                  border: "1px solid rgba(15, 95, 215, 0.14)",
                  fontWeight: 700,
                }}
              >
                {notice}
              </div>
            ) : null}

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
                Bu hesap geçici şifre ile açıldı. Devam etmeden önce şifreni güncelle.
              </div>
            ) : null}

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Mevcut Şifre</span>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="Mevcut şifren"
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Yeni Şifre</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="En az 6 karakter"
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Yeni Şifre Tekrar</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  style={fieldStyle}
                  placeholder="Yeni şifreyi tekrar gir"
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
                {submitting ? "Kaydediliyor..." : "Şifreyi Güncelle"}
              </button>
            </form>
          </section>
        </div>

        {canManageBackup ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(320px, 420px) minmax(360px, 1fr)",
              gap: "18px",
              alignItems: "start",
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
                gap: "16px",
              }}
            >
              <div style={{ display: "grid", gap: "6px" }}>
                <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Yedek ve Veri Yönetimi</h2>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
                  Streamlit tarafındaki yedek araçlarını buraya taşıdık. Önce tam tablo yedeğini, sonra gerekiyorsa SQLite dosyasını indir.
                </p>
              </div>

              <InfoRow label="Aktif kayıt altyapısı" value={backupStatus?.active_backend_label || "-"} />

              <div style={{ display: "grid", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => void handleBackupDownload("archive")}
                  disabled={backupBusy !== "" || !backupStatus?.can_download_archive}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "16px",
                    border: "none",
                    background: "var(--accent)",
                    color: "#fff",
                    fontWeight: 800,
                    fontSize: "0.98rem",
                    cursor: "pointer",
                    opacity: backupBusy !== "" || !backupStatus?.can_download_archive ? 0.6 : 1,
                  }}
                >
                  {backupBusy === "archive"
                    ? "Yedek hazırlanıyor..."
                    : backupStatus?.archive_download_label || "Tüm tabloları yedek olarak indir"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleBackupDownload("sqlite")}
                  disabled={backupBusy !== "" || !backupStatus?.can_download_sqlite_file}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "16px",
                    border: "1px solid var(--line)",
                    background: "rgba(255,255,255,0.92)",
                    color: "var(--text)",
                    fontWeight: 800,
                    fontSize: "0.98rem",
                    cursor: "pointer",
                    opacity: backupBusy !== "" || !backupStatus?.can_download_sqlite_file ? 0.6 : 1,
                  }}
                >
                  {backupBusy === "sqlite"
                    ? "SQLite hazırlanıyor..."
                    : backupStatus?.sqlite_download_label || "SQLite veritabanı dosyasını indir"}
                </button>
              </div>

              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  background: "rgba(255,255,255,0.72)",
                  border: "1px solid var(--line)",
                  color: "var(--muted)",
                  lineHeight: 1.6,
                }}
              >
                {backupStatus?.sqlite_download_note || "Yedek durumu okunuyor."}
              </div>

              {backupError ? (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "16px",
                    background: "rgba(207, 65, 65, 0.08)",
                    color: "#b73636",
                    border: "1px solid rgba(207, 65, 65, 0.12)",
                  }}
                >
                  {backupError}
                </div>
              ) : null}

              {backupMessage ? (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "16px",
                    background: "rgba(44, 138, 84, 0.08)",
                    color: "#1c6c3f",
                    border: "1px solid rgba(44, 138, 84, 0.14)",
                  }}
                >
                  {backupMessage}
                </div>
              ) : null}
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
              <div style={{ display: "grid", gap: "6px" }}>
                <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{backupStatus?.import_title || "SQLite yedeğini içe aktar"}</h2>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
                  {backupStatus?.import_note || "İçe aktarma durumu okunuyor."}
                </p>
              </div>

              <form onSubmit={handleSqliteImport} style={{ display: "grid", gap: "14px" }}>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>SQLite yedeği</span>
                  <input
                    type="file"
                    accept=".db"
                    onChange={(event) => setSqliteImportFile(event.target.files?.[0] || null)}
                    style={fieldStyle}
                    disabled={!backupStatus?.can_import_sqlite_backup || backupBusy !== ""}
                  />
                </label>
                <button
                  type="submit"
                  disabled={!backupStatus?.can_import_sqlite_backup || backupBusy !== "" || !sqliteImportFile}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "16px",
                    border: "none",
                    background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                    color: "#fff7ea",
                    fontWeight: 800,
                    fontSize: "0.98rem",
                    cursor: "pointer",
                    opacity: !backupStatus?.can_import_sqlite_backup || backupBusy !== "" || !sqliteImportFile ? 0.6 : 1,
                  }}
                >
                  {backupBusy === "import" ? "Yedek içe aktarılıyor..." : "Yedeği içe aktar"}
                </button>
              </form>
            </section>
          </div>
        ) : null}
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
