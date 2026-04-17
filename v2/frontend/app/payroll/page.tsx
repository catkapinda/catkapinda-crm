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
  role_breakdown: Array<{
    role: string;
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

function toSafeNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function normalizePayrollDashboard(payload: Partial<PayrollDashboard>): PayrollDashboard {
  const summary =
    payload.summary && typeof payload.summary === "object"
      ? {
          selected_month: toSafeString(payload.summary.selected_month),
          personnel_count: toSafeNumber(payload.summary.personnel_count),
          total_hours: toSafeNumber(payload.summary.total_hours),
          total_packages: toSafeNumber(payload.summary.total_packages),
          gross_payroll: toSafeNumber(payload.summary.gross_payroll),
          total_deductions: toSafeNumber(payload.summary.total_deductions),
          net_payment: toSafeNumber(payload.summary.net_payment),
        }
      : null;

  return {
    module: toSafeString(payload.module, "payroll"),
    status: toSafeString(payload.status, "active"),
    month_options: Array.isArray(payload.month_options)
      ? payload.month_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    selected_month: typeof payload.selected_month === "string" ? payload.selected_month : null,
    role_options: Array.isArray(payload.role_options)
      ? payload.role_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    restaurant_options: Array.isArray(payload.restaurant_options)
      ? payload.restaurant_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    selected_role: toSafeString(payload.selected_role, "Tümü"),
    selected_restaurant: toSafeString(payload.selected_restaurant, "Tümü"),
    summary,
    entries: Array.isArray(payload.entries)
      ? payload.entries.map((entry) => ({
          personnel_id: toSafeNumber(entry.personnel_id),
          personnel: toSafeString(entry.personnel, "-"),
          role: toSafeString(entry.role, "-"),
          status: toSafeString(entry.status, "-"),
          total_hours: toSafeNumber(entry.total_hours),
          total_packages: toSafeNumber(entry.total_packages),
          gross_pay: toSafeNumber(entry.gross_pay),
          total_deductions: toSafeNumber(entry.total_deductions),
          net_payment: toSafeNumber(entry.net_payment),
          restaurant_count: toSafeNumber(entry.restaurant_count),
          cost_model: toSafeString(entry.cost_model, "-"),
        }))
      : [],
    cost_model_breakdown: Array.isArray(payload.cost_model_breakdown)
      ? payload.cost_model_breakdown.map((row) => ({
          cost_model: toSafeString(row.cost_model, "-"),
          personnel_count: toSafeNumber(row.personnel_count),
          total_hours: toSafeNumber(row.total_hours),
          total_packages: toSafeNumber(row.total_packages),
          net_payment: toSafeNumber(row.net_payment),
        }))
      : [],
    role_breakdown: Array.isArray(payload.role_breakdown)
      ? payload.role_breakdown.map((row) => ({
          role: toSafeString(row.role, "-"),
          personnel_count: toSafeNumber(row.personnel_count),
          total_hours: toSafeNumber(row.total_hours),
          total_packages: toSafeNumber(row.total_packages),
          net_payment: toSafeNumber(row.net_payment),
        }))
      : [],
    top_personnel: Array.isArray(payload.top_personnel)
      ? payload.top_personnel.map((row) => ({
          personnel_id: toSafeNumber(row.personnel_id),
          personnel: toSafeString(row.personnel, "-"),
          role: toSafeString(row.role, "-"),
          total_hours: toSafeNumber(row.total_hours),
          total_packages: toSafeNumber(row.total_packages),
          total_deductions: toSafeNumber(row.total_deductions),
          net_payment: toSafeNumber(row.net_payment),
          restaurant_count: toSafeNumber(row.restaurant_count),
          cost_model: toSafeString(row.cost_model, "-"),
        }))
      : [],
  };
}

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
  const [documentPersonId, setDocumentPersonId] = useState<number | "">("");
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [documentMessage, setDocumentMessage] = useState("");

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
        const payload = normalizePayrollDashboard(
          (await response.json()) as Partial<PayrollDashboard>,
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
      metricCard("Saat Başına Net", formatMoney(netPerHour), "Net ödeme / toplam saat"),
      metricCard("Kurye Başına Net", formatMoney(netPerCourier), "Net ödeme / personel"),
      metricCard("Kesinti Oranı", `%${formatNumber(deductionRatio, 1)}`, "Kesinti / brüt hakediş"),
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
        eyebrow: "Ödeme Nabzı",
        title:
          deductionRatio <= 8
            ? "Kesinti baskısı kontrollü görünüyor."
            : deductionRatio <= 14
              ? "Kesinti baskısı izlenmeli."
              : "Kesinti baskısı yükseliyor.",
        body: `${dashboard.summary.selected_month} döneminde ${formatMoney(dashboard.summary.net_payment)} net ödeme çıkıyor. Kesinti oranı %${formatNumber(deductionRatio, 1)} seviyesinde.`,
        tone: deductionRatio <= 8 ? "ink" : "accent",
      },
      {
        eyebrow: "En Yüksek Net Ödeme",
        title: topPersonnel ? topPersonnel.personnel : "Ödeme lideri sinyali henüz yok.",
        body: topPersonnel
          ? `${topPersonnel.role} rolünde ${formatMoney(topPersonnel.net_payment)} net ödeme taşıyor. ${formatNumber(topPersonnel.total_hours, 1)} saat ve ${formatMoney(topPersonnel.total_deductions)} kesinti etkisi birlikte okunmalı.`
          : "Personel dağılımı geldikçe bu kart aylık ödeme ağırlığını önde gösterecek.",
        tone: "paper",
      },
      {
        eyebrow: "Model Yükü",
        title: topCostModel ? topCostModel.cost_model : "Model dağılımı sinyali henüz yok.",
        body: topCostModel
          ? `${formatNumber(topCostModel.personnel_count)} personel ile ${formatMoney(topCostModel.net_payment)} net ödeme yükünü taşıyor. Kurye başına ortalama net ödeme ${formatMoney(netPerCourier)} seviyesinde.`
          : "Hangi maliyet modelinin yük taşıdığını bu alan hızlı gösterecek.",
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

  const documentOptions = useMemo(
    () =>
      (dashboard?.entries ?? []).map((entry) => ({
        id: entry.personnel_id,
        label: `${entry.personnel} | ${entry.role}`,
      })),
    [dashboard?.entries],
  );

  useEffect(() => {
    if (!documentOptions.length) {
      setDocumentPersonId("");
      return;
    }
    if (
      typeof documentPersonId !== "number" ||
      !documentOptions.some((option) => option.id === documentPersonId)
    ) {
      setDocumentPersonId(documentOptions[0].id);
    }
  }, [documentOptions, documentPersonId]);

  async function handleDocumentDownload() {
    if (typeof documentPersonId !== "number") {
      setDocumentError("Belge oluşturmak için önce personel seçmelisin.");
      setDocumentMessage("");
      return;
    }
    const month = dashboard?.selected_month || selectedMonth;
    if (!month) {
      setDocumentError("Belge oluşturmak için önce ay seçmelisin.");
      setDocumentMessage("");
      return;
    }

    setDocumentBusy(true);
    setDocumentError("");
    setDocumentMessage("");
    try {
      const params = new URLSearchParams({
        personnel_id: String(documentPersonId),
        month,
      });
      const response = await apiFetch(`/payroll/document?${params.toString()}`);
      if (!response.ok) {
        let detail = "Hakediş belgesi indirilemedi.";
        try {
          const payload = (await response.json()) as { detail?: string };
          if (payload?.detail) {
            detail = payload.detail;
          }
        } catch {}
        throw new Error(detail);
      }
      const disposition = response.headers.get("Content-Disposition") || "";
      const fileNameMatch = disposition.match(/filename=\"?([^"]+)\"?/i);
      const fileName = fileNameMatch?.[1] || `hakedis_${documentPersonId}_${month}.pdf`;
      const blob = await response.blob();
      triggerBrowserDownload(blob, fileName);
      setDocumentMessage("Hakediş belgesi indirildi.");
    } catch (nextError) {
      setDocumentError(
        nextError instanceof Error ? nextError.message : "Hakediş belgesi indirilemedi.",
      );
    } finally {
      setDocumentBusy(false);
    }
  }

  function handleCsvDownload() {
    if (!filteredEntries.length) {
      setDocumentError("Dışa aktarmak için önce görünür bordro kaydı oluşmalı.");
      setDocumentMessage("");
      return;
    }

    const headers = [
      "Personel",
      "Rol",
      "Durum",
      "Toplam Saat",
      "Toplam Paket",
      "Brüt Hakediş",
      "Toplam Kesinti",
      "Net Ödeme",
      "Restoran Sayısı",
      "Maliyet Modeli",
    ];
    const rows = filteredEntries.map((entry) => [
      entry.personnel,
      entry.role,
      entry.status,
      String(entry.total_hours),
      String(entry.total_packages),
      String(entry.gross_pay),
      String(entry.total_deductions),
      String(entry.net_payment),
      String(entry.restaurant_count),
      entry.cost_model,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "bordro";
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
    triggerBrowserDownload(blob, `catkapinda_aylik_hakedis_${month}.csv`);
    setDocumentError("");
    setDocumentMessage("Aylık hakediş tablosu indirildi.");
  }

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
                Hakediş ve Bordro
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
                  Bordroyu sadece toplamla değil, gerilim noktalarını da okuyarak yönetiyoruz.
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
                  Net ödeme, kesinti, saat ve paket dağılımlarını daha ciddi bir karar
                  odasına çekiyoruz. Hedefimiz, kapanış öncesi riskleri ve ödeme ağırlığını
                  bir bakışta daha doğru hissettirmek.
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
                  Bordro sinyali açık
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
                  Risk ve ödeme aynı katmanda
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
                      Hakediş Dönemi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
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
                      padding: "7px 10px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.8rem",
                      fontWeight: 800,
                    }}
                  >
                    Hakediş Masası
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
                      Net Ödeme
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
                  Bu ekranda önce kesinti baskısını, sonra model yükünü ve en yüksek net
                  ödeme çıkan isimleri okumak kapanış kararını daha netleştirir.
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

          <section
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.15fr) minmax(0, 0.85fr)",
              gap: "14px",
            }}
          >
            <article
              style={{
                padding: "18px 20px",
                borderRadius: "22px",
                border: "1px solid rgba(15, 95, 215, 0.14)",
                background: "rgba(15, 95, 215, 0.06)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div
                style={{
                  color: "#0f5fd7",
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Hakediş Notu
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 800 }}>
                Kesintiler seçilen ayın son gününe yazılır.
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.75, fontSize: "0.95rem" }}>
                Bu ekrandaki net ödeme ay kapanışına göre hesaplanır. Ödeme akışını
                yorumlarken ay sonu kesinti toplamını ve kapanış tarihini birlikte okumak daha doğru olur.
              </div>
            </article>

            <article
              style={{
                padding: "18px 20px",
                borderRadius: "22px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.82)",
                display: "grid",
                gap: "12px",
              }}
            >
              <div
                style={{
                  color: "var(--muted)",
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Sistem Senkronu
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                <div style={{ color: "var(--text)", lineHeight: 1.65 }}>
                  <strong>Kesinti Senkronu:</strong> Puantaj ekleme, güncelleme ve silmede
                  bordro etkisi yeniden hesaplanır.
                </div>
                <div style={{ color: "var(--text)", lineHeight: 1.65 }}>
                  <strong>Hakediş / Raporlar:</strong> Aylık hakediş ve raporlar ekranı açılırken
                  sistem kesintileri yeniden senkronlanır.
                </div>
              </div>
            </article>
          </section>

          <section
            style={{
              borderRadius: "24px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.78)",
              padding: "18px 20px",
              display: "grid",
              gap: "14px",
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
                    fontSize: "0.74rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Belge ve Dışa Aktarım
                </div>
                <div style={{ fontSize: "1rem", fontWeight: 800 }}>
                  Aylık tabloyu dışa aktar, seçili personel için hakediş belgesini indir.
                </div>
              </div>
              <button
                type="button"
                onClick={handleCsvDownload}
                disabled={!filteredEntries.length}
                style={{
                  padding: "12px 16px",
                  borderRadius: "14px",
                  border: "1px solid rgba(15,95,215,0.15)",
                  background: "rgba(15,95,215,0.08)",
                  color: "#0f5fd7",
                  fontWeight: 800,
                  cursor: filteredEntries.length ? "pointer" : "not-allowed",
                  opacity: filteredEntries.length ? 1 : 0.6,
                }}
              >
                Aylık hakediş tablosunu indir
              </button>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(220px, 1fr) auto",
                gap: "12px",
                alignItems: "end",
              }}
            >
              <div style={{ display: "grid", gap: "8px" }}>
                <label style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>
                  Belgesi oluşturulacak personel
                </label>
                <select
                  value={documentPersonId}
                  onChange={(event) =>
                    setDocumentPersonId(event.target.value ? Number(event.target.value) : "")
                  }
                  disabled={documentBusy || !documentOptions.length}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "16px",
                    border: "1px solid var(--line)",
                    background: "rgba(255,255,255,0.96)",
                    color: "var(--text)",
                    fontWeight: 700,
                  }}
                >
                  {documentOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={handleDocumentDownload}
                disabled={documentBusy || typeof documentPersonId !== "number"}
                style={{
                  padding: "14px 18px",
                  borderRadius: "16px",
                  border: "none",
                  background:
                    "linear-gradient(135deg, rgba(185,116,41,1), rgba(212,144,61,0.96))",
                  color: "#fff7ea",
                  fontWeight: 900,
                  cursor:
                    documentBusy || typeof documentPersonId !== "number"
                      ? "not-allowed"
                      : "pointer",
                  opacity: documentBusy || typeof documentPersonId !== "number" ? 0.6 : 1,
                }}
              >
                {documentBusy ? "Belge hazırlanıyor..." : "Hakediş belgesini indir"}
              </button>
            </div>
            {documentError ? (
              <div style={{ color: "#9e2430", fontSize: "0.92rem", fontWeight: 700 }}>
                {documentError}
              </div>
            ) : null}
            {documentMessage ? (
              <div style={{ color: "#22663c", fontSize: "0.92rem", fontWeight: 700 }}>
                {documentMessage}
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
            Hakediş verileri yükleniyor...
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
            Hakediş servisine şu anda erişilemiyor. Backend hazır olduğunda burada
            aylık ödeme özeti ve bordro dağılımları görünecek.
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
                title="Hakediş Özeti"
                subtitle="Personel bazlı çalışma, kesinti ve net ödeme görünümü. Liste kendi içinde kaydırılabilir."
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
                        "Brüt",
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
                  title="Maliyet Modeli Dağılımı"
                  subtitle="Hangi hakediş modelinin ne kadar yük taşıdığını tek bakışta izle."
                >
                  <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                    {dashboard.cost_model_breakdown.length ? (
                      dashboard.cost_model_breakdown.map((row) => (
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
                      ))
                    ) : (
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        Seçili filtrede maliyet modeli dağılımı henüz oluşmadı.
                      </div>
                    )}
                  </div>
                </ScrollCard>

                <ScrollCard
                  title="Rol Dağılımı"
                  subtitle="Hangi rolün net ödeme, saat ve paket yükünü taşıdığını birlikte gör."
                >
                  <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                    {dashboard.role_breakdown.length ? (
                      dashboard.role_breakdown.map((row) => (
                        <article
                          key={row.role}
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
                            <strong>{row.role}</strong>
                            <span style={{ color: "var(--muted)" }}>{formatMoney(row.net_payment)}</span>
                          </div>
                          <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                            {formatNumber(row.personnel_count)} personel • {formatNumber(row.total_hours, 1)} saat • {formatNumber(row.total_packages, 0)} paket
                          </div>
                        </article>
                      ))
                    ) : (
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        Seçili filtrede rol dağılımı henüz oluşmadı.
                      </div>
                    )}
                  </div>
                </ScrollCard>

                <ScrollCard
                  title="En Yüksek Net Ödeme"
                  subtitle="Ay içinde en yüksek net ödeme çıkan çalışanları hızlıca gör."
                >
                  <div style={{ padding: "14px 18px", display: "grid", gap: "14px" }}>
                    {dashboard.top_personnel.length ? (
                      dashboard.top_personnel.map((row) => (
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
                      ))
                    ) : (
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        Seçili filtrede öne çıkan net ödeme kaydı henüz oluşmadı.
                      </div>
                    )}
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
