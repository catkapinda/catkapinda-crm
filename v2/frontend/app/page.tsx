"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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
  finance: {
    selected_month: string | null;
    total_revenue: number;
    gross_profit: number;
    total_personnel_cost: number;
    side_income_net: number;
    top_restaurants: Array<{
      label: string;
      value: string;
    }>;
    risk_restaurants: Array<{
      label: string;
      value: string;
    }>;
  };
  hygiene: {
    missing_personnel_cards: number;
    missing_restaurant_cards: number;
    personnel_samples: Array<{
      title: string;
      subtitle: string;
    }>;
    restaurant_samples: Array<{
      title: string;
      subtitle: string;
    }>;
  };
  operations: {
    missing_attendance_count: number;
    under_target_count: number;
    joker_usage_count: number;
    critical_signal_count: number;
    profitable_restaurant_count: number;
    risky_restaurant_count: number;
    shared_operation_total: number;
    action_alerts: Array<{
      tone: string;
      badge: string;
      title: string;
      detail: string;
    }>;
    brand_summary: Array<{
      brand: string;
      restaurant_count: number;
      total_packages: number;
      total_hours: number;
      gross_invoice: number;
      operation_gap: number;
      status: string;
    }>;
    daily_trend: Array<{
      entry_date: string;
      total_packages: number;
      total_hours: number;
    }>;
    top_restaurants: Array<{
      restaurant: string;
      total_packages: number;
      total_hours: number;
    }>;
    joker_restaurants: Array<{
      restaurant: string;
      joker_count: number;
      total_packages: number;
    }>;
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

const serifTitleStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const kickerStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "6px 10px",
  borderRadius: "999px",
  background: "rgba(255,255,255,0.1)",
  border: "1px solid rgba(255,255,255,0.12)",
  color: "#f5d7b1",
  fontSize: "0.68rem",
  fontWeight: 800,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
} as const;

const paperCardStyle = {
  borderRadius: "22px",
  border: "1px solid var(--line)",
  background: "var(--surface-raised)",
  boxShadow: "var(--shadow-soft)",
} as const;

const masonryItemStyle = {
  display: "inline-grid",
  width: "100%",
  marginBottom: "12px",
  breakInside: "avoid",
  WebkitColumnBreakInside: "avoid",
} as const;

function formatActivityDate(value: string | null) {
  if (!value) {
    return "Takvim yok";
  }
  return value;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function pulseCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        ...paperCardStyle,
        padding: "14px 14px 12px",
        display: "grid",
        gap: "6px",
        background:
          "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(248,241,229,0.96))",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.66rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifTitleStyle,
          fontSize: "1.55rem",
          lineHeight: 0.94,
          fontWeight: 700,
          color: "var(--text)",
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.8rem",
          lineHeight: 1.45,
        }}
      >
        {note}
      </div>
    </article>
  );
}

function executiveMetricCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        padding: "12px 12px 11px",
        borderRadius: "16px",
        background: "rgba(24, 40, 59, 0.05)",
        border: "1px solid rgba(24, 40, 59, 0.08)",
        display: "grid",
        gap: "6px",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.64rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.08rem",
          fontWeight: 900,
          letterSpacing: "-0.03em",
          color: "var(--text)",
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          lineHeight: 1.4,
        }}
      >
        {note}
      </div>
    </article>
  );
}

function moduleCard(
  item: OverviewDashboard["modules"][number],
  index: number,
) {
  return (
    <article
      key={item.key}
      style={{
        ...paperCardStyle,
        padding: "16px",
        display: "grid",
        gap: "12px",
        background:
          index % 2 === 0
            ? "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))"
            : "linear-gradient(180deg, rgba(255,253,250,0.98), rgba(244,238,229,0.96))",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <div style={{ display: "grid", gap: "8px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              color: "var(--accent-strong)",
              fontWeight: 800,
              fontSize: "0.66rem",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                width: "24px",
                height: "24px",
                borderRadius: "999px",
                alignItems: "center",
                justifyContent: "center",
                background: "rgba(185, 116, 41, 0.14)",
              }}
            >
              {String(index + 1).padStart(2, "0")}
            </span>
            Modul
          </div>
          <div
            style={{
              ...serifTitleStyle,
              fontSize: "1.18rem",
              lineHeight: 1,
              fontWeight: 700,
            }}
          >
            {item.title}
          </div>
          <p
            style={{
              margin: 0,
              color: "var(--muted)",
              lineHeight: 1.5,
              fontSize: "0.84rem",
            }}
          >
            {item.description}
          </p>
        </div>
        <div
          style={{
            minWidth: "46px",
            height: "42px",
            borderRadius: "14px",
            display: "grid",
            placeItems: "center",
            background: "var(--surface-ink)",
            color: "#f8efe1",
            fontWeight: 900,
            fontSize: "0.92rem",
            boxShadow: "var(--shadow-deep)",
          }}
        >
          {item.title.charAt(0)}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "8px",
        }}
      >
        <div
          style={{
            padding: "10px 10px 9px",
            borderRadius: "14px",
            background: "rgba(24, 40, 59, 0.06)",
            border: "1px solid rgba(24, 40, 59, 0.08)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.64rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {item.primary_label}
          </div>
          <div
            style={{
              marginTop: "6px",
              fontSize: "1rem",
              fontWeight: 900,
              letterSpacing: "-0.04em",
            }}
          >
            {item.primary_value}
          </div>
        </div>
        <div
          style={{
            padding: "10px 10px 9px",
            borderRadius: "14px",
            background: "rgba(185, 116, 41, 0.08)",
            border: "1px solid rgba(185, 116, 41, 0.14)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.64rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {item.secondary_label}
          </div>
          <div
            style={{
              marginTop: "6px",
              fontSize: "1rem",
              fontWeight: 900,
              letterSpacing: "-0.04em",
            }}
          >
            {item.secondary_value}
          </div>
        </div>
      </div>

      <Link
        href={item.href}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          width: "fit-content",
          padding: "10px 12px",
          borderRadius: "14px",
          background: "var(--surface-ink)",
          color: "#fff6ea",
          fontWeight: 800,
          fontSize: "0.88rem",
          boxShadow: "var(--shadow-deep)",
        }}
      >
        <span>Modülü Aç</span>
        <span
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "999px",
            display: "grid",
            placeItems: "center",
            background: "rgba(255,255,255,0.08)",
          }}
        >
          +
        </span>
      </Link>
    </article>
  );
}

function snapshotList(
  title: string,
  items: Array<{ label: string; value: string }> | Array<{ title: string; subtitle: string }>,
  mode: "value" | "subtitle",
) {
  return (
    <article
      style={{
        ...paperCardStyle,
        padding: "16px",
        background: "rgba(255,255,255,0.9)",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{
          color: "var(--accent-strong)",
          fontWeight: 800,
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {title}
      </div>
      {items.length ? (
        <div style={{ display: "grid", gap: "8px" }}>
          {items.map((item, index) => (
            <div
              key={`${title}-${index}`}
              style={{
                display: "grid",
                gap: "4px",
                paddingBottom: "8px",
                borderBottom: "1px solid rgba(24,40,59,0.08)",
              }}
            >
              <div style={{ fontWeight: 800 }}>
                {"label" in item ? item.label : item.title}
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>
                {mode === "value" && "value" in item ? item.value : "subtitle" in item ? item.subtitle : "-"}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.86rem" }}>
          Bu alanda henüz gösterilecek öne çıkan kayıt yok.
        </div>
      )}
    </article>
  );
}

function toneSurface(tone: string) {
  if (tone === "critical") {
    return {
      background: "rgba(168, 59, 28, 0.12)",
      border: "1px solid rgba(168, 59, 28, 0.18)",
      badgeBackground: "rgba(168, 59, 28, 0.16)",
      badgeColor: "#8a3516",
    };
  }
  if (tone === "warning") {
    return {
      background: "rgba(185, 116, 41, 0.1)",
      border: "1px solid rgba(185, 116, 41, 0.16)",
      badgeBackground: "rgba(185, 116, 41, 0.15)",
      badgeColor: "var(--accent-strong)",
    };
  }
  return {
    background: "rgba(18, 82, 52, 0.08)",
    border: "1px solid rgba(18, 82, 52, 0.14)",
    badgeBackground: "rgba(18, 82, 52, 0.12)",
    badgeColor: "#18563b",
  };
}

function formatShortDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
  }).format(parsed);
}

const quickActions = [
  {
    title: "Bugünkü Puantajı Aç",
    subtitle: "Günlük saha kaydına hemen geç.",
    href: "/attendance",
    badge: "Puantaj",
  },
  {
    title: "Yeni Personel Kartı",
    subtitle: "Yeni kurye veya yönetici ekleme ekranını aç.",
    href: "/personnel",
    badge: "Personel",
  },
  {
    title: "Yeni Şube Kartı",
    subtitle: "Restoran anlaşma kartını hızlıca düzenlemeye geç.",
    href: "/restaurants",
    badge: "Restoran",
  },
  {
    title: "Kesinti Kaydı Gir",
    subtitle: "Ay sonu ve manuel kesinti hareketlerini işle.",
    href: "/deductions",
    badge: "Kesinti",
  },
  {
    title: "Personel Düzenlemeyi Aç",
    subtitle: "Ekipman, iade ve düzeltme akışını kart üstünden yönet.",
    href: "/personnel",
    badge: "Düzenleme",
  },
  {
    title: "Aylık Raporu Aç",
    subtitle: "Bu ayın kârlılık ve maliyet ekranına geç.",
    href: "/reports",
    badge: "Rapor",
  },
] as const;

export default function HomePage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<OverviewDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading) {
        return;
      }
      if (!user) {
        if (active) {
          setDashboard(null);
          setDashboardError("");
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
            setDashboardError(
              response.status === 401
                ? "Genel bakış verisi için oturum doğrulaması tamamlanamadı. Lütfen bir kez çıkış yapıp yeniden giriş yap."
                : "Genel bakış verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene.",
            );
          }
          return;
        }
        const payload = (await response.json()) as OverviewDashboard;
        if (active) {
          setDashboard(payload);
          setDashboardError("");
        }
      } catch {
        if (active) {
          setDashboard(null);
          setDashboardError(
            "Genel bakış verisine ulaşılamıyor. Lütfen bağlantıyı kontrol edip tekrar dene.",
          );
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

  const quickLaunchItems = useMemo(() => dashboard?.modules.slice(0, 3) ?? [], [dashboard?.modules]);

  return (
    <AppShell activeItem="Genel Bakış">
      <section
        style={{
          display: "grid",
          gap: "14px",
        }}
      >
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.5fr) minmax(320px, 0.95fr)",
            gap: "12px",
          }}
        >
          <article
            style={{
              padding: "18px",
              borderRadius: "24px",
              background:
                "linear-gradient(145deg, rgba(22, 38, 58, 0.98), rgba(37, 56, 79, 0.96))",
              color: "#fff7ea",
              boxShadow: "var(--shadow-deep)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: "auto -80px -120px auto",
                width: "240px",
                height: "240px",
                borderRadius: "999px",
                background: "radial-gradient(circle, rgba(185,116,41,0.3), transparent 70%)",
              }}
            />
            <div style={kickerStyle}>Genel Bakış</div>
            <div
              style={{
                marginTop: "14px",
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                width: "fit-content",
                padding: "7px 10px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.09)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#fff4e3",
                fontWeight: 800,
                fontSize: "0.82rem",
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  width: "30px",
                  height: "30px",
                  borderRadius: "999px",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "rgba(185,116,41,0.24)",
                  color: "#f5d7b1",
                }}
              >
                {dashboard?.operations.critical_signal_count ?? 0}
              </span>
              <span>Bugünün kritik sinyalleri burada listelenir.</span>
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: "12px 0 8px",
                fontSize: "clamp(1.7rem, 3vw, 2.6rem)",
                lineHeight: 0.94,
                maxWidth: "11ch",
                fontWeight: 700,
              }}
            >
              Operasyon özeti
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "58ch",
                color: "rgba(255, 247, 234, 0.78)",
                lineHeight: 1.55,
                fontSize: "0.86rem",
              }}
            >
              Şube, personel, puantaj ve kesinti durumunu tek ekrandan izle, ilgili modüle geç.
            </p>

            <div
              style={{
                marginTop: "14px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "8px",
              }}
            >
              {[
                ["Öncelik", "Puantaj ve personel hareketleri öne çıkar."],
                ["Kullanım", "Durumu burada gör, işlemi ilgili modülde tamamla."],
                ["Akış", "Temel göstergeler tek ekranda toplanır."],
              ].map(([label, text]) => (
                <div
                  key={label}
                  style={{
                    padding: "10px 10px 9px",
                    borderRadius: "14px",
                    background: "rgba(255,255,255,0.08)",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <div
                    style={{
                      color: "#f1c28f",
                      fontSize: "0.62rem",
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      marginTop: "4px",
                      color: "rgba(255, 247, 234, 0.84)",
                      lineHeight: 1.4,
                      fontSize: "0.8rem",
                    }}
                  >
                    {text}
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                marginTop: "12px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "8px",
              }}
            >
              {quickLaunchItems.length ? (
                quickLaunchItems.map((item) => (
                  <Link
                    key={item.key}
                    href={item.href}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "10px",
                      padding: "10px 12px",
                      borderRadius: "14px",
                      background: "rgba(255,255,255,0.08)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      color: "#fff7ea",
                      fontWeight: 800,
                      fontSize: "0.82rem",
                    }}
                  >
                    <span>{item.title}</span>
                    <span style={{ color: "#f1c28f" }}>{item.primary_value}</span>
                  </Link>
                ))
              ) : (
                <div style={{ color: "rgba(255, 247, 234, 0.72)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                  Hızlı geçiş bağlantıları burada görünecek.
                </div>
              )}
            </div>
          </article>

          <article
            style={{
              ...paperCardStyle,
              padding: "16px",
              display: "grid",
              gap: "12px",
              background:
                "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
            }}
          >
              <header style={{ display: "grid", gap: "8px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.66rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Temel Göstergeler
                </div>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                  Temel operasyon ve finans göstergeleri burada özetlenir.
                </p>
              </header>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: "8px",
                }}
              >
                {executiveMetricCard(
                  "Puantaj Bekleyen",
                  String(dashboard?.operations.missing_attendance_count ?? 0),
                  "Bugün kayıt bekleyen şube sayısı.",
                )}
                {executiveMetricCard(
                  "Kadro Riski",
                  String(dashboard?.operations.under_target_count ?? 0),
                  "Hedef altında kalan aktif şubeler.",
                )}
                {executiveMetricCard(
                  "Joker Kullanımı",
                  String(dashboard?.operations.joker_usage_count ?? 0),
                  "Bugün destek verilen şube sayısı.",
                )}
                {executiveMetricCard(
                  "Bu Ay Fatura",
                  formatCurrency(dashboard?.finance.total_revenue ?? 0),
                  "KDV dahil restoran toplamı.",
                )}
                {executiveMetricCard(
                  "Operasyon Farkı",
                  formatCurrency(dashboard?.finance.gross_profit ?? 0),
                  "Ay içi brüt operasyon farkı.",
                )}
                {executiveMetricCard(
                  "Riskli Şube",
                  String(dashboard?.operations.risky_restaurant_count ?? 0),
                  `${dashboard?.operations.profitable_restaurant_count ?? 0} kârlı şube ile birlikte.`,
                )}
              </div>
          </article>
        </section>

        {dashboardLoading ? (
          <div
            style={{
              ...paperCardStyle,
              padding: "18px 20px",
              color: "var(--muted)",
              background: "rgba(255, 250, 241, 0.82)",
            }}
          >
            Genel bakış paneli yükleniyor...
          </div>
        ) : !dashboard ? (
          <div
            style={{
              ...paperCardStyle,
              padding: "20px 22px",
              borderStyle: "dashed",
              color: "var(--muted)",
              lineHeight: 1.75,
              background: "rgba(255, 250, 241, 0.82)",
            }}
          >
            {dashboardError ||
              "Genel bakış verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene."}
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
                gap: "10px",
              }}
            >
              {pulseCard(
                "Aktif Şube",
                String(dashboard.hero.active_restaurants),
                "Operasyon omurgasında bugün hareketli olan restoran havuzu.",
              )}
              {pulseCard(
                "Aktif Personel",
                String(dashboard.hero.active_personnel),
                "Sistemde anlık aktif görebileceğin saha ve destek personeli.",
              )}
              {pulseCard(
                "Bu Ay Puantaj",
                String(dashboard.hero.month_attendance_entries),
                "Ay içinde açılan vardiya ve devam kaydı yoğunluğu.",
              )}
              {pulseCard(
                "Bu Ay Kesinti",
                String(dashboard.hero.month_deduction_entries),
                "Ay sonu finans akışına etki eden manuel ve otomatik kesintiler.",
              )}
            </div>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "12px",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gap: "12px",
                }}
              >
                <header
                  style={{
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Komuta Masası
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.55rem",
                      lineHeight: 1,
                      fontWeight: 700,
                    }}
                  >
                    Modüller artık daha net roller oynuyor.
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      lineHeight: 1.5,
                      fontSize: "0.84rem",
                    }}
                  >
                    Her modül artık hem sayı anlatıyor hem de kullanıcıyı doğrudan doğru aksiyona
                    götürüyor.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "10px",
                  }}
                >
                  {dashboard.modules.map((item, index) => moduleCard(item, index))}
                </div>
              </div>

              <aside
                style={{
                  ...paperCardStyle,
                  overflow: "hidden",
                  alignSelf: "start",
                  background:
                    "linear-gradient(180deg, rgba(24, 40, 59, 0.98), rgba(31, 48, 69, 0.96))",
                  color: "#f9f2e6",
                  boxShadow: "var(--shadow-deep)",
                }}
              >
                <div
                  style={{
                    padding: "16px 16px 12px",
                    borderBottom: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div style={kickerStyle}>Hareket Akışı</div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: "10px 0 6px",
                      fontSize: "1.3rem",
                      lineHeight: 1,
                      fontWeight: 700,
                    }}
                  >
                    Son hareketler artık daha okunur.
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "rgba(249, 242, 230, 0.72)",
                      lineHeight: 1.5,
                      fontSize: "0.84rem",
                    }}
                  >
                    Akışta ne değiştiğini modül atlamadan tek panelde okuyabiliyorsun.
                  </p>
                </div>
                <div
                  style={{
                    padding: "10px",
                    display: "grid",
                    gap: "8px",
                    maxHeight: "620px",
                    overflowY: "auto",
                  }}
                >
                  {dashboard.recent_activity.map((item) => (
                    <Link
                      key={`${item.module_key}-${item.href}-${item.title}-${item.meta}`}
                      href={item.href}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "12px",
                        borderRadius: "14px",
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.08)",
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
                            background: "rgba(185,116,41,0.18)",
                            color: "#f1c28f",
                            fontSize: "0.64rem",
                            fontWeight: 800,
                          }}
                        >
                          {item.module_label}
                        </span>
                        <span
                          style={{
                            color: "rgba(249, 242, 230, 0.62)",
                            fontSize: "0.8rem",
                          }}
                        >
                          {formatActivityDate(item.entry_date)}
                        </span>
                      </div>
                      <div
                        style={{
                          ...serifTitleStyle,
                          fontSize: "1rem",
                          lineHeight: 1,
                          fontWeight: 700,
                        }}
                      >
                        {item.title}
                      </div>
                      <div
                        style={{
                          color: "#fff7ea",
                          lineHeight: 1.45,
                          fontSize: "0.84rem",
                        }}
                      >
                        {item.subtitle}
                      </div>
                      <div
                        style={{
                          color: "rgba(249, 242, 230, 0.68)",
                          fontSize: "0.84rem",
                        }}
                      >
                        {item.meta}
                      </div>
                    </Link>
                  ))}
                </div>
              </aside>
            </section>

            <div
              style={{
                columnWidth: "340px",
                columnGap: "12px",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Bu Ay Karlılık Özeti
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.45rem",
                      lineHeight: 1,
                      fontWeight: 700,
                    }}
                  >
                    Gelir, maliyet ve kâr aynı masada okunuyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>
                    {dashboard.finance.selected_month
                      ? `${dashboard.finance.selected_month} dönemi için restoran faturası, personel maliyeti ve yan gelir toplamını tek yerde topluyoruz.`
                      : "Rapor verisi geldikçe aylık kârlılık sinyallerini burada birlikte okuyacağız."}
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "10px",
                  }}
                >
                  {pulseCard(
                    "Restoran Faturası",
                    formatCurrency(dashboard.finance.total_revenue),
                    "Bu ay oluşan toplam restoran faturası.",
                  )}
                  {pulseCard(
                    "Personel Maliyeti",
                    formatCurrency(dashboard.finance.total_personnel_cost),
                    "Net maliyet tarafında okunan toplam kadro yükü.",
                  )}
                  {pulseCard(
                    "Brüt Kâr",
                    formatCurrency(dashboard.finance.gross_profit),
                    "Gelir ve personel maliyeti arasındaki ana fark.",
                  )}
                  {pulseCard(
                    "Yan Gelir",
                    formatCurrency(dashboard.finance.side_income_net),
                    "Muhasebe ve ek işlerden gelen net katkı.",
                  )}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                    gap: "10px",
                  }}
                >
                  {snapshotList("En Güçlü Restoranlar", dashboard.finance.top_restaurants, "value")}
                  {snapshotList("Dikkat İsteyen Restoranlar", dashboard.finance.risk_restaurants, "value")}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Kart ve Zimmet Kontrolü
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.45rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Eksik kartları masanın üstünde tutuyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Eksik alanlı personel ve restoran kartlarını hızlıca görüp operasyon öncesi düzenlemek için.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "10px",
                  }}
                >
                  {pulseCard(
                    "Eksik Personel",
                    String(dashboard.hygiene.missing_personnel_cards),
                    "Telefon, işe giriş, şube veya plaka eksiği olan aktif kartlar.",
                  )}
                  {pulseCard(
                    "Eksik Restoran",
                    String(dashboard.hygiene.missing_restaurant_cards),
                    "Kontak, hedef kadro veya adresi eksik duran şube kartları.",
                  )}
                </div>

                {snapshotList("Eksik Personel Kartları", dashboard.hygiene.personnel_samples, "subtitle")}
                {snapshotList("Eksik Restoran Kartları", dashboard.hygiene.restaurant_samples, "subtitle")}
              </article>
              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Bugün Acil Aksiyon
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.5rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Hangi şubenin beklediğini tek bakışta görüyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Puantaj bekleyen, hedef kadronun altında kalan ve joker desteği alan şubeleri tek panelde topluyoruz.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: "10px",
                  }}
                >
                  {pulseCard(
                    "Puantaj Bekleyen",
                    String(dashboard.operations.missing_attendance_count),
                    "Bugün kaydı henüz düşmeyen aktif şubeler.",
                  )}
                  {pulseCard(
                    "Açık Kadro",
                    String(dashboard.operations.under_target_count),
                    "Hedef kadronun altında duran aktif şubeler.",
                  )}
                  {pulseCard(
                    "Joker Kullanımı",
                    String(dashboard.operations.joker_usage_count),
                    "Bugün destekle dönen şube sayısı.",
                  )}
                </div>

                <div style={{ display: "grid", gap: "10px" }}>
                  {dashboard.operations.action_alerts.length ? (
                    dashboard.operations.action_alerts.map((item, index) => {
                      const tone = toneSurface(item.tone);
                      return (
                        <article
                          key={`${item.badge}-${item.title}-${index}`}
                          style={{
                            padding: "16px",
                            borderRadius: "18px",
                            background: tone.background,
                            border: tone.border,
                            display: "grid",
                            gap: "6px",
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
                                background: tone.badgeBackground,
                                color: tone.badgeColor,
                                fontSize: "0.64rem",
                                fontWeight: 800,
                                letterSpacing: "0.04em",
                                textTransform: "uppercase",
                              }}
                            >
                              {item.badge}
                            </span>
                          </div>
                          <div
                            style={{
                              ...serifTitleStyle,
                              fontSize: "1.08rem",
                              lineHeight: 1,
                              fontWeight: 700,
                            }}
                          >
                            {item.title}
                          </div>
                          <div style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>{item.detail}</div>
                        </article>
                      );
                    })
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                      Bugün öne çıkan aksiyon uyarısı görünmüyor.
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: "grid",
                    gap: "10px",
                    padding: "14px",
                    borderRadius: "18px",
                    background: "rgba(255,248,238,0.92)",
                    border: "1px solid rgba(185,116,41,0.12)",
                  }}
                >
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontSize: "0.66rem",
                      fontWeight: 800,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                    }}
                  >
                    Bugün Joker Kullanılan Şubeler
                  </div>
                  {dashboard.operations.joker_restaurants.length ? (
                    dashboard.operations.joker_restaurants.map((item, index) => (
                      <div
                        key={`${item.restaurant}-${index}`}
                        style={{
                          display: "grid",
                          gridTemplateColumns: "minmax(0, 1fr) auto auto",
                          gap: "12px",
                          alignItems: "center",
                          paddingBottom: "8px",
                          borderBottom: "1px solid rgba(24,40,59,0.08)",
                        }}
                      >
                        <div style={{ fontWeight: 800 }}>{item.restaurant}</div>
                        <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
                          {`${item.joker_count} joker`}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
                          {`${item.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket`}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                      Bugün joker kullanılan şube görünmüyor.
                    </div>
                  )}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Marka Bazlı Özet
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.5rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Hacim ve risk aynı tabloda okunuyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Aylık paket, saat, fatura ve operasyon farkını marka seviyesinde yan yana görüyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "10px" }}>
                  {dashboard.operations.brand_summary.length ? (
                    dashboard.operations.brand_summary.map((entry, index) => (
                      <article
                        key={`${entry.brand}-${index}`}
                        style={{
                          padding: "16px",
                          borderRadius: "18px",
                          background: "rgba(255,255,255,0.78)",
                          border: "1px solid rgba(24,40,59,0.08)",
                          display: "grid",
                          gap: "8px",
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
                          <div
                            style={{
                              ...serifTitleStyle,
                              fontSize: "1.12rem",
                              lineHeight: 1,
                              fontWeight: 700,
                            }}
                          >
                            {entry.brand}
                          </div>
                          <span
                            style={{
                              display: "inline-flex",
                              padding: "6px 10px",
                              borderRadius: "999px",
                              background:
                                entry.status === "Riskte"
                                  ? "rgba(168, 59, 28, 0.14)"
                                  : entry.status === "Dengede"
                                    ? "rgba(185, 116, 41, 0.14)"
                                    : "rgba(18, 82, 52, 0.12)",
                              color:
                                entry.status === "Riskte"
                                  ? "#8a3516"
                                  : entry.status === "Dengede"
                                    ? "var(--accent-strong)"
                                    : "#18563b",
                              fontSize: "0.64rem",
                              fontWeight: 800,
                              letterSpacing: "0.04em",
                              textTransform: "uppercase",
                            }}
                          >
                            {entry.status}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                            gap: "8px",
                          }}
                        >
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.66rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Şube
                            </div>
                            <div style={{ fontWeight: 800 }}>{entry.restaurant_count}</div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.66rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Hacim
                            </div>
                            <div style={{ fontWeight: 800 }}>
                              {`${entry.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket`}
                            </div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.66rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Fatura
                            </div>
                            <div style={{ fontWeight: 800 }}>{formatCurrency(entry.gross_invoice)}</div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.66rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Operasyon Farkı
                            </div>
                            <div style={{ fontWeight: 800 }}>{formatCurrency(entry.operation_gap)}</div>
                          </div>
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>
                          {`${entry.total_hours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} saatlik toplam çalışma ile bu ayki marka ritmi burada okunuyor.`}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                      Marka bazlı özet için bu ay puantaj verisi henüz oluşmadı.
                    </div>
                  )}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Kritik Uyarılar
                  </div>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Günün kritik operasyon ve veri hijyeni sinyallerini tek özet satırında tutuyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "8px" }}>
                  {[
                    ["Bugün puantaj bekleyen şube", String(dashboard.operations.missing_attendance_count)],
                    ["Hedef kadro altında kalan şube", String(dashboard.operations.under_target_count)],
                    ["Bugün joker kullanılan şube", String(dashboard.operations.joker_usage_count)],
                    ["Eksik personel kartı", String(dashboard.hygiene.missing_personnel_cards)],
                    ["Eksik restoran kartı", String(dashboard.hygiene.missing_restaurant_cards)],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "12px",
                        paddingBottom: "8px",
                        borderBottom: "1px solid rgba(24,40,59,0.08)",
                      }}
                    >
                      <span style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Bu Ay Yönetim Özeti
                  </div>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Gelir, operasyon farkı ve ortak yükü kısa bir yönetim özeti halinde topluyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "8px" }}>
                  {[
                    ["Restoran faturası", formatCurrency(dashboard.finance.total_revenue)],
                    ["Operasyon farkı", formatCurrency(dashboard.finance.gross_profit)],
                    ["Ortak operasyon payı", formatCurrency(dashboard.operations.shared_operation_total)],
                    ["Kârlı restoran", String(dashboard.operations.profitable_restaurant_count)],
                    ["Riskli restoran", String(dashboard.operations.risky_restaurant_count)],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "12px",
                        paddingBottom: "8px",
                        borderBottom: "1px solid rgba(24,40,59,0.08)",
                      }}
                    >
                      <span style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Son 14 Gün Paket Akışı
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.5rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Ritimdeki yükseliş ve düşüşü gün gün okuyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Günlük paket hareketi ile saat yükünü birlikte okuyup operasyon temposunu daha erken hissediyoruz.
                  </p>
                </header>

                {dashboard.operations.daily_trend.length ? (
                  <div style={{ display: "grid", gap: "8px" }}>
                    {(() => {
                      const maxPackages = Math.max(
                        ...dashboard.operations.daily_trend.map((item) => item.total_packages || 0),
                        1,
                      );
                      return dashboard.operations.daily_trend.map((item) => (
                        <div
                          key={item.entry_date}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "82px minmax(0, 1fr) 120px",
                            gap: "12px",
                            alignItems: "center",
                          }}
                        >
                          <div
                            style={{
                              color: "var(--muted)",
                              fontSize: "0.84rem",
                              fontWeight: 700,
                            }}
                          >
                            {formatShortDate(item.entry_date)}
                          </div>
                          <div
                            style={{
                              height: "14px",
                              borderRadius: "999px",
                              background: "rgba(24,40,59,0.08)",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${Math.max((item.total_packages / maxPackages) * 100, item.total_packages > 0 ? 6 : 0)}%`,
                                height: "100%",
                                borderRadius: "999px",
                                background:
                                  "linear-gradient(90deg, rgba(185,116,41,0.88), rgba(222,165,92,0.92))",
                              }}
                            />
                          </div>
                          <div
                            style={{
                              textAlign: "right",
                              color: "var(--muted)",
                              fontSize: "0.82rem",
                              lineHeight: 1.45,
                            }}
                          >
                            {`${item.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket`}
                            <br />
                            {`${item.total_hours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} saat`}
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                ) : (
                  <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                    Grafik için son 14 günde puantaj verisi oluşmadı.
                  </div>
                )}
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  ...masonryItemStyle,
                  padding: "16px",
                  display: "grid",
                  gap: "12px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Bu Ay En Yoğun Şubeler
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.5rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Paket ve saat yükü önde gelen şubeleri gösteriyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                    Ay içindeki yoğunluğu erken okuyup destek ve kadro kararlarını daha sakin veriyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "10px" }}>
                  {dashboard.operations.top_restaurants.length ? (
                    dashboard.operations.top_restaurants.map((item, index) => (
                      <article
                        key={`${item.restaurant}-${index}`}
                        style={{
                          padding: "16px",
                          borderRadius: "18px",
                          background: "rgba(255,255,255,0.78)",
                          border: "1px solid rgba(24,40,59,0.08)",
                          display: "grid",
                          gap: "8px",
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
                          <div
                            style={{
                              ...serifTitleStyle,
                              fontSize: "1.08rem",
                              lineHeight: 1,
                              fontWeight: 700,
                            }}
                          >
                            {item.restaurant}
                          </div>
                          <span
                            style={{
                              color: "var(--accent-strong)",
                              fontSize: "0.66rem",
                              fontWeight: 800,
                              letterSpacing: "0.06em",
                              textTransform: "uppercase",
                            }}
                          >
                            #{index + 1}
                          </span>
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>
                          {`${item.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket | ${item.total_hours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} saat`}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                      Bu ay öne çıkan şube yükü henüz görünmüyor.
                    </div>
                  )}
                </div>
              </article>

            <section
              style={{
                ...paperCardStyle,
                ...masonryItemStyle,
                padding: "16px",
                display: "grid",
                gap: "12px",
                background: "rgba(255,255,255,0.94)",
              }}
            >
              <header style={{ display: "grid", gap: "8px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.66rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Hızlı Komuta Alanı
                </div>
                <h2
                  style={{
                    ...serifTitleStyle,
                    margin: 0,
                    fontSize: "1.55rem",
                    lineHeight: 0.98,
                    fontWeight: 700,
                  }}
                >
                  Sık kullanılan ekranlara tek dokunuşla geçiyoruz.
                </h2>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                  Günün operasyonu başlarken en sık açılan modülleri tek masada topluyoruz.
                </p>
              </header>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "10px",
                }}
              >
                {quickActions.map((item) => (
                  <Link
                    key={item.title}
                    href={item.href}
                    style={{
                      ...paperCardStyle,
                      padding: "14px",
                      display: "grid",
                      gap: "8px",
                      background:
                        "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                      textDecoration: "none",
                      color: "inherit",
                    }}
                  >
                    <div
                      style={{
                        display: "inline-flex",
                        alignSelf: "start",
                        padding: "6px 10px",
                        borderRadius: "999px",
                        background: "rgba(185,116,41,0.12)",
                        color: "var(--accent-strong)",
                        fontSize: "0.64rem",
                        fontWeight: 800,
                        letterSpacing: "0.05em",
                        textTransform: "uppercase",
                      }}
                    >
                      {item.badge}
                    </div>
                    <div
                      style={{
                        ...serifTitleStyle,
                        fontSize: "1.08rem",
                        lineHeight: 1,
                        fontWeight: 700,
                      }}
                    >
                      {item.title}
                    </div>
                    <div style={{ color: "var(--muted)", lineHeight: 1.5, fontSize: "0.84rem" }}>{item.subtitle}</div>
                    <div
                      style={{
                        color: "var(--accent-strong)",
                        fontSize: "0.82rem",
                        fontWeight: 800,
                      }}
                    >
                      Ekranı Aç
                    </div>
                  </Link>
                ))}
              </div>
            </section>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
