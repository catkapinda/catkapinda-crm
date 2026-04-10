"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "../components/auth/auth-provider";
import { AppShell } from "../components/shell/app-shell";
import { apiFetch } from "../lib/api";

type OverviewDashboard = {
  module: string;
  status: string;
  hero: {
    active_restaurants: number;
    active_personnel: number;
    month_attendance_entries: number;
    month_deduction_entries: number;
  };
  modules: Array<{
    key: string;
    title: string;
    description: string;
    href: string;
    primary_label: string;
    primary_value: string;
    secondary_label: string;
    secondary_value: string;
  }>;
  recent_activity: Array<{
    module_key: string;
    module_label: string;
    title: string;
    subtitle: string;
    meta: string;
    entry_date: string | null;
    href: string;
  }>;
};

function metricCard(label: string, value: string) {
  return (
    <article
      key={label}
      style={{
        padding: "20px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "12px",
          fontSize: "2rem",
          fontWeight: 900,
          letterSpacing: "-0.05em",
        }}
      >
        {value}
      </div>
    </article>
  );
}

export default function HomePage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<OverviewDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading) {
        return;
      }
      if (!user) {
        if (active) {
          setDashboard(null);
          setDashboardLoading(false);
        }
        return;
      }

      setDashboardLoading(true);
      try {
        const response = await apiFetch("/overview/dashboard");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as OverviewDashboard;
        if (active) {
          setDashboard(payload);
        }
      } catch {
        if (active) {
          setDashboard(null);
        }
      } finally {
        if (active) {
          setDashboardLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [loading, user]);

  return (
    <AppShell activeItem="Genel Bakış">
      <section
        style={{
          display: "grid",
          gap: "18px",
        }}
      >
        <div
          style={{
            padding: "28px",
            borderRadius: "30px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              padding: "7px 12px",
              borderRadius: "999px",
              background: "var(--accent-soft)",
              color: "var(--accent)",
              fontSize: "0.78rem",
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Operasyon Merkezi
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 4vw, 3.2rem)",
              lineHeight: 1.03,
            }}
          >
            Yeni operasyon merkezi artik hazir.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "76ch",
              color: "var(--muted)",
              fontSize: "1.02rem",
              lineHeight: 1.7,
            }}
          >
            Puantaj, personel, kesinti, restoran ve finans akislarini ayni omurgada
            ozetleyen yeni merkez burasi. Ekipler gunluk isi tek bakista gorecek ve
            dogru module hizli gececek.
          </p>
        </div>

        {dashboardLoading ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px solid rgba(15, 95, 215, 0.14)",
              background: "rgba(15, 95, 215, 0.06)",
              color: "var(--muted)",
            }}
          >
            Operasyon ozeti yukleniyor...
          </div>
        ) : !dashboard ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px dashed rgba(15, 95, 215, 0.35)",
              background: "rgba(255, 255, 255, 0.66)",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Genel bakis servisine su anda erisilemiyor. Backend hazir oldugunda bu ekran
            genel operasyon ozetini ve son hareketleri gercek veriden gosterecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Aktif Sube", String(dashboard.hero.active_restaurants))}
              {metricCard("Aktif Personel", String(dashboard.hero.active_personnel))}
              {metricCard("Bu Ay Puantaj", String(dashboard.hero.month_attendance_entries))}
              {metricCard("Bu Ay Kesinti", String(dashboard.hero.month_deduction_entries))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.65fr) minmax(320px, 0.95fr)",
                gap: "18px",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                  gap: "16px",
                }}
              >
                {dashboard.modules.map((item) => (
                  <article
                    key={item.key}
                    style={{
                      padding: "20px",
                      borderRadius: "24px",
                      border: "1px solid var(--line)",
                      background: "var(--surface-strong)",
                      boxShadow: "0 18px 44px rgba(20, 39, 67, 0.06)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                        gap: "14px",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: "1.08rem",
                            fontWeight: 900,
                            letterSpacing: "-0.02em",
                          }}
                        >
                          {item.title}
                        </div>
                        <p
                          style={{
                            margin: "8px 0 0",
                            color: "var(--muted)",
                            lineHeight: 1.6,
                          }}
                        >
                          {item.description}
                        </p>
                      </div>
                      <div
                        style={{
                          minWidth: "44px",
                          height: "44px",
                          display: "grid",
                          placeItems: "center",
                          borderRadius: "16px",
                          background: "var(--accent-soft)",
                          color: "var(--accent)",
                          fontWeight: 900,
                        }}
                      >
                        {item.title.charAt(0)}
                      </div>
                    </div>

                    <div
                      style={{
                        marginTop: "18px",
                        display: "grid",
                        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                        gap: "12px",
                      }}
                    >
                      <div
                        style={{
                          padding: "14px",
                          borderRadius: "18px",
                          background: "rgba(15, 95, 215, 0.06)",
                          border: "1px solid rgba(15, 95, 215, 0.12)",
                        }}
                      >
                        <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 800 }}>
                          {item.primary_label}
                        </div>
                        <div style={{ marginTop: "8px", fontSize: "1.45rem", fontWeight: 900 }}>
                          {item.primary_value}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: "14px",
                          borderRadius: "18px",
                          background: "var(--surface)",
                          border: "1px solid var(--line)",
                        }}
                      >
                        <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 800 }}>
                          {item.secondary_label}
                        </div>
                        <div style={{ marginTop: "8px", fontSize: "1.45rem", fontWeight: 900 }}>
                          {item.secondary_value}
                        </div>
                      </div>
                    </div>

                    <Link
                      href={item.href}
                      style={{
                        marginTop: "18px",
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        padding: "12px 16px",
                        borderRadius: "16px",
                        background: "var(--accent)",
                        color: "#fff",
                        fontWeight: 800,
                      }}
                    >
                      Modulu Ac
                    </Link>
                  </article>
                ))}
              </div>

              <aside
                style={{
                  borderRadius: "26px",
                  border: "1px solid var(--line)",
                  background: "var(--surface-strong)",
                  boxShadow: "0 18px 44px rgba(20, 39, 67, 0.06)",
                  overflow: "hidden",
                  alignSelf: "start",
                }}
              >
                <div
                  style={{
                    padding: "18px 20px",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      background: "rgba(15, 95, 215, 0.06)",
                      color: "var(--accent)",
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    Son Hareketler
                  </div>
                  <h2 style={{ margin: "12px 0 6px", fontSize: "1.12rem" }}>Operasyon Akisi</h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
                    En son hareket eden kayitlari moduller arasinda tek yerde izleyin.
                  </p>
                </div>
                <div
                  style={{
                    maxHeight: "640px",
                    overflowY: "auto",
                    padding: "8px",
                  }}
                >
                  {dashboard.recent_activity.map((item) => (
                    <Link
                      key={`${item.module_key}-${item.href}-${item.title}-${item.meta}`}
                      href={item.href}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "14px 14px 16px",
                        borderRadius: "18px",
                        marginBottom: "8px",
                        background: "rgba(248, 251, 255, 0.95)",
                        border: "1px solid rgba(188, 205, 230, 0.7)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "12px",
                        }}
                      >
                        <span
                          style={{
                            display: "inline-flex",
                            padding: "6px 10px",
                            borderRadius: "999px",
                            background: "var(--accent-soft)",
                            color: "var(--accent)",
                            fontSize: "0.72rem",
                            fontWeight: 800,
                          }}
                        >
                          {item.module_label}
                        </span>
                        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                          {item.entry_date ?? "-"}
                        </span>
                      </div>
                      <div style={{ fontWeight: 900, letterSpacing: "-0.01em" }}>{item.title}</div>
                      <div style={{ color: "var(--text)", fontSize: "0.95rem" }}>{item.subtitle}</div>
                      <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{item.meta}</div>
                    </Link>
                  ))}
                </div>
              </aside>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
