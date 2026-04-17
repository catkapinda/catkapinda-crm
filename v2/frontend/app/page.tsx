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
        padding: "20px 20px 18px",
        display: "grid",
        gap: "10px",
        background:
          "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(248,241,229,0.96))",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.75rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifTitleStyle,
          fontSize: "2.4rem",
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
          fontSize: "0.92rem",
          lineHeight: 1.6,
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
        padding: "22px",
        display: "grid",
        gap: "18px",
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
              fontSize: "0.74rem",
              letterSpacing: "0.08em",
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
              fontSize: "1.7rem",
              lineHeight: 0.98,
              fontWeight: 700,
            }}
          >
            {item.title}
          </div>
          <p
            style={{
              margin: 0,
              color: "var(--muted)",
              lineHeight: 1.7,
              fontSize: "0.96rem",
            }}
          >
            {item.description}
          </p>
        </div>
        <div
          style={{
            minWidth: "54px",
            height: "54px",
            borderRadius: "18px",
            display: "grid",
            placeItems: "center",
            background: "var(--surface-ink)",
            color: "#f8efe1",
            fontWeight: 900,
            fontSize: "1.15rem",
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
          gap: "12px",
        }}
      >
        <div
          style={{
            padding: "14px 14px 12px",
            borderRadius: "20px",
            background: "rgba(24, 40, 59, 0.06)",
            border: "1px solid rgba(24, 40, 59, 0.08)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.75rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            {item.primary_label}
          </div>
          <div
            style={{
              marginTop: "8px",
              fontSize: "1.45rem",
              fontWeight: 900,
              letterSpacing: "-0.04em",
            }}
          >
            {item.primary_value}
          </div>
        </div>
        <div
          style={{
            padding: "14px 14px 12px",
            borderRadius: "20px",
            background: "rgba(185, 116, 41, 0.08)",
            border: "1px solid rgba(185, 116, 41, 0.14)",
          }}
        >
          <div
            style={{
              color: "var(--muted)",
              fontSize: "0.75rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            {item.secondary_label}
          </div>
          <div
            style={{
              marginTop: "8px",
              fontSize: "1.45rem",
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
          padding: "13px 16px",
          borderRadius: "18px",
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
          gap: "24px",
        }}
      >
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "18px",
          }}
        >
          <article
            style={{
              padding: "30px",
              borderRadius: "34px",
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
            <h1
              style={{
                ...serifTitleStyle,
                margin: "20px 0 14px",
                fontSize: "clamp(2.7rem, 6vw, 4.7rem)",
                lineHeight: 0.92,
                maxWidth: "10ch",
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
                lineHeight: 1.75,
                fontSize: "1rem",
              }}
            >
              Bu yüzey artık sadece bir dashboard değil; şube, personel, puantaj ve kesinti
              hareketlerini ritimli, daha editoryal ve daha karakterli bir dille toplayan yeni
              komuta masası.
            </p>

            <div
              style={{
                marginTop: "24px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "12px",
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
                    padding: "14px 14px 12px",
                    borderRadius: "20px",
                    background: "rgba(255,255,255,0.08)",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <div
                    style={{
                      color: "#f1c28f",
                      fontSize: "0.72rem",
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      marginTop: "8px",
                      color: "rgba(255, 247, 234, 0.84)",
                      lineHeight: 1.6,
                      fontSize: "0.93rem",
                    }}
                  >
                    {text}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <div
            style={{
              display: "grid",
              gap: "18px",
            }}
          >
            <article
              style={{
                ...paperCardStyle,
                padding: "24px",
                background:
                  "linear-gradient(180deg, rgba(255,250,241,0.98), rgba(245,236,220,0.96))",
              }}
            >
              <div
                style={{
                  color: "var(--accent-strong)",
                  fontWeight: 800,
                  fontSize: "0.75rem",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Bugünün Vurgusu
              </div>
              <div
                style={{
                  ...serifTitleStyle,
                  marginTop: "14px",
                  fontSize: "2rem",
                  lineHeight: 0.96,
                  fontWeight: 700,
                }}
              >
                Daha cesur, daha editoryal, daha ürün gibi.
              </div>
              <p
                style={{
                  margin: "12px 0 0",
                  color: "var(--muted)",
                  lineHeight: 1.7,
                  fontSize: "0.96rem",
                }}
              >
                Güvenli beyaz kart düzeninden çıkıp daha iddialı bir marka hissi kuruyoruz.
              </p>
            </article>

            <article
              style={{
                ...paperCardStyle,
                padding: "24px",
                background: "rgba(255, 253, 247, 0.96)",
              }}
            >
              <div
                style={{
                  color: "var(--muted)",
                  fontWeight: 800,
                  fontSize: "0.75rem",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Hızlı Açılış
              </div>
              <div
                style={{
                  marginTop: "16px",
                  display: "grid",
                  gap: "10px",
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
                        padding: "14px 16px",
                        borderRadius: "18px",
                        background: "rgba(24, 40, 59, 0.05)",
                        border: "1px solid rgba(24, 40, 59, 0.08)",
                        fontWeight: 800,
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
                gap: "14px",
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
                gap: "18px",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gap: "18px",
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
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Komuta Masası
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "2.4rem",
                      lineHeight: 0.96,
                      fontWeight: 700,
                    }}
                  >
                    Modüller artık daha net roller oynuyor.
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      lineHeight: 1.7,
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
                    gap: "16px",
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
                    padding: "22px 22px 18px",
                    borderBottom: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div style={kickerStyle}>Hareket Akışı</div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: "14px 0 8px",
                      fontSize: "2rem",
                      lineHeight: 0.96,
                      fontWeight: 700,
                    }}
                  >
                    Son hareketler artık daha okunur.
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "rgba(249, 242, 230, 0.72)",
                      lineHeight: 1.7,
                    }}
                  >
                    Akışta ne değiştiğini modül atlamadan tek panelde okuyabiliyorsun.
                  </p>
                </div>
                <div
                  style={{
                    padding: "10px",
                    display: "grid",
                    gap: "10px",
                    maxHeight: "760px",
                    overflowY: "auto",
                  }}
                >
                  {dashboard.recent_activity.map((item) => (
                    <Link
                      key={`${item.module_key}-${item.href}-${item.title}-${item.meta}`}
                      href={item.href}
                      style={{
                        display: "grid",
                        gap: "8px",
                        padding: "16px",
                        borderRadius: "20px",
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
                            fontSize: "0.72rem",
                            fontWeight: 800,
                          }}
                        >
                          {item.module_label}
                        </span>
                        <span
                          style={{
                            color: "rgba(249, 242, 230, 0.62)",
                            fontSize: "0.84rem",
                          }}
                        >
                          {formatActivityDate(item.entry_date)}
                        </span>
                      </div>
                      <div
                        style={{
                          ...serifTitleStyle,
                          fontSize: "1.32rem",
                          lineHeight: 1,
                          fontWeight: 700,
                        }}
                      >
                        {item.title}
                      </div>
                      <div
                        style={{
                          color: "#fff7ea",
                          lineHeight: 1.55,
                        }}
                      >
                        {item.subtitle}
                      </div>
                      <div
                        style={{
                          color: "rgba(249, 242, 230, 0.68)",
                          fontSize: "0.9rem",
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
                    Bu Ay Karlılık Özeti
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: 0,
                      fontSize: "2.15rem",
                      lineHeight: 0.96,
                      fontWeight: 700,
                    }}
                  >
                    Gelir, maliyet ve kâr aynı masada okunuyor.
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
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
          </>
        )}
      </section>
    </AppShell>
  );
}
