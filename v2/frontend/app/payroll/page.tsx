"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type PayrollDashboard = {
  module: string;
  status: string;
  month_options: string[];
  selected_month: string | null;
  role_options: string[];
  restaurant_options: string[];
  selected_role: string;
  selected_restaurant: string;
  summary: {
    selected_month: string;
    personnel_count: number;
    total_hours: number;
    total_packages: number;
    gross_payroll: number;
    total_deductions: number;
    net_payment: number;
  } | null;
  entries: Array<{
    personnel_id: number;
    personnel: string;
    role: string;
    status: string;
    total_hours: number;
    total_packages: number;
    gross_pay: number;
    total_deductions: number;
    net_payment: number;
    restaurant_count: number;
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

export default function PayrollPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<PayrollDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedRole, setSelectedRole] = useState("Tümü");
  const [selectedRestaurant, setSelectedRestaurant] = useState("Tümü");

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
        const params = new URLSearchParams();
        if (selectedMonth) {
          params.set("month", selectedMonth);
        }
        if (selectedRole && selectedRole !== "Tümü") {
          params.set("role", selectedRole);
        }
        if (selectedRestaurant && selectedRestaurant !== "Tümü") {
          params.set("restaurant", selectedRestaurant);
        }
        const query = params.toString() ? `?${params.toString()}` : "";
        const response = await apiFetch(`/payroll/dashboard${query}`);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as PayrollDashboard;
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
  }, [loading, selectedMonth, selectedRestaurant, selectedRole, user]);

  const summaryCards = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }
    return [
      metricCard("Brüt Hakediş", formatMoney(dashboard.summary.gross_payroll), `${dashboard.summary.selected_month} toplamı`),
      metricCard("Toplam Kesinti", formatMoney(dashboard.summary.total_deductions), "Ay sonu kesinti toplamı"),
      metricCard("Net Ödeme", formatMoney(dashboard.summary.net_payment), "Hakediş kapanış özeti"),
      metricCard("Personel", formatNumber(dashboard.summary.personnel_count), "Hakediş havuzundaki çalışan"),
      metricCard("Toplam Saat", formatNumber(dashboard.summary.total_hours, 1), "Seçili filtre çalışma saati"),
      metricCard("Toplam Paket", formatNumber(dashboard.summary.total_packages, 0), "Seçili filtre paket toplamı"),
    ];
  }, [dashboard]);

  return (
    <AppShell activeItem="Aylık Hakediş">
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
                Aylık hakediş yönetimini yeni sistemde çalıştırıyoruz.
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
                Personel bazlı brüt, kesinti ve net ödeme görünümünü ay, rol ve restoran filtresiyle tek yüzeyde takip et.
              </p>
            </div>
            <div
              style={{
                minWidth: "280px",
                display: "grid",
                gap: "10px",
              }}
            >
              <label
                htmlFor="payroll-month"
                style={{
                  color: "var(--muted)",
                  fontSize: "0.82rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  fontWeight: 800,
                }}
              >
                Hakediş Dönemi
              </label>
              <select
                id="payroll-month"
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

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <div style={{ display: "grid", gap: "8px" }}>
              <label style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>Rol</label>
              <select
                value={selectedRole}
                onChange={(event) => setSelectedRole(event.target.value)}
                disabled={dashboardLoading}
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.96)",
                  color: "var(--text)",
                  fontWeight: 700,
                }}
              >
                {(dashboard?.role_options ?? ["Tümü"]).map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: "grid", gap: "8px" }}>
              <label style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>Restoran</label>
              <select
                value={selectedRestaurant}
                onChange={(event) => setSelectedRestaurant(event.target.value)}
                disabled={dashboardLoading}
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.96)",
                  color: "var(--text)",
                  fontWeight: 700,
                }}
              >
                {(dashboard?.restaurant_options ?? ["Tümü"]).map((restaurant) => (
                  <option key={restaurant} value={restaurant}>
                    {restaurant}
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
            Hakediş ekranı hazırlanıyor...
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
            Bu ekran için uygun hakediş verisi bulunamadı. v2 hakediş servisi ay verisi geldiğinde personel bazlı ödeme görünümü burada çalışacak.
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
                }}
              >
                <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Hakediş Özeti</h2>
                <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
                  Personel bazlı çalışma, kesinti ve net ödeme görünümü. Liste kendi içinde scroll eder.
                </p>
              </div>
              <div
                style={{
                  maxHeight: "560px",
                  overflow: "auto",
                }}
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
                        "Personel",
                        "Rol",
                        "Durum",
                        "Saat",
                        "Paket",
                        "Brüt",
                        "Kesinti",
                        "Net",
                        "Restoran",
                        "Model",
                      ].map(tableHeaderCell)}
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.entries.map((row) => (
                      <tr key={row.personnel_id}>
                        {tableCell(row.personnel)}
                        {tableCell(row.role, "left", true)}
                        {tableCell(row.status, "left", true)}
                        {tableCell(formatNumber(row.total_hours, 1), "right")}
                        {tableCell(formatNumber(row.total_packages, 0), "right")}
                        {tableCell(formatMoney(row.gross_pay), "right")}
                        {tableCell(formatMoney(row.total_deductions), "right")}
                        {tableCell(formatMoney(row.net_payment), "right")}
                        {tableCell(formatNumber(row.restaurant_count, 0), "right", true)}
                        {tableCell(row.cost_model, "left", true)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
