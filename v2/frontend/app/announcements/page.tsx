"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type AnnouncementsDashboard = {
  module: string;
  status: string;
  kicker: string;
  title: string;
  description: string;
  metrics: Array<{
    label: string;
    value: string;
  }>;
  snapshots: Array<{
    title: string;
    items: Array<{
      label: string;
      value: string;
    }>;
  }>;
  notes_title: string;
  notes_body: string;
  footer_note: string;
};

const serifTitleStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const paperCardStyle = {
  borderRadius: "28px",
  border: "1px solid var(--line)",
  background: "var(--surface-raised)",
  boxShadow: "var(--shadow-soft)",
} as const;

export default function AnnouncementsPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<AnnouncementsDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading || !user) {
        return;
      }
      try {
        const response = await apiFetch("/announcements/dashboard");
        if (!response.ok) {
          throw new Error("Duyurular panosu şu anda yüklenemiyor.");
        }
        const payload = (await response.json()) as AnnouncementsDashboard;
        if (active) {
          setDashboard(payload);
          setError("");
        }
      } catch (nextError) {
        if (active) {
          setError(
            nextError instanceof Error ? nextError.message : "Duyurular panosu şu anda yüklenemiyor.",
          );
        }
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [loading, user]);

  return (
    <AppShell activeItem="Duyurular">
      <div
        style={{
          display: "grid",
          gap: "22px",
        }}
      >
        <section
          style={{
            ...paperCardStyle,
            padding: "28px",
            background:
              "linear-gradient(135deg, rgba(22,39,63,0.96), rgba(38,58,86,0.95) 62%, rgba(171,114,47,0.18))",
            color: "#fff7ea",
          }}
        >
          <div
            style={{
              maxWidth: "920px",
              display: "grid",
              gap: "12px",
            }}
          >
            <div
              style={{
                fontSize: "0.76rem",
                fontWeight: 800,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "rgba(255,247,234,0.72)",
              }}
            >
              {dashboard?.kicker || "Güncellemeler ve Duyurular"}
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: 0,
                fontSize: "clamp(2.8rem, 6vw, 5.3rem)",
                lineHeight: 0.94,
                fontWeight: 700,
              }}
            >
              {dashboard?.title || "Sistemdeki son iyileştirmeler ve takip notları"}
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "760px",
                lineHeight: 1.8,
                color: "rgba(255,247,234,0.82)",
                fontSize: "1rem",
              }}
            >
              {dashboard?.description ||
                "Operasyon ekibinin son yayınlanan geliştirmeleri tek ekranda görmesi için hazırlanan hızlı özet alanı."}
            </p>
          </div>
        </section>

        {error ? (
          <section
            style={{
              ...paperCardStyle,
              padding: "20px",
              background: "rgba(196,53,53,0.08)",
              color: "#9e2430",
            }}
          >
            {error}
          </section>
        ) : null}

        {dashboard ? (
          <>
            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "14px",
              }}
            >
              {dashboard.metrics.map((metric) => (
                <article
                  key={metric.label}
                  style={{
                    ...paperCardStyle,
                    padding: "18px 18px 16px",
                    background:
                      "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))",
                  }}
                >
                  <div
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.74rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      fontWeight: 800,
                    }}
                  >
                    {metric.label}
                  </div>
                  <div
                    style={{
                      ...serifTitleStyle,
                      marginTop: "10px",
                      fontSize: "1.8rem",
                      lineHeight: 0.95,
                      fontWeight: 700,
                    }}
                  >
                    {metric.value}
                  </div>
                </article>
              ))}
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "18px",
              }}
            >
              {dashboard.snapshots.map((snapshot) => (
                <article
                  key={snapshot.title}
                  style={{
                    ...paperCardStyle,
                    padding: "22px",
                    display: "grid",
                    gap: "16px",
                    background:
                      "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(249,244,235,0.95))",
                  }}
                >
                  <div
                    style={{
                      ...serifTitleStyle,
                      fontSize: "2rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    {snapshot.title}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gap: "12px",
                    }}
                  >
                    {snapshot.items.map((item) => (
                      <div
                        key={`${snapshot.title}-${item.label}`}
                        style={{
                          display: "grid",
                          gap: "6px",
                          paddingBottom: "12px",
                          borderBottom: "1px solid rgba(24,40,59,0.08)",
                        }}
                      >
                        <div
                          style={{
                            fontWeight: 800,
                            color: "var(--text)",
                          }}
                        >
                          {item.label}
                        </div>
                        <div
                          style={{
                            color: "var(--muted)",
                            lineHeight: 1.65,
                          }}
                        >
                          {item.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </section>

            <section
              style={{
                ...paperCardStyle,
                padding: "22px",
                display: "grid",
                gap: "10px",
                background:
                  "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
                border: "1px solid rgba(185,116,41,0.18)",
              }}
            >
              <div
                style={{
                  color: "var(--accent-strong)",
                  fontWeight: 800,
                  fontSize: "0.74rem",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                {dashboard.notes_title}
              </div>
              <div
                style={{
                  color: "var(--text)",
                  lineHeight: 1.75,
                }}
              >
                {dashboard.notes_body}
              </div>
              <div
                style={{
                  color: "var(--muted)",
                  lineHeight: 1.7,
                }}
              >
                {dashboard.footer_note}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
