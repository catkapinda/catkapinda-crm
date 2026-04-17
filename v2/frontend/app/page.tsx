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
  gap: "8px",
  padding: "7px 12px",
  borderRadius: "999px",
  background: "rgba(255,255,255,0.1)",
  border: "1px solid rgba(255,255,255,0.12)",
  color: "#f5d7b1",
  fontSize: "0.74rem",
  fontWeight: 800,
  letterSpacing: "0.09em",
  textTransform: "uppercase",
} as const;

const paperCardStyle = {
  borderRadius: "28px",
  border: "1px solid var(--line)",
  background: "var(--surface-raised)",
  boxShadow: "var(--shadow-soft)",
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
        padding: "16px 16px 14px",
        display: "grid",
        gap: "8px",
        background:
          "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(248,241,229,0.96))",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.7rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.07em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifTitleStyle,
          fontSize: "1.95rem",
          lineHeight: 0.96,
          fontWeight: 700,
          color: "var(--text)",
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.86rem",
          lineHeight: 1.5,
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
        padding: "18px",
        display: "grid",
        gap: "14px",
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
              fontSize: "0.7rem",
              letterSpacing: "0.07em",
              textTransform: "uppercase",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                width: "26px",
                height: "26px",
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
              fontSize: "1.42rem",
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
              lineHeight: 1.6,
              fontSize: "0.9rem",
            }}
          >
            {item.description}
          </p>
        </div>
        <div
          style={{
            minWidth: "54px",
            height: "48px",
            borderRadius: "16px",
            display: "grid",
            placeItems: "center",
            background: "var(--surface-ink)",
            color: "#f8efe1",
            fontWeight: 900,
            fontSize: "1rem",
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
          gap: "10px",
        }}
      >
        <div
          style={{
            padding: "12px 12px 10px",
            borderRadius: "16px",
            background: "rgba(24, 40, 59, 0.06)",
            border: "1px solid rgba(24, 40, 59, 0.08)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.7rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.07em",
            }}
          >
            {item.primary_label}
          </div>
          <div
            style={{
              marginTop: "8px",
              fontSize: "1.2rem",
              fontWeight: 900,
              letterSpacing: "-0.04em",
            }}
          >
            {item.primary_value}
          </div>
        </div>
        <div
          style={{
            padding: "12px 12px 10px",
            borderRadius: "16px",
            background: "rgba(185, 116, 41, 0.08)",
            border: "1px solid rgba(185, 116, 41, 0.14)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.7rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.07em",
            }}
          >
            {item.secondary_label}
          </div>
          <div
            style={{
              marginTop: "8px",
              fontSize: "1.2rem",
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
          padding: "11px 14px",
          borderRadius: "16px",
          background: "var(--surface-ink)",
          color: "#fff6ea",
          fontWeight: 800,
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
        padding: "18px",
        background: "rgba(255,255,255,0.9)",
        display: "grid",
        gap: "12px",
      }}
    >
      <div
        style={{
          color: "var(--accent-strong)",
          fontWeight: 800,
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {title}
      </div>
      {items.length ? (
        <div style={{ display: "grid", gap: "10px" }}>
          {items.map((item, index) => (
            <div
              key={`${title}-${index}`}
              style={{
                display: "grid",
                gap: "4px",
                paddingBottom: "10px",
                borderBottom: "1px solid rgba(24,40,59,0.08)",
              }}
            >
              <div style={{ fontWeight: 800 }}>
                {"label" in item ? item.label : item.title}
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                {mode === "value" && "value" in item ? item.value : "subtitle" in item ? item.subtitle : "-"}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
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

  const quickLaunchItems = useMemo(() => dashboard?.modules.slice(0, 3) ?? [], [dashboard?.modules]);

  return (
    <AppShell activeItem="Genel Bakış">
      <section
        style={{
          display: "grid",
          gap: "18px",
        }}
      >
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.45fr) minmax(300px, 0.95fr) minmax(240px, 0.8fr)",
            gap: "14px",
          }}
        >
          <article
            style={{
              padding: "22px",
              borderRadius: "28px",
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
            <div style={kickerStyle}>Operasyon Masası</div>
            <div
              style={{
                marginTop: "14px",
                display: "inline-flex",
                alignItems: "center",
                gap: "10px",
                width: "fit-content",
                padding: "8px 12px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.09)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#fff4e3",
                fontWeight: 800,
                fontSize: "0.9rem",
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
              <span>Bugünün kritik sinyalleri bu masada toplanıyor.</span>
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: "16px 0 10px",
                fontSize: "clamp(2.05rem, 4.4vw, 3.45rem)",
                lineHeight: 0.96,
                maxWidth: "12ch",
                fontWeight: 700,
              }}
            >
              Ofisin ritmi tek bir bakışta okunuyor.
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "66ch",
                color: "rgba(255, 247, 234, 0.78)",
                lineHeight: 1.65,
                fontSize: "0.94rem",
              }}
            >
              Bu yüzey artık sadece bir dashboard değil; şube, personel, puantaj ve kesinti
              hareketlerini ritimli, daha editoryal ve daha karakterli bir dille toplayan yeni
              komuta masası.
            </p>

            <div
              style={{
                marginTop: "18px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "10px",
              }}
            >
              {[
                ["Yönetim Notu", "Bugünün en yoğun alanları puantaj ve personel senkronu."],
                ["Kullanım Hissi", "Daha az kart kalabalığı, daha net aksiyon akışı."],
                ["Tasarlanan Ton", "Premium ama sıcak; operasyonel ama editoryal."],
              ].map(([label, text]) => (
                <div
                  key={label}
                  style={{
                    padding: "12px 12px 10px",
                    borderRadius: "16px",
                    background: "rgba(255,255,255,0.08)",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <div
                    style={{
                      color: "#f1c28f",
                      fontSize: "0.68rem",
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "0.07em",
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      marginTop: "6px",
                      color: "rgba(255, 247, 234, 0.84)",
                      lineHeight: 1.5,
                      fontSize: "0.88rem",
                    }}
                  >
                    {text}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article
            style={{
              ...paperCardStyle,
              padding: "18px",
              display: "grid",
              gap: "14px",
              background:
                "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
            }}
          >
              <header style={{ display: "grid", gap: "8px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.7rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.07em",
                  }}
                >
                  Yönetim Kartları
                </div>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                  Hızlı karar için öne çıkan operasyon ve finans sinyallerini tek satırda topluyoruz.
                </p>
              </header>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                  gap: "10px",
                }}
              >
                {pulseCard(
                  "Puantaj Bekleyen",
                  String(dashboard?.operations.missing_attendance_count ?? 0),
                  "Bugün kayıt bekleyen şube sayısı.",
                )}
                {pulseCard(
                  "Kadro Riski",
                  String(dashboard?.operations.under_target_count ?? 0),
                  "Hedef altında kalan aktif şubeler.",
                )}
                {pulseCard(
                  "Joker Kullanımı",
                  String(dashboard?.operations.joker_usage_count ?? 0),
                  "Bugün destek verilen şube sayısı.",
                )}
                {pulseCard(
                  "Bu Ay Fatura",
                  formatCurrency(dashboard?.finance.total_revenue ?? 0),
                  "KDV dahil restoran toplamı.",
                )}
                {pulseCard(
                  "Operasyon Farkı",
                  formatCurrency(dashboard?.finance.gross_profit ?? 0),
                  "Ay içi brüt operasyon farkı.",
                )}
                {pulseCard(
                  "Riskli Şube",
                  String(dashboard?.operations.risky_restaurant_count ?? 0),
                  `${dashboard?.operations.profitable_restaurant_count ?? 0} kârlı şube ile birlikte.`,
                )}
              </div>
          </article>

          <div
            style={{
              display: "grid",
              gap: "14px",
            }}
          >
            <article
              style={{
                ...paperCardStyle,
                padding: "18px",
                background:
                  "linear-gradient(180deg, rgba(255,250,241,0.98), rgba(245,236,220,0.96))",
              }}
            >
              <div
                style={{
                  color: "var(--accent-strong)",
                  fontWeight: 800,
                  fontSize: "0.7rem",
                  letterSpacing: "0.07em",
                  textTransform: "uppercase",
                }}
              >
                Bugünün Vurgusu
              </div>
              <div
                style={{
                  ...serifTitleStyle,
                  marginTop: "10px",
                  fontSize: "1.55rem",
                  lineHeight: 1,
                  fontWeight: 700,
                }}
              >
                Daha cesur, daha editoryal, daha ürün gibi.
              </div>
              <p
                style={{
                  margin: "8px 0 0",
                  color: "var(--muted)",
                  lineHeight: 1.6,
                  fontSize: "0.9rem",
                }}
              >
                Güvenli beyaz kart düzeninden çıkıp daha iddialı bir marka hissi kuruyoruz.
              </p>
            </article>

            <article
              style={{
                ...paperCardStyle,
                padding: "18px",
                background: "rgba(255, 253, 247, 0.96)",
              }}
            >
              <div
                style={{
                  color: "var(--muted)",
                  fontWeight: 800,
                  fontSize: "0.7rem",
                  letterSpacing: "0.07em",
                  textTransform: "uppercase",
                }}
              >
                Hızlı Açılış
              </div>
              <div
                style={{
                  marginTop: "10px",
                  display: "grid",
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
                        gap: "14px",
                        padding: "12px 14px",
                        borderRadius: "14px",
                        background: "rgba(24, 40, 59, 0.05)",
                        border: "1px solid rgba(24, 40, 59, 0.08)",
                        fontWeight: 800,
                        fontSize: "0.92rem",
                      }}
                    >
                      <span>{item.title}</span>
                      <span style={{ color: "var(--accent-strong)" }}>{item.primary_value}</span>
                    </Link>
                  ))
                ) : (
                  <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                    Modül verisi geldiğinde hızlı açılış önerileri burada görünecek.
                  </div>
                )}
              </div>
            </article>
          </div>
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
            Genel bakış servisi şu anda cevap vermiyor. Veri geri geldiğinde bu yeni yüzey gerçek
            operasyon nabzını ve son hareketleri daha güçlü bir dille gösterecek.
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
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "14px",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gap: "14px",
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
                      fontSize: "0.7rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.07em",
                    }}
                  >
                    Komuta Masası
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.9rem",
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
                      lineHeight: 1.6,
                      fontSize: "0.92rem",
                    }}
                  >
                    Her modül artık hem sayı anlatıyor hem de kullanıcıyı doğrudan doğru aksiyona
                    götürüyor.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: "12px",
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
                    padding: "18px 18px 14px",
                    borderBottom: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div style={kickerStyle}>Hareket Akışı</div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: "10px 0 6px",
                      fontSize: "1.6rem",
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
                      lineHeight: 1.6,
                      fontSize: "0.92rem",
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
                    maxHeight: "680px",
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
                        padding: "14px",
                        borderRadius: "16px",
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
                            fontSize: "0.68rem",
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
                          fontSize: "1.12rem",
                          lineHeight: 1,
                          fontWeight: 700,
                        }}
                      >
                        {item.title}
                      </div>
                      <div
                        style={{
                          color: "#fff7ea",
                          lineHeight: 1.5,
                          fontSize: "0.92rem",
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

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.15fr) minmax(320px, 0.85fr)",
                gap: "14px",
                alignItems: "start",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  padding: "18px",
                  display: "grid",
                  gap: "14px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.7rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.07em",
                    }}
                  >
                    Bu Ay Karlılık Özeti
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.7rem",
                      lineHeight: 1,
                      fontWeight: 700,
                    }}
                  >
                    Gelir, maliyet ve kâr aynı masada okunuyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6, fontSize: "0.92rem" }}>
                    {dashboard.finance.selected_month
                      ? `${dashboard.finance.selected_month} dönemi için restoran faturası, personel maliyeti ve yan gelir toplamını tek yerde topluyoruz.`
                      : "Rapor verisi geldikçe aylık kârlılık sinyallerini burada birlikte okuyacağız."}
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "12px",
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
                    gap: "14px",
                  }}
                >
                  {snapshotList("En Güçlü Restoranlar", dashboard.finance.top_restaurants, "value")}
                  {snapshotList("Dikkat İsteyen Restoranlar", dashboard.finance.risk_restaurants, "value")}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "16px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Kart ve Zimmet Kontrolü
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.85rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Eksik kartları masanın üstünde tutuyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Eksik alanlı personel ve restoran kartlarını hızlıca görüp operasyon öncesi düzenlemek için.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "12px",
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
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 0.95fr) minmax(320px, 1.05fr)",
                gap: "18px",
                alignItems: "start",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "18px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Bugün Acil Aksiyon
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.95rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Hangi şubenin beklediğini tek bakışta görüyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Puantaj bekleyen, hedef kadronun altında kalan ve joker desteği alan şubeleri tek panelde topluyoruz.
                  </p>
                </header>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: "12px",
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

                <div style={{ display: "grid", gap: "12px" }}>
                  {dashboard.operations.action_alerts.length ? (
                    dashboard.operations.action_alerts.map((item, index) => {
                      const tone = toneSurface(item.tone);
                      return (
                        <article
                          key={`${item.badge}-${item.title}-${index}`}
                          style={{
                            padding: "16px",
                            borderRadius: "22px",
                            background: tone.background,
                            border: tone.border,
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
                            <span
                              style={{
                                display: "inline-flex",
                                padding: "6px 10px",
                                borderRadius: "999px",
                                background: tone.badgeBackground,
                                color: tone.badgeColor,
                                fontSize: "0.72rem",
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
                              fontSize: "1.35rem",
                              lineHeight: 1,
                              fontWeight: 700,
                            }}
                          >
                            {item.title}
                          </div>
                          <div style={{ color: "var(--muted)", lineHeight: 1.65 }}>{item.detail}</div>
                        </article>
                      );
                    })
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                      Bugün öne çıkan aksiyon uyarısı görünmüyor.
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: "grid",
                    gap: "10px",
                    padding: "16px",
                    borderRadius: "24px",
                    background: "rgba(255,248,238,0.92)",
                    border: "1px solid rgba(185,116,41,0.12)",
                  }}
                >
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      letterSpacing: "0.08em",
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
                          paddingBottom: "10px",
                          borderBottom: "1px solid rgba(24,40,59,0.08)",
                        }}
                      >
                        <div style={{ fontWeight: 800 }}>{item.restaurant}</div>
                        <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                          {`${item.joker_count} joker`}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                          {`${item.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket`}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                      Bugün joker kullanılan şube görünmüyor.
                    </div>
                  )}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "18px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Marka Bazlı Özet
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.95rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Hacim ve risk aynı tabloda okunuyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Aylık paket, saat, fatura ve operasyon farkını marka seviyesinde yan yana görüyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "12px" }}>
                  {dashboard.operations.brand_summary.length ? (
                    dashboard.operations.brand_summary.map((entry, index) => (
                      <article
                        key={`${entry.brand}-${index}`}
                        style={{
                          padding: "16px",
                          borderRadius: "22px",
                          background: "rgba(255,255,255,0.78)",
                          border: "1px solid rgba(24,40,59,0.08)",
                          display: "grid",
                          gap: "10px",
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
                              fontSize: "1.4rem",
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
                              fontSize: "0.72rem",
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
                            gap: "10px",
                          }}
                        >
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.74rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Şube
                            </div>
                            <div style={{ fontWeight: 800 }}>{entry.restaurant_count}</div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.74rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Hacim
                            </div>
                            <div style={{ fontWeight: 800 }}>
                              {`${entry.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket`}
                            </div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.74rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Fatura
                            </div>
                            <div style={{ fontWeight: 800 }}>{formatCurrency(entry.gross_invoice)}</div>
                          </div>
                          <div>
                            <div style={{ color: "var(--muted)", fontSize: "0.74rem", fontWeight: 800, textTransform: "uppercase" }}>
                              Operasyon Farkı
                            </div>
                            <div style={{ fontWeight: 800 }}>{formatCurrency(entry.operation_gap)}</div>
                          </div>
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.65 }}>
                          {`${entry.total_hours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} saatlik toplam çalışma ile bu ayki marka ritmi burada okunuyor.`}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                      Marka bazlı özet için bu ay puantaj verisi henüz oluşmadı.
                    </div>
                  )}
                </div>
              </article>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: "18px",
                alignItems: "start",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "14px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Kritik Uyarılar
                  </div>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Günün kritik operasyon ve veri hijyeni sinyallerini tek özet satırında tutuyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "10px" }}>
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
                        paddingBottom: "10px",
                        borderBottom: "1px solid rgba(24,40,59,0.08)",
                      }}
                    >
                      <span style={{ color: "var(--muted)", lineHeight: 1.6 }}>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "14px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Bu Ay Yönetim Özeti
                  </div>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Gelir, operasyon farkı ve ortak yükü kısa bir yönetim özeti halinde topluyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "10px" }}>
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
                        paddingBottom: "10px",
                        borderBottom: "1px solid rgba(24,40,59,0.08)",
                      }}
                    >
                      <span style={{ color: "var(--muted)", lineHeight: 1.6 }}>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.05fr) minmax(320px, 0.95fr)",
                gap: "18px",
                alignItems: "start",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "18px",
                  background: "rgba(255,255,255,0.94)",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Son 14 Gün Paket Akışı
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.95rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Ritimdeki yükseliş ve düşüşü gün gün okuyoruz.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Günlük paket hareketi ile saat yükünü birlikte okuyup operasyon temposunu daha erken hissediyoruz.
                  </p>
                </header>

                {dashboard.operations.daily_trend.length ? (
                  <div style={{ display: "grid", gap: "10px" }}>
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
                              fontSize: "0.9rem",
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
                              fontSize: "0.9rem",
                              lineHeight: 1.5,
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
                  <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                    Grafik için son 14 günde puantaj verisi oluşmadı.
                  </div>
                )}
              </article>

              <article
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "18px",
                  background:
                    "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,241,229,0.96))",
                }}
              >
                <header style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Bu Ay En Yoğun Şubeler
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "1.95rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Paket ve saat yükü önde gelen şubeleri gösteriyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Ay içindeki yoğunluğu erken okuyup destek ve kadro kararlarını daha sakin veriyoruz.
                  </p>
                </header>

                <div style={{ display: "grid", gap: "12px" }}>
                  {dashboard.operations.top_restaurants.length ? (
                    dashboard.operations.top_restaurants.map((item, index) => (
                      <article
                        key={`${item.restaurant}-${index}`}
                        style={{
                          padding: "16px",
                          borderRadius: "22px",
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
                              fontSize: "1.32rem",
                              lineHeight: 1,
                              fontWeight: 700,
                            }}
                          >
                            {item.restaurant}
                          </div>
                          <span
                            style={{
                              color: "var(--accent-strong)",
                              fontSize: "0.75rem",
                              fontWeight: 800,
                              letterSpacing: "0.06em",
                              textTransform: "uppercase",
                            }}
                          >
                            #{index + 1}
                          </span>
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.65 }}>
                          {`${item.total_packages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} paket | ${item.total_hours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} saat`}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                      Bu ay öne çıkan şube yükü henüz görünmüyor.
                    </div>
                  )}
                </div>
              </article>
            </section>

            <section
              style={{
                ...paperCardStyle,
                padding: "22px",
                display: "grid",
                gap: "18px",
                background: "rgba(255,255,255,0.94)",
              }}
            >
              <header style={{ display: "grid", gap: "8px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.75rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Hızlı Komuta Alanı
                </div>
                <h2
                  style={{
                    ...serifTitleStyle,
                    margin: 0,
                    fontSize: "2rem",
                    lineHeight: 0.98,
                    fontWeight: 700,
                  }}
                >
                  Sık kullanılan ekranlara tek dokunuşla geçiyoruz.
                </h2>
                <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                  Günün operasyonu başlarken en sık açılan modülleri tek masada topluyoruz.
                </p>
              </header>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                {quickActions.map((item) => (
                  <Link
                    key={item.title}
                    href={item.href}
                    style={{
                      ...paperCardStyle,
                      padding: "18px",
                      display: "grid",
                      gap: "10px",
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
                        fontSize: "0.72rem",
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
                        fontSize: "1.4rem",
                        lineHeight: 1,
                        fontWeight: 700,
                      }}
                    >
                      {item.title}
                    </div>
                    <div style={{ color: "var(--muted)", lineHeight: 1.65 }}>{item.subtitle}</div>
                    <div
                      style={{
                        color: "var(--accent-strong)",
                        fontSize: "0.9rem",
                        fontWeight: 800,
                      }}
                    >
                      Ekranı Aç
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
