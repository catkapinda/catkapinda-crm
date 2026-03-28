export async function GET() {
  const proxyConfigured = Boolean(
    process.env.CK_V2_INTERNAL_API_BASE_URL || process.env.CK_V2_INTERNAL_API_HOSTPORT,
  );

  return Response.json(
    {
      status: proxyConfigured ? "ok" : "degraded",
      service: "crmcatkapinda-v2-frontend",
      proxyConfigured,
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
