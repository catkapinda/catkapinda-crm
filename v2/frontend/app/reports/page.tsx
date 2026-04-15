"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type ReportsDashboard = {
  module: string;
  status: string;
  month_options: string[];
  selected_month: string | null;
  summary: {
    selected_month: string;
    restaurant_count: number;
    courier_count: number;
    total_hours: number;
    total_packages: number;
    total_revenue: number;
    total_personnel_cost: number;
    gross_profit: number;
    side_income_net: number;
  } | null;
  invoice_entries: Array<{
    restaurant: string;
    pricing_model: string;
    total_hours: number;
    total_packages: number;
    net_invoice: number;
    gross_invoice: number;
  }>;
  cost_entries: Array<{
    personnel: string;
    role: string;
    total_hours: number;
    total_packages: number;
    total_deductions: number;
    net_cost: number;
    cost_model: string;
  }>;
  model_breakdown: Array<{
    pricing_model: string;
    restaurant_count: number;
    total_hours: number;
    total_packages: number;
    gross_invoice: number;
  }>;
  top_restaurants: Array<{
    restaurant: string;
    pricing_model: string;
    total_hours: number;
    total_packages: number;
    gross_invoice: number;
  }>;
  top_couriers: Array<{
    personnel: string;
    role: string;
    total_hours: number;
    total_deductions: number;
    net_cost: number;
    cost_model: string;
  }>;
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function formatMoney(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value || 0);
}

function metricCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        padding: "20px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
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
          marginTop: "12px",
          fontSize: "1.9rem",
          fontWeight: 900,
          letterSpacing: "-0.05em",
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "8px",
          color: "var(--muted)",
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
          fontSize: "1.5rem",
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

function tableHeaderCell(label: string) {
  return (
    <th
      key={label}
      style={{
        textAlign: "left",
        padding: "14px 16px",
        fontSize: "0.82rem",
        color: "var(--muted)",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        fontWeight: 800,
        borderBottom: "1px solid var(--line)",
        background: "rgba(245, 248, 255, 0.9)",
        position: "sticky",
        top: 0,
        zIndex: 1,
      }}
    >
      {label}
    </th>
  );
}

function tableCell(value: string, align: "left" | "right" = "left", muted = false) {
  return (
    <td
      style={{
        padding: "14px 16px",
        borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
        color: muted ? "var(--muted)" : "var(--text)",
        textAlign: align,
        whiteSpace: "nowrap",
      }}
    >
      {value}
    </td>
  );
}

function ScrollCard({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      style={{
        borderRadius: "24px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        overflow: "hidden",
        boxShadow: "0 18px 44px rgba(20, 39, 67, 0.05)",
      }}
    >
      <div
        style={{
          padding: "18px 20px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{title}</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>{subtitle}</p>
        </div>
        {actions}
      </div>
      <div
        style={{
          maxHeight: "520px",
          overflow: "auto",
        }}
      >
        {children}
      </div>
    </section>
  );
}

export default function ReportsPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<ReportsDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [invoiceQuery, setInvoiceQuery] = useState("");
  const [costQuery, setCostQuery] = useState("");

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
        const query = selectedMonth ? `?month=${encodeURIComponent(selectedMonth)}` : "";
        const response = await apiFetch(`/reports/dashboard${query}`);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as ReportsDashboard;
        if (active) {
          setDashboard(payload);
          if (!selectedMonth && payload.selected_month) {
            setSelectedMonth(payload.selected_month);
          }
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
  }, [loading, selectedMonth, user]);

  const summaryCards = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }
    return [
      metricCard("Toplam Fatura", formatMoney(dashboard.summary.total_revenue), `${dashboard.summary.selected_month} toplam restoran faturası`),
      metricCard("Kurye Maliyeti", formatMoney(dashboard.summary.total_personnel_cost), "Net kurye maliyeti"),
      metricCard("Brüt Fark", formatMoney(dashboard.summary.gross_profit), "Fatura - kurye maliyeti"),
      metricCard("Yan Gelir", formatMoney(dashboard.summary.side_income_net), "İndirim ve yan gelir toplamı"),
      metricCard("Şube", formatNumber(dashboard.summary.restaurant_count), "Faturalanan restoran sayısı"),
      metricCard("Kurye", formatNumber(dashboard.summary.courier_count), "Maliyet havuzundaki çalışan sayısı"),
    ];
  }, [dashboard]);

  const signalCards = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }
    const revenuePerHour =
      dashboard.summary.total_hours > 0
        ? dashboard.summary.total_revenue / dashboard.summary.total_hours
        : 0;
    const averageCourierCost =
      dashboard.summary.courier_count > 0
        ? dashboard.summary.total_personnel_cost / dashboard.summary.courier_count
        : 0;
    const marginRatio =
      dashboard.summary.total_revenue > 0
        ? (dashboard.summary.gross_profit / dashboard.summary.total_revenue) * 100
        : 0;

    return [
      metricCard("Saat Başına Fatura", formatMoney(revenuePerHour), "Toplam fatura / toplam saat"),
      metricCard("Kurye Başına Maliyet", formatMoney(averageCourierCost), "Net maliyet / kurye"),
      metricCard("Marj", `%${formatNumber(marginRatio, 1)}`, "Brüt fark / toplam fatura"),
    ];
  }, [dashboard]);

  const decisionDeck = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }

    const marginRatio =
      dashboard.summary.total_revenue > 0
        ? (dashboard.summary.gross_profit / dashboard.summary.total_revenue) * 100
        : 0;
    const topRestaurant = dashboard.top_restaurants[0] ?? null;
    const topCourier = dashboard.top_couriers[0] ?? null;
    const topModel = dashboard.model_breakdown[0] ?? null;
    const sideIncomePositive = dashboard.summary.side_income_net >= 0;

    return [
      {
        eyebrow: "Ayin Odagi",
        title:
          marginRatio >= 18
            ? "Marj resmi saglam gorunuyor."
            : marginRatio >= 10
              ? "Marj korunuyor ama dikkat istiyor."
              : "Marj alarm seviyesine yakin.",
        body: `${dashboard.summary.selected_month} doneminde brut fark ${formatMoney(dashboard.summary.gross_profit)} ve marj %${formatNumber(marginRatio, 1)} seviyesinde.`,
        tone: marginRatio >= 18 ? "ink" : "accent",
      },
      {
        eyebrow: "En Guclu Restoran",
        title: topRestaurant ? topRestaurant.restaurant : "Restoran sinyali henuz yok.",
        body: topRestaurant
          ? `${topRestaurant.pricing_model} modeli ile ${formatMoney(topRestaurant.gross_invoice)} fatura uretiyor; ${formatNumber(topRestaurant.total_hours, 1)} saat ve ${formatNumber(topRestaurant.total_packages)} paket hacmi tasiyor.`
          : "Ilk restoran sinyali geldikce bu kart ilgili ciro hareketini one cikaracak.",
        tone: "paper",
      },
      {
        eyebrow: sideIncomePositive ? "Denge Katkisi" : "Risk Alani",
        title: topCourier ? topCourier.personnel : "Maliyet lideri henuz yok.",
        body: topCourier
          ? `${topCourier.role} rolunde ${formatMoney(topCourier.net_cost)} net maliyet tasiyor. ${formatMoney(topCourier.total_deductions)} kesinti etkisiyle birlikte ${
              topModel ? `${topModel.pricing_model} modeli ayin ana hacmini surukluyor.` : "model dagilimi bu maliyeti okumakta kritik."
            }`
          : sideIncomePositive
            ? `Yan gelir dengesi ${formatMoney(dashboard.summary.side_income_net)} seviyesinde. Kesinti ve ek gelirler genel resmi su anda destekliyor.`
            : `Yan gelir dengesi ${formatMoney(dashboard.summary.side_income_net)} seviyesinde. Kesinti ve ek gelir tarafini daha yakindan izlemek gerekiyor.`,
        tone: sideIncomePositive ? "paper" : "accent",
      },
    ] as const;
  }, [dashboard]);

  const filteredInvoiceEntries = useMemo(() => {
    const rows = dashboard?.invoice_entries ?? [];
    const query = invoiceQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.restaurant} ${row.pricing_model}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.invoice_entries, invoiceQuery]);

  const filteredCostEntries = useMemo(() => {
    const rows = dashboard?.cost_entries ?? [];
    const query = costQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.personnel} ${row.role} ${row.cost_model}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.cost_entries, costQuery]);

  return (
    <AppShell activeItem="Raporlar">
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
                Karlilik ve Rapor
              </div>
              <div style={{ display: "grid", gap: "10px", maxWidth: "72ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(2.2rem, 4vw, 3.7rem)",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Aylik resmi yalnizca okumuyor, artik yonlendiriyoruz.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "72ch",
                    color: "var(--muted)",
                    fontSize: "1.02rem",
                    lineHeight: 1.78,
                  }}
                >
                  Fatura, maliyet, marj ve model dagilimlarini ayni editorial yuzeyde
                  toplayip hangi hattin iyi gittigini, hangi alanin dikkat istedigini
                  daha hizli gormeyi hedefliyoruz.
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
                  Karar katmani aktif
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
                  Fatura ve maliyet ayni satirda
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
                      Rapor Donemi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {(dashboard?.summary?.selected_month ?? selectedMonth) || "Ay sec"}
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
                    Decision Room
                  </div>
                </div>
                <select
                  id="reports-month"
                  value={selectedMonth}
                  onChange={(event) => setSelectedMonth(event.target.value)}
                  disabled={dashboardLoading || !dashboard?.month_options?.length}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "16px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.06)",
                    color: "#fff7ea",
                    fontWeight: 700,
                  }}
                >
                  {(dashboard?.month_options ?? []).map((month) => (
                    <option key={month} value={month} style={{ color: "#16283b" }}>
                      {month}
                    </option>
                  ))}
                </select>
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
                      Toplam Fatura
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.total_revenue ?? 0)}
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
                      Brut Fark
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.gross_profit ?? 0)}
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
                  Bu yuzeyde once fark ve marja, sonra model dagilimi ile en yuksek
                  fatura ve maliyet tasiyan isimlere bakmak en saglikli okuma sirasini verir.
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
            Rapor verileri yukleniyor...
          </div>
        ) : !dashboard || !dashboard.summary ? (
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
            Rapor servisine su anda erisilemiyor. Backend hazir oldugunda restoran
            faturasi ve kurye maliyeti burada gercek veriden acilacak.
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
              {summaryCards}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "14px",
              }}
            >
              {signalCards}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "14px",
              }}
            >
              {decisionDeck.map((item) => (
                <div key={`${item.eyebrow}-${item.title}`}>
                  {narrativeCard(item)}
                </div>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
                gap: "18px",
              }}
            >
              <ScrollCard
                title="Restoran Faturası"
                subtitle="Şube bazlı toplam saat, paket ve restoran faturası. Liste kendi içinde scroll eder."
                actions={
                  <input
                    value={invoiceQuery}
                    onChange={(event) => setInvoiceQuery(event.target.value)}
                    placeholder="Şube veya model ara"
                    style={{
                      minWidth: "220px",
                      padding: "12px 14px",
                      borderRadius: "14px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.96)",
                      color: "var(--text)",
                    }}
                  />
                }
              >
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                  }}
                >
                  <thead>
                    <tr>
                      {["Şube", "Model", "Saat", "Paket", "KDV Hariç", "KDV Dahil"].map(tableHeaderCell)}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInvoiceEntries.map((row) => (
                      <tr key={`${row.restaurant}-${row.pricing_model}`}>
                        {tableCell(row.restaurant)}
                        {tableCell(row.pricing_model, "left", true)}
                        {tableCell(formatNumber(row.total_hours, 1), "right")}
                        {tableCell(formatNumber(row.total_packages, 0), "right")}
                        {tableCell(formatMoney(row.net_invoice), "right")}
                        {tableCell(formatMoney(row.gross_invoice), "right")}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollCard>

              <ScrollCard
                title="Kurye Maliyeti"
                subtitle="Personel bazlı saat, paket, kesinti ve net maliyet görünümü. Liste kendi içinde scroll eder."
                actions={
                  <input
                    value={costQuery}
                    onChange={(event) => setCostQuery(event.target.value)}
                    placeholder="Personel veya rol ara"
                    style={{
                      minWidth: "220px",
                      padding: "12px 14px",
                      borderRadius: "14px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.96)",
                      color: "var(--text)",
                    }}
                  />
                }
              >
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                  }}
                >
                  <thead>
                    <tr>
                      {["Personel", "Rol", "Saat", "Paket", "Kesinti", "Net Maliyet"].map(tableHeaderCell)}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCostEntries.map((row) => (
                      <tr key={`${row.personnel}-${row.role}`}>
                        {tableCell(row.personnel)}
                        {tableCell(row.role, "left", true)}
                        {tableCell(formatNumber(row.total_hours, 1), "right")}
                        {tableCell(formatNumber(row.total_packages, 0), "right")}
                        {tableCell(formatMoney(row.total_deductions), "right")}
                        {tableCell(formatMoney(row.net_cost), "right")}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollCard>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "18px",
              }}
            >
              <ScrollCard
                title="Model Dağılımı"
                subtitle="Aynı ayda hangi anlaşma modelinin ne kadar hacim ürettiğini tek bakışta izle."
              >
                <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                  {dashboard.model_breakdown.map((row) => (
                    <article
                      key={row.pricing_model}
                      style={{
                        display: "grid",
                        gap: "8px",
                        padding: "14px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                        <strong>{row.pricing_model}</strong>
                        <span style={{ color: "var(--muted)" }}>{formatMoney(row.gross_invoice)}</span>
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        {formatNumber(row.restaurant_count)} şube • {formatNumber(row.total_hours, 1)} saat • {formatNumber(row.total_packages, 0)} paket
                      </div>
                    </article>
                  ))}
                </div>
              </ScrollCard>

              <ScrollCard
                title="En Yüksek Fatura Şubeler"
                subtitle="Ay içindeki en büyük restoran faturalarını hızlıca kontrol et."
              >
                <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                  {dashboard.top_restaurants.map((row) => (
                    <article
                      key={`${row.restaurant}-${row.pricing_model}`}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "14px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <strong>{row.restaurant}</strong>
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{row.pricing_model}</div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.92rem",
                        }}
                      >
                        <span>{formatNumber(row.total_hours, 1)} saat • {formatNumber(row.total_packages, 0)} paket</span>
                        <strong style={{ color: "var(--text)" }}>{formatMoney(row.gross_invoice)}</strong>
                      </div>
                    </article>
                  ))}
                </div>
              </ScrollCard>

              <ScrollCard
                title="En Yüksek Maliyetli Kuryeler"
                subtitle="Net maliyeti en yüksek personelleri ve kesinti etkisini bir arada gör."
              >
                <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                  {dashboard.top_couriers.map((row) => (
                    <article
                      key={`${row.personnel}-${row.role}`}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "14px",
                        borderRadius: "18px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <strong>{row.personnel}</strong>
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        {row.role} • {row.cost_model}
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.92rem",
                        }}
                      >
                        <span>{formatNumber(row.total_hours, 1)} saat • {formatMoney(row.total_deductions)} kesinti</span>
                        <strong style={{ color: "var(--text)" }}>{formatMoney(row.net_cost)}</strong>
                      </div>
                    </article>
                  ))}
                </div>
              </ScrollCard>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
