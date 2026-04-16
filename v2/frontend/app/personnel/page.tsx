"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { PersonnelEntryWorkspace } from "../../components/personnel/personnel-entry-workspace";
import { PersonnelManagementWorkspace } from "../../components/personnel/personnel-management-workspace";
import { PersonnelPlateWorkspace } from "../../components/personnel/personnel-plate-workspace";
import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type PersonnelDashboard = {
  module: string;
  status: string;
  summary: {
    total_personnel: number;
    active_personnel: number;
    passive_personnel: number;
    assigned_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    person_code: string;
    full_name: string;
    role: string;
    status: string;
    phone: string;
    restaurant_id: number | null;
    restaurant_label: string;
    vehicle_mode: string;
    current_plate: string;
    start_date: string | null;
    monthly_fixed_cost: number;
    notes: string;
  }>;
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

function metricCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
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
        {label}
      </div>
      <div
        style={{
          ...serifTitleStyle,
          marginTop: "10px",
          fontSize: "2rem",
          lineHeight: 0.95,
          fontWeight: 700,
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "8px",
          color: "var(--muted)",
          lineHeight: 1.6,
          fontSize: "0.92rem",
        }}
      >
        {note}
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
        ...paperCardStyle,
        padding: "18px 18px 16px",
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
          ...serifTitleStyle,
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

function workspaceFrame(
  kicker: string,
  title: string,
  description: string,
  child: ReactNode,
) {
  return (
    <section
      style={{
        ...paperCardStyle,
        padding: "20px",
        display: "grid",
        gap: "18px",
        background:
          "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(249,244,235,0.95))",
      }}
    >
      <div style={{ display: "grid", gap: "8px" }}>
        <div
          style={{
            color: "var(--accent-strong)",
            fontWeight: 800,
            fontSize: "0.74rem",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          {kicker}
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
          {title}
        </h2>
        <p
          style={{
            margin: 0,
            color: "var(--muted)",
            lineHeight: 1.7,
          }}
        >
          {description}
        </p>
      </div>
      {child}
    </section>
  );
}

export default function PersonnelPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<PersonnelDashboard | null>(null);
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
        const response = await apiFetch("/personnel/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as PersonnelDashboard;
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

  const roleBreakdown = useMemo(() => {
    const counts = new Map<string, number>();
    for (const entry of dashboard?.recent_entries ?? []) {
      counts.set(entry.role, (counts.get(entry.role) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, 4);
  }, [dashboard?.recent_entries]);

  const restaurantCoverage =
    dashboard?.summary.total_personnel && dashboard.summary.total_personnel > 0
      ? Math.round((dashboard.summary.assigned_restaurants / dashboard.summary.total_personnel) * 100)
      : 0;
  const canViewPlateArea = user?.allowed_actions.includes("personnel.plate") ?? false;
  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const activeRatio =
      dashboard.summary.total_personnel > 0
        ? (dashboard.summary.active_personnel / dashboard.summary.total_personnel) * 100
        : 0;
    const topEntry = dashboard.recent_entries[0] ?? null;
    const unassignedCount = dashboard.recent_entries.filter((entry) => !entry.restaurant_label).length;
    const topRole = roleBreakdown[0] ?? null;

    return [
      {
        eyebrow: "Kadro Dengesi",
        title:
          activeRatio >= 80
            ? "Aktif kadro dengesi güçlü görünüyor."
            : activeRatio >= 60
              ? "Aktif kadro korunuyor."
              : "Aktif kadro dikkat istiyor.",
        body: `${dashboard.summary.total_personnel} kartın %${activeRatio.toFixed(1)} aktif durumda. Bu oran sahaya çıkabilecek gerçek kadro gücünü hızlı okumayı sağlar.`,
        tone: activeRatio >= 80 ? "ink" : "accent",
      },
      {
        eyebrow: "En Sıcak Kart",
        title: topEntry ? topEntry.full_name : "Kadro sinyali henüz yok.",
        body: topEntry
          ? canViewPlateArea && topEntry.vehicle_mode
            ? `${topEntry.role} rolünde ${topEntry.restaurant_label || "atamasız"} bağlamı ile öne çıkıyor. ${topEntry.vehicle_mode} ve ${topEntry.phone || "telefon yok"} bilgisiyle sahaya hazırlık seviyesi görünüyor.`
            : `${topEntry.role} rolünde ${topEntry.restaurant_label || "atamasız"} bağlamı ile öne çıkıyor. ${topEntry.phone || "telefon yok"} bilgisiyle sahaya hazırlık seviyesi görünüyor.`
          : "Yeni kart ve güncellemeler geldikçe burada dikkat isteyen personel kartı öne çıkarılacak.",
        tone: "paper",
      },
      {
        eyebrow: unassignedCount > 0 ? "Atama Baskısı" : "Rol Yoğunluğu",
        title: unassignedCount > 0 ? "Atama bekleyen kartlar var." : topRole ? `${topRole[0]} önde gidiyor.` : "Rol sinyali henüz yok.",
        body:
          unassignedCount > 0
            ? `Son kartlarda ${unassignedCount} kişi şube ataması olmadan görünüyor. Bu, saha planlaması öncesi hızlı bir kontrol gerektirebilir.`
            : topRole
              ? `Son hareketlerde ${topRole[0]} rolü ${topRole[1]} kartla öne çıkıyor. Aynı anda %${restaurantCoverage} şube kapsamı operasyon dağılımını okumayı kolaylaştırıyor.`
              : "Rol dağılımı geldikçe burada hangi kadro tipinin ağırlık kazandığı daha erken okunacak.",
        tone: unassignedCount > 0 ? "accent" : "paper",
      },
    ] as const;
  }, [canViewPlateArea, dashboard, restaurantCoverage, roleBreakdown]);

  return (
    <AppShell activeItem="Personel">
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
                inset: "auto auto -110px -70px",
                width: "240px",
                height: "240px",
                borderRadius: "999px",
                background: "radial-gradient(circle, rgba(185,116,41,0.34), transparent 72%)",
              }}
            />
            <div
              style={{
                display: "inline-flex",
                padding: "7px 12px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#f5d7b1",
                fontSize: "0.74rem",
                fontWeight: 800,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              kadro komuta masası
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: "18px 0 12px",
                fontSize: "clamp(2.5rem, 5vw, 4.4rem)",
                lineHeight: 0.9,
                fontWeight: 700,
                maxWidth: "9ch",
              }}
            >
              Personel akışını merkezden yönet.
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "58ch",
                color: "rgba(255,247,234,0.76)",
                lineHeight: 1.8,
                fontSize: "1rem",
              }}
            >
              Kart oluşturma, aktif-pasif takibi, şube atamaları ve son hareketler tek editoryal
              yüzeyde toplanıyor. Hedefimiz bu ekranı ofisin gerçek çalışma masası gibi hissettirmek.
            </p>

            <div
              style={{
                marginTop: "24px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {[
                ["Kayıt", "Yeni personel kartı, sahadan kopmadan hızlı oluşsun."],
                ["Takip", "Durum, şube ve araç sinyalleri tek yerde toplansın."],
                ["Denge", "Operasyon eksiği veya yığılma daha ilk bakışta görünsün."],
              ].map(([title, text]) => (
                <article
                  key={title}
                  style={{
                    padding: "18px 16px",
                    borderRadius: "22px",
                    background: "rgba(255,255,255,0.07)",
                    border: "1px solid rgba(255,255,255,0.09)",
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  <div style={{ color: "#fff4e5", fontWeight: 800 }}>{title}</div>
                  <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.65, fontSize: "0.92rem" }}>
                    {text}
                  </div>
                </article>
              ))}
            </div>
          </article>

          <div style={{ display: "grid", gap: "18px" }}>
            <article
              style={{
                ...paperCardStyle,
                padding: "22px",
                background:
                  "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(247,241,230,0.96))",
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  color: "var(--accent-strong)",
                  fontSize: "0.74rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 800,
                }}
              >
                Kadro Nabzı
              </div>
              <div
                style={{
                  ...serifTitleStyle,
                  fontSize: "2.3rem",
                  lineHeight: 0.92,
                  fontWeight: 700,
                }}
              >
                {dashboard?.summary.total_personnel ?? "-"}
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                {dashboard
                  ? `${dashboard.summary.active_personnel} aktif, ${dashboard.summary.passive_personnel} pasif kart aynı yüzeyde izleniyor.`
                  : "Toplam kart havuzu. Bu yüzey aktiflik, atama ve son hareketleri aynı ritimde okumaya odaklı."}
              </div>
            </article>

            <article
              style={{
                ...paperCardStyle,
                padding: "22px",
                background:
                  "linear-gradient(145deg, rgba(245,238,226,0.95), rgba(255,250,242,0.98))",
                display: "grid",
                gap: "12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.74rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Şube Kapsamı
                </div>
                <div style={{ fontWeight: 800, color: "var(--text)" }}>%{restaurantCoverage}</div>
              </div>
              <div
                style={{
                  height: "12px",
                  borderRadius: "999px",
                  background: "rgba(62,81,107,0.08)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${Math.min(restaurantCoverage, 100)}%`,
                    height: "100%",
                    borderRadius: "999px",
                    background:
                      "linear-gradient(90deg, var(--accent-strong), rgba(62,81,107,0.85))",
                  }}
                />
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.65, fontSize: "0.92rem" }}>
                Atanmış şube sayısının toplam personele oranını hızlı sinyal olarak veriyoruz.
              </div>
            </article>

            <article
              style={{
                ...paperCardStyle,
                padding: "22px",
                background:
                  "linear-gradient(145deg, rgba(255,253,247,0.98), rgba(248,244,236,0.95))",
                display: "grid",
                gap: "12px",
              }}
            >
              <div
                style={{
                  color: "var(--accent-strong)",
                  fontSize: "0.74rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 800,
                }}
              >
                Son Rollerde Dağılım
              </div>
              {roleBreakdown.length ? (
                <div style={{ display: "grid", gap: "10px" }}>
                  {roleBreakdown.map(([role, count]) => (
                    <div
                      key={role}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        paddingBottom: "10px",
                        borderBottom: "1px solid rgba(62,81,107,0.1)",
                      }}
                    >
                      <span style={{ fontWeight: 700 }}>{role}</span>
                      <span style={{ color: "var(--muted)", fontWeight: 700 }}>{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                  Dashboard verisi geldikçe son rol yoğunluğu burada görünecek.
                </div>
              )}
            </article>
          </div>
        </section>

        {dashboardLoading ? (
          <div
            style={{
              ...paperCardStyle,
              padding: "20px 22px",
              background: "rgba(185, 116, 41, 0.08)",
              color: "var(--muted)",
            }}
          >
            Personel verileri yükleniyor...
          </div>
        ) : !dashboard ? (
          <div
            style={{
              ...paperCardStyle,
              padding: "20px 22px",
              borderStyle: "dashed",
              background: "rgba(255,255,255,0.68)",
              color: "var(--muted)",
              lineHeight: 1.75,
            }}
          >
            Personel servisine şu anda erişilemiyor. Pilot arka uç ayağa kalktığında bu ekran
            kadro özetini ve son hareketleri gerçek veriden besleyecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Personel", String(dashboard.summary.total_personnel), "Kayıt havuzundaki tüm kartlar")}
              {metricCard("Aktif", String(dashboard.summary.active_personnel), "Sahaya çıkabilecek aktif kadro")}
              {metricCard("Pasif", String(dashboard.summary.passive_personnel), "Pasif veya beklemede duran kartlar")}
              {metricCard("Atanmış Şube", String(dashboard.summary.assigned_restaurants), "Kadro içinde görünen aktif atamalar")}
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

            {workspaceFrame(
              "Kayıt Hattı",
              "Yeni personel kartını hızlı aç.",
              "Sahadan gelen yeni kurye ya da saha personeli, ofis tarafında ekstra sürtünme olmadan sisteme eklenebilsin.",
              <PersonnelEntryWorkspace />,
            )}

            {workspaceFrame(
              "Yönetim Hattı",
              "Kartları düzenle, durumları dengele.",
              "Rol, şube, araç modu ve aktiflik değişimleri daha net bir operasyon çerçevesinde görünsün diye bu bölümü daha editoryal bir panele taşıdık.",
              <PersonnelManagementWorkspace />,
            )}

            {canViewPlateArea
              ? workspaceFrame(
                  "Plaka Hattı",
                  "Plaka ve motor geçmişini ayrı masada yönet.",
                  "Araç zimmeti, plaka değişimi ve açık motor hattını personel düzenleme akışından ayırıp daha net bir operasyon yüzeyine taşıyoruz.",
                  <PersonnelPlateWorkspace />,
                )
              : null}

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.25fr) minmax(280px, 0.75fr)",
                gap: "18px",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  overflow: "hidden",
                  background:
                    "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))",
                }}
              >
                <div
                  style={{
                    padding: "20px 22px",
                    borderBottom: "1px solid rgba(62,81,107,0.1)",
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.74rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Son Kayitlar
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
                    Son personel hareketleri
                  </h2>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Son açılan ve güncellenen kartları operasyon gözüyle hızlı sekilde tarayabilirsin.
                  </p>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table
                    style={{
                      width: "100%",
                      borderCollapse: "collapse",
                    }}
                  >
                    <thead>
                      <tr
                        style={{
                          textAlign: "left",
                          background: "rgba(239,232,219,0.56)",
                        }}
                      >
                        {[
                          "Kod",
                          "Ad Soyad",
                          "Rol",
                          "Durum",
                          "Şube",
                          ...(canViewPlateArea ? ["Arac"] : []),
                          "Telefon",
                        ].map((header) => (
                          <th
                            key={header}
                            style={{
                              padding: "14px 16px",
                              fontSize: "0.78rem",
                              textTransform: "uppercase",
                              letterSpacing: "0.08em",
                              color: "var(--muted)",
                              fontWeight: 800,
                            }}
                          >
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_entries.map((entry) => (
                        <tr
                          key={entry.id}
                          style={{
                            borderTop: "1px solid rgba(62,81,107,0.08)",
                          }}
                        >
                          <td style={tableCellStyle}>{entry.person_code}</td>
                          <td style={tableCellStyle}>{entry.full_name}</td>
                          <td style={tableCellStyle}>{entry.role}</td>
                          <td style={tableCellStyle}>
                            <span
                              style={{
                                display: "inline-flex",
                                padding: "6px 10px",
                                borderRadius: "999px",
                                background:
                                  entry.status.toLocaleLowerCase("tr-TR").includes("aktif")
                                    ? "rgba(98,165,124,0.14)"
                                    : "rgba(185,116,41,0.12)",
                                color:
                                  entry.status.toLocaleLowerCase("tr-TR").includes("aktif")
                                    ? "#2b6a45"
                                    : "#8f5a1f",
                                fontWeight: 800,
                                fontSize: "0.82rem",
                              }}
                            >
                              {entry.status}
                            </span>
                          </td>
                          <td style={tableCellStyle}>{entry.restaurant_label || "-"}</td>
                          {canViewPlateArea ? <td style={tableCellStyle}>{entry.vehicle_mode || "-"}</td> : null}
                          <td style={tableCellStyle}>{entry.phone || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <div style={{ display: "grid", gap: "18px" }}>
                <article
                  style={{
                    ...paperCardStyle,
                    padding: "22px",
                    background:
                      "linear-gradient(145deg, rgba(255,253,247,0.98), rgba(249,244,235,0.95))",
                    display: "grid",
                    gap: "12px",
                  }}
                >
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.74rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Operasyon Notu
                  </div>
                  <div
                    style={{
                      ...serifTitleStyle,
                      fontSize: "1.8rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Aktif ve pasif dengeyi ekrandan oku.
                  </div>
                  <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                    Buradaki hedef sadece veri görmek değil; sahadaki kadro bosluklarini, atama
                    yoğunluğunu ve kart kalitesini daha hızlı okumak.
                  </div>
                </article>

                <article
                  style={{
                    ...paperCardStyle,
                    padding: "22px",
                    background:
                      "linear-gradient(145deg, rgba(27,43,63,0.98), rgba(43,62,85,0.95))",
                    color: "#fff7ea",
                    display: "grid",
                    gap: "12px",
                  }}
                >
                  <div
                    style={{
                      color: "#f2cf9e",
                      fontWeight: 800,
                      fontSize: "0.74rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    Yorum
                  </div>
                  <div
                    style={{
                      ...serifTitleStyle,
                      fontSize: "1.75rem",
                      lineHeight: 0.96,
                      fontWeight: 700,
                    }}
                  >
                    Kadro paneli artık yalnızca form değil, karar yüzeyi.
                  </div>
                  <div style={{ color: "rgba(255,247,234,0.72)", lineHeight: 1.75 }}>
                    Bu dilin amaci formlari daha guzel gostermekten ote, ofisin günlük insan ve saha
                    planlama ritmini ekranda daha net hissettirmek.
                  </div>
                </article>
              </div>
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}

const tableCellStyle = {
  padding: "14px 16px",
  fontSize: "0.95rem",
  color: "var(--text)",
} as const;
