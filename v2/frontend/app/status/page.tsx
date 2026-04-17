"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type FrontendStatus = {
  status: string;
  service: string;
  commitSha: string | null;
  releaseLabel: string | null;
  proxyConfigured: boolean;
  proxyMode: string;
  sourceEnvKey: string | null;
  backendReachable: boolean;
  backendStatus: string;
  pilotHttpStatus?: number | null;
  pilotErrorDetail?: string | null;
  targetBaseUrl: string | null;
  detail: string;
};

type BackendReadiness = {
  status: string;
  core_ready: boolean;
  service: string;
  version: string;
  environment: string;
  commit_sha: string | null;
  release_label: string | null;
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
  decision: {
    title: string;
    detail: string;
    tone: string;
    primary_label: string;
    primary_href: string;
  };
  go_live: {
    phase: string;
    phase_label: string;
    tone: string;
    summary: string;
    recommended_next_step: string;
    pilot_ready: boolean;
    cutover_ready: boolean;
    blocking_items: string[];
    future_cutover_blocking_items: string[];
  };
  pilot_accounts: Array<{
    email: string;
    full_name: string;
    role: string;
    has_phone: boolean;
    must_change_password: boolean;
    default_password_active: boolean;
  }>;
  pilot_flow: Array<{
    title: string;
    detail: string;
    href: string;
  }>;
  pilot_scenarios: Array<{
    title: string;
    module: string;
    detail: string;
    success_hint: string;
    href: string;
  }>;
  deploy_steps: Array<{
    title: string;
    detail: string;
    service_name: string | null;
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
  helper_commands: Array<{
    label: string;
    category: string;
    command: string;
  }>;
  command_pack: Array<{
    title: string;
    detail: string;
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

type LocalSetupStatus = {
  ready: boolean;
  backend_env_path: string;
  frontend_env_path: string;
  backend_env_exists: boolean;
  frontend_env_exists: boolean;
  database_url_present: boolean;
  database_url_source: string | null;
  runtime_database_url_present: boolean;
  runtime_database_url_source: string | null;
  backend_env_database_url_present: boolean;
  backend_env_database_url_source: string | null;
  backend_restart_required: boolean;
  backend_restart_reason: string | null;
  default_auth_password_present: boolean;
  default_auth_password_source: string | null;
  default_auth_password_is_default: boolean;
  frontend_proxy_target_present: boolean;
  frontend_proxy_target: string | null;
  frontend_proxy_source: string | null;
  frontend_env_needs_sync: boolean;
  detected_frontend_urls: string[];
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
  current_app_seed_detected: boolean;
  current_app_seed_sources: string[];
  current_app_seed_placeholders: string[];
  current_app_available_sources: Array<{
    label: string;
    path: string;
    kind: string;
    exists: boolean;
  }>;
  missing_phone_keys: string[];
  blocking_items: string[];
  warnings: string[];
  next_actions: string[];
  decision_status: string;
  decision_headline: string;
  decision_detail: string;
  decision_command: string | null;
};

type PilotStatusResponse = {
  status: string;
  frontend: FrontendStatus;
  backend: BackendReadiness | null;
  localSetup: LocalSetupStatus | null;
  localSetupSource?: "backend" | "frontend_local_doctor" | null;
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

function tonePill(tone: string) {
  if (tone === "success") {
    return statusPill(true);
  }

  if (tone === "info") {
    return {
      display: "inline-flex",
      alignItems: "center",
      gap: "8px",
      padding: "8px 12px",
      borderRadius: "999px",
      fontSize: "0.82rem",
      fontWeight: 800,
      background: "rgba(15, 95, 215, 0.12)",
      color: "#0f5fd7",
    } as const;
  }

  return {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    borderRadius: "999px",
    fontSize: "0.82rem",
    fontWeight: 800,
    background: "rgba(245, 158, 11, 0.12)",
    color: "#9a6700",
  } as const;
}

export default function StatusPage() {
  const [frontend, setFrontend] = useState<FrontendStatus | null>(null);
  const [backend, setBackend] = useState<BackendReadiness | null>(null);
  const [localSetup, setLocalSetup] = useState<LocalSetupStatus | null>(null);
  const [localSetupSource, setLocalSetupSource] = useState<"backend" | "frontend_local_doctor" | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadNote, setLoadNote] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>({});
  useEffect(() => {
    let active = true;

    async function loadStatus() {
      setLoading(true);
      setLoadNote(null);
      try {
        const response = await fetch("/api/pilot-status", { cache: "no-store" });
        const payload = response.ok ? ((await response.json()) as PilotStatusResponse) : null;

        if (active) {
          setFrontend(payload?.frontend ?? null);
          setBackend(payload?.backend ?? null);
          setLocalSetup(payload?.localSetup ?? null);
          setLocalSetupSource(payload?.localSetupSource ?? null);
          setLastUpdatedAt(new Date().toLocaleTimeString("tr-TR"));
          if (!payload?.backend) {
            setLoadNote("Arka uç pilot verisi şu an alınamadı. Ön yüz teşhis kartlarıyla devam edebiliriz.");
          }
        }
      } catch {
        try {
          const readyResponse = await fetch("/api/ready", { cache: "no-store" });
          const readyPayload = readyResponse.ok ? ((await readyResponse.json()) as FrontendStatus) : null;

          if (active) {
            setFrontend(readyPayload);
            setBackend(null);
            setLocalSetup(null);
            setLastUpdatedAt(new Date().toLocaleTimeString("tr-TR"));
            setLoadNote("Pilot köprüsü şu an cevap vermiyor. Ön yüz hazır mı diye yedek `/api/ready` kontrolü gösteriliyor.");
          }
        } catch {
          if (active) {
            setFrontend(null);
            setBackend(null);
            setLocalSetup(null);
            setLastUpdatedAt(new Date().toLocaleTimeString("tr-TR"));
            setLoadNote("Pilot durumu alınamadı. Önce /api/pilot-status ve /api/ready endpointlerini kontrol edeceğiz.");
          }
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadStatus();
    const intervalId = window.setInterval(() => {
      void loadStatus();
    }, 20000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("ck-v2-pilot-checklist");
      if (!stored) {
        return;
      }

      const parsed = JSON.parse(stored) as Record<string, boolean>;
      setCompletedItems(parsed);
    } catch {
      setCompletedItems({});
    }
  }, []);

  const backendChecks = useMemo(() => backend?.checks ?? [], [backend]);
  const backendConfig = useMemo(() => backend?.config ?? [], [backend]);
  const backendModules = useMemo(() => backend?.modules ?? [], [backend]);
  const pilotAccounts = useMemo(() => backend?.pilot_accounts ?? [], [backend]);
  const pilotFlow = useMemo(() => backend?.pilot_flow ?? [], [backend]);
  const pilotScenarios = useMemo(() => backend?.pilot_scenarios ?? [], [backend]);
  const deploySteps = useMemo(() => backend?.deploy_steps ?? [], [backend]);
  const rolloutSteps = useMemo(() => backend?.rollout_steps ?? [], [backend]);
  const pilotLinks = useMemo(() => backend?.pilot_links ?? [], [backend]);
  const smokeCommands = useMemo(() => backend?.smoke_commands ?? [], [backend]);
  const helperCommands = useMemo(() => backend?.helper_commands ?? [], [backend]);
  const commandPack = useMemo(() => backend?.command_pack ?? [], [backend]);
  const envHelperCommands = useMemo(
    () => helperCommands.filter((command) => command.category === "env"),
    [helperCommands],
  );
  const packetHelperCommands = useMemo(
    () => helperCommands.filter((command) => command.category === "packet"),
    [helperCommands],
  );
  const quickCheckCommands = useMemo(
    () => helperCommands.filter((command) => command.category === "quick-check"),
    [helperCommands],
  );
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
        detail: "/v2-api (hem yerel gelistirme hem Render pilot için aynı kalir)",
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
  const checklistKeys = useMemo(
    () => ({
      pilotFlow: pilotFlow.map((step) => `pilot-flow-${step.title}`),
      pilotScenarios: pilotScenarios.map((scenario) => `pilot-scenario-${scenario.title}`),
      deploySteps: deploySteps.map((step) => `deploy-step-${step.title}`),
      rolloutSteps: rolloutSteps.map((step) => `rollout-step-${step.title}`),
    }),
    [deploySteps, pilotFlow, pilotScenarios, rolloutSteps],
  );
  const checklistSummary = useMemo(() => {
    const pilotFlowCompleted = checklistKeys.pilotFlow.filter((key) => completedItems[key]).length;
    const pilotScenariosCompleted = checklistKeys.pilotScenarios.filter((key) => completedItems[key]).length;
    const deployStepsCompleted = checklistKeys.deploySteps.filter((key) => completedItems[key]).length;
    const rolloutStepsCompleted = checklistKeys.rolloutSteps.filter((key) => completedItems[key]).length;
    const total =
      checklistKeys.pilotFlow.length +
      checklistKeys.pilotScenarios.length +
      checklistKeys.deploySteps.length +
      checklistKeys.rolloutSteps.length;
    const completed =
      pilotFlowCompleted + pilotScenariosCompleted + deployStepsCompleted + rolloutStepsCompleted;

    return {
      pilotFlowCompleted,
      pilotScenariosCompleted,
      deployStepsCompleted,
      rolloutStepsCompleted,
      total,
      completed,
    };
  }, [checklistKeys, completedItems]);
  const readinessSummary = useMemo(() => {
    const activeModules = backendModules.filter((entry) => entry.status === "active").length;
    const totalModules = backendModules.length;
    const readyRolloutSteps = rolloutSteps.filter((step) => step.status === "ready").length;
    const totalRolloutSteps = rolloutSteps.length;
    const configuredRequiredBackendEnv = backendConfigEntries.filter((entry) => entry.required && entry.ok).length;
    const totalRequiredBackendEnv = backendConfigEntries.filter((entry) => entry.required).length;
    const phoneReadyAccounts = pilotAccounts.filter((entry) => entry.has_phone).length;

    return {
      activeModules,
      totalModules,
      readyRolloutSteps,
      totalRolloutSteps,
      configuredRequiredBackendEnv,
      totalRequiredBackendEnv,
      phoneReadyAccounts,
      totalPilotAccounts: pilotAccounts.length,
    };
  }, [backendConfigEntries, backendModules, pilotAccounts, rolloutSteps]);
  const overallOk = Boolean(frontend?.proxyConfigured) && Boolean(frontend?.backendReachable) && backend?.status === "ok";
  const coreReady = Boolean(frontend?.backendReachable) && Boolean(backend?.core_ready);
  const releaseAlignment = useMemo(() => {
    const frontendRelease = frontend?.releaseLabel || null;
    const backendRelease = backend?.release_label || null;
    const bothPresent = Boolean(frontendRelease && backendRelease);
    const mismatch = Boolean(frontendRelease && backendRelease && frontendRelease !== backendRelease);

    return {
      frontendRelease,
      backendRelease,
      bothPresent,
      mismatch,
    };
  }, [backend?.release_label, frontend?.releaseLabel]);
  const pilotSummaryText = useMemo(() => {
    const lines = [
      "Cat Kapında CRM v2 Pilot Durum Özeti",
      `Son kontrol: ${lastUpdatedAt ?? "bekleniyor"}`,
      `Durum: ${overallOk ? "Pilot hazır" : coreReady ? "Temel olarak hazır" : "Kontrol gerekli"}`,
      frontend?.releaseLabel ? `Ön yüz derlemesi: ${frontend.releaseLabel}` : null,
      backend?.release_label ? `Arka uç derlemesi: ${backend.release_label}` : null,
      backend?.decision ? `Bugünün kararı: ${backend.decision.title}` : null,
      `Modüller: ${readinessSummary.activeModules}/${readinessSummary.totalModules || 0}`,
      `Rollout: ${readinessSummary.readyRolloutSteps}/${readinessSummary.totalRolloutSteps || 0}`,
      `Arka uç ortamı: ${readinessSummary.configuredRequiredBackendEnv}/${readinessSummary.totalRequiredBackendEnv || 0}`,
      `Pilot hesap: ${readinessSummary.phoneReadyAccounts}/${readinessSummary.totalPilotAccounts || 0}`,
      backend?.cutover
        ? `Go-live fazı: ${
            backend.cutover.phase === "ready_for_cutover"
              ? "ready_for_cutover"
              : backend.cutover.phase === "ready_for_pilot"
                ? "ready_for_pilot"
                : "blocked"
          }`
        : null,
      backend?.next_actions?.[0] ? `Sonraki adım: ${backend.next_actions[0]}` : null,
      backend?.cutover?.blocking_items?.length
        ? `Blokajlar: ${backend.cutover.blocking_items.join(" | ")}`
        : "Blokajlar: yok",
      backend?.cutover?.remaining_items?.length
        ? `Kalan maddeler: ${backend.cutover.remaining_items.join(" | ")}`
        : "Kalan maddeler: yok",
      releaseAlignment.mismatch
        ? `Sürüm uyumsuzluğu: ön yüz=${releaseAlignment.frontendRelease} arka uç=${releaseAlignment.backendRelease}`
        : releaseAlignment.bothPresent
          ? `Sürüm uyumu: ${releaseAlignment.frontendRelease}`
          : "Sürüm uyumu: eksik bilgi",
      frontend?.detail ? `Ön yüz: ${frontend.detail}` : null,
    ];

    return lines.filter(Boolean).join("\n");
  }, [backend, coreReady, frontend, lastUpdatedAt, overallOk, readinessSummary, releaseAlignment]);
  const frontendRecoveryTips = useMemo(() => {
    if (!frontend) {
      return ["Ön yüz durum verisi alınamadı. Önce `/api/pilot-status` ve `/api/ready` uç noktalarını açıp cevap dönüyor mu kontrol et."];
    }

    if (!frontend.proxyConfigured) {
      return [
        "Ön yüz tarafında arka uç hedefi hiç görünmüyor. Render pilotunda `CK_V2_INTERNAL_API_HOSTPORT` hizmet bağlantısını kontrol et.",
        "Yerel denemede çalışıyorsan CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000 ayarının .env.local içinde olduğundan emin ol.",
      ];
    }

    if (frontend.proxyMode === "render_hostport" && !frontend.backendReachable) {
      return [
        "Ön yüz Render iç adres kipinde ama arka uca ulaşamıyor. Önce `crmcatkapinda-v2-api` servisinin `/api/health` uç noktasını aç.",
        "Render ön yüz servisinde `CK_V2_INTERNAL_API_HOSTPORT` değerinin gerçekten arka uç servisine hizmet bağlantısıyla bağlı olduğunu kontrol et.",
      ];
    }

    if (frontend.proxyMode === "explicit_base_url" && !frontend.backendReachable) {
      return [
        "Ön yüz açık taban adresi kipinde. Bu genelde yerel geliştirme içindir; pilotta yanlışlıkla bu ortam girildiyse kaldır.",
        "Yereldeysen CK_V2_INTERNAL_API_BASE_URL değerinin çalışan backend adresine işaret ettiğini doğrula.",
      ];
    }

    if (frontend.backendReachable) {
      return [
        "Ön yüz arka ucu görüyor. Bundan sonraki odak `/status` ekranındaki geçiş ve modül kartları olmalı.",
      ];
    }

    return ["Ön yüz geçiş katmanı kontrol edilmeli. `/api/ready` ve `/api/pilot-status` cevaplarını birlikte incele."];
  }, [frontend]);
  const cutoverTone =
    backend?.cutover.phase === "ready_for_cutover"
      ? true
      : backend?.cutover.phase === "ready_for_pilot"
        ? true
        : false;
  const goLiveDecisionCommand = useMemo(
    () => helperCommands.find((command) => command.label === "Go-Live Decision Report")?.command ?? null,
    [helperCommands],
  );
  const goLiveSummary = backend?.go_live ?? null;
  const localBackendEnvRestartNeeded =
    !!localSetup &&
    (localSetup.backend_restart_required ||
      (!!frontend &&
        localSetup.database_url_present &&
        frontend.backendReachable &&
        frontend.pilotHttpStatus === 503 &&
        (frontend.pilotErrorDetail?.includes("DATABASE_URL") || frontend.detail.includes("DATABASE_URL"))));
  const localSetupGuidance = useMemo(() => {
    if (!frontend || frontend.proxyMode !== "explicit_base_url") {
      return null;
    }

    if ((!frontend.proxyConfigured || localSetup?.frontend_env_needs_sync) && localSetup?.suggested_frontend_env_command) {
      return {
        tone: "warning" as const,
        title: "Ön yüz yerel geçiş ayarı yeniden yazılmalı.",
        detail:
          "Bu yerel kipte ön yüz, arka uç hedefini `.env.local` içinden okuyor. Kurulum yardımcısı şu an en doğru yerel API hedefiyle bu dosyayı tek komutla yeniden üretebilir.",
        commands: [
          localSetup.suggested_frontend_env_command,
          "python v2/scripts/local_v2_doctor.py",
        ],
      };
    }

    if (!frontend.backendReachable) {
      return {
        tone: "warning" as const,
        title: "Yerel arka uç henüz görünmüyor.",
        detail:
          "Ön yüz açık taban adresi kipinde 127.0.0.1:8000 hedefini arıyor. Bu yerel senaryoda normal; arka uç ayağa kalkmadan giriş ve şifre kurtarma akışı tamamlanmaz.",
        commands: [
          localSetup?.suggested_backend_start_command || "cd v2/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
          "python v2/scripts/local_v2_doctor.py",
        ],
      };
    }

    if (localBackendEnvRestartNeeded) {
      return {
        tone: "warning" as const,
        title: "Arka uç ortamı güncel, ama çalışan süreç yeniden başlatılmalı.",
        detail:
          localSetup?.backend_restart_reason ||
          "Kurulum yardımcısı `backend/.env` tarafında `DATABASE_URL` gördüğü halde çalışan arka uç hâlâ eski ortam ile 503 dönüyor. Bu yerel durumda tipik olarak uvicorn sürecinin ortam yazıldıktan sonra yeniden başlatılması gerekir.",
        commands: [
          localSetup?.suggested_backend_restart_command ||
            localSetup?.suggested_backend_start_command ||
            "cd v2/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
          "python v2/scripts/local_v2_doctor.py",
        ],
      };
    }

    const databaseMissing =
      frontend.pilotHttpStatus === 503 &&
      (frontend.pilotErrorDetail?.includes("DATABASE_URL") || frontend.detail.includes("DATABASE_URL"));

    if (databaseMissing) {
      return {
        tone: "warning" as const,
        title: "Arka uç ayakta, veritabanı ortamı eksik.",
        detail:
          "Bu yerel durumda API cevap veriyor ama `DATABASE_URL` olmadığı için gerçek kimlik doğrulama akışı tamamlanamıyor. Kurulum yardımcısı komutlarıyla mevcut kaynakları tarayıp `backend/.env` dosyasını hazırlayabiliriz.",
        commands: [
          "python v2/scripts/local_v2_doctor.py",
          localSetup?.suggested_bootstrap_command || localSetup?.suggested_scaffold_command || "python v2/scripts/local_v2_doctor.py --write-backend-scaffold --sync-from-current-app",
          localSetup?.suggested_bootstrap_with_db_command || localSetup?.suggested_env_write_command || "python v2/scripts/local_v2_doctor.py --write-backend-env --database-url '<postgresql://...>' --overwrite-backend-env",
        ],
      };
    }

    if (frontend.backendReachable && !backend) {
      return {
        tone: "info" as const,
        title: "Arka uç görünüyor, ayrıntılı hazırlık verisi sınırlı.",
        detail:
          frontend.pilotErrorDetail ||
          "Pilot durumu tam dönmedi ama ön yüz arka ucu görüyor. Bir sonraki odak yerel ortam ve veritabanı bağlantısı olmalı.",
        commands: ["python v2/scripts/local_v2_doctor.py"],
      };
    }

    return null;
  }, [backend, frontend, localBackendEnvRestartNeeded, localSetup]);
  const localSqliteLoginReady = useMemo(() => {
    if (!localSetup || !frontend || frontend.proxyMode !== "explicit_base_url" || !frontend.backendReachable) {
      return null;
    }

    const sqliteFallbackReady =
      localSetup.warnings.some((item) => item.toLowerCase().includes("sqlite fallback")) ||
      localSetup.decision_headline.toLowerCase().includes("sqlite");

    if (!sqliteFallbackReady || pilotAccounts.length === 0) {
      return null;
    }

    return {
      accounts: pilotAccounts.slice(0, 3),
      defaultPasswordPresent: localSetup.default_auth_password_present,
      defaultPasswordIsDefault: localSetup.default_auth_password_is_default,
    };
  }, [frontend, localSetup, pilotAccounts]);
  const localSqliteSmokeCommand = useMemo(() => {
    if (!localSqliteLoginReady || localSqliteLoginReady.accounts.length === 0) {
      return null;
    }

    const smokeAccount =
      localSqliteLoginReady.accounts.find((account) => account.default_password_active) || localSqliteLoginReady.accounts[0];
    const passwordPart =
      localSqliteLoginReady.defaultPasswordIsDefault && smokeAccount.default_password_active
        ? " --password 123456"
        : " --password <güncel-şifre>";
    return `python v2/scripts/pilot_smoke.py --base-url http://127.0.0.1:3001 --identity ${smokeAccount.email}${passwordPart}`;
  }, [localSqliteLoginReady]);

  async function copyText(key: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      window.setTimeout(() => {
        setCopiedKey((current) => (current === key ? null : current));
      }, 1800);
    } catch {
      setCopiedKey(null);
    }
  }

  function toggleCompleted(key: string) {
    setCompletedItems((current) => {
      const next = { ...current, [key]: !current[key] };
      try {
        window.localStorage.setItem("ck-v2-pilot-checklist", JSON.stringify(next));
      } catch {
        // localStorage erişimi olmasa da checklist deneyimi bozulmasın.
      }
      return next;
    });
  }

  function clearChecklist() {
    setCompletedItems({});
    try {
      window.localStorage.removeItem("ck-v2-pilot-checklist");
    } catch {
      // localStorage erişimi olmasa da ekran çalışmaya devam etsin.
    }
  }

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
            Bu sayfa yeni sistemin gerçekten ayağa kalkıp kalkmadığını tek bakışta gösterir. Ön yüz geçiş katmanı,
            arka uç servis ve veritabanı erişimi burada birlikte kontrol edilir.
          </p>
          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <Link href="/login" style={actionButtonStyle("primary")}>
              Pilotu Aç
            </Link>
            <Link href="/" style={actionButtonStyle()}>
              Genel Bakışa Dön
            </Link>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{
                ...actionButtonStyle(),
                cursor: "pointer",
              }}
            >
              Şimdi Yenile
            </button>
            <button
              type="button"
              onClick={() => void copyText("pilot-summary", pilotSummaryText)}
              style={{
                ...actionButtonStyle(),
                cursor: "pointer",
              }}
            >
              {copiedKey === "pilot-summary" ? "Durum Kopyalandı" : "Durum Özetini Kopyala"}
            </button>
            <div
              style={{
                color: "#5f7294",
                fontWeight: 700,
                fontSize: "0.92rem",
              }}
            >
              {lastUpdatedAt ? `Son kontrol: ${lastUpdatedAt}` : "Son kontrol bekleniyor"}
            </div>
          </div>
        </section>

        <section
          style={{
            ...cardStyle(),
            display: "grid",
            gap: "16px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.15rem" }}>Pilot Hazırlık Özeti</h2>
            <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
              Tek bakışta ne kadar yol aldığımızı ve ilk açılış için hangi halkaların tamam olduğunu buradan görebiliriz.
            </p>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div style={{ color: "#5f7294", fontSize: "0.82rem", fontWeight: 800, textTransform: "uppercase" }}>Modüller</div>
              <strong style={{ fontSize: "1.6rem", color: "#16274a" }}>
                {readinessSummary.activeModules}/{readinessSummary.totalModules || 0}
              </strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>Pilotta açık ana modüller</div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div style={{ color: "#5f7294", fontSize: "0.82rem", fontWeight: 800, textTransform: "uppercase" }}>Açılış Sırası</div>
              <strong style={{ fontSize: "1.6rem", color: "#16274a" }}>
                {readinessSummary.readyRolloutSteps}/{readinessSummary.totalRolloutSteps || 0}
              </strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>Hazır açılış adımları</div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div style={{ color: "#5f7294", fontSize: "0.82rem", fontWeight: 800, textTransform: "uppercase" }}>Arka Uç Ortamı</div>
              <strong style={{ fontSize: "1.6rem", color: "#16274a" }}>
                {readinessSummary.configuredRequiredBackendEnv}/{readinessSummary.totalRequiredBackendEnv || 0}
              </strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>Zorunlu arka uç ayarı</div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div style={{ color: "#5f7294", fontSize: "0.82rem", fontWeight: 800, textTransform: "uppercase" }}>Pilot Hesap</div>
              <strong style={{ fontSize: "1.6rem", color: "#16274a" }}>
                {readinessSummary.phoneReadyAccounts}/{readinessSummary.totalPilotAccounts || 0}
              </strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>Telefon hazır hesap</div>
            </article>
          </div>
        </section>

        {goLiveSummary ? (
          <section
            style={{
              ...cardStyle(),
              display: "grid",
              gap: "16px",
              background:
                goLiveSummary.phase === "ready_for_cutover"
                  ? "linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(255,255,255,0.98))"
                  : goLiveSummary.phase === "ready_for_pilot"
                    ? "linear-gradient(135deg, rgba(15, 95, 215, 0.06), rgba(255,255,255,0.98))"
                    : "linear-gradient(135deg, rgba(239, 68, 68, 0.06), rgba(255,255,255,0.98))",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.15fr) minmax(280px, 0.85fr)",
                gap: "18px",
              }}
            >
              <div style={{ display: "grid", gap: "12px" }}>
                <div style={tonePill(goLiveSummary.tone)}>{goLiveSummary.phase_label}</div>
                <div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Go-live kararı</h2>
                  <p style={{ margin: "8px 0 0", color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
                    {goLiveSummary.summary}
                  </p>
                </div>
                <article
                  style={{
                    padding: "14px 16px",
                    borderRadius: "16px",
                    border: "1px solid rgba(219, 228, 243, 0.9)",
                    background: "rgba(255,255,255,0.92)",
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  <strong>Sonraki adım</strong>
                  <div style={{ color: "#5f7294", lineHeight: 1.7 }}>{goLiveSummary.recommended_next_step}</div>
                </article>
                {goLiveSummary.future_cutover_blocking_items.length ? (
                  <article
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
                    <strong>
                      {goLiveSummary.phase === "blocked" ? "Açılış blokajları" : "Cutover için kalanlar"}
                    </strong>
                    {goLiveSummary.future_cutover_blocking_items.slice(0, 4).map((item) => (
                      <div key={item} style={{ lineHeight: 1.6 }}>
                        • {item}
                      </div>
                    ))}
                  </article>
                ) : null}
              </div>
              <div style={{ display: "grid", gap: "12px", alignContent: "start" }}>
                <div style={statusPill(goLiveSummary.phase !== "blocked")}>
                  Pilot: {goLiveSummary.phase === "blocked" ? "bloklu" : "açılabilir"}
                </div>
                <div style={statusPill(goLiveSummary.phase === "ready_for_cutover")}>
                  Cutover: {goLiveSummary.phase === "ready_for_cutover" ? "hazır" : "bekliyor"}
                </div>
                <Link href="#deploy-readiness" style={actionButtonStyle("primary")}>
                  Deploy Hazırlığını Aç
                </Link>
                <Link href="#rollout-steps" style={actionButtonStyle()}>
                  Açılış Sırasına Git
                </Link>
                {goLiveDecisionCommand ? (
                  <button
                    type="button"
                    onClick={() => void copyText("go-live-decision-command", goLiveDecisionCommand)}
                    style={{
                      ...actionButtonStyle(),
                      cursor: "pointer",
                    }}
                  >
                    {copiedKey === "go-live-decision-command" ? "Komut Kopyalandı" : "Go-Live Komutunu Kopyala"}
                  </button>
                ) : null}
              </div>
            </div>
          </section>
        ) : null}

        {localSetupGuidance ? (
          <section
            style={{
              ...cardStyle(),
              display: "grid",
              gap: "16px",
              border:
                localSetupGuidance.tone === "warning"
                  ? "1px solid rgba(245, 158, 11, 0.22)"
                  : "1px solid rgba(15, 95, 215, 0.16)",
              background:
                localSetupGuidance.tone === "warning"
                  ? "linear-gradient(180deg, rgba(255,249,235,0.98), rgba(255,255,255,0.98))"
                  : "linear-gradient(180deg, rgba(239,246,255,0.98), rgba(255,255,255,0.98))",
            }}
          >
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={tonePill(localSetupGuidance.tone === "warning" ? "warning" : "info")}>
                Yerel Kurulum Rehberi
              </div>
              <div style={{ color: "#5f7294", fontWeight: 700, fontSize: "0.92rem" }}>
                Localhost + açık taban adresi kipi
              </div>
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.15rem" }}>{localSetupGuidance.title}</h2>
              <p style={{ margin: "8px 0 0", color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
                {localSetupGuidance.detail}
              </p>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "12px",
              }}
            >
              {localSetupGuidance.commands.map((command, index) => (
                <article
                  key={command}
                  style={{
                    borderRadius: "18px",
                    border: "1px solid rgba(219, 228, 243, 0.9)",
                    background: "rgba(255,255,255,0.88)",
                    padding: "16px",
                    display: "grid",
                    gap: "10px",
                  }}
                >
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>
                    Adım {index + 1}
                  </div>
                  <code
                    style={{
                      display: "block",
                      padding: "10px 12px",
                      borderRadius: "14px",
                      background: "rgba(16, 24, 40, 0.06)",
                      color: "#16274a",
                      fontSize: "0.84rem",
                      lineHeight: 1.6,
                      overflowX: "auto",
                    }}
                  >
                    {command}
                  </code>
                  <button
                    type="button"
                    onClick={() => void copyText(`local-setup-${index}`, command)}
                    style={{
                      ...actionButtonStyle(index === 0 ? "primary" : "ghost"),
                      cursor: "pointer",
                      width: "fit-content",
                    }}
                  >
                    {copiedKey === `local-setup-${index}` ? "Komut Kopyalandı" : "Komutu Kopyala"}
                  </button>
                </article>
              ))}
            </div>
            {localSetup ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Kurulum Özeti</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    Karar: {localSetup.decision_headline || "belirsiz"}
                    <br />
                    Arka uç `.env`: {localSetup.backend_env_exists ? "var" : "yok"}
                    <br />
                    Ön yüz `.env.local`: {localSetup.frontend_env_exists ? "var" : "yok"}
                    <br />
                    Ön yüz ortam eşitlemesi: {localSetup.frontend_env_needs_sync ? "gerekiyor" : "hazır"}
                    <br />
                    Arka uç yeniden başlatma: {localBackendEnvRestartNeeded ? "gerekiyor" : "gerekli görünmüyor"}
                    <br />
                    Çalışan veritabanı bağlantısı: {localSetup.runtime_database_url_present ? "var" : "yok"}
                    <br />
                    Arka uç `.env` veritabanı: {localSetup.backend_env_database_url_present ? "var" : "yok"}
                    <br />
                    Yerel kurulum kaynağı:{" "}
                    {localSetupSource === "frontend_local_doctor"
                      ? "ön yüz yedeği"
                      : localSetupSource === "backend"
                        ? "arka uç uç noktası"
                        : "bilinmiyor"}
                    <br />
                    Mevcut uygulama kaynağı: {localSetup.current_app_seed_detected ? "bulundu" : "bulunmadı"}
                  </div>
                </article>
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Canlı Yerel Ön Yüz</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    {localSetup.detected_frontend_urls.length
                      ? localSetup.detected_frontend_urls.join(" | ")
                      : "Kurulum yardımcısı şu an cevap veren bir yerel ön yüz adresi göremedi."}
                  </div>
                </article>
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Önerilen Yerel Hedef</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    Ön yüz: {localSetup.suggested_frontend_url || "bilinmiyor"}
                    <br />
                    API: {localSetup.suggested_api_url || "bilinmiyor"}
                  </div>
                </article>
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Eksik Halkalar</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    {localSetup.blocking_items.length
                      ? localSetup.blocking_items.join(" ")
                      : "Zorunlu blokaj görünmüyor."}
                  </div>
                </article>
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>İlk Hamle</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    {localSetup.decision_detail || "Kurulum yardımcısı ayrı bir ilk öneri notu üretmedi."}
                  </div>
                  {localSetup.decision_command ? (
                    <button
                      type="button"
                      onClick={() => void copyText("doctor-decision-command", localSetup.decision_command!)}
                      style={{
                        ...actionButtonStyle("ghost"),
                        cursor: "pointer",
                        marginTop: "12px",
                        width: "fit-content",
                      }}
                    >
                      {copiedKey === "doctor-decision-command" ? "Komut Kopyalandı" : "İlk Komutu Kopyala"}
                    </button>
                  ) : null}
                </article>
                {localSqliteLoginReady ? (
                  <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                    <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Yerel Gerçek Giriş</div>
                    <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                      Arka uç şu an yerel sqlite desteğiyle ayakta. PostgreSQL olmadan da gerçek e-posta/şifre
                      akışını burada deneyebiliriz.
                    </div>
                    <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
                      {localSqliteLoginReady.accounts.map((account) => (
                        <div
                          key={account.email}
                          style={{
                            borderRadius: "14px",
                            border: "1px solid rgba(219, 228, 243, 0.9)",
                            background: "rgba(248,250,255,0.78)",
                            padding: "10px 12px",
                            display: "grid",
                            gap: "4px",
                          }}
                        >
                          <strong style={{ color: "#16274a" }}>{account.full_name}</strong>
                          <code
                            style={{
                              display: "inline-block",
                              fontSize: "0.84rem",
                              color: "#0f3f91",
                              wordBreak: "break-all",
                            }}
                          >
                            {account.email}
                          </code>
                          <span style={{ color: "#5f7294", fontSize: "0.92rem" }}>{account.role}</span>
                          <span style={{ color: "#5f7294", fontSize: "0.88rem" }}>
                            {account.default_password_active
                              ? "Varsayılan şifre aktif görünüyor."
                              : account.must_change_password
                                ? "Geçici şifre bekliyor; güncel şifre gerekli."
                                : "Şifre daha önce değiştirilmiş görünüyor."}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: "12px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                      {localSqliteLoginReady.defaultPasswordIsDefault &&
                      localSqliteLoginReady.accounts.some((account) => account.default_password_active)
                        ? "Sadece 'Varsayılan şifre aktif' yazan hesaplarda yerel şifre 123456 olarak kullanılabilir."
                        : localSqliteLoginReady.defaultPasswordPresent
                          ? "Hesap şifreleri bu makinede değişmiş olabilir; smoke veya login denemesinde güncel şifreyi kullan."
                          : "Şifre tanımlı görünmüyor; giriş öncesi `backend/.env` tarafını kontrol et."}
                    </div>
                    {localSqliteSmokeCommand ? (
                      <>
                        <code
                          style={{
                            display: "block",
                            marginTop: "12px",
                            padding: "10px 12px",
                            borderRadius: "14px",
                            background: "rgba(16, 24, 40, 0.06)",
                            color: "#16274a",
                            fontSize: "0.84rem",
                            lineHeight: 1.6,
                            overflowX: "auto",
                          }}
                        >
                          {localSqliteSmokeCommand}
                        </code>
                        <button
                          type="button"
                          onClick={() => void copyText("local-sqlite-smoke", localSqliteSmokeCommand)}
                          style={{
                            ...actionButtonStyle("ghost"),
                            cursor: "pointer",
                            marginTop: "12px",
                            width: "fit-content",
                          }}
                        >
                          {copiedKey === "local-sqlite-smoke" ? "Komut Kopyalandı" : "Yerel Yoklama Komutunu Kopyala"}
                        </button>
                      </>
                    ) : null}
                  </article>
                ) : null}
                <article style={{ ...cardStyle(), padding: "16px", boxShadow: "none" }}>
                  <div style={{ color: "#35507d", fontWeight: 800, fontSize: "0.84rem" }}>Seed Kaynaklari</div>
                  <div style={{ marginTop: "8px", color: "#5f7294", lineHeight: 1.7, fontSize: "0.92rem" }}>
                    {localSetup.current_app_seed_sources.length
                      ? localSetup.current_app_seed_sources.join(" | ")
                      : localSetup.current_app_seed_placeholders.length
                        ? `Sadece template bulundu: ${localSetup.current_app_seed_placeholders.join(" | ")}`
                        : "Kullanilabilir current app seed bulunamadı."}
                  </div>
                </article>
              </div>
            ) : null}
          </section>
        ) : null}

        <section
          style={{
            ...cardStyle(),
            display: "grid",
            gap: "12px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.15rem" }}>Hızlı Geçişler</h2>
            <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
              Pilot açılışında en çok bakacağımız bölümlere buradan doğrudan atlayabiliriz.
            </p>
          </div>
          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <a href="#pilot-scenarios" style={actionButtonStyle()}>
              Pilot Senaryolari
            </a>
            <a href="#rollout-steps" style={actionButtonStyle()}>
              Açılış Sırası
            </a>
            <a href="#deploy-readiness" style={actionButtonStyle()}>
              Deploy Hazırlığı
            </a>
            <a href="#render-services" style={actionButtonStyle()}>
              Render Servisleri
            </a>
          </div>
        </section>

        <section
          style={{
            ...cardStyle(),
            display: "grid",
            gap: "16px",
          }}
        >
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
              <h2 style={{ margin: 0, fontSize: "1.15rem" }}>Pilot Takip Listesi</h2>
              <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                Açılış günü hangi adımı tamamladığımızı burada işaretleyebiliriz. Bu işaretler tarayıcıda saklanır.
              </p>
            </div>
            <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={statusPill(checklistSummary.completed === checklistSummary.total && checklistSummary.total > 0)}>
                {checklistSummary.completed}/{checklistSummary.total || 0} tamam
              </div>
              <button
                type="button"
                onClick={clearChecklist}
                style={{
                  ...actionButtonStyle(),
                  cursor: "pointer",
                }}
              >
                Listeyi Sıfırla
              </button>
            </div>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "6px",
              }}
            >
              <strong>İlk Pilot Akışı</strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>
                {checklistSummary.pilotFlowCompleted}/{checklistKeys.pilotFlow.length || 0} adım tamam
              </div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "6px",
              }}
            >
              <strong>Pilot Senaryoları</strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>
                {checklistSummary.pilotScenariosCompleted}/{checklistKeys.pilotScenarios.length || 0} senaryo tamam
              </div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "6px",
              }}
            >
              <strong>Render Açılışı</strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>
                {checklistSummary.deployStepsCompleted}/{checklistKeys.deploySteps.length || 0} adım tamam
              </div>
            </article>
            <article
              style={{
                padding: "16px",
                borderRadius: "18px",
                border: "1px solid rgba(219, 228, 243, 0.9)",
                background: "rgba(248, 250, 255, 0.86)",
                display: "grid",
                gap: "6px",
              }}
            >
              <strong>Rollout Geçişi</strong>
              <div style={{ color: "#5f7294", lineHeight: 1.6 }}>
                {checklistSummary.rolloutStepsCompleted}/{checklistKeys.rolloutSteps.length || 0} adım tamam
              </div>
            </article>
          </div>
        </section>

        {loading ? (
          <section style={cardStyle()}>Pilot durumu yükleniyor...</section>
        ) : (
          <>
            {loadNote ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "10px",
                  background: "linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(255,255,255,0.98))",
                }}
              >
                <div style={statusPill(Boolean(frontend))}>
                  {frontend ? "Yedek Teşhis Açık" : "Bağlantı Kontrolü Gerekli"}
                </div>
                <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Pilot durum notu</h2>
                <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>{loadNote}</p>
              </section>
            ) : null}

            <section
              style={{
                ...cardStyle(),
                display: "grid",
                gap: "12px",
                background: releaseAlignment.mismatch
                  ? "linear-gradient(135deg, rgba(239, 68, 68, 0.06), rgba(255,255,255,0.98))"
                  : "linear-gradient(135deg, rgba(15, 95, 215, 0.05), rgba(255,255,255,0.98))",
              }}
            >
              <div style={statusPill(!releaseAlignment.mismatch)}>
                {releaseAlignment.mismatch
                  ? "Sürüm Uyumsuzluğu"
                  : releaseAlignment.bothPresent
                    ? "Sürümler Uyumlu"
                    : "Sürüm Etiketi Bekleniyor"}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "14px",
                }}
              >
                <article
                  style={{
                    padding: "16px",
                    borderRadius: "18px",
                    border: "1px solid rgba(219, 228, 243, 0.9)",
                    background: "rgba(248, 251, 255, 0.92)",
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <strong>Ön Yüz Derlemesi</strong>
                  <div style={{ color: "#35507d", fontSize: "1rem", fontWeight: 800 }}>
                    {releaseAlignment.frontendRelease ?? "henüz görünmüyor"}
                  </div>
                  <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{frontend?.service ?? "Ön yüz servisi bekleniyor"}</div>
                </article>
                <article
                  style={{
                    padding: "16px",
                    borderRadius: "18px",
                    border: "1px solid rgba(219, 228, 243, 0.9)",
                    background: "rgba(248, 251, 255, 0.92)",
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <strong>Arka Uç Derlemesi</strong>
                  <div style={{ color: "#35507d", fontSize: "1rem", fontWeight: 800 }}>
                    {releaseAlignment.backendRelease ?? "henüz görünmüyor"}
                  </div>
                  <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{backend?.service ?? "Arka uç servisi bekleniyor"}</div>
                </article>
              </div>
              <p style={{ margin: 0, color: releaseAlignment.mismatch ? "#b42318" : "#5f7294", lineHeight: 1.7 }}>
                {releaseAlignment.mismatch
                  ? "Ön yüz ve arka uç farklı dağıtım sürümlerinde görünüyor. Pilotta ilerlemeden önce iki servisin de aynı kayıtta olduğunu doğrulayalım."
                  : releaseAlignment.bothPresent
                    ? "İki servis aynı sürüm etiketini gösteriyor; bu, pilot açılışında doğru derleme ile ilerlediğimizi anlamayı kolaylaştırır."
                    : "Sürüm etiketi ortam değişkenlerinden henüz gelmiyor olabilir. Pilotta Render kayıt bilgisi gelince bu alan otomatik dolacak."}
              </p>
            </section>

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
                    ? "Cutover Hazır"
                    : backend.cutover.phase === "ready_for_pilot"
                    ? "Pilot Açılabilir"
                      : "Önce Blokajlar Kapanmalı"}
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1.2fr) minmax(280px, 0.8fr)",
                    gap: "18px",
                  }}
                >
                  <div style={{ display: "grid", gap: "10px" }}>
                    <h2 style={{ margin: 0, fontSize: "1.5rem" }}>Streamlit'ten çıkış özeti</h2>
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
                    <div style={statusPill(backend.cutover.core_checks_ready)}>Temel Kontroller Hazır</div>
                    <div style={statusPill(backend.cutover.auth_ready)}>Kimlik Doğrulama Hazır</div>
                    <div style={statusPill(backend.cutover.modules_ready_count === backend.cutover.modules_total_count)}>
                      Modül {backend.cutover.modules_ready_count}/{backend.cutover.modules_total_count}
                    </div>
                    <Link href="/login" style={actionButtonStyle("primary")}>
                      Giriş Ekranını Aç
                    </Link>
                    <Link href="/attendance" style={actionButtonStyle()}>
                      İlk Pilot Akışını Test Et
                    </Link>
                  </div>
                </div>
              </section>
            ) : null}

            {backend?.decision ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "12px",
                  background:
                    backend.decision.tone === "success"
                      ? "linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(255,255,255,0.98))"
                      : backend.decision.tone === "info"
                        ? "linear-gradient(135deg, rgba(15, 95, 215, 0.06), rgba(255,255,255,0.98))"
                        : "linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(255,255,255,0.98))",
                }}
              >
                <div style={tonePill(backend.decision.tone)}>Bugünün Kararı</div>
                <h2 style={{ margin: 0, fontSize: "1.45rem" }}>{backend.decision.title}</h2>
                <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7, maxWidth: "74ch" }}>
                  {backend.decision.detail}
                </p>
                <div>
                  <Link href={backend.decision.primary_href} style={actionButtonStyle("primary")}>
                    {backend.decision.primary_label}
                  </Link>
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
                <div style={statusPill(true)}>{overallOk ? "Pilot Kullanıma Hazır" : "Temel Yüzey Hazır"}</div>
                <h2 style={{ margin: 0, fontSize: "1.45rem" }}>
                  {overallOk ? "Yeni sisteme kontrollü geçiş başlayabilir." : "Pilot çekirdek olarak hazır, son ayarlar tamamlanabilir."}
                </h2>
                <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7, maxWidth: "72ch" }}>
                  {overallOk
                    ? "Ön yüz, arka uç ve temel kimlik doğrulama kontrolleri şu anda olumlu görünüyor. Ofis ekibi önce giriş ekranından girip puantaj, personel ve kesinti akışlarını yeni sistemde test etmeye başlayabilir."
                    : "Ön yüz ve arka uç çekirdek olarak ayakta. SMS gibi isteğe bağlı ayarlar tamamlandıkça pilot tam hazır seviyesine çıkacak."}
                </p>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <Link href="/login" style={actionButtonStyle("primary")}>
                    Giriş Ekranını Aç
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
                  <div style={statusPill(Boolean(frontend?.backendReachable))}>Pilot Bağlantıları</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Yayın sonrası bakacağın yerler</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Pilot açıldığında ekip bu linklerden ilerleyebilir. Aynı kartta smoke komutları da hazır.
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
                    <div
                      key={link.href}
                      style={{
                        display: "flex",
                        gap: "8px",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <a href={link.href} style={actionButtonStyle(link.label === "Pilot Login" ? "primary" : "ghost")}>
                        {link.label}
                      </a>
                      <button
                        type="button"
                        onClick={() => void copyText(`pilot-link-${link.label}`, link.href)}
                        style={{
                          ...actionButtonStyle(),
                          cursor: "pointer",
                          padding: "10px 12px",
                        }}
                      >
                        {copiedKey === `pilot-link-${link.label}` ? "Kopyalandı" : "Bağlantıyı Kopyala"}
                      </button>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                    gap: "14px",
                  }}
                >
                  {commandPack.length ? (
                    <div
                      style={{
                        gridColumn: "1 / -1",
                        display: "grid",
                        gap: "14px",
                      }}
                    >
                      <div>
                        <h3 style={{ margin: 0, fontSize: "1rem" }}>Açılış Komut Paketi</h3>
                        <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                          Pilot günü hangi komutu hangi sırayla çalıştıracağımızı tek blokta görüyoruz.
                        </p>
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                          gap: "14px",
                        }}
                      >
                        {commandPack.map((entry) => (
                          <div
                            key={entry.title}
                            style={{
                              padding: "16px",
                              borderRadius: "18px",
                              border: "1px solid rgba(219, 228, 243, 0.9)",
                              background: "rgba(248, 251, 255, 0.92)",
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
                                flexWrap: "wrap",
                              }}
                            >
                              <strong>{entry.title}</strong>
                              <button
                                type="button"
                                onClick={() => void copyText(`command-pack-${entry.title}`, entry.command)}
                                style={{
                                  ...actionButtonStyle(),
                                  cursor: "pointer",
                                  padding: "10px 12px",
                                }}
                              >
                                {copiedKey === `command-pack-${entry.title}` ? "Kopyalandı" : "Komutu Kopyala"}
                              </button>
                            </div>
                            <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{entry.detail}</div>
                            <code
                              style={{
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-word",
                                fontSize: "0.88rem",
                                lineHeight: 1.7,
                                color: "#25406b",
                              }}
                            >
                              {entry.command}
                            </code>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
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
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "10px",
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>{command.label}</strong>
                        <button
                          type="button"
                          onClick={() => void copyText(`smoke-${command.label}`, command.command)}
                          style={{
                            ...actionButtonStyle(),
                            cursor: "pointer",
                            padding: "10px 12px",
                          }}
                        >
                          {copiedKey === `smoke-${command.label}` ? "Kopyalandı" : "Komutu Kopyala"}
                        </button>
                      </div>
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

                {helperCommands.length ? (
                  <div
                    style={{
                      display: "grid",
                      gap: "14px",
                    }}
                  >
                    <div>
                      <h3 style={{ margin: 0, fontSize: "1rem" }}>Ortam Yardımcı Komutları</h3>
                      <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                        Render env bloklarini tek komutta üretmek için bu yardımcıları kullanabiliriz.
                      </p>
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                        gap: "14px",
                      }}
                    >
                      {envHelperCommands.map((command) => (
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
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "10px",
                              flexWrap: "wrap",
                            }}
                          >
                            <strong>{command.label}</strong>
                            <button
                              type="button"
                              onClick={() => void copyText(`helper-${command.label}`, command.command)}
                              style={{
                                ...actionButtonStyle(),
                                cursor: "pointer",
                                padding: "10px 12px",
                              }}
                            >
                              {copiedKey === `helper-${command.label}` ? "Kopyalandı" : "Komutu Kopyala"}
                            </button>
                          </div>
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
                    {packetHelperCommands.length ? (
                      <div style={{ display: "grid", gap: "14px" }}>
                        <div>
                          <h3 style={{ margin: 0, fontSize: "1rem" }}>Açılış Paketi Komutları</h3>
                          <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                            Ekip için paylaşılabilir markdown açılış paketi üretmek istediğimizde bu komutları kullanabiliriz.
                          </p>
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                            gap: "14px",
                          }}
                        >
                          {packetHelperCommands.map((command) => (
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
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  gap: "10px",
                                  flexWrap: "wrap",
                                }}
                              >
                                <strong>{command.label}</strong>
                                <button
                                  type="button"
                                  onClick={() => void copyText(`helper-${command.label}`, command.command)}
                                  style={{
                                    ...actionButtonStyle(),
                                    cursor: "pointer",
                                    padding: "10px 12px",
                                  }}
                                >
                                  {copiedKey === `helper-${command.label}` ? "Kopyalandı" : "Komutu Kopyala"}
                                </button>
                              </div>
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
                      </div>
                    ) : null}
                    {quickCheckCommands.length ? (
                      <div style={{ display: "grid", gap: "14px" }}>
                        <div>
                          <h3 style={{ margin: 0, fontSize: "1rem" }}>Hızlı Kontrol Komutları</h3>
                          <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                            Full smoke koşturmadan önce servislerin temel sağlık yanıtlarını hızlıca doğrulamak için kullanabiliriz.
                          </p>
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                            gap: "14px",
                          }}
                        >
                          {quickCheckCommands.map((command) => (
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
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  gap: "10px",
                                  flexWrap: "wrap",
                                }}
                              >
                                <strong>{command.label}</strong>
                                <button
                                  type="button"
                                  onClick={() => void copyText(`helper-${command.label}`, command.command)}
                                  style={{
                                    ...actionButtonStyle(),
                                    cursor: "pointer",
                                    padding: "10px 12px",
                                  }}
                                >
                                  {copiedKey === `helper-${command.label}` ? "Kopyalandı" : "Komutu Kopyala"}
                                </button>
                              </div>
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
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>
            ) : null}

            {deploySteps.length ? (
              <section
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "16px",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={statusPill(true)}>Render Açılış Adımları</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Pilotu açarken izleyeceğimiz sıra</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Bu bölüm doğrudan Render tarafındaki manuel kurulumu adım adım özetler. Zamanı geldiğinde tek referans ekranımız burası olacak.
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "14px",
                  }}
                >
                  {deploySteps.map((step) => (
                    <article
                      key={step.title}
                      style={{
                        padding: "16px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.9)",
                        background: "rgba(248, 251, 255, 0.92)",
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
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>{step.title}</strong>
                        <button
                          type="button"
                          onClick={() => toggleCompleted(`deploy-step-${step.title}`)}
                          style={{
                            ...actionButtonStyle(completedItems[`deploy-step-${step.title}`] ? "primary" : "ghost"),
                            cursor: "pointer",
                            padding: "10px 12px",
                          }}
                        >
                          {completedItems[`deploy-step-${step.title}`] ? "Tamamlandı" : "Tamamla"}
                        </button>
                      </div>
                      <div style={{ color: "#5f7294", lineHeight: 1.7 }}>{step.detail}</div>
                      {step.service_name ? (
                        <div style={{ color: "#35507d", fontSize: "0.9rem", fontWeight: 700 }}>
                          Servis: {step.service_name}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {pilotServices.length ? (
              <section
                id="render-services"
                style={{
                  ...cardStyle(),
                  display: "grid",
                  gap: "16px",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={statusPill(true)}>Render Servisleri</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Pilotta açacağımız servisler</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Render üzerinde göreceğin servis adları ve açık sağlık adresleri burada tek yerde duruyor.
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
                        {service.service_type === "frontend" ? "Ön Yüz Servisi" : "Arka Uç Servisi"}
                      </div>
                      <strong style={{ fontSize: "1rem" }}>{service.name}</strong>
                      <div style={{ color: "#5f7294", fontSize: "0.92rem", lineHeight: 1.7 }}>
                        Açık Adres: {service.public_url}
                      </div>
                      <div style={{ color: "#5f7294", fontSize: "0.92rem", lineHeight: 1.7 }}>
                        Sağlık Adresi: {service.health_path}
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
                                {entry.configured ? "Hazır" : entry.required ? "Zorunlu" : "Opsiyonel"}
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
                  <div style={statusPill(true)}>Kopyala Yapıştır Ortam Planı</div>
                  <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Render'a girilecek örnek env blokları</h2>
                  <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.7 }}>
                    Pilotu açarken servis bazlı ortam değişkenlerini buradan referans alabilirsin. V2 servisleri yanında eski Streamlit servisine geçiş bandı veya yönlendirme vermek için gereken ortam bloğu da burada. Gizli alanları kendi gerçek değerlerinle doldurman yeterli.
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
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "10px",
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>{snippet.title}</strong>
                        <button
                          type="button"
                          onClick={() => void copyText(`env-${snippet.service_name}`, snippet.body)}
                          style={{
                            ...actionButtonStyle(),
                            cursor: "pointer",
                            padding: "10px 12px",
                          }}
                        >
                          {copiedKey === `env-${snippet.service_name}` ? "Kopyalandı" : "Ortam Bloğunu Kopyala"}
                        </button>
                      </div>
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
                  Ön Yüz
                </div>
                <h2 style={{ margin: "12px 0 8px", fontSize: "1.4rem" }}>{frontend?.service ?? "Erişilemiyor"}</h2>
                <div style={statusPill(Boolean(frontend?.proxyConfigured) && Boolean(frontend?.backendReachable))}>
                  {frontend?.proxyConfigured && frontend?.backendReachable
                    ? "Ön Yüz Hazır"
                    : frontend?.proxyConfigured
                      ? "Arka Uç Erişimi Eksik"
                      : "Geçiş Ayarı Eksik"}
                </div>
                {frontend ? (
                  <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
                    <p style={{ margin: 0, color: "#5f7294", lineHeight: 1.6 }}>{frontend.detail}</p>
                    {frontend.releaseLabel ? (
                      <div style={{ color: "#35507d", fontSize: "0.92rem", fontWeight: 700 }}>
                        Derleme: {frontend.releaseLabel}
                      </div>
                    ) : null}
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <div style={statusPill(Boolean(frontend.proxyConfigured))}>Geçiş Katmanı</div>
                      <div style={statusPill(frontend.proxyMode !== "missing")}>
                        {frontend.proxyMode === "explicit_base_url"
                          ? "Yerel Taban Adresi"
                          : frontend.proxyMode === "render_hostport"
                            ? "Render İç Adresi"
                            : "Geçiş Kipi Eksik"}
                      </div>
                      <div style={statusPill(Boolean(frontend.backendReachable))}>
                        Arka Uç {frontend.backendStatus !== "unknown" ? `(${frontend.backendStatus})` : ""}
                      </div>
                    </div>
                    {frontend.sourceEnvKey ? (
                      <div style={{ color: "#5f7294", fontSize: "0.92rem" }}>Kaynak değişken: {frontend.sourceEnvKey}</div>
                    ) : null}
                    {frontend.targetBaseUrl ? (
                      <div style={{ color: "#5f7294", fontSize: "0.92rem" }}>İç hedef: {frontend.targetBaseUrl}</div>
                    ) : null}
                  </div>
                ) : null}
              </article>

              <article style={cardStyle()}>
                <div style={{ color: "#5f7294", fontSize: "0.82rem", textTransform: "uppercase", fontWeight: 800 }}>
                  Arka Uç ve Kimlik Doğrulama
                </div>
                <h2 style={{ margin: "12px 0 8px", fontSize: "1.4rem" }}>{backend?.service ?? "Erişilemiyor"}</h2>
                  <div style={statusPill(Boolean(backend?.core_ready))}>
                  {backend?.status === "ok" ? "Arka Uç Hazır" : backend?.core_ready ? "Arka Uç Temel Olarak Hazır" : "Arka Uç Kontrol Gerekli"}
                </div>
                {backend ? (
                  <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
                    <p style={{ margin: 0, color: "#5f7294" }}>
                    {backend.environment} • v{backend.version}
                    </p>
                    {backend.release_label ? (
                      <div style={{ color: "#35507d", fontSize: "0.92rem", fontWeight: 700 }}>
                        Derleme: {backend.release_label}
                      </div>
                    ) : null}
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <div style={statusPill(backend.auth.email_login)}>E-posta</div>
                      <div style={statusPill(backend.auth.phone_login)}>Telefon</div>
                      <div style={statusPill(backend.auth.sms_login)}>
                        SMS {backend.auth.sms_allowlist_count ? `(${backend.auth.sms_allowlist_count})` : ""}
                      </div>
                      <div style={statusPill((backend.auth.admin_user_count ?? 0) > 0)}>
                        Yönetici {(backend.auth.admin_user_count ?? 0)}
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
                        Varsayılan v2 şifresi hala aktif görünüyor. Pilot öncesi bunu değiştirmen önerilir.
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            </section>

            <section id="deploy-readiness" style={cardStyle()}>
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
                  <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Ön Yüz Hızlı Teşhisi</h2>
                  <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                    Pilotta ön yüz tarafı tökezlerse önce bu kısa yorumlara bakacağız. Geçiş kipi ve arka uç erişimi birlikte yorumlanır.
                  </p>
                </div>
                <div style={statusPill(Boolean(frontend?.backendReachable))}>
                  {frontend?.backendReachable ? "Bağlantı Görünüyor" : "Kontrol Gerekli"}
                </div>
              </div>
              <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                {frontendRecoveryTips.map((tip) => (
                  <article
                    key={tip}
                    style={{
                      padding: "14px 16px",
                      borderRadius: "18px",
                      border: "1px solid rgba(219, 228, 243, 0.9)",
                      background: "rgba(248, 250, 255, 0.86)",
                      color: "#35507d",
                      lineHeight: 1.7,
                    }}
                  >
                    {tip}
                  </article>
                ))}
              </div>
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
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>İlk Pilot Test Akışı</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Ofisin yeni sisteme ilk girişte izleyeceği önerilen kısa rota.
                    </p>
                  </div>
                  <div style={statusPill(pilotFlow.length > 0)}>
                    {checklistSummary.pilotFlowCompleted}/{pilotFlow.length} adım
                  </div>
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
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "10px",
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>{step.title}</strong>
                        <div
                          style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => toggleCompleted(`pilot-flow-${step.title}`)}
                            style={{
                              ...actionButtonStyle(completedItems[`pilot-flow-${step.title}`] ? "primary" : "ghost"),
                              cursor: "pointer",
                              padding: "10px 12px",
                            }}
                          >
                            {completedItems[`pilot-flow-${step.title}`] ? "Tamamlandı" : "Tamamla"}
                          </button>
                          <button
                            type="button"
                            onClick={() => void copyText(`pilot-flow-${step.title}`, `${step.title}\n${step.detail}\n${step.href}`)}
                            style={{
                              ...actionButtonStyle(),
                              cursor: "pointer",
                              padding: "10px 12px",
                            }}
                          >
                            {copiedKey === `pilot-flow-${step.title}` ? "Kopyalandı" : "Adımı Kopyala"}
                          </button>
                        </div>
                      </div>
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

            {pilotScenarios.length ? (
              <section id="pilot-scenarios" style={cardStyle()}>
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
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Pilot Test Senaryoları</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Pilotu açtığımız ilk gün ekip bunları sırasıyla denerse yeni sistemin ana operasyon akışları hızlı şekilde doğrulanır.
                    </p>
                  </div>
                  <div style={statusPill(pilotScenarios.length > 0)}>
                    {checklistSummary.pilotScenariosCompleted}/{pilotScenarios.length} senaryo
                  </div>
                </div>
                <div
                  style={{
                    marginTop: "18px",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: "12px",
                  }}
                >
                  {pilotScenarios.map((scenario) => (
                    <article
                      key={scenario.title}
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
                          flexWrap: "wrap",
                          }}
                        >
                          <strong>{scenario.title}</strong>
                          <div
                            style={{
                              display: "flex",
                              gap: "8px",
                              alignItems: "center",
                              flexWrap: "wrap",
                            }}
                          >
                            <div style={statusPill(true)}>{scenario.module}</div>
                            <button
                              type="button"
                              onClick={() => toggleCompleted(`pilot-scenario-${scenario.title}`)}
                              style={{
                                ...actionButtonStyle(completedItems[`pilot-scenario-${scenario.title}`] ? "primary" : "ghost"),
                                cursor: "pointer",
                                padding: "10px 12px",
                              }}
                            >
                              {completedItems[`pilot-scenario-${scenario.title}`] ? "Tamamlandı" : "Tamamla"}
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                void copyText(
                                  `pilot-scenario-${scenario.title}`,
                                  `${scenario.title}\n${scenario.module}\n${scenario.detail}\nBaşarı işareti: ${scenario.success_hint}\n${scenario.href}`,
                                )
                              }
                              style={{
                                ...actionButtonStyle(),
                                cursor: "pointer",
                                padding: "10px 12px",
                              }}
                            >
                              {copiedKey === `pilot-scenario-${scenario.title}` ? "Kopyalandı" : "Senaryoyu Kopyala"}
                            </button>
                          </div>
                        </div>
                      <div style={{ color: "#5f7294", lineHeight: 1.6 }}>{scenario.detail}</div>
                      <div
                        style={{
                          padding: "12px 14px",
                          borderRadius: "16px",
                          border: "1px solid rgba(15, 95, 215, 0.12)",
                          background: "rgba(15, 95, 215, 0.05)",
                          color: "#35507d",
                          lineHeight: 1.6,
                        }}
                      >
                        Basari isareti: {scenario.success_hint}
                      </div>
                      <div>
                        <Link href={scenario.href} style={actionButtonStyle()}>
                          Senaryoyu Ac
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {rolloutSteps.length ? (
              <section id="rollout-steps" style={cardStyle()}>
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
                    {checklistSummary.rolloutStepsCompleted}/{rolloutSteps.length} adım tamam
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
                        <div
                          style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <div style={statusPill(step.status === "ready")}>
                            {step.status === "ready" ? "Hazır" : step.status === "blocked" ? "Bloklu" : "Sırada"}
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleCompleted(`rollout-step-${step.title}`)}
                            style={{
                              ...actionButtonStyle(completedItems[`rollout-step-${step.title}`] ? "primary" : "ghost"),
                              cursor: "pointer",
                              padding: "10px 12px",
                            }}
                          >
                            {completedItems[`rollout-step-${step.title}`] ? "Tamamlandı" : "Tamamla"}
                          </button>
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
                    <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Yayın Hazırlığı</h2>
                    <p style={{ margin: "6px 0 0", color: "#5f7294", lineHeight: 1.6 }}>
                      Pilotu açmadan önce hangi ortam değerlerinin eksik olduğunu ve sıradaki adımları burada gör.
                    </p>
                  </div>
                  <div style={statusPill((backend?.required_missing_env_vars?.length ?? 0) === 0)}>
                    {(backend?.required_missing_env_vars?.length ?? 0) === 0
                      ? "Zorunlu Ortam Tamam"
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
                    Opsiyonel eksikler: {backend?.optional_missing_env_vars.join(", ")}. Bunlar pilotu durdurmaz, sadece SMS gibi ek akışlar için gerekir.
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
                        Arka uç servisine girilecek ortam değişkenleri. Zorunlu eksikler burada görünür.
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
                      <strong style={{ fontSize: "1rem" }}>Render Ön Yüz Servisi</strong>
                      <div style={{ color: "#5f7294", lineHeight: 1.5 }}>
                        Ön yüz servisi Render pilotunda planla gelen ayarlarla ayağa kalkar. Yerel denemede ise aynı geçiş rotası korunur ama hedef ortam anahtarı değişir; aşağıdaki bloklar bunu netleştirir.
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
