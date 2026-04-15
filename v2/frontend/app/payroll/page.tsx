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
  cost_model_breakdown: Array<{
    cost_model: string;
    personnel_count: number;
    total_hours: number;
    total_packages: number;
    net_payment: number;
  }>;
  top_personnel: Array<{
    personnel_id: number;
    personnel: string;
    role: string;
    total_hours: number;
    total_packages: number;
    total_deductions: number;
    net_payment: number;
    restaurant_count: number;
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

export default function PayrollPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<PayrollDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedRole, setSelectedRole] = useState("Tümü");
  const [selectedRestaurant, setSelectedRestaurant] = useState("Tümü");
  const [entryQuery, setEntryQuery] = useState("");

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
      metricCard("Brut Hakedis", formatMoney(dashboard.summary.gross_payroll), `${dashboard.summary.selected_month} toplami`),
      metricCard("Toplam Kesinti", formatMoney(dashboard.summary.total_deductions), "Ay sonu kesinti toplami"),
      metricCard("Net Odeme", formatMoney(dashboard.summary.net_payment), "Hakedis kapanis ozeti"),
      metricCard("Personel", formatNumber(dashboard.summary.personnel_count), "Hakedis havuzundaki calisan"),
      metricCard("Toplam Saat", formatNumber(dashboard.summary.total_hours, 1), "Secili filtre calisma saati"),
      metricCard("Toplam Paket", formatNumber(dashboard.summary.total_packages, 0), "Secili filtre paket toplami"),
    ];
  }, [dashboard]);

  const signalCards = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }
    const netPerHour =
      dashboard.summary.total_hours > 0
        ? dashboard.summary.net_payment / dashboard.summary.total_hours
        : 0;
    const netPerCourier =
      dashboard.summary.personnel_count > 0
        ? dashboard.summary.net_payment / dashboard.summary.personnel_count
        : 0;
    const deductionRatio =
      dashboard.summary.gross_payroll > 0
        ? (dashboard.summary.total_deductions / dashboard.summary.gross_payroll) * 100
        : 0;

    return [
      metricCard("Saat Basina Net", formatMoney(netPerHour), "Net odeme / toplam saat"),
      metricCard("Kurye Basina Net", formatMoney(netPerCourier), "Net odeme / personel"),
      metricCard("Kesinti Orani", `%${formatNumber(deductionRatio, 1)}`, "Kesinti / brut hakedis"),
    ];
  }, [dashboard]);

  const decisionDeck = useMemo(() => {
    if (!dashboard?.summary) {
      return [];
    }

    const deductionRatio =
      dashboard.summary.gross_payroll > 0
        ? (dashboard.summary.total_deductions / dashboard.summary.gross_payroll) * 100
        : 0;
    const topPersonnel = dashboard.top_personnel[0] ?? null;
    const topCostModel = dashboard.cost_model_breakdown[0] ?? null;
    const netPerCourier =
      dashboard.summary.personnel_count > 0
        ? dashboard.summary.net_payment / dashboard.summary.personnel_count
        : 0;

    return [
      {
        eyebrow: "Odeme Nabzi",
        title:
          deductionRatio <= 8
            ? "Kesinti baskisi kontrollu gorunuyor."
            : deductionRatio <= 14
              ? "Kesinti baskisi izlenmeli."
              : "Kesinti baskisi yukseliyor.",
        body: `${dashboard.summary.selected_month} doneminde ${formatMoney(dashboard.summary.net_payment)} net odeme cikiyor. Kesinti orani %${formatNumber(deductionRatio, 1)} seviyesinde.`,
        tone: deductionRatio <= 8 ? "ink" : "accent",
      },
      {
        eyebrow: "En Yuksek Net Odeme",
        title: topPersonnel ? topPersonnel.personnel : "Odeme lideri sinyali henuz yok.",
        body: topPersonnel
          ? `${topPersonnel.role} rolunde ${formatMoney(topPersonnel.net_payment)} net odeme tasiyor. ${formatNumber(topPersonnel.total_hours, 1)} saat ve ${formatMoney(topPersonnel.total_deductions)} kesinti etkisi birlikte okunmali.`
          : "Personel dagilimi geldikce bu kart aylik odeme agirligini onde gosterecek.",
        tone: "paper",
      },
      {
        eyebrow: "Model Yuku",
        title: topCostModel ? topCostModel.cost_model : "Model dagilimi sinyali henuz yok.",
        body: topCostModel
          ? `${formatNumber(topCostModel.personnel_count)} personel ile ${formatMoney(topCostModel.net_payment)} net odeme yukunu tasiyor. Kurye basina ortalama net odeme ${formatMoney(netPerCourier)} seviyesinde.`
          : "Hangi maliyet modelinin yuk tasidigini bu alan hizli gosterecek.",
        tone: "paper",
      },
    ] as const;
  }, [dashboard]);

  const filteredEntries = useMemo(() => {
    const rows = dashboard?.entries ?? [];
    const query = entryQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.personnel} ${row.role} ${row.cost_model}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.entries, entryQuery]);

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
                Hakedis ve Bordro
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
                  Bordroyu sadece toplamla degil, gerilim noktalarini da okuyarak yonetiyoruz.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "76ch",
                    color: "var(--muted)",
                    fontSize: "1.02rem",
                    lineHeight: 1.76,
                  }}
                >
                  Net odeme, kesinti, saat ve paket dagilimlarini daha ciddi bir karar
                  odasina cekiyoruz. Hedefimiz, kapanis oncesi riskleri ve odeme agirligini
                  bir bakista daha dogru hissettirmek.
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
                  Bordro sinyali acik
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
                  Risk ve odeme ayni katmanda
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
                      Hakedis Donemi
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
                    Payroll Room
                  </div>
                </div>
                <select
                  id="payroll-month"
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
                      Net Odeme
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.net_payment ?? 0)}
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
                      Toplam Kesinti
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatMoney(dashboard?.summary?.total_deductions ?? 0)}
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
                  Bu ekranda once kesinti baskisini, sonra model yukunu ve en yuksek net
                  odeme cikan isimleri okumak kapanis kararini daha netlestirir.
                </div>
              </article>
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
            Hakedis verileri yukleniyor...
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
            Hakedis servisine su anda erisilemiyor. Backend hazir oldugunda burada
            aylik odeme ozeti ve bordro dagilimlari gorunecek.
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
                <div key={`${item.eyebrow}-${item.title}`}>{narrativeCard(item)}</div>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.8fr) minmax(320px, 1fr)",
                gap: "18px",
              }}
            >
              <ScrollCard
                title="Hakedis Ozeti"
                subtitle="Personel bazli calisma, kesinti ve net odeme gorunumu. Liste kendi icinde scroll eder."
                actions={
                  <input
                    value={entryQuery}
                    onChange={(event) => setEntryQuery(event.target.value)}
                    placeholder="Personel, rol veya model ara"
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
                      {[
                        "Personel",
                        "Rol",
                        "Durum",
                        "Saat",
                        "Paket",
                        "Brut",
                        "Kesinti",
                        "Net",
                        "Restoran",
                        "Model",
                      ].map(tableHeaderCell)}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEntries.map((row) => (
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
              </ScrollCard>

              <div style={{ display: "grid", gap: "18px" }}>
                <ScrollCard
                  title="Maliyet Modeli Dagilimi"
                  subtitle="Hangi hakedis modelinin ne kadar yuk tasidigini tek bakista izle."
                >
                  <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                    {dashboard.cost_model_breakdown.map((row) => (
                      <article
                        key={row.cost_model}
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
                          <strong>{row.cost_model}</strong>
                          <span style={{ color: "var(--muted)" }}>{formatMoney(row.net_payment)}</span>
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                          {formatNumber(row.personnel_count)} personel • {formatNumber(row.total_hours, 1)} saat • {formatNumber(row.total_packages, 0)} paket
                        </div>
                      </article>
                    ))}
                  </div>
                </ScrollCard>

                <ScrollCard
                  title="En Yuksek Net Odeme"
                  subtitle="Ay icinde en yuksek net odeme cikan calisanlari hizlica gor."
                >
                  <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                    {dashboard.top_personnel.map((row) => (
                      <article
                        key={`top-${row.personnel_id}`}
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
                          <strong>{row.personnel}</strong>
                          <span>{formatMoney(row.net_payment)}</span>
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                          {row.role} • {formatNumber(row.total_hours, 1)} saat • {formatNumber(row.total_packages, 0)} paket
                        </div>
                        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                          {formatNumber(row.restaurant_count, 0)} restoran • {row.cost_model}
                        </div>
                      </article>
                    ))}
                  </div>
                </ScrollCard>
              </div>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
