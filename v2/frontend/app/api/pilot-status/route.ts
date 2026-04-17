import { spawnSync } from "node:child_process";
import path from "node:path";

export const runtime = "nodejs";

const DEFAULT_TIMEOUT_MS = 12000;
const LOCAL_SETUP_DETAIL_KEYS = [
  "frontend_env_needs_sync",
  "suggested_frontend_url",
  "suggested_api_url",
  "suggested_bootstrap_command",
  "suggested_backend_restart_command",
  "backend_restart_required",
  "decision_status",
  "decision_headline",
  "decision_detail",
  "decision_command",
];

function isLoopbackTarget(targetBaseUrl: string) {
  try {
    const parsed = new URL(targetBaseUrl);
    return parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
  } catch {
    return false;
  }
}

function hasDetailedLocalSetupPayload(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return false;
  }

  return LOCAL_SETUP_DETAIL_KEYS.every((key) => key in payload);
}

function loadFreshLocalSetupPayload() {
  const scriptPath = path.resolve(process.cwd(), "..", "scripts", "local_v2_doctor.py");
  const result = spawnSync("python3", [scriptPath, "--json"], {
    encoding: "utf-8",
    env: process.env,
    timeout: DEFAULT_TIMEOUT_MS,
  });

  if (result.error || !result.stdout?.trim()) {
    return null;
  }

  try {
    const parsed = JSON.parse(result.stdout) as Record<string, unknown>;
    return parsed && !Array.isArray(parsed) && "ready" in parsed ? parsed : null;
  } catch {
    return null;
  }
}

function resolveInternalTarget() {
  const explicitBaseUrl = process.env.CK_V2_INTERNAL_API_BASE_URL || "";
  const hostportTarget = process.env.CK_V2_INTERNAL_API_HOSTPORT || "";
  const internalTarget = explicitBaseUrl || hostportTarget;
  const proxyConfigured = Boolean(internalTarget);
  const proxyMode = explicitBaseUrl ? "explicit_base_url" : hostportTarget ? "render_hostport" : "missing";
  const sourceEnvKey = explicitBaseUrl
    ? "CK_V2_INTERNAL_API_BASE_URL"
    : hostportTarget
      ? "CK_V2_INTERNAL_API_HOSTPORT"
      : null;
  const targetBaseUrl = explicitBaseUrl || (hostportTarget ? `http://${hostportTarget}` : "");

  return {
    proxyConfigured,
    proxyMode,
    sourceEnvKey,
    targetBaseUrl,
  };
}

export async function GET() {
  const frontendCommitSha = process.env.CK_V2_FRONTEND_RELEASE_SHA || process.env.RENDER_GIT_COMMIT || null;
  const frontendServiceName =
    process.env.CK_V2_FRONTEND_SERVICE_NAME || process.env.RENDER_SERVICE_NAME || "crmcatkapinda-v2-frontend";
  const frontendReleaseLabel = frontendCommitSha ? frontendCommitSha.slice(0, 7) : frontendServiceName;
  const target = resolveInternalTarget();
  let backendReachable = false;
  let backendStatus = "unknown";
  let detail = target.proxyConfigured
    ? `Proxy ayarlı (${target.proxyMode}), backend pilot durumu kontrol ediliyor.`
    : "Proxy hedefi eksik.";
  let pilotPayload: unknown = null;
  let localSetupPayload: unknown = null;
  let localSetupSource: "backend" | "frontend_local_doctor" | null = null;
  let pilotHttpStatus: number | null = null;
  let pilotErrorDetail: string | null = null;

  if (target.targetBaseUrl) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
    try {
      const [healthResponse, pilotResponse, localSetupResponse] = await Promise.all([
        fetch(`${target.targetBaseUrl}/api/health`, {
          cache: "no-store",
          signal: controller.signal,
        }),
        fetch(`${target.targetBaseUrl}/api/health/pilot`, {
          cache: "no-store",
          signal: controller.signal,
        }),
        fetch(`${target.targetBaseUrl}/api/health/local-setup`, {
          cache: "no-store",
          signal: controller.signal,
        }),
      ]);

      if (healthResponse.ok) {
        const healthPayload = (await healthResponse.json()) as { status?: string };
        backendReachable = true;
        backendStatus = healthPayload.status || "ok";
      } else {
        backendStatus = `http_${healthResponse.status}`;
      }

      if (pilotResponse.ok) {
        pilotPayload = await pilotResponse.json();
        detail = `Pilot status alındı (${target.proxyMode}).`;
      } else {
        pilotHttpStatus = pilotResponse.status;
        const errorPayload = (await pilotResponse.json().catch(() => null)) as { detail?: string } | null;
        pilotErrorDetail = typeof errorPayload?.detail === "string" ? errorPayload.detail : null;
        detail = pilotErrorDetail
          ? `Pilot status HTTP ${pilotResponse.status} döndü (${target.proxyMode}): ${pilotErrorDetail}`
          : `Pilot status HTTP ${pilotResponse.status} döndü (${target.proxyMode}).`;
      }

      if (localSetupResponse.ok) {
        localSetupPayload = await localSetupResponse.json();
        localSetupSource = "backend";
      }
    } catch (error) {
      backendStatus = "unreachable";
      detail =
        error instanceof Error
          ? `Pilot status alınamadı (${target.proxyMode}): ${error.message}`
          : `Pilot status alınamadı (${target.proxyMode}).`;
    } finally {
      clearTimeout(timeout);
    }
  }

  if (target.targetBaseUrl && isLoopbackTarget(target.targetBaseUrl) && !hasDetailedLocalSetupPayload(localSetupPayload)) {
    const freshLocalSetupPayload = loadFreshLocalSetupPayload();
    if (freshLocalSetupPayload) {
      localSetupPayload = freshLocalSetupPayload;
      localSetupSource = "frontend_local_doctor";
    }
  }

  return Response.json(
    {
      status: target.proxyConfigured && backendReachable && pilotPayload ? "ok" : "degraded",
      frontend: {
        status: target.proxyConfigured && backendReachable ? "ok" : "degraded",
        service: frontendServiceName,
        commitSha: frontendCommitSha,
        releaseLabel: frontendReleaseLabel,
        proxyConfigured: target.proxyConfigured,
        proxyMode: target.proxyMode,
        sourceEnvKey: target.sourceEnvKey,
        backendReachable,
        backendStatus,
        pilotHttpStatus,
        pilotErrorDetail,
        targetBaseUrl: target.targetBaseUrl || null,
        detail,
      },
      backend: pilotPayload,
      localSetup: localSetupPayload,
      localSetupSource,
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
