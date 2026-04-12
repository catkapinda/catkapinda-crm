export async function GET() {
  const commitSha = process.env.CK_V2_FRONTEND_RELEASE_SHA || process.env.RENDER_GIT_COMMIT || null;
  const serviceName = process.env.CK_V2_FRONTEND_SERVICE_NAME || process.env.RENDER_SERVICE_NAME || "crmcatkapinda-v2-frontend";
  const releaseLabel = commitSha ? commitSha.slice(0, 7) : serviceName;
  return Response.json(
    {
      status: "ok",
      service: serviceName,
      commitSha,
      releaseLabel,
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
