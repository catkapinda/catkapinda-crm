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
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
            display: "grid",
            gap: "18px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: "18px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <div
                style={{
                  display: "inline-flex",
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
                Finans v2
              </div>
              <h1
                style={{
                  margin: "16px 0 10px",
                  fontSize: "clamp(2rem, 4vw, 3rem)",
                  lineHeight: 1.03,
                }}
              >
                Finans yüzeyini yeni sistemde daha okunur ve daha hızlı hale getiriyoruz.
              </h1>
              <p
                style={{
                  margin: 0,
                  maxWidth: "76ch",
                  color: "var(--muted)",
                  fontSize: "1.02rem",
                  lineHeight: 1.7,
                }}
              >
                Bu ilk rapor yüzeyi, günlük kullanımda en çok açılan iki finans tablosunu tek ay filtresi ve kontrollü scroll alanlarıyla sunar.
              </p>
            </div>
            <div
              style={{
                minWidth: "200px",
                display: "grid",
                gap: "8px",
              }}
            >
              <label
                htmlFor="reports-month"
                style={{
                  color: "var(--muted)",
                  fontSize: "0.82rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  fontWeight: 800,
                }}
              >
                Rapor Dönemi
              </label>
              <select
                id="reports-month"
                value={selectedMonth}
                onChange={(event) => setSelectedMonth(event.target.value)}
                disabled={dashboardLoading || !dashboard?.month_options?.length}
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.96)",
                  color: "var(--text)",
                  fontWeight: 700,
                }}
              >
                {(dashboard?.month_options ?? []).map((month) => (
                  <option key={month} value={month}>
                    {month}
                  </option>
                ))}
              </select>
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
            Rapor ekranı hazırlanıyor...
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
            Bu ekran için uygun rapor verisi bulunamadı. v2 rapor servisi ay verisi geldiğinde restoran faturası ve kurye maliyetini burada gösterecek.
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
