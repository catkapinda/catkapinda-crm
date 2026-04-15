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
        <span>Modulu Ac</span>
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
            <div style={kickerStyle}>Operations Newsroom</div>
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
              Ofisin ritmi tek bir bakista okunuyor.
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
                ["Yonetim Notu", "Bugunun en yogun alanlari puantaj ve personel senkronu."],
                ["Kullanim Hissi", "Daha az kart kalabaligi, daha net aksiyon akisi."],
                ["Tasarlanan Ton", "Premium ama sicak; operasyonel ama editoryal."],
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
                Bugunun Vurgusu
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
                Daha cesur, daha editorial, daha urun gibi.
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
            Genel bakis newsroom paneli yukleniyor...
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
            Overview backend şu anda cevap vermiyor. Veri geri geldiğinde bu yeni yüzey gerçek
            operasyon nabzını ve son hareketleri daha premium bir dille gösterecek.
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
                "Aktif Sube",
                String(dashboard.hero.active_restaurants),
                "Operasyon omurgasinda bugun hareketli olan restoran havuzu.",
              )}
              {pulseCard(
                "Aktif Personel",
                String(dashboard.hero.active_personnel),
                "Sistemde anlik aktif gorebilecegin saha ve destek personeli.",
              )}
              {pulseCard(
                "Bu Ay Puantaj",
                String(dashboard.hero.month_attendance_entries),
                "Ay icinde acilan vardiya ve devam kaydi yogunlugu.",
              )}
              {pulseCard(
                "Bu Ay Kesinti",
                String(dashboard.hero.month_deduction_entries),
                "Ay sonu finans akisina etki eden manuel ve otomatik kesintiler.",
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
                    Komuta Masasi
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
                    Moduller artik daha net roller oynuyor.
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
                  <div style={kickerStyle}>Activity Wire</div>
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
          </>
        )}
      </section>
    </AppShell>
  );
}
