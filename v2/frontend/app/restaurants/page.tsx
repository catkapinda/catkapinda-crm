"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { RestaurantEntryWorkspace } from "../../components/restaurants/restaurant-entry-workspace";
import { RestaurantManagementWorkspace } from "../../components/restaurants/restaurant-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type RestaurantsDashboard = {
  module: string;
  status: string;
  summary: {
    total_restaurants: number;
    active_restaurants: number;
    passive_restaurants: number;
    fixed_monthly_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    brand: string;
    branch: string;
    pricing_model: string;
    pricing_model_label: string;
    hourly_rate: number;
    package_rate: number;
    package_threshold: number;
    package_rate_low: number;
    package_rate_high: number;
    fixed_monthly_fee: number;
    vat_rate: number;
    target_headcount: number;
    contact_name: string;
    active: boolean;
  }>;
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function metricCard(label: string, value: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      key={label}
      style={{
        padding: "18px",
        borderRadius: "20px",
        border: "1px solid var(--line)",
        background: tone === "accent" ? "rgba(15, 95, 215, 0.06)" : "var(--surface)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "10px",
          fontSize: "1.85rem",
          fontWeight: 900,
          letterSpacing: "-0.04em",
        }}
      >
        {value}
      </div>
    </article>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function pricingSummary(entry: RestaurantsDashboard["recent_entries"][number]) {
  if (entry.pricing_model === "fixed_monthly") {
    return `${formatCurrency(entry.fixed_monthly_fee)}/ay`;
  }
  if (entry.pricing_model === "threshold_package") {
    return `${formatCurrency(entry.hourly_rate)}/saat | ${entry.package_threshold} altı ${formatCurrency(entry.package_rate_low)} | üstü ${formatCurrency(entry.package_rate_high)}`;
  }
  if (entry.pricing_model === "hourly_plus_package") {
    return `${formatCurrency(entry.hourly_rate)}/saat + ${formatCurrency(entry.package_rate)}/paket`;
  }
  return `${formatCurrency(entry.hourly_rate)}/saat`;
}

function narrativeCard({
  eyebrow,
  title,
  body,
  tone = "paper",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "paper" | "ink" | "accent";
}) {
  const palette =
    tone === "ink"
      ? {
          background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
          border: "1px solid rgba(255,255,255,0.08)",
          title: "#fff7ea",
          body: "rgba(255,247,234,0.72)",
          eyebrow: "rgba(255,247,234,0.62)",
        }
      : tone === "accent"
        ? {
            background: "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
            border: "1px solid rgba(185,116,41,0.18)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--accent-strong)",
          }
        : {
            background: "rgba(255,255,255,0.84)",
            border: "1px solid var(--line)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--muted)",
          };

  return (
    <article
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        background: palette.background,
        border: palette.border,
        boxShadow: tone === "ink" ? "var(--shadow-deep)" : "var(--shadow-soft)",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{
          color: palette.eyebrow,
          fontSize: "0.74rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          ...serifStyle,
          color: palette.title,
          fontSize: "1.45rem",
          lineHeight: 0.98,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: palette.body,
          fontSize: "0.93rem",
          lineHeight: 1.65,
        }}
      >
        {body}
      </div>
    </article>
  );
}

function workspaceCard({
  eyebrow,
  title,
  body,
  href,
}: {
  eyebrow: string;
  title: string;
  body: string;
  href: string;
}) {
  return (
    <a
      href={href}
      style={{
        display: "grid",
        gap: "10px",
        padding: "18px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "rgba(255,255,255,0.86)",
        boxShadow: "var(--shadow-soft)",
        color: "inherit",
        textDecoration: "none",
      }}
    >
      <div
        style={{
          color: "var(--accent-strong)",
          fontSize: "0.74rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          ...serifStyle,
          fontSize: "1.28rem",
          lineHeight: 0.98,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.92rem",
          lineHeight: 1.65,
        }}
      >
        {body}
      </div>
      <div
        style={{
          fontSize: "0.82rem",
          fontWeight: 800,
          color: "#0f5fd7",
        }}
      >
        Çalışma alanını aç
      </div>
    </a>
  );
}

export default function RestaurantsPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<RestaurantsDashboard | null>(null);
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
        const response = await apiFetch("/restaurants/dashboard?limit=10");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as RestaurantsDashboard;
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

  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const total = dashboard.summary.total_restaurants || 0;
    const activeRatio = total > 0 ? (dashboard.summary.active_restaurants / total) * 100 : 0;
    const fixedMonthlyRatio =
      total > 0 ? (dashboard.summary.fixed_monthly_restaurants / total) * 100 : 0;
    const topRestaurant = dashboard.recent_entries[0] ?? null;
    const passivePressure = dashboard.summary.passive_restaurants >= Math.max(2, total / 3);

    return [
      {
        eyebrow: "Şube Nabzı",
        title:
          activeRatio >= 80
            ? "Aktif şube dengesi güçlü görünüyor."
            : activeRatio >= 60
              ? "Aktif şube dengesi korunuyor."
              : "Aktif şube dengesi dikkat istiyor.",
        body: `${dashboard.summary.total_restaurants} şubenin %${activeRatio.toFixed(1)} aktif. Bu oran operasyonun ne kadar canlı ve yaygın olduğunu hızlı okumayı sağlar.`,
        tone: activeRatio >= 80 ? "ink" : "accent",
      },
      {
        eyebrow: "En Sıcak Şube",
        title: topRestaurant ? `${topRestaurant.brand} / ${topRestaurant.branch}` : "Şube verisi henüz yok.",
        body: topRestaurant
          ? `${topRestaurant.pricing_model_label} modeliyle ${pricingSummary(topRestaurant)} yapısında çalışıyor. Hedef kadro ${topRestaurant.target_headcount} ve kontak ${topRestaurant.contact_name}.`
          : "Yeni restoran kayıtları geldikçe burada dikkat isteyen şube yapısını öne çıkaracağız.",
        tone: "paper",
      },
      {
        eyebrow: passivePressure ? "Portföy Baskısı" : "Portföy Yapısı",
        title: passivePressure ? "Pasif şube yükselişi izlenmeli." : "Sabit aylık çekirdek olgun görünüyor.",
        body: passivePressure
          ? `${dashboard.summary.passive_restaurants} pasif şube bulunuyor. Portföyde kapanan veya bekleyen şubeleri ayıklamak satış ve operasyon geçişini daha temiz yapar.`
          : `${dashboard.summary.fixed_monthly_restaurants} şube sabit aylık modelde. Bu, portföyün %${fixedMonthlyRatio.toFixed(1)} kadarının daha öngörülebilir gelir modeliyle çalıştığını gösteriyor.`,
        tone: passivePressure ? "accent" : "paper",
      },
    ] as const;
  }, [dashboard]);

  const workflowDeck = useMemo(
    () => [
      {
        eyebrow: "İlk Adım",
        title: "Yeni şube kartını aç",
        body: "Marka, fiyat modeli, kadro ve vergi alanlarını aynı kartta kurarak yeni restoranı kaydet.",
        href: "#restaurant-entry-workspace",
      },
      {
        eyebrow: "İkinci Adım",
        title: "Portföy havuzunu süz",
        body: "Marka, şube ve fiyat modeli üzerinden kayıtları daralt; dikkat isteyen kartı hızlıca bul.",
        href: "#restaurant-management-workspace",
      },
      {
        eyebrow: "Üçüncü Adım",
        title: "Seçili kartı güncelle",
        body: "Kadro, fiyat, iletişim ve durum alanlarını aynı panelde yenile; gerekirse pasife al.",
        href: "#restaurant-management-workspace",
      },
    ],
    [],
  );

  return (
    <AppShell activeItem="Restoranlar">
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
            background:
              "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
            display: "grid",
            gap: "18px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.35fr) minmax(280px, 0.9fr)",
              gap: "18px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "16px",
                alignContent: "start",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
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
                Şube Akışı
              </div>
              <div style={{ display: "grid", gap: "10px", maxWidth: "72ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(2.2rem, 4vw, 3.6rem)",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Restoran ve şube kayıtlarını yönet.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "74ch",
                    color: "var(--muted)",
                    lineHeight: 1.76,
                    fontSize: "1.02rem",
                  }}
                >
                  Marka, şube, fiyat modeli, hedef kadro, iletişim ve vergi bilgilerini tek ekranda takip et.
                </p>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                  >
                  Aktif portföy takibi
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Model ve şube aynı satırda
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gap: "12px",
              }}
            >
              <article
                style={{
                  padding: "18px 18px 16px",
                  borderRadius: "24px",
                  background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    alignItems: "start",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "6px" }}>
                    <div
                      style={{
                        color: "rgba(255,247,234,0.62)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Portföy Nabzı
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.active_restaurants ?? 0} aktif şube
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "7px 10px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.8rem",
                      fontWeight: 800,
                    }}
                  >
                    Portföy Masası
                  </div>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "10px",
                  }}
                >
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Sabit Aylık
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.fixed_monthly_restaurants ?? 0}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Pasif
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.passive_restaurants ?? 0}
                    </div>
                  </div>
                </div>
              </article>

              <article
                style={{
                  padding: "16px 18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.74rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Portföy Kontrolü
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  {dashboard?.summary.active_restaurants ?? 0} aktif şube, {dashboard?.summary.passive_restaurants ?? 0} pasif şube,
                  {dashboard?.summary.fixed_monthly_restaurants ?? 0} sabit aylık anlaşma.
                </div>
              </article>
            </div>
          </div>
        </div>

        <section
          style={{
            padding: "20px",
            borderRadius: "24px",
            border: "1px solid var(--line)",
            background: "var(--surface-strong)",
            boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
            display: "grid",
            gap: "14px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Çalışma Sırası</h2>
            <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.65 }}>
              Eski restoran akışındaki yeni kart, portföy havuzu ve kart güncelleme düzenini aynı
              sayfada görünür kılıyoruz.
            </p>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            {workflowDeck.map((item) => (
              <div key={item.title}>
                {workspaceCard(item)}
              </div>
            ))}
          </div>
        </section>

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
            Restoran verileri yükleniyor...
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
            Restoran verileri şu an alınamadı. Bağlantı toparlandığında şube özeti
            ve yönetim kayıtları otomatik yenilenecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Şube", String(dashboard.summary.total_restaurants), "accent")}
              {metricCard("Aktif", String(dashboard.summary.active_restaurants))}
              {metricCard("Pasif", String(dashboard.summary.passive_restaurants))}
              {metricCard("Sabit Aylık", String(dashboard.summary.fixed_monthly_restaurants))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "14px",
              }}
            >
              {decisionDeck.map((item) => (
                <div key={`${item.eyebrow}-${item.title}`}>{narrativeCard(item)}</div>
              ))}
            </div>

            <section
              style={{
                padding: "20px",
                borderRadius: "24px",
                border: "1px solid var(--line)",
                background: "var(--surface-strong)",
                boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
                display: "grid",
                gap: "14px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "16px",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Son Şube Sinyalleri</h2>
                  <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.65 }}>
                    Portföyde hangi şubenin dikkat ve aksiyon istediğini hızlandıran son kartlar.
                  </p>
                </div>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(24,40,59,0.08)",
                    color: "var(--text)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Son {dashboard.recent_entries.length} kayıt
                </span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: "12px",
                }}
              >
                {dashboard.recent_entries.map((entry) => (
                  <article
                    key={entry.id}
                    style={{
                      display: "grid",
                      gap: "10px",
                      padding: "16px 16px 14px",
                      borderRadius: "20px",
                      border: "1px solid rgba(24,40,59,0.08)",
                      background:
                        "linear-gradient(180deg, rgba(255,253,248,0.98), rgba(247,241,231,0.96))",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        alignItems: "start",
                      }}
                    >
                      <div style={{ display: "grid", gap: "4px" }}>
                        <div
                          style={{
                            ...serifStyle,
                            fontSize: "1.22rem",
                            lineHeight: 0.98,
                            fontWeight: 700,
                          }}
                        >
                          {entry.brand}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                          {entry.branch}
                        </div>
                      </div>
                      <span
                        style={{
                          display: "inline-flex",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          background: entry.active
                            ? "rgba(15,95,215,0.08)"
                            : "rgba(185,116,41,0.12)",
                          color: entry.active ? "#0f5fd7" : "var(--accent-strong)",
                          fontSize: "0.74rem",
                          fontWeight: 800,
                        }}
                      >
                        {entry.active ? "Aktif" : "Pasif"}
                      </span>
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                        gap: "10px",
                      }}
                    >
                      <div
                        style={{
                          padding: "10px 12px",
                          borderRadius: "14px",
                          background: "rgba(24,40,59,0.05)",
                        }}
                      >
                        <div
                          style={{
                            color: "var(--muted)",
                            fontSize: "0.72rem",
                            fontWeight: 800,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                          }}
                        >
                          Model
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {entry.pricing_model_label}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: "10px 12px",
                          borderRadius: "14px",
                          background: "rgba(15,95,215,0.06)",
                        }}
                      >
                        <div
                          style={{
                            color: "var(--muted)",
                            fontSize: "0.72rem",
                            fontWeight: 800,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                          }}
                        >
                          Hedef Kadro
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {entry.target_headcount}
                        </div>
                      </div>
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gap: "4px",
                        color: "var(--muted)",
                        fontSize: "0.9rem",
                      }}
                    >
                      <div>{pricingSummary(entry)}</div>
                      <div>{entry.contact_name} • KDV %{entry.vat_rate}</div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section id="restaurant-entry-workspace" style={{ scrollMarginTop: "110px" }}>
              <RestaurantEntryWorkspace />
            </section>
            <section id="restaurant-management-workspace" style={{ scrollMarginTop: "110px" }}>
              <RestaurantManagementWorkspace />
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
