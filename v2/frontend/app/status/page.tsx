"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type FrontendStatus = {
  status: string;
  service: string;
  proxyConfigured: boolean;
  backendReachable: boolean;
  backendStatus: string;
  targetBaseUrl: string | null;
  detail: string;
};

type BackendReadiness = {
  status: string;
  service: string;
  version: string;
  environment: string;
  checks: Array<{
    name: string;
    ok: boolean;
    detail: string | null;
  }>;
  auth: {
    email_login: boolean;
    phone_login: boolean;
    sms_login: boolean;
    sms_allowlist_count: number;
  };
  config: Array<{
    name: string;
    ok: boolean;
    detail: string | null;
    missing_envs: string[];
  }>;
  missing_env_vars: string[];
  next_actions: string[];
  modules: Array<{
    module: string;
    label: string;
    status: string;
    next_slice: string;
    href: string;
    detail: string | null;
    missing_tables: string[];
  }>;
};

function statusPill(ok: boolean) {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    borderRadius: "999px",
    fontSize: "0.82rem",
    fontWeight: 800,
    background: ok ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)",
    color: ok ? "#0f9f6e" : "#c24141",
  } as const;
}

function cardStyle() {
  return {
    borderRadius: "24px",
    border: "1px solid rgba(219, 228, 243, 0.9)",
    background: "rgba(255,255,255,0.96)",
    boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
    padding: "22px",
  } as const;
}

function actionButtonStyle(tone: "primary" | "ghost" = "ghost") {
  return {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "12px 16px",
    borderRadius: "16px",
    border: tone === "primary" ? "1px solid rgba(15, 95, 215, 0.18)" : "1px solid rgba(219, 228, 243, 0.9)",
    background: tone === "primary" ? "linear-gradient(135deg, rgba(15, 95, 215, 0.12), rgba(62, 126, 232, 0.08))" : "rgba(255,255,255,0.92)",
    color: tone === "primary" ? "#0f5fd7" : "#35507d",
    fontWeight: 800,
    textDecoration: "none",
  } as const;
}

export default function StatusPage() {
  const [frontend, setFrontend] = useState<FrontendStatus | null>(null);
  const [backend, setBackend] = useState<BackendReadiness | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      setLoading(true);
      try {
        const [frontendRes, backendRes] = await Promise.all([
          fetch("/api/ready", { cache: "no-store" }),
          fetch("/v2-api/health/pilot", { cache: "no-store" }),
        ]);

        const frontendPayload = frontendRes.ok ? ((await frontendRes.json()) as FrontendStatus) : null;
        const backendPayload = backendRes.ok ? ((await backendRes.json()) as BackendReadiness) : null;

        if (active) {
          setFrontend(frontendPayload);
          setBackend(backendPayload);
        }
      } catch {
        if (active) {
          setFrontend(null);
          setBackend(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadStatus();
    return () => {
      active = false;
    };
  }, []);

  const backendChecks = useMemo(() => backend?.checks ?? [], [backend]);
  const backendConfig = useMemo(() => backend?.config ?? [], [backend]);
  const backendModules = useMemo(() => backend?.modules ?? [], [backend]);
  const overallOk = Boolean(frontend?.proxyConfigured) && Boolean(frontend?.backendReachable) && backend?.status === "ok";

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #f4f8ff 0%, #ffffff 100%)",
        padding: "48px 24px",
        color: "#16274a",
      }}
    >
      <div
        style={{
          maxWidth: "1120px",
          margin: "0 auto",
          display: "grid",
          gap: "18px",
        }}
      >
        <section
          style={{
            ...cardStyle(),
            display: "grid",
            gap: "14px",
          }}
        >
          <div style={statusPill(overallOk)}>Pilot Durumu: {overallOk ? "Hazır" : "Kontrol Gerekli"}</div>
          <h1 style={{ margin: 0, fontSize: "clamp(2rem, 4vw, 3rem)", lineHeight: 1.04 }}>
            Cat Kapında CRM v2 pilot kontrol ekranı
          </h1>
          <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
            Bu sayfa yeni sistemin gerçekten ayağa kalkıp kalkmadığını tek bakışta gösterir. Frontend proxy,
            backend servis ve veritabanı erişimi burada birlikte kontrol edilir.
          </p>
          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
            }}
          >
            <Link href="/login" style={actionButtonStyle("primary")}>
              Pilotu Ac
            </Link>
            <Link href="/" style={actionButtonStyle()}>
              Dashboard'a Don
            </Link>
          </div>
        </section>

        {loading ? (
          <section style={cardStyle()}>Pilot durumu yükleniyor...</section>
        ) : (
          <>
            {overallOk ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "12px",
                  background: "linear-gradient(135deg, rgba(15, 95, 215, 0.05), rgba(255,255,255,0.98))",
                }}
              >
                <div style={statusPill(true)}>Pilot Kullanima Hazir</div>
                <h2 style={{ margin: 0, fontSize: "1.45rem" }}>Yeni sisteme kontrollu gecis baslayabilir.</h2>
                <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
                  Frontend, backend ve temel auth kontrolleri su anda olumlu gorunuyor. Ofis ekibi once login
                  ekranindan girip puantaj, personel ve kesinti akislarini yeni sistemde test etmeye baslayabilir.
                </p>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <Link href="/login" style={actionButtonStyle("primary")}>
                    Login Ekranini Ac
                  </Link>
                  <Link href="/attendance" style={actionButtonStyle()}>
                    Puantaja Git
                  </Link>
                  <Link href="/personnel" style={actionButtonStyle()}>
                    Personel'e Git
                  </Link>
                </div>
              </section>
            ) : null}

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "18px",
              }}
            >
              <article style={cardStyle()}>
                <div style={{ color: "#5f7294", fontSize: "0.82rem", textTransform: "uppercase", fontWeight: 800 }}>
                  Frontend
                </div>
                <h2 style={{ margin: "12px 0 8px", fontSize: "1.4rem" }}>{frontend?.service ?? "Erisilemiyor"}</h2>
                <div style={statusPill(Boolean(frontend?.proxyConfigured) && Boolean(frontend?.backendReachable))}>
                  {frontend?.proxyConfigured && frontend?.backendReachable
                    ? "Frontend Hazır"
                    : frontend?.proxyConfigured
                      ? "Backend Erişimi Eksik"
                      : "Proxy Eksik"}
                </div>
                {frontend ? (
                  <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
                    <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.6 }}>{frontend.detail}</p>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <div style={statusPill(Boolean(frontend.proxyConfigured))}>Proxy</div>
                      <div style={statusPill(Boolean(frontend.backendReachable))}>
                        Backend {frontend.backendStatus !== "unknown" ? `(${frontend.backendStatus})` : ""}
                      </div>
                    </div>
                    {frontend.targetBaseUrl ? (
                      <div style={{ color: "#5f7294", fontSize: "0.92rem" }}>İç hedef: {frontend.targetBaseUrl}</div>
                    ) : null}
                  </div>
                ) : null}
              </article>

              <article style={cardStyle()}>
                <div style={{ color: "#5f7294", fontSize: "0.82rem", textTransform: "uppercase", fontWeight: 800 }}>
                  Backend ve Auth
                </div>
                <h2 style={{ margin: "12px 0 8px", fontSize: "1.4rem" }}>{backend?.service ?? "Erisilemiyor"}</h2>
                <div style={statusPill(backend?.status === "ok")}>
                  {backend?.status === "ok" ? "Backend Hazır" : "Backend Kontrol Gerekli"}
                </div>
                {backend ? (
                  <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
                    <p style={{ margin: 0, color: "#5f7294" }}>
                    {backend.environment} • v{backend.version}
                    </p>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <div style={statusPill(backend.auth.email_login)}>E-posta</div>
                      <div style={statusPill(backend.auth.phone_login)}>Telefon</div>
                      <div style={statusPill(backend.auth.sms_login)}>
                        SMS {backend.auth.sms_allowlist_count ? `(${backend.auth.sms_allowlist_count})` : ""}
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            </section>

            <section style={cardStyle()}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "18px",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Pilot Modülleri</h2>
                  <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                    Pilot açıldığında ekip doğrudan bu modülleri test edecek. Hazır modüller yeni sistemden açılabilir.
                  </p>
                </div>
                <div style={statusPill(backendModules.every((entry) => entry.status === "active") && backendModules.length > 0)}>
                  {backendModules.filter((entry) => entry.status === "active").length}/{backendModules.length || 0} modül hazır
                </div>
              </div>
              <div
                style={{
                  marginTop: "18px",
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                {backendModules.map((module) => (
                  <article
                    key={module.module}
                    style={{
                      padding: "16px",
                      borderRadius: "18px",
                      border: "1px solid rgba(219, 228, 243, 0.9)",
                      background: "rgba(248, 250, 255, 0.86)",
                      display: "grid",
                      gap: "10px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "10px",
                      }}
                    >
                      <strong>{module.label}</strong>
                      <div style={statusPill(module.status === "active")}>
                        {module.status === "active" ? "Hazır" : module.status}
                      </div>
                    </div>
                    <div style={{ color: "#5f7294", fontSize: "0.92rem" }}>{module.next_slice}</div>
                    {module.detail ? (
                      <div style={{ color: "#5f7294", fontSize: "0.9rem", lineHeight: 1.5 }}>{module.detail}</div>
                    ) : null}
                    {module.missing_tables.length ? (
                      <div style={{ color: "#c24141", fontSize: "0.88rem", lineHeight: 1.5 }}>
                        Eksik tablolar: {module.missing_tables.join(", ")}
                      </div>
                    ) : null}
                    <Link
                      href={module.href}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        padding: "10px 12px",
                        borderRadius: "14px",
                        border: "1px solid rgba(15, 95, 215, 0.18)",
                        background: "rgba(15, 95, 215, 0.06)",
                        color: "#0f5fd7",
                        fontWeight: 800,
                        textDecoration: "none",
                      }}
                    >
                      Modülü Aç
                    </Link>
                  </article>
                ))}
              </div>
            </section>

            <section style={cardStyle()}>
              <div
                style={{
                  display: "grid",
                  gap: "18px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "18px",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Deploy Hazırlığı</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Pilotu açmadan önce hangi environment değerlerinin eksik olduğunu ve sıradaki adımları burada gör.
                    </p>
                  </div>
                  <div style={statusPill((backend?.missing_env_vars?.length ?? 0) === 0)}>
                    {(backend?.missing_env_vars?.length ?? 0) === 0 ? "Env Tamam" : `${backend?.missing_env_vars?.length ?? 0} eksik env`}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                    gap: "12px",
                  }}
                >
                  {backendConfig.map((entry) => (
                    <article
                      key={entry.name}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 250, 255, 0.86)",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "10px",
                        }}
                      >
                        <strong style={{ textTransform: "capitalize" }}>{entry.name.replaceAll("_", " ")}</strong>
                        <div style={statusPill(entry.ok)}>{entry.ok ? "Hazır" : "Eksik"}</div>
                      </div>
                      <div style={{ color: "#5f7294", lineHeight: 1.5 }}>{entry.detail ?? "-"}</div>
                      {entry.missing_envs.length ? (
                        <div style={{ color: "#c24141", fontSize: "0.9rem", lineHeight: 1.5 }}>
                          Eksik: {entry.missing_envs.join(", ")}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>

                <div
                  style={{
                    padding: "18px",
                    borderRadius: "18px",
                    border: "1px solid rgba(219, 228, 243, 0.9)",
                    background: "rgba(248, 250, 255, 0.86)",
                    display: "grid",
                    gap: "10px",
                  }}
                >
                  <strong>Sıradaki Adımlar</strong>
                  <div style={{ display: "grid", gap: "8px" }}>
                    {(backend?.next_actions ?? []).map((step) => (
                      <div
                        key={step}
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "10px",
                          color: "#35507d",
                          lineHeight: 1.6,
                        }}
                      >
                        <span style={{ color: "#0f5fd7", fontWeight: 900 }}>•</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            <section style={cardStyle()}>
              <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Hazırlık Kontrolleri</h2>
              <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                {backendChecks.map((check) => (
                  <article
                    key={check.name}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "18px",
                      flexWrap: "wrap",
                      padding: "14px 16px",
                      borderRadius: "16px",
                      border: "1px solid rgba(219, 228, 243, 0.9)",
                      background: "rgba(248, 250, 255, 0.86)",
                    }}
                  >
                    <div>
                      <strong style={{ textTransform: "capitalize" }}>{check.name.replaceAll("_", " ")}</strong>
                      <div style={{ marginTop: "6px", color: "#5f7294", lineHeight: 1.5 }}>{check.detail ?? "-"}</div>
                    </div>
                    <div style={statusPill(check.ok)}>{check.ok ? "Tamam" : "Eksik"}</div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
