const DEFAULT_TIMEOUT_MS = 4000;

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
  const target = resolveInternalTarget();
  let backendReachable = false;
  let backendStatus = "unknown";
  let detail = target.proxyConfigured
    ? `Proxy ayarlı (${target.proxyMode}), backend pilot durumu kontrol ediliyor.`
    : "Proxy hedefi eksik.";
  let pilotPayload: unknown = null;

  if (target.targetBaseUrl) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
    try {
      const [healthResponse, pilotResponse] = await Promise.all([
        fetch(`${target.targetBaseUrl}/api/health`, {
          cache: "no-store",
          signal: controller.signal,
        }),
        fetch(`${target.targetBaseUrl}/api/health/pilot`, {
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
        detail = `Pilot status HTTP ${pilotResponse.status} döndü (${target.proxyMode}).`;
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

  return Response.json(
    {
      status: target.proxyConfigured && backendReachable && pilotPayload ? "ok" : "degraded",
      frontend: {
        status: target.proxyConfigured && backendReachable ? "ok" : "degraded",
        service: "crmcatkapinda-v2-frontend",
        proxyConfigured: target.proxyConfigured,
        proxyMode: target.proxyMode,
        sourceEnvKey: target.sourceEnvKey,
        backendReachable,
        backendStatus,
        targetBaseUrl: target.targetBaseUrl || null,
        detail,
      },
      backend: pilotPayload,
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
