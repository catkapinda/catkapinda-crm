const DEFAULT_TIMEOUT_MS = 4000;

export async function GET() {
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

  let backendReachable = false;
  let backendStatus = "unknown";
  let detail = proxyConfigured
    ? `Proxy ayarlı (${proxyMode}), backend kontrol ediliyor.`
    : "Proxy hedefi eksik.";

  if (targetBaseUrl) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
    try {
      const response = await fetch(`${targetBaseUrl}/api/health`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (response.ok) {
        const payload = (await response.json()) as { status?: string };
        backendReachable = true;
        backendStatus = payload.status || "ok";
        detail = `Frontend backend'e ulaşıyor (${proxyMode}).`;
      } else {
        backendStatus = `http_${response.status}`;
        detail = `Backend health HTTP ${response.status} döndü (${proxyMode}).`;
      }
    } catch (error) {
      backendStatus = "unreachable";
      detail =
        error instanceof Error
          ? `Backend erişimi kurulamadı (${proxyMode}): ${error.message}`
          : `Backend erişimi kurulamadı (${proxyMode}).`;
    } finally {
      clearTimeout(timeout);
    }
  }

  return Response.json(
    {
      status: proxyConfigured && backendReachable ? "ok" : "degraded",
      service: "crmcatkapinda-v2-frontend",
      proxyConfigured,
      proxyMode,
      sourceEnvKey,
      backendReachable,
      backendStatus,
      targetBaseUrl: targetBaseUrl || null,
      detail,
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
