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
  profit_entries: Array<{
    restaurant: string;
    pricing_model: string;
    total_hours: number;
    total_packages: number;
    net_invoice: number;
    gross_invoice: number;
    direct_personnel_cost: number;
    shared_overhead_cost: number;
    total_personnel_cost: number;
    gross_profit: number;
    profit_margin_percent: number;
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
  coverage: {
    covered_restaurant_count: number;
    operational_restaurant_count: number;
  };
  shared_overhead_entries: Array<{
    personnel: string;
    role: string;
    gross_cost: number;
    total_deductions: number;
    net_cost: number;
    allocated_restaurant_count: number;
    share_per_restaurant: number;
  }>;
  distribution_entries: Array<{
    restaurant: string;
    personnel: string;
    role: string;
    total_hours: number;
    total_packages: number;
    allocated_cost: number;
    allocation_source: string;
  }>;
  side_income_entries: Array<{
    item: string;
    revenue: number;
    cost: number;
    net_profit: number;
  }>;
  side_income_snapshot: {
    fuel_reflection_amount: number;
    company_fuel_reflection_amount: number;
    utts_fuel_discount_amount: number;
    partner_card_discount_amount: number;
  };
};

const EMPTY_REPORTS_COVERAGE = {
  covered_restaurant_count: 0,
  operational_restaurant_count: 0,
} as const;

const EMPTY_REPORTS_SIDE_INCOME_SNAPSHOT = {
  fuel_reflection_amount: 0,
  company_fuel_reflection_amount: 0,
  utts_fuel_discount_amount: 0,
  partner_card_discount_amount: 0,
} as const;

function normalizeReportsDashboard(payload: Partial<ReportsDashboard>): ReportsDashboard {
  return {
    module: payload.module ?? "reports",
    status: payload.status ?? "active",
    month_options: payload.month_options ?? [],
    selected_month: payload.selected_month ?? null,
    summary: payload.summary ?? null,
    invoice_entries: payload.invoice_entries ?? [],
    cost_entries: payload.cost_entries ?? [],
    profit_entries: payload.profit_entries ?? [],
    model_breakdown: payload.model_breakdown ?? [],
    top_restaurants: payload.top_restaurants ?? [],
    top_couriers: payload.top_couriers ?? [],
    coverage: payload.coverage ?? EMPTY_REPORTS_COVERAGE,
    shared_overhead_entries: payload.shared_overhead_entries ?? [],
    distribution_entries: payload.distribution_entries ?? [],
    side_income_entries: payload.side_income_entries ?? [],
    side_income_snapshot:
      payload.side_income_snapshot ?? EMPTY_REPORTS_SIDE_INCOME_SNAPSHOT,
  };
}

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

function displayPricingModel(value: string) {
  const labels: Record<string, string> = {
    hourly_plus_package: "Saat + Paket",
    threshold_package: "Eşikli Paket",
    hourly_only: "Sadece Saatlik",
    fixed_monthly: "Sabit Aylık Ücret",
  };
  return labels[value] ?? value;
}

function triggerBrowserDownload(blob: Blob, fileName: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function metricCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        padding: "14px 14px 12px",
        borderRadius: "18px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 12px 28px rgba(20, 39, 67, 0.05)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.66rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "6px",
          fontSize: "1.38rem",
          fontWeight: 900,
          letterSpacing: "-0.05em",
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "6px",
          color: "var(--muted)",
          fontSize: "0.82rem",
          lineHeight: 1.45,
        }}
      >
        {note}
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
        borderRadius: "18px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        overflow: "hidden",
        boxShadow: "0 12px 28px rgba(20, 39, 67, 0.05)",
      }}
    >
      <div
        style={{
          padding: "14px 16px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "0.98rem" }}>{title}</h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", lineHeight: 1.5, fontSize: "0.82rem" }}>{subtitle}</p>
        </div>
        {actions}
      </div>
      <div
        style={{
          maxHeight: "380px",
          overflow: "auto",
        }}
      >
        {children}
      </div>
    </section>
  );
}

function ExecutiveReportChart({ dashboard }: { dashboard: ReportsDashboard }) {
  const summary = dashboard.summary;
  if (!summary) {
    return null;
  }

  const topRestaurants = dashboard.top_restaurants.slice(0, 5);
  const maxRestaurantInvoice = Math.max(
    ...topRestaurants.map((item) => item.gross_invoice || 0),
    1,
  );
  const totals = [
    { label: "Fatura", value: summary.total_revenue, color: "rgba(15, 95, 215, 0.92)" },
    { label: "Kurye Maliyeti", value: summary.total_personnel_cost, color: "rgba(185, 116, 41, 0.88)" },
    { label: "Fatura-Kurye Farkı", value: summary.gross_profit, color: "rgba(31, 151, 112, 0.9)" },
  ];
  const maxTotal = Math.max(...totals.map((item) => Math.abs(item.value || 0)), 1);
  const marginPercent = summary.total_revenue
    ? (summary.gross_profit / summary.total_revenue) * 100
    : 0;

  return (
    <section
      style={{
        borderRadius: "24px",
        border: "1px solid rgba(219, 228, 243, 0.86)",
        background:
          "radial-gradient(circle at 12% 20%, rgba(15,95,215,0.12), transparent 30%), linear-gradient(135deg, rgba(255,255,255,0.98), rgba(248,244,236,0.92))",
        boxShadow: "0 22px 58px rgba(20, 39, 67, 0.1)",
        padding: "18px",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: "18px",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "grid", gap: "16px" }}>
        <div>
          <div
            style={{
              color: "var(--accent-strong)",
              fontSize: "0.68rem",
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Finans Nabzı
          </div>
          <h2
            style={{
              ...serifStyle,
              margin: "6px 0 0",
              fontSize: "1.7rem",
              lineHeight: 0.98,
              fontWeight: 700,
            }}
          >
            Restoran faturası, kurye maliyeti ve fark tek grafikte.
          </h2>
        </div>

        <div style={{ display: "grid", gap: "11px" }}>
          {totals.map((item) => {
            const width = Math.max((Math.abs(item.value || 0) / maxTotal) * 100, item.value ? 8 : 0);
            return (
              <div key={item.label} style={{ display: "grid", gap: "6px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", fontSize: "0.86rem" }}>
                  <strong>{item.label}</strong>
                  <span style={{ color: "var(--muted)", fontWeight: 800 }}>{formatMoney(item.value)}</span>
                </div>
                <div
                  style={{
                    height: "18px",
                    borderRadius: "999px",
                    background: "rgba(24,40,59,0.08)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${width}%`,
                      height: "100%",
                      borderRadius: "999px",
                      background: item.color,
                      boxShadow: "0 10px 24px rgba(20,39,67,0.12)",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
            gap: "10px",
          }}
        >
          {[
            ["Marj", `%${formatNumber(marginPercent, 1)}`],
            ["Saat", formatNumber(summary.total_hours, 1)],
            ["Paket", formatNumber(summary.total_packages, 0)],
            ["Yan Gelir", formatMoney(summary.side_income_net)],
          ].map(([label, value]) => (
            <article
              key={label}
              style={{
                padding: "11px 12px",
                borderRadius: "16px",
                border: "1px solid rgba(219, 228, 243, 0.82)",
                background: "rgba(255,255,255,0.72)",
              }}
            >
              <div
                style={{
                  color: "var(--muted)",
                  fontSize: "0.66rem",
                  fontWeight: 900,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                }}
              >
                {label}
              </div>
              <div style={{ marginTop: "5px", fontWeight: 900, fontSize: "1rem" }}>{value}</div>
            </article>
          ))}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gap: "12px",
          padding: "14px",
          borderRadius: "20px",
          background: "rgba(24, 40, 59, 0.96)",
          color: "#fff7ea",
        }}
      >
        <div>
          <div
            style={{
              color: "rgba(255,247,234,0.62)",
              fontSize: "0.66rem",
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            En Yüksek Fatura
          </div>
          <div style={{ marginTop: "5px", fontWeight: 900 }}>
            {topRestaurants.length ? "İlk 5 restoran" : "Restoran faturası bekleniyor"}
          </div>
        </div>

        <div style={{ display: "grid", gap: "10px" }}>
          {topRestaurants.map((item, index) => (
            <div key={`${item.restaurant}-${item.pricing_model}`} style={{ display: "grid", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", fontSize: "0.84rem" }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {index + 1}. {item.restaurant}
                </span>
                <strong>{formatMoney(item.gross_invoice)}</strong>
              </div>
              <div
                style={{
                  height: "10px",
                  borderRadius: "999px",
                  background: "rgba(255,247,234,0.12)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${Math.max((item.gross_invoice / maxRestaurantInvoice) * 100, 6)}%`,
                    height: "100%",
                    borderRadius: "999px",
                    background:
                      "linear-gradient(90deg, rgba(255,247,234,0.95), rgba(222,165,92,0.94))",
                  }}
                />
              </div>
            </div>
          ))}
          {!topRestaurants.length ? (
            <div style={{ color: "rgba(255,247,234,0.66)", lineHeight: 1.55, fontSize: "0.84rem" }}>
              Puantaj ve fiyat modeli geldiğinde restoran fatura sıralaması burada açılacak.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function ReportModelMatrix({
  dashboard,
  coverageGap,
}: {
  dashboard: ReportsDashboard;
  coverageGap: number;
}) {
  const modelRows = dashboard.model_breakdown.slice(0, 6);
  const courierRows = dashboard.top_couriers.slice(0, 5);
  const maxModelInvoice = Math.max(...modelRows.map((row) => row.gross_invoice || 0), 1);
  const maxCourierCost = Math.max(...courierRows.map((row) => row.net_cost || 0), 1);
  const margin =
    dashboard.summary && dashboard.summary.total_revenue > 0
      ? (dashboard.summary.gross_profit / dashboard.summary.total_revenue) * 100
      : 0;

  return (
    <section
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: "12px",
      }}
    >
      <article
        style={{
          borderRadius: "22px",
          border: "1px solid rgba(219, 228, 243, 0.9)",
          background: "rgba(255,255,255,0.9)",
          padding: "16px",
          display: "grid",
          gap: "12px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div
              style={{
                color: "var(--accent-strong)",
                fontSize: "0.66rem",
                fontWeight: 900,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              Model Haritası
            </div>
            <div style={{ marginTop: "5px", fontWeight: 900 }}>
              Fiyat modeli, hacim ve fatura dağılımı
            </div>
          </div>
          <span
            style={{
              padding: "8px 10px",
              borderRadius: "999px",
              background: coverageGap > 0 ? "rgba(185,116,41,0.12)" : "rgba(31,151,112,0.1)",
              color: coverageGap > 0 ? "var(--accent-strong)" : "#167f51",
              fontSize: "0.78rem",
              fontWeight: 900,
            }}
          >
            {coverageGap > 0 ? `${formatNumber(coverageGap)} açık şube` : "Kapsama tam"}
          </span>
        </div>

        <div style={{ display: "grid", gap: "9px" }}>
          {modelRows.length ? (
            modelRows.map((row) => (
              <div
                key={row.pricing_model}
                style={{
                  display: "grid",
                  gap: "7px",
                  padding: "10px 0",
                  borderBottom: "1px solid rgba(24,40,59,0.08)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "12px",
                    fontSize: "0.86rem",
                  }}
                >
                  <strong>{displayPricingModel(row.pricing_model)}</strong>
                  <span style={{ color: "var(--muted)", fontWeight: 800 }}>
                    {formatMoney(row.gross_invoice)}
                  </span>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1fr) auto auto",
                    alignItems: "center",
                    gap: "10px",
                    fontSize: "0.78rem",
                    color: "var(--muted)",
                  }}
                >
                  <div
                    style={{
                      height: "12px",
                      borderRadius: "999px",
                      background: "rgba(24,40,59,0.08)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.max((row.gross_invoice / maxModelInvoice) * 100, 6)}%`,
                        height: "100%",
                        borderRadius: "999px",
                        background:
                          "linear-gradient(90deg, rgba(15,95,215,0.92), rgba(222,165,92,0.9))",
                      }}
                    />
                  </div>
                  <span>{formatNumber(row.restaurant_count)} şube</span>
                  <span>{formatNumber(row.total_packages)} paket</span>
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
              Fiyat modeli dağılımı için bu ay henüz rapor satırı yok.
            </div>
          )}
        </div>
      </article>

      <article
        style={{
          borderRadius: "22px",
          border: "1px solid rgba(24, 40, 59, 0.08)",
          background:
            "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
          color: "#fff7ea",
          padding: "16px",
          display: "grid",
          gap: "12px",
        }}
      >
        <div>
          <div
            style={{
              color: "rgba(255,247,234,0.62)",
              fontSize: "0.66rem",
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Maliyet Liderleri
          </div>
          <div style={{ marginTop: "5px", fontWeight: 900 }}>
            %{formatNumber(margin, 1)} marj ile en yüksek net maliyetler
          </div>
        </div>

        <div style={{ display: "grid", gap: "10px" }}>
          {courierRows.length ? (
            courierRows.map((row) => (
              <div key={`${row.personnel}-${row.role}`} style={{ display: "grid", gap: "6px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "10px",
                    fontSize: "0.84rem",
                  }}
                >
                  <span
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {row.personnel}
                  </span>
                  <strong>{formatMoney(row.net_cost)}</strong>
                </div>
                <div
                  style={{
                    height: "9px",
                    borderRadius: "999px",
                    background: "rgba(255,247,234,0.12)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.max((row.net_cost / maxCourierCost) * 100, 6)}%`,
                      height: "100%",
                      borderRadius: "999px",
                      background:
                        "linear-gradient(90deg, rgba(255,247,234,0.96), rgba(222,165,92,0.9))",
                    }}
                  />
                </div>
                <div style={{ color: "rgba(255,247,234,0.58)", fontSize: "0.76rem" }}>
                  {row.role} · {formatNumber(row.total_hours, 1)} saat
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: "rgba(255,247,234,0.66)", lineHeight: 1.55, fontSize: "0.84rem" }}>
              Kurye maliyeti için bu ay henüz rapor satırı yok.
            </div>
          )}
        </div>
      </article>
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
  const [profitQuery, setProfitQuery] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const [exportError, setExportError] = useState("");

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
        const payload = normalizeReportsDashboard(
          (await response.json()) as Partial<ReportsDashboard>,
        );
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
      metricCard("Fatura-Kurye Farkı", formatMoney(dashboard.summary.gross_profit), "Restoran faturası - kurye maliyeti"),
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
      metricCard("Marj", `%${formatNumber(marginRatio, 1)}`, "Fark / toplam fatura"),
    ];
  }, [dashboard]);

  const coverageGap = useMemo(() => {
    if (!dashboard) {
      return 0;
    }
    return Math.max(
      dashboard.coverage.operational_restaurant_count - dashboard.coverage.covered_restaurant_count,
      0,
    );
  }, [dashboard]);

  const extendedSignalCards = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    const sharedOverheadTotal = dashboard.shared_overhead_entries.reduce(
      (total, entry) => total + entry.net_cost,
      0,
    );
    return [
      metricCard(
        "Kapsanan Şube",
        formatNumber(dashboard.coverage.covered_restaurant_count),
        "Rapor tablosunda satırı olan şube sayısı",
      ),
      metricCard(
        "Operasyon Şubesi",
        formatNumber(dashboard.coverage.operational_restaurant_count),
        "Ay içinde aktif kabul edilen toplam şube",
      ),
      metricCard(
        "Açıkta Kalan",
        formatNumber(coverageGap),
        coverageGap > 0 ? "Henüz faturaya düşmeyen operasyon hacmi" : "Kapsama şu anda tam görünüyor",
      ),
      metricCard(
        "Ortak Operasyon",
        formatMoney(sharedOverheadTotal),
        "Joker ve yönetim desteğinin toplam net yükü",
      ),
      metricCard(
        "UTTS İndirimi",
        formatMoney(dashboard.side_income_snapshot.utts_fuel_discount_amount),
        "Şirket motorundan gelen yakıt avantajı",
      ),
      metricCard(
        "Partner Kartı",
        formatMoney(dashboard.side_income_snapshot.partner_card_discount_amount),
        "Kart indiriminin yan gelire katkısı",
      ),
    ];
  }, [coverageGap, dashboard]);

  const filteredInvoiceEntries = useMemo(() => {
    const rows = dashboard?.invoice_entries ?? [];
    const query = invoiceQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.restaurant} ${displayPricingModel(row.pricing_model)}`.toLocaleLowerCase("tr-TR").includes(query),
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

  const filteredProfitEntries = useMemo(() => {
    const rows = dashboard?.profit_entries ?? [];
    const query = profitQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.restaurant} ${displayPricingModel(row.pricing_model)}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.profit_entries, profitQuery]);

  function downloadInvoiceCsv() {
    if (!filteredInvoiceEntries.length) {
      setExportError("Dışa aktarmak için önce görünür fatura kaydı oluşmalı.");
      setExportMessage("");
      return;
    }
    const headers = ["Şube", "Model", "Toplam Saat", "Toplam Paket", "KDV Hariç", "KDV Dahil"];
    const rows = filteredInvoiceEntries.map((entry) => [
      entry.restaurant,
      displayPricingModel(entry.pricing_model),
      String(entry.total_hours),
      String(entry.total_packages),
      String(entry.net_invoice),
      String(entry.gross_invoice),
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "rapor";
    triggerBrowserDownload(
      new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" }),
      `catkapinda_restoran_faturasi_${month}.csv`,
    );
    setExportError("");
    setExportMessage("Restoran faturası tablosu indirildi.");
  }

  function downloadCostCsv() {
    if (!filteredCostEntries.length) {
      setExportError("Dışa aktarmak için önce görünür maliyet kaydı oluşmalı.");
      setExportMessage("");
      return;
    }
    const headers = ["Personel", "Rol", "Toplam Saat", "Toplam Paket", "Toplam Kesinti", "Net Maliyet", "Maliyet Modeli"];
    const rows = filteredCostEntries.map((entry) => [
      entry.personnel,
      entry.role,
      String(entry.total_hours),
      String(entry.total_packages),
      String(entry.total_deductions),
      String(entry.net_cost),
      entry.cost_model,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "rapor";
    triggerBrowserDownload(
      new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" }),
      `catkapinda_kurye_maliyeti_${month}.csv`,
    );
    setExportError("");
    setExportMessage("Kurye maliyeti tablosu indirildi.");
  }

  function downloadProfitCsv() {
    if (!filteredProfitEntries.length) {
      setExportError("Dışa aktarmak için önce görünür kârlılık satırı oluşmalı.");
      setExportMessage("");
      return;
    }
    const headers = [
      "Şube",
      "Model",
      "Toplam Saat",
      "Toplam Paket",
      "KDV Hariç",
      "KDV Dahil",
      "Doğrudan Kurye Maliyeti",
      "Ortak Operasyon Payı",
      "Toplam Kurye Maliyeti",
      "Fatura-Kurye Farkı",
      "Kâr Marjı",
    ];
    const rows = filteredProfitEntries.map((entry) => [
      entry.restaurant,
      displayPricingModel(entry.pricing_model),
      String(entry.total_hours),
      String(entry.total_packages),
      String(entry.net_invoice),
      String(entry.gross_invoice),
      String(entry.direct_personnel_cost),
      String(entry.shared_overhead_cost),
      String(entry.total_personnel_cost),
      String(entry.gross_profit),
      String(entry.profit_margin_percent),
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "rapor";
    triggerBrowserDownload(
      new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" }),
      `catkapinda_restoran_karliligi_${month}.csv`,
    );
    setExportError("");
    setExportMessage("Restoran kârlılığı tablosu indirildi.");
  }

  return (
    <AppShell activeItem="Raporlar">
      <section
        style={{
          display: "grid",
          gap: "14px",
        }}
      >
        <div
          style={{
            padding: "18px",
            borderRadius: "22px",
            background:
              "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 16px 34px rgba(22, 42, 74, 0.06)",
            display: "grid",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.25fr) minmax(260px, 0.9fr)",
              gap: "12px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "12px",
                alignContent: "start",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
                  padding: "6px 10px",
                  borderRadius: "999px",
                  background: "var(--accent-soft)",
                  color: "var(--accent)",
                  fontSize: "0.68rem",
                  fontWeight: 800,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                }}
              >
                Kârlılık ve Rapor
              </div>
              <div style={{ display: "grid", gap: "8px", maxWidth: "62ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(1.8rem, 3vw, 2.7rem)",
                    lineHeight: 0.94,
                    fontWeight: 700,
                  }}
                >
                  Aylık resmi daha kısa yoldan okuyoruz.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "60ch",
                    color: "var(--muted)",
                    fontSize: "0.86rem",
                    lineHeight: 1.55,
                  }}
                >
                  Fatura, maliyet, marj ve model dağılımını aynı yerde toplayıp iyi giden ve dikkat isteyen alanı hızlıca görüyoruz.
                </p>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "6px 10px",
                    borderRadius: "999px",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.72rem",
                    fontWeight: 800,
                  }}
                >
                  Karar katmanı aktif
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "6px 10px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.72rem",
                    fontWeight: 800,
                  }}
                >
                  Fatura ve maliyet aynı satırda
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gap: "10px",
              }}
            >
              <article
                style={{
                  padding: "14px 14px 12px",
                  borderRadius: "18px",
                  background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "10px",
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
                        fontSize: "0.66rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Rapor Dönemi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.4rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {(dashboard?.summary?.selected_month ?? selectedMonth) || "Ay seç"}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "6px 9px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.72rem",
                      fontWeight: 800,
                    }}
                  >
                    Karar Odası
                  </div>
                </div>
                <select
                  id="reports-month"
                  value={selectedMonth}
                  onChange={(event) => setSelectedMonth(event.target.value)}
                  disabled={dashboardLoading || !dashboard?.month_options?.length}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "14px",
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
                    gap: "8px",
                  }}
                >
                  <div
                    style={{
                      padding: "10px 10px 9px",
                      borderRadius: "14px",
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.64rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Toplam Fatura
                    </div>
                    <div style={{ marginTop: "6px", fontSize: "0.96rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.total_revenue ?? 0)}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "10px 10px 9px",
                      borderRadius: "14px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.64rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Fatura-Kurye Farkı
                    </div>
                    <div style={{ marginTop: "6px", fontSize: "0.96rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.gross_profit ?? 0)}
                    </div>
                  </div>
                </div>
              </article>

              <article
                style={{
                  padding: "14px 14px 12px",
                  borderRadius: "18px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "10px",
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
                  Finans Kontrolü
                </div>
                <div style={{ display: "grid", gap: "8px" }}>
                  {[
                    [
                      "Marj",
                      dashboard?.summary?.total_revenue
                        ? `%${formatNumber(((dashboard.summary.gross_profit || 0) / dashboard.summary.total_revenue) * 100, 1)}`
                        : "%0",
                    ],
                    ["Saat", formatNumber(dashboard?.summary?.total_hours ?? 0, 1)],
                    ["Paket", formatNumber(dashboard?.summary?.total_packages ?? 0)],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "12px",
                        paddingBottom: "7px",
                        borderBottom: "1px solid rgba(24,40,59,0.08)",
                        fontSize: "0.84rem",
                      }}
                    >
                      <span style={{ color: "var(--muted)", fontWeight: 800 }}>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </article>
            </div>
          </div>

          <section
            style={{
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.78)",
              padding: "14px 16px",
              display: "grid",
              gap: "10px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "16px",
                alignItems: "start",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: "6px" }}>
                <div
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.66rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Dışa Aktarım
                </div>
                <div style={{ fontSize: "0.9rem", fontWeight: 800 }}>
                  Filtrelenmiş rapor tablolarını tek tıkla dışa aktar.
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={downloadInvoiceCsv}
                  disabled={!filteredInvoiceEntries.length}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    border: "1px solid rgba(15,95,215,0.15)",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontWeight: 800,
                    cursor: filteredInvoiceEntries.length ? "pointer" : "not-allowed",
                    opacity: filteredInvoiceEntries.length ? 1 : 0.6,
                  }}
                >
                  Restoran faturasını indir
                </button>
                <button
                  type="button"
                  onClick={downloadCostCsv}
                  disabled={!filteredCostEntries.length}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    border: "1px solid rgba(185,116,41,0.18)",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    cursor: filteredCostEntries.length ? "pointer" : "not-allowed",
                    opacity: filteredCostEntries.length ? 1 : 0.6,
                  }}
                >
                  Kurye maliyetini indir
                </button>
                <button
                  type="button"
                  onClick={downloadProfitCsv}
                  disabled={!filteredProfitEntries.length}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    border: "1px solid rgba(34,102,60,0.18)",
                    background: "rgba(34,102,60,0.1)",
                    color: "#22663c",
                    fontWeight: 800,
                    cursor: filteredProfitEntries.length ? "pointer" : "not-allowed",
                    opacity: filteredProfitEntries.length ? 1 : 0.6,
                  }}
                >
                  Restoran kârlılığını indir
                </button>
              </div>
            </div>
            {exportError ? (
                <div style={{ color: "#9e2430", fontSize: "0.84rem", fontWeight: 700 }}>
                  {exportError}
                </div>
              ) : null}
            {exportMessage ? (
              <div style={{ color: "#22663c", fontSize: "0.84rem", fontWeight: 700 }}>
                {exportMessage}
              </div>
            ) : null}
          </section>
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
            Rapor verileri yükleniyor...
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
            Rapor verileri şu an alınamadı. Bağlantı toparlandığında restoran
            faturası ve kurye maliyeti otomatik yenilenecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "10px",
              }}
            >
              {summaryCards}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "10px",
              }}
            >
              {signalCards}
            </div>

            <ExecutiveReportChart dashboard={dashboard} />

            <ReportModelMatrix dashboard={dashboard} coverageGap={coverageGap} />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "10px",
              }}
            >
              {extendedSignalCards}
            </div>

            {coverageGap > 0 ? (
              <section
                style={{
                  padding: "18px 20px",
                  borderRadius: "18px",
                  border: "1px solid rgba(185,116,41,0.22)",
                  background: "rgba(255,248,236,0.92)",
                  display: "grid",
                  gap: "6px",
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
                  Kısmi Kapsama Uyarısı
                </div>
                <div style={{ fontSize: "0.92rem", fontWeight: 800 }}>
                  {formatNumber(coverageGap)} şube operasyonel görünüyor ama bu ayın rapor tablosuna henüz düşmemiş.
                </div>
                <div style={{ color: "var(--muted)", lineHeight: 1.55, fontSize: "0.84rem" }}>
                  Puantaj, fatura veya şube eşleşmesi eksik olabilir. Restoran faturası ve personel dağılımını birlikte kontrol et.
                </div>
              </section>
            ) : null}

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "12px",
              }}
            >
              <ScrollCard
                title="Restoran Faturası"
                subtitle="Şube bazlı toplam saat, paket ve restoran faturası. Liste kendi içinde kaydırılabilir."
                actions={
                  <input
                    value={invoiceQuery}
                    onChange={(event) => setInvoiceQuery(event.target.value)}
                    placeholder="Şube veya model ara"
                    style={{
                      minWidth: "220px",
                      padding: "10px 12px",
                      borderRadius: "12px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.96)",
                      color: "var(--text)",
                      fontSize: "0.84rem",
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
                        {tableCell(displayPricingModel(row.pricing_model), "left", true)}
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
                subtitle="Personel bazlı saat, paket, kesinti ve net maliyet görünümü. Liste kendi içinde kaydırılabilir."
                actions={
                  <input
                    value={costQuery}
                    onChange={(event) => setCostQuery(event.target.value)}
                    placeholder="Personel veya rol ara"
                    style={{
                      minWidth: "220px",
                      padding: "10px 12px",
                      borderRadius: "12px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.96)",
                      color: "var(--text)",
                      fontSize: "0.84rem",
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

            <ScrollCard
              title="Restoran Kârlılığı"
              subtitle="Fatura ile doğrudan personel ve ortak operasyon yükünü aynı satırda okuyup gerçek şube farkını gör."
              actions={
                <input
                  value={profitQuery}
                  onChange={(event) => setProfitQuery(event.target.value)}
                  placeholder="Şube veya model ara"
                  style={{
                    minWidth: "220px",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    border: "1px solid var(--line)",
                    background: "rgba(255,255,255,0.96)",
                    color: "var(--text)",
                    fontSize: "0.84rem",
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
                    {[
                      "Şube",
                      "KDV Dahil",
                      "Doğrudan Maliyet",
                      "Ortak Operasyon",
                      "Fatura-Kurye Farkı",
                      "Kâr Marjı",
                    ].map(tableHeaderCell)}
                  </tr>
                </thead>
                <tbody>
                  {filteredProfitEntries.map((row) => (
                    <tr key={`${row.restaurant}-${row.pricing_model}`}>
                      {tableCell(row.restaurant)}
                      {tableCell(formatMoney(row.gross_invoice), "right")}
                      {tableCell(formatMoney(row.direct_personnel_cost), "right")}
                      {tableCell(formatMoney(row.shared_overhead_cost), "right")}
                      {tableCell(formatMoney(row.gross_profit), "right")}
                      {tableCell(`%${formatNumber(row.profit_margin_percent, 1)}`, "right")}
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollCard>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "18px",
              }}
            >
              <ScrollCard
                title="Ortak Operasyon Payı"
                subtitle="Joker ve yönetim desteğinin şubelere nasıl yayıldığını kişi bazında oku."
              >
                <div style={{ padding: "12px 14px", display: "grid", gap: "10px" }}>
                  {dashboard.shared_overhead_entries.length ? (
                    dashboard.shared_overhead_entries.map((row) => (
                      <article
                        key={`${row.personnel}-${row.role}`}
                        style={{
                          display: "grid",
                          gap: "8px",
                          padding: "12px",
                          borderRadius: "16px",
                          border: "1px solid rgba(219, 228, 243, 0.8)",
                          background: "rgba(248, 250, 255, 0.9)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                          <strong>{row.personnel}</strong>
                          <span style={{ color: "var(--muted)" }}>{formatMoney(row.net_cost)}</span>
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>{row.role}</div>
                        <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
                          {formatNumber(row.allocated_restaurant_count)} şubeye dağılıyor • şube başı {formatMoney(row.share_per_restaurant)}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.84rem" }}>
                      Bu ay ortak operasyon payı görünmüyor. Joker ya da yönetim desteği oluştuğunda burada şube başına etkisini açacağız.
                    </div>
                  )}
                </div>
              </ScrollCard>

              <ScrollCard
                title="Yan Gelir Analizi"
                subtitle="Yakıt ve kart indirimi başta olmak üzere yan gelir katkısını aynı blokta gör."
              >
                <div style={{ padding: "12px 14px", display: "grid", gap: "10px" }}>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                      gap: "10px",
                    }}
                  >
                    {[
                      ["Yakıt Tahsilatı", dashboard.side_income_snapshot.fuel_reflection_amount],
                      ["Şirket Motoru Yakıtı", dashboard.side_income_snapshot.company_fuel_reflection_amount],
                      ["UTTS İndirimi", dashboard.side_income_snapshot.utts_fuel_discount_amount],
                      ["Partner Kartı", dashboard.side_income_snapshot.partner_card_discount_amount],
                    ].map(([label, value]) => (
                      <article
                        key={label}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "14px",
                          border: "1px solid rgba(219, 228, 243, 0.8)",
                          background: "rgba(248, 250, 255, 0.9)",
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
                        <div style={{ marginTop: "6px", fontWeight: 900, fontSize: "0.92rem" }}>{formatMoney(Number(value))}</div>
                      </article>
                    ))}
                  </div>

                  <table
                    style={{
                      width: "100%",
                      borderCollapse: "collapse",
                    }}
                  >
                    <thead>
                      <tr>
                        {["Kalem", "Gelir", "Maliyet", "Net Kâr"].map(tableHeaderCell)}
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.side_income_entries.map((row) => (
                        <tr key={row.item}>
                          {tableCell(row.item)}
                          {tableCell(formatMoney(row.revenue), "right")}
                          {tableCell(formatMoney(row.cost), "right")}
                          {tableCell(formatMoney(row.net_profit), "right")}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </ScrollCard>

              <ScrollCard
                title="Model Dağılımı"
                subtitle="Aynı ayda hangi anlaşma modelinin ne kadar hacim ürettiğini tek bakışta izle."
              >
                <div style={{ padding: "12px 14px", display: "grid", gap: "10px" }}>
                  {dashboard.model_breakdown.map((row) => (
                    <article
                      key={row.pricing_model}
                      style={{
                        display: "grid",
                        gap: "8px",
                        padding: "12px",
                        borderRadius: "16px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                        <strong>{displayPricingModel(row.pricing_model)}</strong>
                        <span style={{ color: "var(--muted)" }}>{formatMoney(row.gross_invoice)}</span>
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
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
                <div style={{ padding: "12px 14px", display: "grid", gap: "10px" }}>
                  {dashboard.top_restaurants.map((row) => (
                    <article
                      key={`${row.restaurant}-${row.pricing_model}`}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "12px",
                        borderRadius: "16px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <strong>{row.restaurant}</strong>
                      <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>{displayPricingModel(row.pricing_model)}</div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.84rem",
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
                <div style={{ padding: "12px 14px", display: "grid", gap: "10px" }}>
                  {dashboard.top_couriers.map((row) => (
                    <article
                      key={`${row.personnel}-${row.role}`}
                      style={{
                        display: "grid",
                        gap: "6px",
                        padding: "12px",
                        borderRadius: "16px",
                        border: "1px solid rgba(219, 228, 243, 0.8)",
                        background: "rgba(248, 250, 255, 0.9)",
                      }}
                    >
                      <strong>{row.personnel}</strong>
                      <div style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
                        {row.role} • {row.cost_model}
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.84rem",
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

            <ScrollCard
              title="Personel-Şube Dağılımı"
              subtitle="Kurye maliyetinin hangi şubeye, hangi yoğunlukla aktığını daha seçilebilir bir listede izle."
            >
              {dashboard.distribution_entries.length ? (
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                  }}
                >
                  <thead>
                    <tr>
                      {["Şube", "Personel", "Rol", "Saat", "Paket", "Maliyet Payı", "Kaynak"].map(
                        tableHeaderCell,
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.distribution_entries.map((row) => (
                      <tr key={`${row.restaurant}-${row.personnel}-${row.role}`}>
                        {tableCell(row.restaurant)}
                        {tableCell(row.personnel)}
                        {tableCell(row.role, "left", true)}
                        {tableCell(formatNumber(row.total_hours, 1), "right")}
                        {tableCell(formatNumber(row.total_packages, 0), "right")}
                        {tableCell(formatMoney(row.allocated_cost), "right")}
                        {tableCell(row.allocation_source, "left", true)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div
                  style={{
                    padding: "18px 20px",
                    color: "var(--muted)",
                    lineHeight: 1.7,
                  }}
                >
                  Bu ay personel-şube dağılımı için yeterli puantaj verisi oluşmamış görünüyor.
                </div>
              )}
            </ScrollCard>
          </>
        )}
      </section>
    </AppShell>
  );
}
