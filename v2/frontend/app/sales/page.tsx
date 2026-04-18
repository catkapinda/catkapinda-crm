"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { SalesEntryWorkspace } from "../../components/sales/sales-entry-workspace";
import { SalesManagementWorkspace } from "../../components/sales/sales-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type SalesDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    open_follow_up: number;
    proposal_stage: number;
    won_count: number;
  };
  recent_entries: Array<{
    id: number;
    restaurant_name: string;
    city: string;
    district: string;
    contact_name: string;
    lead_source: string;
    proposed_quote: number;
    pricing_model_label: string;
    status: string;
    assigned_owner: string;
    updated_at: string;
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

function formatTimestamp(value: string) {
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
    hour: "2-digit",
    minute: "2-digit",
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

export default function SalesPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<SalesDashboard | null>(null);
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
        const response = await apiFetch("/sales/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as SalesDashboard;
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

    const proposalRatio =
      dashboard.summary.total_entries > 0
        ? (dashboard.summary.proposal_stage / dashboard.summary.total_entries) * 100
        : 0;
    const winRatio =
      dashboard.summary.total_entries > 0
        ? (dashboard.summary.won_count / dashboard.summary.total_entries) * 100
        : 0;
    const topOpportunity = dashboard.recent_entries[0] ?? null;
    const followUpPressure =
      dashboard.summary.open_follow_up >= Math.max(3, dashboard.summary.won_count);

    return [
      {
        eyebrow: "Fırsat Hattı Sinyali",
        title:
          proposalRatio >= 35
            ? "Teklif havuzu canlı görünüyor."
            : proposalRatio >= 20
              ? "Teklif akışında hareket var."
              : "Teklif hacmi daha fazla itis isteyebilir.",
        body: `${dashboard.summary.total_entries} fırsatın %${proposalRatio.toFixed(1)} kadarı teklif aşamasında. Bu oran fırsat hattının ne kadar olgunlaştığını gösterir.`,
        tone: proposalRatio >= 35 ? "ink" : "accent",
      },
      {
        eyebrow: "En Sıcak Fırsat",
        title: topOpportunity ? topOpportunity.restaurant_name : "Fırsat kaydı henüz yok.",
        body: topOpportunity
          ? `${topOpportunity.city} / ${topOpportunity.district} hattında ${topOpportunity.pricing_model_label} modeliyle ${formatCurrency(topOpportunity.proposed_quote)} teklif seviyesinde. Sorumlu: ${topOpportunity.assigned_owner || "Atanmadı"}.`
          : "Yeni fırsat kayıtları geldikçe bu alan hangi müşterinin daha çok dikkat istediğini öne çıkaracak.",
        tone: "paper",
      },
      {
        eyebrow: followUpPressure ? "Takip Baskısı" : "Kapanış Ritmi",
        title: followUpPressure ? "Açık takip kuyruğu ağırlaşıyor." : "Kazanılan fırsat ritmi korunuyor.",
        body: followUpPressure
          ? `${dashboard.summary.open_follow_up} açık takip var. Ekibin görüşme ve dönüş disiplinini koruması bu haftanın ana ticari riski olabilir.`
          : `${dashboard.summary.won_count} kazanılan fırsat ve %${winRatio.toFixed(1)} dönüşüm, mevcut hattın kapanış tarafında güven verdiğini gösteriyor.`,
        tone: followUpPressure ? "accent" : "paper",
      },
    ] as const;
  }, [dashboard]);

  const workflowDeck = useMemo(
    () => [
      {
        eyebrow: "İlk Adım",
        title: "Yeni fırsatı aç",
        body: "Talep yeri, yetkili bilgisi, teklif modeli ve takip tarihini aynı kartta kaydet.",
        href: "#sales-entry-workspace",
      },
      {
        eyebrow: "İkinci Adım",
        title: "Fırsat havuzunu tara",
        body: "Gelen restoran taleplerini soldaki havuzda süz, sıcak kayıtları hızlıca seç.",
        href: "#sales-management-workspace",
      },
      {
        eyebrow: "Üçüncü Adım",
        title: "Seçili fırsatı güncelle",
        body: "Teklifi, durumu ve takip tarihini aynı panelde yenile; gerekirse kaydı kapat.",
        href: "#sales-management-workspace",
      },
    ],
    [],
  );

  return (
    <AppShell activeItem="Satış">
      <section style={{ display: "grid", gap: "18px" }}>
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
                Ticari Akış
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
                  Fırsat hattını sadece listelemiyor, artık sahneliyoruz.
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
                  Fırsat havuzu, teklif modeli ve takip aksiyonlarını daha canlı bir
                  ticari panelde topluyoruz. Hedefimiz, ekip hangi müşteriye yüklenmeli
                  sorusuna sayfa açılır açılmaz daha iyi cevap verebilmek.
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
                  Fırsat hattı görünürlüğü açık
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
                  Teklif ve takip aynı satırda
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
                      Ticari Nabız
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.total_entries ?? 0} aktif fırsat
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
                    Ticari Oda
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
                      Açık Takip
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.open_follow_up ?? 0}
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
                      Kazanılan
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.won_count ?? 0}
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
                  Satış Kontrolü
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  {dashboard?.summary.open_follow_up ?? 0} açık takip, {dashboard?.summary.proposal_stage ?? 0} teklif aşaması,
                  {dashboard?.summary.won_count ?? 0} kazanılan fırsat.
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
              Eski satış akışındaki yeni kayıt, fırsat havuzu ve güncelleme düzenini aynı sayfada
              görünür kılıyoruz.
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
            Satış verileri yükleniyor...
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
            Satış verileri şu an alınamadı. Bağlantı toparlandığında canlı fırsat
            özeti otomatik yenilenecek.
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
              {metricCard("Toplam Fırsat", String(dashboard.summary.total_entries), "accent")}
              {metricCard("Açık Takip", String(dashboard.summary.open_follow_up))}
              {metricCard("Teklif Aşaması", String(dashboard.summary.proposal_stage))}
              {metricCard("Kazanılan", String(dashboard.summary.won_count))}
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
                  <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Son Ticari Sinyaller</h2>
                  <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.65 }}>
                    Ekip nereye dönmeli sorusunu hızlandıran en güncel müşteri hareketleri.
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
                          {entry.restaurant_name}
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                          {entry.city} / {entry.district}
                        </div>
                      </div>
                      <span
                        style={{
                          display: "inline-flex",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          background: "rgba(185,116,41,0.12)",
                          color: "var(--accent-strong)",
                          fontSize: "0.74rem",
                          fontWeight: 800,
                        }}
                      >
                        {entry.status}
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
                          Teklif
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {formatCurrency(entry.proposed_quote)}
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
                          Sorumlu
                        </div>
                        <div style={{ marginTop: "7px", fontWeight: 900 }}>
                          {entry.assigned_owner || "Atanmadı"}
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
                      <div>
                        {entry.pricing_model_label} • {entry.lead_source}
                      </div>
                      <div>
                        {entry.contact_name} • {formatTimestamp(entry.updated_at)}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section id="sales-entry-workspace" style={{ scrollMarginTop: "110px" }}>
              <SalesEntryWorkspace />
            </section>
            <section id="sales-management-workspace" style={{ scrollMarginTop: "110px" }}>
              <SalesManagementWorkspace />
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
