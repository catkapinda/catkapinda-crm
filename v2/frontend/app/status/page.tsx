"use client";

import { useEffect, useMemo, useState } from "react";

type FrontendStatus = {
  status: string;
  service: string;
  proxyConfigured: boolean;
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
          fetch("/v2-api/health/ready", { cache: "no-store" }),
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
  const overallOk = Boolean(frontend?.proxyConfigured) && backend?.status === "ok";

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
        </section>

        {loading ? (
          <section style={cardStyle()}>Pilot durumu yükleniyor...</section>
        ) : (
          <>
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
                <div style={statusPill(Boolean(frontend?.proxyConfigured))}>
                  {frontend?.proxyConfigured ? "Proxy Hazır" : "Proxy Eksik"}
                </div>
              </article>

              <article style={cardStyle()}>
                <div style={{ color: "#5f7294", fontSize: "0.82rem", textTransform: "uppercase", fontWeight: 800 }}>
                  Backend
                </div>
                <h2 style={{ margin: "12px 0 8px", fontSize: "1.4rem" }}>{backend?.service ?? "Erisilemiyor"}</h2>
                <div style={statusPill(backend?.status === "ok")}>
                  {backend?.status === "ok" ? "Backend Hazır" : "Backend Kontrol Gerekli"}
                </div>
                {backend ? (
                  <p style={{ margin: "12px 0 0", color: "#5f7294" }}>
                    {backend.environment} • v{backend.version}
                  </p>
                ) : null}
              </article>
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
