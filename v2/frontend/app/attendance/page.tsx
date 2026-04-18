"use client";

import { useEffect, useMemo, useState } from "react";

import { AttendanceBulkWorkspace } from "../../components/attendance/attendance-bulk-workspace";
import { AttendanceEntryWorkspace } from "../../components/attendance/attendance-entry-workspace";
import { AttendanceManagementWorkspace } from "../../components/attendance/attendance-management-workspace";
import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type AttendanceDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    today_entries: number;
    month_entries: number;
    active_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    entry_date: string;
    restaurant: string;
    employee_name: string;
    entry_mode: string;
    absence_reason: string;
    coverage_type: string;
    worked_hours: number;
    package_count: number;
    monthly_invoice_amount: number;
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
  child: React.ReactNode,
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
      <div
        style={{
          display: "grid",
          gap: "8px",
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

export default function AttendancePage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<AttendanceDashboard | null>(null);
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
        const response = await apiFetch("/attendance/dashboard?limit=14");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
            setDashboardError(
              response.status === 401
                ? "Puantaj verisi için oturum doğrulaması tamamlanamadı. Lütfen bir kez çıkış yapıp yeniden giriş yap."
                : "Puantaj verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene.",
            );
          }
          return;
        }
        const payload = (await response.json()) as AttendanceDashboard;
        if (active) {
          setDashboard(payload);
          setDashboardError("");
        }
      } catch {
        if (active) {
          setDashboard(null);
          setDashboardError(
            "Puantaj verisine ulaşılamıyor. Lütfen bağlantıyı kontrol edip tekrar dene.",
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

  const modeBreakdown = useMemo(() => {
    const rows = dashboard?.recent_entries ?? [];
    const counts = new Map<string, number>();
    for (const row of rows) {
      counts.set(row.entry_mode, (counts.get(row.entry_mode) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, 4);
  }, [dashboard?.recent_entries]);

  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const todayRatio =
      dashboard.summary.month_entries > 0
        ? (dashboard.summary.today_entries / dashboard.summary.month_entries) * 100
        : 0;
    const topEntry = dashboard.recent_entries[0] ?? null;
    const dominantMode = modeBreakdown[0] ?? null;
    const todayPressure =
      dashboard.summary.today_entries >= Math.max(6, Math.ceil(dashboard.summary.active_restaurants * 1.5));

    return [
      {
        eyebrow: "Günlük Nabız",
        title: todayPressure ? "Bugün giriş yoğunluğu yüksek." : "Bugün giriş akışı dengeli.",
        body: `${dashboard.summary.today_entries} kayıt bugün açıldı. Bu değer, aylık toplamın %${todayRatio.toFixed(1)} kısmını oluşturuyor.`,
        tone: todayPressure ? "accent" : "ink",
      },
      {
        eyebrow: "En Sıcak Hareket",
        title: topEntry ? topEntry.restaurant : "Son kayıt bulunmuyor.",
        body: topEntry
          ? `${topEntry.employee_name || "Atanmamış personel"} için ${topEntry.entry_mode} kaydı var. ${topEntry.worked_hours.toFixed(1)} saat, ${topEntry.package_count.toFixed(0)} paket ve ${formatCurrency(topEntry.monthly_invoice_amount)} tutar görünüyor.`
          : "Yeni puantaj kayıtları burada görünecek.",
        tone: "paper",
      },
      {
        eyebrow: "Akış İmzası",
        title: dominantMode ? `${dominantMode[0]} önde gidiyor.` : "Kayıt dağılımı oluşmadı.",
        body: dominantMode
          ? `Son kayıtlar içinde ${dominantMode[0]} modu ${dominantMode[1]} adet ile öne çıkıyor.`
          : "Kayıt türü dağılımı burada görünecek.",
        tone: "paper",
      },
    ] as const;
  }, [dashboard, modeBreakdown]);

  return (
    <AppShell activeItem="Puantaj">
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
                letterSpacing: "0.09em",
                textTransform: "uppercase",
              }}
            >
              Puantaj
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: "20px 0 14px",
                fontSize: "clamp(2.6rem, 5vw, 4.3rem)",
                lineHeight: 0.92,
                maxWidth: "11ch",
                fontWeight: 700,
              }}
            >
              Puantaj yönetimi
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "68ch",
                color: "rgba(255, 247, 234, 0.78)",
                lineHeight: 1.75,
                fontSize: "1rem",
              }}
            >
              Günlük giriş, toplu giriş, düzeltme ve son kayıtlar aynı ekranda yönetilir.
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
                ["Toplu işlem", "Ay filtresiyle toplu puantaj temizliği yönetim alanında."],
                ["Gün sonu", "Vardiya düzeltmeleri tek ekranda tamamlanır."],
                ["Odak", "Kayıt, düzeltme ve liste aynı akışta tutulur."],
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
                Günlük Durum
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
                {dashboard
                  ? dashboard.summary.today_entries > Math.max(6, Math.ceil(dashboard.summary.active_restaurants * 1.5))
                    ? "Bugün puantaj hareketi yüksek."
                    : "Bugün puantaj akışı dengeli."
                  : "Günlük puantaj akışı burada yönetilir."}
              </div>
              <p
                style={{
                  margin: "12px 0 0",
                  color: "var(--muted)",
                  lineHeight: 1.7,
                  fontSize: "0.96rem",
                }}
              >
                {dashboard
                  ? `Bugün ${dashboard.summary.today_entries} hareket, ${dashboard.summary.active_restaurants} aktif şube ve ${dashboard.summary.month_entries} aylık toplamla akışın hızını daha erken okuyabiliyoruz.`
                  : "Önce kayıt oluştur, sonra düzeltme ve toplu temizlik işlemlerini tamamla."}
              </p>
            </article>

            <article
              style={{
                ...paperCardStyle,
                padding: "24px",
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
                Son Akis Tipleri
              </div>
              <div
                style={{
                  marginTop: "16px",
                  display: "grid",
                  gap: "10px",
                }}
              >
                {modeBreakdown.length ? (
                  modeBreakdown.map(([label, count]) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "14px",
                        padding: "14px 16px",
                        borderRadius: "18px",
                        background: "rgba(24, 40, 59, 0.05)",
                        border: "1px solid rgba(24, 40, 59, 0.08)",
                      }}
                    >
                      <span style={{ fontWeight: 800 }}>{label}</span>
                      <span style={{ color: "var(--accent-strong)", fontWeight: 900 }}>{count}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                    Son hareket verisi geldiğinde akış kırılımı burada belirecek.
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
            Puantaj paneli yükleniyor...
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
              "Puantaj verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene."}
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
              {metricCard(
                "Toplam Kayıt",
                String(dashboard.summary.total_entries),
                "Sistemde geriye donuk tutulan tüm puantaj omurgasi.",
              )}
              {metricCard(
                "Bugün",
                String(dashboard.summary.today_entries),
                "Bugün açılan vardiya ve devam hareketleri.",
              )}
              {metricCard(
                "Bu Ay",
                String(dashboard.summary.month_entries),
                "Aylık yoğunluk, temizlik ve kontrol hacmi.",
              )}
              {metricCard(
                "Aktif Şube",
                String(dashboard.summary.active_restaurants),
                "Bugün operasyon akışı beklenen aktif şubeler.",
              )}
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
              "Giriş",
              "Yeni puantaj kaydı",
              "Günlük puantaj kaydını bu alandan oluştur.",
              <AttendanceEntryWorkspace />,
            )}

            {workspaceFrame(
              "Toplu Giriş",
              "Şube bazlı puantaj",
              "Aynı şubedeki birden fazla kayıt için toplu puantaj gir.",
              <AttendanceBulkWorkspace />,
            )}

            {workspaceFrame(
              "Yönetim",
              "Kayıt düzeltme ve temizlik",
              "Kayıtları düzenle, seçili kayıtları sil veya ay bazlı temizlik yap.",
              <AttendanceManagementWorkspace />,
            )}

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "18px",
              }}
            >
              <article
                style={{
                  ...paperCardStyle,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "22px 22px 16px",
                    borderBottom: "1px solid var(--line)",
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
                    Son Puantaj Hareketleri
                  </div>
                  <h2
                    style={{
                      ...serifTitleStyle,
                      margin: "10px 0 6px",
                      fontSize: "2rem",
                      lineHeight: 0.98,
                      fontWeight: 700,
                    }}
                  >
                    Akış masası
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      lineHeight: 1.7,
                    }}
                  >
                    Son kayıtlar artık daha sakin ama daha karakterli bir tabloda akıyor.
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
                          background: "rgba(24, 40, 59, 0.05)",
                        }}
                      >
                        {["Tarih", "Şube", "Çalışan", "Akis", "Saat", "Paket"].map((header) => (
                          <th
                            key={header}
                            style={{
                              padding: "15px 16px",
                              fontSize: "0.76rem",
                              textTransform: "uppercase",
                              letterSpacing: "0.08em",
                              color: "var(--muted)",
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
                            borderTop: "1px solid rgba(24, 40, 59, 0.08)",
                          }}
                        >
                          <td style={tableCellStyle}>{entry.entry_date}</td>
                          <td style={tableCellStyle}>{entry.restaurant}</td>
                          <td style={tableCellStyle}>{entry.employee_name || "-"}</td>
                          <td style={tableCellStyle}>
                            <span
                              style={{
                                display: "inline-flex",
                                padding: "6px 10px",
                                borderRadius: "999px",
                                background:
                                  entry.entry_mode === "Restoran Kuryesi"
                                    ? "rgba(24, 40, 59, 0.08)"
                                    : "rgba(185, 116, 41, 0.12)",
                                color:
                                  entry.entry_mode === "Restoran Kuryesi"
                                    ? "var(--text)"
                                    : "var(--accent-strong)",
                                fontWeight: 800,
                                fontSize: "0.78rem",
                              }}
                            >
                              {entry.entry_mode}
                            </span>
                          </td>
                          <td style={tableCellStyle}>{entry.worked_hours.toFixed(1)}</td>
                          <td style={tableCellStyle}>{entry.package_count.toFixed(0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <aside
                style={{
                  ...paperCardStyle,
                  padding: "22px",
                  display: "grid",
                  gap: "14px",
                  alignSelf: "start",
                  background:
                    "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))",
                }}
              >
                <div
                  style={{
                    color: "var(--muted)",
                    fontWeight: 800,
                    fontSize: "0.74rem",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  Operasyon Notlari
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
                  Bugün dikkat edilmesi gerekenler
                </h2>
                <div
                  style={{
                    display: "grid",
                    gap: "10px",
                  }}
                >
                  {[
                    `Bugün ${dashboard.summary.today_entries} kayıt açıldı.`,
                    `Bu ay toplam ${dashboard.summary.month_entries} puantaj satırı birikti.`,
                    "Ay bazli toplu silme yalnızca filtreli alan için görünür durumda.",
                    "Son hareketler paneli hızlı vardiya temizliği için referans akışı sunuyor.",
                  ].map((item) => (
                    <div
                      key={item}
                      style={{
                        padding: "14px 14px 12px",
                        borderRadius: "18px",
                        border: "1px solid rgba(24, 40, 59, 0.08)",
                        background: "rgba(24, 40, 59, 0.04)",
                        color: "var(--text)",
                        lineHeight: 1.65,
                      }}
                    >
                      {item}
                    </div>
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

const tableCellStyle = {
  padding: "15px 16px",
  fontSize: "0.95rem",
  color: "var(--text)",
};
