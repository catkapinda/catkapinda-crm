"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { DeductionEntryWorkspace } from "../../components/deductions/deduction-entry-workspace";
import { DeductionManagementWorkspace } from "../../components/deductions/deduction-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type DeductionsDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    this_month_entries: number;
    manual_entries: number;
    auto_entries: number;
  };
  recent_entries: Array<{
    id: number;
    personnel_id: number;
    personnel_label: string;
    deduction_date: string;
    deduction_type: string;
    type_caption: string;
    amount: number;
    notes: string;
    auto_source_key: string;
    is_auto_record: boolean;
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

function formatMoney(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
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

export default function DeductionsPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<DeductionsDashboard | null>(null);
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
        const response = await apiFetch("/deductions/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
            setDashboardError(
              response.status === 401
                ? "Kesinti verisi için oturum doğrulaması tamamlanamadı. Lütfen bir kez çıkış yapıp yeniden giriş yap."
                : "Kesinti verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene.",
            );
          }
          return;
        }
        const payload = (await response.json()) as DeductionsDashboard;
        if (active) {
          setDashboard(payload);
          setDashboardError("");
        }
      } catch {
        if (active) {
          setDashboard(null);
          setDashboardError(
            "Kesinti verisine ulaşılamıyor. Lütfen bağlantıyı kontrol edip tekrar dene.",
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

  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const totalEntries = dashboard.summary.total_entries || 0;
    const autoRatio = totalEntries > 0 ? (dashboard.summary.auto_entries / totalEntries) * 100 : 0;
    const manualRatio = totalEntries > 0 ? (dashboard.summary.manual_entries / totalEntries) * 100 : 0;
    const topDeduction = dashboard.recent_entries[0] ?? null;
    const autoDominant = dashboard.summary.auto_entries >= dashboard.summary.manual_entries;

    return [
      {
        eyebrow: "Kayıt Dengesi",
        title: autoDominant ? "Otomatik kayıtlar önde." : "Manuel kayıtlar önde.",
        body: `${dashboard.summary.total_entries} kaydın %${autoRatio.toFixed(1)} otomatik, %${manualRatio.toFixed(1)} manuel.`,
        tone: autoDominant ? "ink" : "accent",
      },
      {
        eyebrow: "En Sıcak Kesinti",
        title: topDeduction ? topDeduction.personnel_label : "Son kesinti bulunmuyor.",
        body: topDeduction
          ? `${topDeduction.type_caption} türünde ${formatMoney(topDeduction.amount)} kayıt var. ${formatDate(topDeduction.deduction_date)} tarihli bu hareket ${
              topDeduction.is_auto_record ? "otomatik" : "manuel"
            } kaynaklı.`
          : "Son kesinti hareketi burada görünecek.",
        tone: "paper",
      },
      {
        eyebrow: "Bu Ayın Baskı Noktası",
        title:
          dashboard.summary.this_month_entries >= Math.max(6, dashboard.summary.manual_entries)
            ? "Bu ay kesinti hacmi yüksek."
            : "Bu ay kesinti hacmi dengeli.",
        body:
          dashboard.summary.this_month_entries >= Math.max(6, dashboard.summary.manual_entries)
            ? `${dashboard.summary.this_month_entries} kayıt bu ay oluştu. Bordro kapanışı öncesi kontrol edilmesi gereken yoğunluk var.`
            : `${dashboard.summary.this_month_entries} kayıt bu ay oluştu. Akış şu an dengeli görünüyor.`,
        tone:
          dashboard.summary.this_month_entries >= Math.max(6, dashboard.summary.manual_entries)
            ? "accent"
            : "paper",
      },
    ] as const;
  }, [dashboard]);

  return (
    <AppShell activeItem="Kesintiler">
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
                Kesintiler
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
                  Kesinti yönetimi
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
                  Manuel ve otomatik kesinti kayıtlarını aynı ekrandan takip et ve düzenle.
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
                  Manuel ve otomatik kayıtlar
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
                  Bordro öncesi kontrol
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
                      Aylık Durum
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.this_month_entries ?? 0} aylık hareket
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
                    Kesintiler
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
                      Manuel
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.manual_entries ?? 0}
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
                      Otomatik
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.auto_entries ?? 0}
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
                  Okuma Notu
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  Bu ekranda önce manuel ve otomatik dağılıma, sonra aylık yoğunluğa bak.
                </div>
              </article>
            </div>
          </div>
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
            Kesinti paneli yükleniyor...
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
            {dashboardError ||
              "Kesinti verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene."}
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
              {metricCard("Toplam Kayıt", String(dashboard.summary.total_entries), "accent")}
              {metricCard("Bu Ay", String(dashboard.summary.this_month_entries))}
              {metricCard("Manuel", String(dashboard.summary.manual_entries))}
              {metricCard("Otomatik", String(dashboard.summary.auto_entries))}
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
                  <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Son Kesinti Sinyalleri</h2>
                  <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.65 }}>
                    Son kesinti kayıtları burada listelenir.
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
                          {entry.personnel_label}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                          {entry.type_caption}
                        </div>
                      </div>
                      <span
                        style={{
                          display: "inline-flex",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          background: entry.is_auto_record
                            ? "rgba(15,95,215,0.08)"
                            : "rgba(185,116,41,0.12)",
                          color: entry.is_auto_record ? "#0f5fd7" : "var(--accent-strong)",
                          fontSize: "0.74rem",
                          fontWeight: 800,
                        }}
                      >
                        {entry.is_auto_record ? "Otomatik" : "Manuel"}
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
                          Tutar
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {formatMoney(entry.amount)}
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
                          Tarih
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {formatDate(entry.deduction_date)}
                        </div>
                      </div>
                    </div>

                    <div style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.65 }}>
                      {entry.notes || (entry.auto_source_key ? `Kaynak: ${entry.auto_source_key}` : "Ek not bulunmuyor.")}
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <DeductionEntryWorkspace />
            <DeductionManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
