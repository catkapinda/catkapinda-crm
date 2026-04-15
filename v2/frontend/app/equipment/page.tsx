"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { EquipmentEntryWorkspace } from "../../components/equipment/equipment-entry-workspace";
import { EquipmentManagementWorkspace } from "../../components/equipment/equipment-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type EquipmentDashboard = {
  module: string;
  status: string;
  summary: {
    total_issues: number;
    this_month_issues: number;
    installment_rows: number;
    total_box_returns: number;
    total_box_payout: number;
    distinct_items: number;
  };
  recent_issues: Array<{
    id: number;
    personnel_label: string;
    issue_date: string;
    item_name: string;
    quantity: number;
    total_sale: number;
    sale_type: string;
    is_auto_record: boolean;
  }>;
  recent_box_returns: Array<{
    id: number;
    personnel_label: string;
    return_date: string;
    quantity: number;
    condition_status: string;
    payout_amount: number;
    waived: boolean;
  }>;
  installment_entries: Array<{
    deduction_date: string;
    personnel_label: string;
    deduction_type: string;
    amount: number;
    notes: string;
  }>;
  sales_profit: Array<{
    item_name: string;
    sold_qty: number;
    total_cost: number;
    total_sale: number;
    gross_profit: number;
  }>;
  purchase_summary: Array<{
    item_name: string;
    purchased_qty: number;
    purchased_total: number;
    weighted_unit_cost: number;
  }>;
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function metricCard(label: string, value: string, note: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      key={label}
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background:
          tone === "accent"
            ? "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))"
            : "var(--surface-strong)",
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
          ...serifStyle,
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

function listCard(
  title: string,
  subtitle: string,
  items: Array<{ title: string; meta: string; value: string }>,
) {
  return (
    <section
      style={{
        display: "grid",
        gap: "12px",
        padding: "20px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.08rem" }}>{title}</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>{subtitle}</p>
      </div>
      <div
        style={{
          display: "grid",
          gap: "10px",
          maxHeight: "280px",
          overflow: "auto",
          paddingRight: "4px",
        }}
      >
        {items.length ? (
          items.map((item, index) => (
            <article
              key={`${title}-${index}-${item.title}`}
              style={{
                display: "grid",
                gap: "6px",
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.88)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "12px",
                  alignItems: "center",
                }}
              >
                <strong>{item.title}</strong>
                <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>{item.value}</span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{item.meta}</div>
            </article>
          ))
        ) : (
          <div
            style={{
              padding: "18px",
              borderRadius: "16px",
              border: "1px dashed rgba(15, 95, 215, 0.25)",
              color: "var(--muted)",
              background: "rgba(255, 255, 255, 0.72)",
            }}
          >
            Henuz kayit yok.
          </div>
        )}
      </div>
    </section>
  );
}

export default function EquipmentPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<EquipmentDashboard | null>(null);
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
        const response = await apiFetch("/equipment/dashboard?limit=10");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as EquipmentDashboard;
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

    const topIssue = dashboard.recent_issues[0] ?? null;
    const topReturn = dashboard.recent_box_returns[0] ?? null;
    const topProfitItem = dashboard.sales_profit[0] ?? null;
    const installmentPressure =
      dashboard.summary.installment_rows >= Math.max(4, dashboard.summary.this_month_issues);

    return [
      {
        eyebrow: "Zimmet Nabzi",
        title:
          dashboard.summary.this_month_issues >= Math.max(4, dashboard.summary.total_box_returns)
            ? "Bu ay zimmet akisi daha agir."
            : "Zimmet ve iade dengesi korunuyor.",
        body: `${dashboard.summary.this_month_issues} aylik zimmet ve ${dashboard.summary.total_box_returns} box iadesi ayni hatta okunuyor. Bu oran ekipman hareketinin ne kadar tek yone yukseldigini gosterir.`,
        tone:
          dashboard.summary.this_month_issues >= Math.max(4, dashboard.summary.total_box_returns)
            ? "ink"
            : "paper",
      },
      {
        eyebrow: "En Sicak Hareket",
        title: topIssue ? `${topIssue.item_name} / ${topIssue.personnel_label}` : "Ekipman sinyali henuz yok.",
        body: topIssue
          ? `${topIssue.issue_date} tarihli ${topIssue.quantity} adet teslim, ${formatCurrency(topIssue.total_sale)} satis etkisi tasiyor. ${topIssue.sale_type}${topIssue.is_auto_record ? " ve otomatik kaynak" : ""} gorunumuyle onde duruyor.`
          : "Yeni zimmet hareketleri geldikce burada ilk dikkat isteyen ekipman karti gorunecek.",
        tone: "paper",
      },
      {
        eyebrow: installmentPressure ? "Taksit Baskisi" : "Karlilik Sinyali",
        title: installmentPressure
          ? "Taksit satirlari agirlasiyor."
          : topProfitItem
            ? `${topProfitItem.item_name} onde gidiyor.`
            : "Karlilik sinyali henuz yok.",
        body: installmentPressure
          ? `${dashboard.summary.installment_rows} taksit satiri var. Kesinti zincirinin bordroya etkisi daha yakin takip edilmeli.`
          : topProfitItem
            ? `${formatCurrency(topProfitItem.gross_profit)} brut kar ile ${topProfitItem.sold_qty} adet satis tasiyor. Filo ve ekipman hattinda en saglikli urun sinyallerinden biri bu.`
            : "Satis ve alim ozetleri geldikce burada en verimli ekipman kalemi one cikarilacak.",
        tone: installmentPressure ? "accent" : "paper",
      },
    ] as const;
  }, [dashboard]);

  return (
    <AppShell activeItem="Ekipman">
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
                Filo ve Ekipman
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
                  Ekipman akisini sadece takip etmiyor, artik maliyet ve geri donusle birlikte okuyoruz.
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
                  Zimmet, box iadesi, taksit dagilimi ve ekipman karliligini ayni karar
                  katmaninda topluyoruz. Hedefimiz, sadece hareketi degil agirlik merkezi ve
                  finansal etkisini de daha hizli gostermek.
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
                  Zimmet ve iade ayni hatta
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
                  Karlilik ve taksit sinyali acik
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
                      Filo Nabzi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.this_month_issues ?? 0} aylik zimmet
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
                    Equipment Room
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
                      Box Odemesi
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatCurrency(dashboard?.summary.total_box_payout ?? 0)}
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
                      Taksit Satiri
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.installment_rows ?? 0}
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
                  Bu ekranda once zimmet ve iade dengesine, sonra taksit baskisina ve en
                  son satis karliligi sinyaline bakmak en saglikli operasyon okumasini verir.
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
            Ekipman verileri yukleniyor...
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
            Ekipman servisine su anda erisilemiyor. Backend hazir oldugunda bu ekran
            son zimmetleri, box iadelerini ve taksit akislarini gercek veriden gosterecek.
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
              {metricCard("Toplam Zimmet", String(dashboard.summary.total_issues), "Tum teslim zinciri", "accent")}
              {metricCard("Bu Ay Zimmet", String(dashboard.summary.this_month_issues), "Aylik ekipman hareketi")}
              {metricCard("Taksit Satiri", String(dashboard.summary.installment_rows), "Kesinti hattina dusen taksitler")}
              {metricCard("Box Iadesi", String(dashboard.summary.total_box_returns), "Toplam geri alim hareketi")}
              {metricCard("Box Odemesi", formatCurrency(dashboard.summary.total_box_payout), "Iade icin cikan toplam odeme")}
              {metricCard("Ayri Kalem", String(dashboard.summary.distinct_items), "Takip edilen ekipman cesidi")}
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

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
              }}
            >
              {listCard(
                "Son Zimmetler",
                "Operasyona son girilen ekipman teslimleri.",
                dashboard.recent_issues.map((entry) => ({
                  title: `${entry.item_name} · ${entry.personnel_label}`,
                  meta: `${entry.issue_date} · ${entry.quantity} adet · ${entry.sale_type}${entry.is_auto_record ? " · Otomatik" : ""}`,
                  value: formatCurrency(entry.total_sale),
                })),
              )}
              {listCard(
                "Son Box Iadeleri",
                "Geri alinan box ve varsa personele odeme tutari.",
                dashboard.recent_box_returns.map((entry) => ({
                  title: entry.personnel_label,
                  meta: `${entry.return_date} · ${entry.quantity} adet · ${entry.waived ? "Talep edilmedi" : entry.condition_status}`,
                  value: formatCurrency(entry.payout_amount),
                })),
              )}
              {listCard(
                "Taksit Akisi",
                "Zimmetten otomatik olusan deduction satirlari.",
                dashboard.installment_entries.map((entry) => ({
                  title: entry.personnel_label,
                  meta: `${entry.deduction_date} · ${entry.notes || entry.deduction_type}`,
                  value: formatCurrency(entry.amount),
                })),
              )}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
              }}
            >
              {listCard(
                "Satis Karliligi",
                "Satilan ekipmanlarda brüt kar sinyali tasiyan kalemler.",
                dashboard.sales_profit.map((entry) => ({
                  title: entry.item_name,
                  meta: `${entry.sold_qty} adet · Maliyet ${formatCurrency(entry.total_cost)} · Satis ${formatCurrency(entry.total_sale)}`,
                  value: formatCurrency(entry.gross_profit),
                })),
              )}
              {listCard(
                "Alim Ozeti",
                "Satinalma tarafinda hangi kalemin ne maliyetle beslendigini oku.",
                dashboard.purchase_summary.map((entry) => ({
                  title: entry.item_name,
                  meta: `${entry.purchased_qty} adet · Toplam alim ${formatCurrency(entry.purchased_total)}`,
                  value: `${formatCurrency(entry.weighted_unit_cost)}/adet`,
                })),
              )}
            </div>

            <EquipmentEntryWorkspace />
            <EquipmentManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
