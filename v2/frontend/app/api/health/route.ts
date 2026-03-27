export async function GET() {
  return Response.json(
    {
      status: "ok",
      service: "crmcatkapinda-v2-frontend",
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
