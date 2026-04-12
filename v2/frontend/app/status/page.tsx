"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type FrontendStatus = {
  status: string;
  service: string;
  proxyConfigured: boolean;
  proxyMode: string;
  sourceEnvKey: string | null;
  backendReachable: boolean;
  backendStatus: string;
  targetBaseUrl: string | null;
  detail: string;
};

type BackendReadiness = {
  status: string;
  core_ready: boolean;
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
    admin_user_count: number;
    mobile_ops_user_count: number;
    default_password_configured: boolean;
  };
  config: Array<{
    name: string;
    service: string;
    ok: boolean;
    required: boolean;
    detail: string | null;
    missing_envs: string[];
  }>;
  missing_env_vars: string[];
  required_missing_env_vars: string[];
  optional_missing_env_vars: string[];
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
  cutover: {
    phase: string;
    ready: boolean;
    summary: string;
    core_checks_ready: boolean;
    auth_ready: boolean;
    modules_ready_count: number;
    modules_total_count: number;
    blocking_items: string[];
    remaining_items: string[];
  };
  pilot_accounts: Array<{
    email: string;
    full_name: string;
    role: string;
    has_phone: boolean;
  }>;
  pilot_flow: Array<{
    title: string;
    detail: string;
    href: string;
  }>;
  rollout_steps: Array<{
    title: string;
    detail: string;
    status: string;
    service_name: string | null;
    env_keys: string[];
  }>;
  pilot_links: Array<{
    label: string;
    href: string;
  }>;
  smoke_commands: Array<{
    label: string;
    command: string;
  }>;
  services: Array<{
    name: string;
    service_type: string;
    public_url: string;
    health_path: string;
    env_vars: Array<{
      key: string;
      required: boolean;
      configured: boolean;
      detail: string | null;
    }>;
  }>;
  env_snippets: Array<{
    service_name: string;
    title: string;
    body: string;
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
  const pilotAccounts = useMemo(() => backend?.pilot_accounts ?? [], [backend]);
  const pilotFlow = useMemo(() => backend?.pilot_flow ?? [], [backend]);
  const rolloutSteps = useMemo(() => backend?.rollout_steps ?? [], [backend]);
  const pilotLinks = useMemo(() => backend?.pilot_links ?? [], [backend]);
  const smokeCommands = useMemo(() => backend?.smoke_commands ?? [], [backend]);
  const pilotServices = useMemo(() => backend?.services ?? [], [backend]);
  const envSnippets = useMemo(() => backend?.env_snippets ?? [], [backend]);
  const backendConfigEntries = useMemo(
    () => backendConfig.filter((entry) => entry.service === "backend"),
    [backendConfig],
  );
  const frontendConfigEntries = useMemo(
    () => [
      {
        name: "NEXT_PUBLIC_V2_API_BASE_URL",
        ok: true,
        required: true,
        detail: "/v2-api (hem yerel gelistirme hem Render pilot icin ayni kalir)",
      },
      {
        name: "CK_V2_INTERNAL_API_HOSTPORT veya CK_V2_INTERNAL_API_BASE_URL",
        ok: true,
        required: true,
        detail:
          "Render pilotta CK_V2_INTERNAL_API_HOSTPORT blueprint ile otomatik gelir. Yerelde CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000 kullanilir.",
      },
      {
        name: "NEXT_TELEMETRY_DISABLED",
        ok: true,
        required: false,
        detail: "1 (blueprint ile otomatik gelir)",
      },
    ],
    [],
  );
  const frontendEnvModes = useMemo(
    () =>
      envSnippets.filter(
        (entry) => entry.service_name === "crmcatkapinda-v2" || entry.service_name === "local-v2-frontend",
      ),
    [envSnippets],
  );
  const overallOk = Boolean(frontend?.proxyConfigured) && Boolean(frontend?.backendReachable) && backend?.status === "ok";
  const coreReady = Boolean(frontend?.backendReachable) && Boolean(backend?.core_ready);
  const cutoverTone =
    backend?.cutover.phase === "ready_for_cutover"
      ? true
      : backend?.cutover.phase === "ready_for_pilot"
        ? true
        : false;

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
          <div style={statusPill(coreReady)}>Pilot Durumu: {overallOk ? "Hazır" : coreReady ? "Temel Olarak Hazır" : "Kontrol Gerekli"}</div>
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
            {backend?.cutover ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "14px",
                  background:
                    backend.cutover.phase === "ready_for_cutover"
                      ? "linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(255,255,255,0.98))"
                      : backend.cutover.phase === "ready_for_pilot"
                        ? "linear-gradient(135deg, rgba(15, 95, 215, 0.06), rgba(255,255,255,0.98))"
                        : "linear-gradient(135deg, rgba(239, 68, 68, 0.06), rgba(255,255,255,0.98))",
                }}
              >
                <div style={statusPill(cutoverTone)}>
                  {backend.cutover.phase === "ready_for_cutover"
                    ? "Cutover Hazir"
                    : backend.cutover.phase === "ready_for_pilot"
                      ? "Pilot Acilabilir"
                      : "Once Blokajlar Kapanmali"}
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1.2fr) minmax(280px, 0.8fr)",
                    gap: "18px",
                  }}
                >
                  <div style={{ display: "grid", gap: "10px" }}>
                    <h2 style={{ margin: 0, fontSize: "1.5rem" }}>Streamlit'ten cikis ozeti</h2>
                    <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>{backend.cutover.summary}</p>
                    {backend.cutover.blocking_items.length ? (
                      <div
                        style={{
                          padding: "14px 16px",
                          borderRadius: "16px",
                          border: "1px solid rgba(239, 68, 68, 0.18)",
                          background: "rgba(239, 68, 68, 0.06)",
                          color: "#b42318",
                          display: "grid",
                          gap: "8px",
                        }}
                      >
                        <strong>Blokajlar</strong>
                        {backend.cutover.blocking_items.map((item) => (
                          <div key={item} style={{ lineHeight: 1.6 }}>
                            • {item}
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {backend.cutover.remaining_items.length ? (
                      <div
                        style={{
                          padding: "14px 16px",
                          borderRadius: "16px",
                          border: "1px solid rgba(245, 158, 11, 0.18)",
                          background: "rgba(245, 158, 11, 0.08)",
                          color: "#9a6700",
                          display: "grid",
                          gap: "8px",
                        }}
                      >
                        <strong>Kalan Son Maddeler</strong>
                        {backend.cutover.remaining_items.map((item) => (
                          <div key={item} style={{ lineHeight: 1.6 }}>
                            • {item}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gap: "12px",
                      alignContent: "start",
                    }}
                  >
                    <div style={statusPill(backend.cutover.core_checks_ready)}>Core Checks</div>
                    <div style={statusPill(backend.cutover.auth_ready)}>Auth Hazir</div>
                    <div style={statusPill(backend.cutover.modules_ready_count === backend.cutover.modules_total_count)}>
                      Modul {backend.cutover.modules_ready_count}/{backend.cutover.modules_total_count}
                    </div>
                    <Link href="/login" style={actionButtonStyle("primary")}>
                      Login Ekranini Ac
                    </Link>
                    <Link href="/attendance" style={actionButtonStyle()}>
                      Ilk Pilot Akisini Test Et
                    </Link>
                  </div>
                </div>
              </section>
            ) : null}

            {coreReady ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "12px",
                  background: "linear-gradient(135deg, rgba(15, 95, 215, 0.05), rgba(255,255,255,0.98))",
                }}
              >
                <div style={statusPill(true)}>{overallOk ? "Pilot Kullanima Hazir" : "Temel Yuzey Hazir"}</div>
                <h2 style={{ margin: 0, fontSize: "1.45rem" }}>
                  {overallOk ? "Yeni sisteme kontrollu gecis baslayabilir." : "Pilot cekirdek olarak hazir, son ayarlar tamamlanabilir."}
                </h2>
                <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
                  {overallOk
                    ? "Frontend, backend ve temel auth kontrolleri su anda olumlu gorunuyor. Ofis ekibi once login ekranindan girip puantaj, personel ve kesinti akislarini yeni sistemde test etmeye baslayabilir."
                    : "Frontend ve backend cekirdek olarak ayakta. SMS gibi opsiyonel ayarlar tamamlandikca pilot tam hazir seviyesine cikacak."}
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

            {pilotLinks.length ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "16px",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={statusPill(Boolean(frontend?.backendReachable))}>Pilot Baglantilari</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Deploy sonrasi bakacagin yerler</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Pilot acildiginda ekip bu linklerden ilerleyebilir. Ayni kartta smoke komutlari da hazir.
                  </p>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  {pilotLinks.map((link) => (
                    <a key={link.href} href={link.href} style={actionButtonStyle(link.label === "Pilot Login" ? "primary" : "ghost")}>
                      {link.label}
                    </a>
                  ))}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                    gap: "14px",
                  }}
                >
                  {smokeCommands.map((command) => (
                    <div
                      key={command.label}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 251, 255, 0.92)",
                        display: "grid",
                        gap: "10px",
                      }}
                    >
                      <strong>{command.label}</strong>
                      <code
                        style={{
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontSize: "0.88rem",
                          lineHeight: 1.7,
                          color: "#25406b",
                        }}
                      >
                        {command.command}
                      </code>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {pilotServices.length ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "16px",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={statusPill(true)}>Render Servisleri</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Pilotta acacagimiz servisler</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Render uzerinde gorecegin servis adlari ve public health adresleri burada tek yerde duruyor.
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "14px",
                  }}
                >
                  {pilotServices.map((service) => (
                    <div
                      key={service.name}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 251, 255, 0.92)",
                        display: "grid",
                        gap: "10px",
                      }}
                    >
                      <div style={statusPill(service.service_type === "frontend")}>
                        {service.service_type === "frontend" ? "Frontend Servisi" : "Backend Servisi"}
                      </div>
                      <strong style={{ fontSize: "1rem" }}>{service.name}</strong>
                      <div style={{ color: "#5f7294", fontSize: "0.92rem", lineHeight: 1.7 }}>
                        Public URL: {service.public_url}
                      </div>
                      <div style={{ color: "#5f7294", fontSize: "0.92rem", lineHeight: 1.7 }}>
                        Health: {service.health_path}
                      </div>
                      <div style={{ display: "grid", gap: "8px" }}>
                        {service.env_vars.map((entry) => (
                          <div
                            key={`${service.name}-${entry.key}`}
                            style={{
                              display: "grid",
                              gap: "4px",
                              padding: "10px 12px",
                              borderRadius: "14px",
                              border: "1px solid rgba(219, 228, 243, 0.9)",
                              background: "rgba(255,255,255,0.92)",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: "10px",
                                flexWrap: "wrap",
                              }}
                            >
                              <strong style={{ fontSize: "0.92rem" }}>{entry.key}</strong>
                              <div style={statusPill(entry.configured || !entry.required)}>
                                {entry.configured ? "Hazir" : entry.required ? "Zorunlu" : "Opsiyonel"}
                              </div>
                            </div>
                            {entry.detail ? (
                              <div style={{ color: "#5f7294", fontSize: "0.86rem", lineHeight: 1.5 }}>{entry.detail}</div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {envSnippets.length ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "16px",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={statusPill(true)}>Kopyala-Yapistir Env Planı</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Render'a girilecek örnek env blokları</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Pilotu açarken servis bazlı environment değerlerini buradan referans alabilirsin. V2 servisleri yanında eski Streamlit servisine geçiş banneri/redirect vermek için gereken env bloku da burada. Gizli alanları kendi gerçek değerlerinle doldurman yeterli.
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                    gap: "14px",
                  }}
                >
                  {envSnippets.map((snippet) => (
                    <article
                      key={snippet.service_name}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 251, 255, 0.92)",
                        display: "grid",
                        gap: "10px",
                      }}
                    >
                      <strong>{snippet.title}</strong>
                      <code
                        style={{
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontSize: "0.88rem",
                          lineHeight: 1.7,
                          color: "#25406b",
                        }}
                      >
                        {snippet.body}
                      </code>
                    </article>
                  ))}
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
                      <div style={statusPill(frontend.proxyMode !== "missing")}>
                        {frontend.proxyMode === "explicit_base_url"
                          ? "Yerel Base URL"
                          : frontend.proxyMode === "render_hostport"
                            ? "Render Hostport"
                            : "Proxy Modu Eksik"}
                      </div>
                      <div style={statusPill(Boolean(frontend.backendReachable))}>
                        Backend {frontend.backendStatus !== "unknown" ? `(${frontend.backendStatus})` : ""}
                      </div>
                    </div>
                    {frontend.sourceEnvKey ? (
                      <div style={{ color: "#5f7294", fontSize: "0.92rem" }}>Kaynak env: {frontend.sourceEnvKey}</div>
                    ) : null}
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
                  <div style={statusPill(Boolean(backend?.core_ready))}>
                  {backend?.status === "ok" ? "Backend Hazır" : backend?.core_ready ? "Backend Temel Olarak Hazır" : "Backend Kontrol Gerekli"}
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
                      <div style={statusPill((backend.auth.admin_user_count ?? 0) > 0)}>
                        Admin {(backend.auth.admin_user_count ?? 0)}
                      </div>
                      <div style={statusPill((backend.auth.mobile_ops_user_count ?? 0) > 0)}>
                        Mobil {(backend.auth.mobile_ops_user_count ?? 0)}
                      </div>
                    </div>
                    {!backend.auth.default_password_configured ? (
                      <div
                        style={{
                          padding: "12px 14px",
                          borderRadius: "16px",
                          border: "1px solid rgba(245, 158, 11, 0.18)",
                          background: "rgba(245, 158, 11, 0.08)",
                          color: "#9a6700",
                          lineHeight: 1.6,
                          fontSize: "0.92rem",
                        }}
                      >
                        Varsayilan v2 sifresi hala aktif gorunuyor. Pilot oncesi bunu degistirmen onerilir.
                      </div>
                    ) : null}
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

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.1fr) minmax(320px, 0.9fr)",
                gap: "18px",
              }}
            >
              <article style={cardStyle()}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "16px",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Ilk Pilot Test Akışı</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Ofisin yeni sisteme ilk girişte izleyeceği önerilen kısa rota.
                    </p>
                  </div>
                  <div style={statusPill(pilotFlow.length > 0)}>{pilotFlow.length} adım</div>
                </div>
                <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                  {pilotFlow.map((step) => (
                    <article
                      key={step.title}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 250, 255, 0.86)",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      <strong>{step.title}</strong>
                      <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{step.detail}</div>
                      <div>
                        <Link href={step.href} style={actionButtonStyle()}>
                          Adımı Aç
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              </article>

              <article style={cardStyle()}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "16px",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Pilot Giriş Hesapları</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      İlk denemede kullanılabilecek yönetici hesaplar ve telefon giriş durumu.
                    </p>
                  </div>
                  <div style={statusPill(pilotAccounts.length > 0)}>{pilotAccounts.length} hesap</div>
                </div>
                <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                  {pilotAccounts.map((account) => (
                    <article
                      key={account.email}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 250, 255, 0.86)",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      <strong>{account.full_name}</strong>
                      <div style={{ color: "#35507d", lineHeight: 1.5 }}>{account.email}</div>
                      <div style={{ color: "#5f7294", lineHeight: 1.5 }}>{account.role}</div>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        <div style={statusPill(true)}>E-posta giriş</div>
                        <div style={statusPill(account.has_phone)}>Telefon {account.has_phone ? "hazır" : "eksik"}</div>
                      </div>
                    </article>
                  ))}
                </div>
              </article>
            </section>

            {rolloutSteps.length ? (
              <section style={cardStyle()}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "16px",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Pilot Açılış Sırası</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Render tarafında adım adım hangi sırayla ilerleyeceğimizi burada net olarak görebilirsin.
                    </p>
                  </div>
                  <div style={statusPill(rolloutSteps.every((step) => step.status !== "blocked"))}>
                    {rolloutSteps.filter((step) => step.status === "ready").length}/{rolloutSteps.length} adım hazır
                  </div>
                </div>
                <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                  {rolloutSteps.map((step) => (
                    <article
                      key={step.title}
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
                          gap: "12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>{step.title}</strong>
                        <div style={statusPill(step.status === "ready")}>
                          {step.status === "ready" ? "Hazır" : step.status === "blocked" ? "Bloklu" : "Sırada"}
                        </div>
                      </div>
                      <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{step.detail}</div>
                      {step.service_name ? (
                        <div style={{ color: "#35507d", fontSize: "0.92rem", lineHeight: 1.5 }}>
                          Servis: {step.service_name}
                        </div>
                      ) : null}
                      {step.env_keys.length ? (
                        <div style={{ color: "#5f7294", fontSize: "0.9rem", lineHeight: 1.5 }}>
                          Env: {step.env_keys.join(", ")}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

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
                  <div style={statusPill((backend?.required_missing_env_vars?.length ?? 0) === 0)}>
                    {(backend?.required_missing_env_vars?.length ?? 0) === 0
                      ? "Zorunlu Env Tamam"
                      : `${backend?.required_missing_env_vars?.length ?? 0} zorunlu eksik`}
                  </div>
                </div>

                {(backend?.optional_missing_env_vars?.length ?? 0) > 0 ? (
                  <div
                    style={{
                      padding: "14px 16px",
                      borderRadius: "16px",
                      border: "1px solid rgba(245, 158, 11, 0.18)",
                      background: "rgba(245, 158, 11, 0.08)",
                      color: "#9a6700",
                      lineHeight: 1.6,
                    }}
                  >
                    Opsiyonel eksikler: {backend?.optional_missing_env_vars.join(", ")}. Bunlar pilotu durdurmaz, sadece SMS gibi ek akislar icin gerekir.
                  </div>
                ) : null}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "16px",
                  }}
                >
                  <article
                    style={{
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid rgba(219, 228, 243, 0.9)",
                      background: "rgba(248, 250, 255, 0.86)",
                      display: "grid",
                      gap: "12px",
                      alignContent: "start",
                    }}
                  >
                    <div style={{ display: "grid", gap: "6px" }}>
                      <strong style={{ fontSize: "1rem" }}>Render API Servisi</strong>
                      <div style={{ color: "#5f7294", lineHeight: 1.5 }}>
                        Backend servisine girilecek ortam degiskenleri. Zorunlu eksikler burada gorunur.
                      </div>
                    </div>
                    <div style={{ display: "grid", gap: "10px" }}>
                      {backendConfigEntries.map((entry) => (
                        <article
                          key={entry.name}
                          style={{
                            padding: "14px",
                            borderRadius: "16px",
                            border: "1px solid rgba(219, 228, 243, 0.9)",
                            background: "rgba(255,255,255,0.92)",
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
                            <div style={statusPill(entry.ok)}>
                              {entry.ok ? "Hazır" : entry.required ? "Zorunlu Eksik" : "İsteğe Bağlı Eksik"}
                            </div>
                          </div>
                          <div style={{ color: "#5f7294", lineHeight: 1.5 }}>{entry.detail ?? "-"}</div>
                          {entry.missing_envs.length ? (
                            <div
                              style={{
                                color: entry.required ? "#c24141" : "#9a6700",
                                fontSize: "0.9rem",
                                lineHeight: 1.5,
                              }}
                            >
                              Eksik: {entry.missing_envs.join(", ")}
                            </div>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  </article>

                  <article
                    style={{
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid rgba(219, 228, 243, 0.9)",
                      background: "rgba(248, 250, 255, 0.86)",
                      display: "grid",
                      gap: "12px",
                      alignContent: "start",
                    }}
                  >
                    <div style={{ display: "grid", gap: "6px" }}>
                      <strong style={{ fontSize: "1rem" }}>Render Frontend Servisi</strong>
                      <div style={{ color: "#5f7294", lineHeight: 1.5 }}>
                        Frontend servisi Render pilotta blueprint ile otomatik gelen ayarlarla ayaga kalkar. Yerel denemede ise ayni proxy rotasi korunur ama hedef env anahtari degisir; asagidaki bloklar bunu netlestirir.
                      </div>
                    </div>
                    <div style={{ display: "grid", gap: "10px" }}>
                      {frontendConfigEntries.map((entry) => (
                        <article
                          key={entry.name}
                          style={{
                            padding: "14px",
                            borderRadius: "16px",
                            border: "1px solid rgba(219, 228, 243, 0.9)",
                            background: "rgba(255,255,255,0.92)",
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
                            <strong>{entry.name}</strong>
                            <div style={statusPill(entry.ok)}>
                              {entry.ok ? "Blueprint ile Hazır" : entry.required ? "Zorunlu Eksik" : "İsteğe Bağlı Eksik"}
                            </div>
                          </div>
                          <div style={{ color: "#5f7294", lineHeight: 1.5 }}>{entry.detail}</div>
                        </article>
                      ))}
                    </div>
                    <div
                      style={{
                        marginTop: "4px",
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                        gap: "10px",
                      }}
                    >
                      {frontendEnvModes.map((mode) => (
                        <article
                          key={mode.title}
                          style={{
                            padding: "14px",
                            borderRadius: "16px",
                            border: "1px solid rgba(219, 228, 243, 0.9)",
                            background: "rgba(255,255,255,0.92)",
                            display: "grid",
                            gap: "8px",
                          }}
                        >
                          <strong>{mode.title}</strong>
                          <code
                            style={{
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              fontSize: "0.88rem",
                              lineHeight: 1.7,
                              color: "#25406b",
                            }}
                          >
                            {mode.body}
                          </code>
                        </article>
                      ))}
                    </div>
                  </article>
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
