const DEFAULT_TIMEOUT_MS = 4000;

export async function GET() {
  const internalTarget =
    process.env.CK_V2_INTERNAL_API_BASE_URL || process.env.CK_V2_INTERNAL_API_HOSTPORT || "";
  const proxyConfigured = Boolean(internalTarget);
  const targetBaseUrl =
    process.env.CK_V2_INTERNAL_API_BASE_URL ||
    (process.env.CK_V2_INTERNAL_API_HOSTPORT ? `http://${process.env.CK_V2_INTERNAL_API_HOSTPORT}` : "");

  let backendReachable = false;
  let backendStatus = "unknown";
  let detail = proxyConfigured ? "Proxy ayarlı, backend kontrol ediliyor." : "Proxy hedefi eksik.";

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
        detail = "Frontend backend'e ulaşabiliyor.";
      } else {
        backendStatus = `http_${response.status}`;
        detail = `Backend health HTTP ${response.status} döndü.`;
      }
    } catch (error) {
      backendStatus = "unreachable";
      detail =
        error instanceof Error ? `Backend erişimi kurulamadı: ${error.message}` : "Backend erişimi kurulamadı.";
    } finally {
      clearTimeout(timeout);
    }
  }

  return Response.json(
    {
      status: proxyConfigured && backendReachable ? "ok" : "degraded",
      service: "crmcatkapinda-v2-frontend",
      proxyConfigured,
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
