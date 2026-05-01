"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

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
    total_tevkifat: number;
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
    tevkifat_amount: number;
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

type DeductionRecord = {
  id: number;
  personnel_id: number;
  personnel_label: string;
  deduction_date: string;
  deduction_type: string;
  type_caption: string;
  amount: number;
  notes: string;
};

type DeductionsManagementResponse = {
  total_entries: number;
  entries: DeductionRecord[];
};

type PayrollDeltaTone = "positive" | "negative" | "neutral";
type PayrollTab = "finance" | "operations" | "trend" | "pdf";
type DeductionListItem = {
  key: number | string;
  label: string;
  amount: number;
};

type MonthlySeriesItem = {
  month: string;
  label: string;
  summary: NonNullable<PayrollDashboard["summary"]> | null;
  entries: PayrollDashboard["entries"];
};

const CHART_COLORS = ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd"];
const COST_MODEL_LABELS: Record<string, string> = {
  hourly_plus_package: "Saatlik",
  threshold_package: "Paket Başı",
  hourly_only: "Günlük",
  fixed_monthly: "Diğer",
};

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
          total_tevkifat: toSafeNumber(payload.summary.total_tevkifat),
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
          tevkifat_amount: toSafeNumber(entry.tevkifat_amount),
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
  })
    .format(value || 0)
    .replace("₺", "")
    .trim()
    .concat(" ₺");
}

function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value || 0);
}

function monthToLabel(month: string) {
  const [year, rawMonth] = month.split("-");
  const parsedYear = Number(year);
  const parsedMonth = Number(rawMonth);
  if (!parsedYear || !parsedMonth) {
    return month;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    month: "short",
    year: "2-digit",
  })
    .format(new Date(Date.UTC(parsedYear, parsedMonth - 1, 1)))
    .replace(".", "");
}

function getInitials(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR") ?? "")
    .join("");
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

function buildDelta(
  current: number,
  previous: number,
  positiveIsGood = true,
): { label: string; tone: PayrollDeltaTone } {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) {
    return {
      label: "İlk kıyas",
      tone: "neutral" as PayrollDeltaTone,
    };
  }

  const ratio = ((current - previous) / previous) * 100;
  if (Math.abs(ratio) < 0.05) {
    return {
      label: "Değişim sınırlı",
      tone: "neutral" as PayrollDeltaTone,
    };
  }

  const improved = positiveIsGood ? ratio > 0 : ratio < 0;
  return {
    label: `${ratio > 0 ? "+" : ""}${formatNumber(ratio, 1)}% geçen aya göre`,
    tone: improved ? "positive" : "negative",
  };
}

function buildLinePath(values: number[], width: number, height: number, padding = 18) {
  if (!values.length) {
    return { path: "", points: [] as Array<{ x: number; y: number; value: number }> };
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  const points = values.map((value, index) => {
    const x =
      padding + (values.length === 1 ? chartWidth / 2 : (chartWidth / (values.length - 1)) * index);
    const y = padding + chartHeight - ((value - min) / range) * chartHeight;
    return { x, y, value };
  });
  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
  return { path, points };
}

function buildAreaPath(
  points: Array<{ x: number; y: number }>,
  width: number,
  height: number,
  padding = 18,
) {
  if (!points.length) {
    return "";
  }
  const bottom = height - padding;
  return `${points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ")} L ${points[points.length - 1].x.toFixed(2)} ${bottom.toFixed(2)} L ${points[0].x.toFixed(2)} ${bottom.toFixed(2)} Z`;
}

function TrendChart({
  items,
}: {
  items: Array<{ label: string; value: number }>;
}) {
  const width = 760;
  const height = 280;
  const values = items.map((item) => item.value);
  const { path, points } = buildLinePath(values, width, height, 28);
  const areaPath = buildAreaPath(points, width, height, 28);
  const maxValue = Math.max(...values, 0);
  const minValue = Math.min(...values, 0);
  const ticks = Array.from({ length: 4 }, (_, index) => minValue + ((maxValue - minValue || 1) / 3) * index).reverse();

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="trend-chart" role="img" aria-label="Hakediş trendi">
      <defs>
        <linearGradient id="payrollTrendFill" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(37, 99, 235, 0.24)" />
          <stop offset="100%" stopColor="rgba(37, 99, 235, 0)" />
        </linearGradient>
      </defs>
      {ticks.map((tick, index) => {
        const y = 28 + ((height - 56) / 3) * index;
        return (
          <g key={`tick-${tick}-${index}`}>
            <line x1="28" x2={width - 28} y1={y} y2={y} stroke="rgba(148, 163, 184, 0.18)" strokeDasharray="4 6" />
            <text x="0" y={y + 4} className="trend-axis">
              {formatMoney(tick)}
            </text>
          </g>
        );
      })}
      {areaPath ? <path d={areaPath} fill="url(#payrollTrendFill)" /> : null}
      {path ? <path d={path} fill="none" stroke="#1d4ed8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {points.map((point, index) => (
        <g key={`${items[index]?.label ?? index}`}>
          <circle cx={point.x} cy={point.y} r="5.5" fill="#ffffff" stroke="#1d4ed8" strokeWidth="3" />
          <text x={point.x} y={point.y - 16} textAnchor="middle" className="trend-point-label">
            {formatMoney(point.value)}
          </text>
          <text x={point.x} y={height - 6} textAnchor="middle" className="trend-axis bottom">
            {items[index]?.label ?? ""}
          </text>
        </g>
      ))}
    </svg>
  );
}

function Sparkline({
  values,
  tone = "blue",
}: {
  values: number[];
  tone?: "blue" | "green" | "red";
}) {
  const width = 160;
  const height = 52;
  const { path } = buildLinePath(values.length ? values : [0], width, height, 8);
  const stroke =
    tone === "green" ? "#16a34a" : tone === "red" ? "#dc2626" : "#2563eb";
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" role="img" aria-hidden="true">
      <path d={path} fill="none" stroke={stroke} strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DonutChart({
  items,
  total,
}: {
  items: Array<{ label: string; value: number; color: string }>;
  total: number;
}) {
  const radius = 54;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <div className="donut-shell">
      <svg viewBox="0 0 160 160" className="donut-chart" role="img" aria-label="Maliyet modeli dağılımı">
        <circle cx="80" cy="80" r={radius} fill="none" stroke="rgba(148, 163, 184, 0.16)" strokeWidth={strokeWidth} />
        {items.map((item) => {
          const ratio = total > 0 ? item.value / total : 0;
          const dash = circumference * ratio;
          const strokeDasharray = `${dash} ${circumference - dash}`;
          const currentOffset = offset;
          offset += dash;
          return (
            <circle
              key={item.label}
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={item.color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={-currentOffset}
              transform="rotate(-90 80 80)"
            />
          );
        })}
      </svg>
      <div className="donut-total">
        <strong>{formatMoney(total)}</strong>
        <span>Toplam hakediş</span>
      </div>
    </div>
  );
}

function DeltaPill({
  label,
  tone,
}: {
  label: string;
  tone: PayrollDeltaTone;
}) {
  return <span className={`delta-pill delta-pill--${tone}`}>{label}</span>;
}

function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLocaleLowerCase("tr-TR");
  const tone = normalized.includes("aktif") ? "active" : normalized.includes("pasif") ? "muted" : "neutral";
  return <span className={`status-badge status-badge--${tone}`}>{value || "—"}</span>;
}

function RankingCard({
  title,
  items,
  formatter,
  onSelect,
  selectedId,
}: {
  title: string;
  items: Array<{
    id: number;
    name: string;
    role: string;
    value: number;
    subValue?: string;
  }>;
  formatter: (value: number) => string;
  onSelect: (id: number) => void;
  selectedId: number | null;
}) {
  return (
    <section className="surface-card rankings-card">
      <div className="section-head compact">
        <div>
          <h3>{title}</h3>
        </div>
      </div>
      <div className="ranking-list">
        {items.length ? (
          items.map((item, index) => (
            <button
              key={`${title}-${item.id}`}
              type="button"
              onClick={() => onSelect(item.id)}
              className={`ranking-item ${selectedId === item.id ? "is-selected" : ""}`}
            >
              <span className="ranking-index">{index + 1}</span>
              <span className="ranking-copy">
                <strong>{item.name}</strong>
                <small>{item.role}{item.subValue ? ` • ${item.subValue}` : ""}</small>
              </span>
              <span className="ranking-value">{formatter(item.value)}</span>
            </button>
          ))
        ) : (
          <div className="empty-state compact">Seçili filtrede sıralama oluşmadı.</div>
        )}
      </div>
    </section>
  );
}

function PayrollKpiCard({
  title,
  value,
  delta,
  badge,
  tone = "blue",
}: {
  title: string;
  value: string;
  delta: { label: string; tone: PayrollDeltaTone };
  badge: string;
  tone?: "blue" | "green" | "orange" | "violet";
}) {
  return (
    <article className={`surface-card kpi-card tone-${tone}`}>
      <div className="kpi-badge">{badge}</div>
      <div className="kpi-title">{title}</div>
      <div className="kpi-value">{value}</div>
      <DeltaPill label={delta.label} tone={delta.tone} />
    </article>
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
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<PayrollTab>("finance");
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [documentMessage, setDocumentMessage] = useState("");
  const [monthlySeries, setMonthlySeries] = useState<MonthlySeriesItem[]>([]);
  const [deductionEntries, setDeductionEntries] = useState<DeductionRecord[]>([]);
  const [deductionLoading, setDeductionLoading] = useState(false);
  const deferredEntryQuery = useDeferredValue(entryQuery);

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
        params.set("limit", "500");
        const query = params.toString() ? `?${params.toString()}` : "";
        const response = await apiFetch(`/payroll/dashboard${query}`);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = normalizePayrollDashboard((await response.json()) as Partial<PayrollDashboard>);
        if (!selectedMonth && payload.selected_month) {
          setSelectedMonth(payload.selected_month);
        }
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
  }, [loading, selectedMonth, selectedRestaurant, selectedRole, user]);

  const monthWindow = useMemo(() => {
    if (!dashboard?.month_options?.length) {
      return [];
    }
    const targetMonth = dashboard.selected_month || selectedMonth || dashboard.month_options[0];
    const monthIndex = dashboard.month_options.indexOf(targetMonth);
    const startIndex = monthIndex === -1 ? 0 : monthIndex;
    return dashboard.month_options.slice(startIndex, startIndex + 6).reverse();
  }, [dashboard?.month_options, dashboard?.selected_month, selectedMonth]);

  useEffect(() => {
    let active = true;

    async function loadSeries() {
      if (!user || !monthWindow.length) {
        if (active) {
          setMonthlySeries([]);
        }
        return;
      }

      try {
        const snapshots = await Promise.all(
          monthWindow.map(async (month) => {
            const params = new URLSearchParams({ month, limit: "500" });
            if (selectedRole && selectedRole !== "Tümü") {
              params.set("role", selectedRole);
            }
            if (selectedRestaurant && selectedRestaurant !== "Tümü") {
              params.set("restaurant", selectedRestaurant);
            }
            const response = await apiFetch(`/payroll/dashboard?${params.toString()}`);
            if (!response.ok) {
              return null;
            }
            const payload = normalizePayrollDashboard(
              (await response.json()) as Partial<PayrollDashboard>,
            );
            return {
              month,
              label: monthToLabel(month),
              summary: payload.summary,
              entries: payload.entries,
            } satisfies MonthlySeriesItem;
          }),
        );
        if (active) {
          setMonthlySeries(snapshots.filter(Boolean) as MonthlySeriesItem[]);
        }
      } catch {
        if (active) {
          setMonthlySeries([]);
        }
      }
    }

    void loadSeries();
    return () => {
      active = false;
    };
  }, [monthWindow, selectedRestaurant, selectedRole, user]);

  const filteredEntries = useMemo(() => {
    const rows = dashboard?.entries ?? [];
    const query = deferredEntryQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.personnel} ${row.role} ${row.cost_model}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.entries, deferredEntryQuery]);

  useEffect(() => {
    if (!filteredEntries.length) {
      setSelectedPersonnelId(null);
      return;
    }
    if (!selectedPersonnelId || !filteredEntries.some((entry) => entry.personnel_id === selectedPersonnelId)) {
      setSelectedPersonnelId(filteredEntries[0].personnel_id);
    }
  }, [filteredEntries, selectedPersonnelId]);

  const selectedPersonnel = useMemo(
    () => filteredEntries.find((entry) => entry.personnel_id === selectedPersonnelId) ?? null,
    [filteredEntries, selectedPersonnelId],
  );

  useEffect(() => {
    let active = true;

    async function loadDeductions() {
      if (!user || !selectedPersonnel) {
        if (active) {
          setDeductionEntries([]);
          setDeductionLoading(false);
        }
        return;
      }

      setDeductionLoading(true);
      try {
        const params = new URLSearchParams({
          personnel_id: String(selectedPersonnel.personnel_id),
          limit: "60",
        });
        const response = await apiFetch(`/deductions/records?${params.toString()}`);
        if (!response.ok) {
          if (active) {
            setDeductionEntries([]);
          }
          return;
        }
        const payload = (await response.json()) as DeductionsManagementResponse;
        const monthPrefix = (dashboard?.selected_month || selectedMonth || "").trim();
        const rows = (payload.entries ?? []).filter((entry) =>
          monthPrefix ? String(entry.deduction_date).startsWith(monthPrefix) : true,
        );
        if (active) {
          setDeductionEntries(rows);
        }
      } catch {
        if (active) {
          setDeductionEntries([]);
        }
      } finally {
        if (active) {
          setDeductionLoading(false);
        }
      }
    }

    void loadDeductions();
    return () => {
      active = false;
    };
  }, [dashboard?.selected_month, selectedMonth, selectedPersonnel, user]);

  const payrollOverview = useMemo(() => {
    const summary = dashboard?.summary;
    return {
      selectedMonth: summary?.selected_month ?? selectedMonth ?? dashboard?.selected_month ?? "",
      personnelCount: summary?.personnel_count ?? 0,
      totalHours: summary?.total_hours ?? 0,
      totalPackages: summary?.total_packages ?? 0,
      grossPayroll: summary?.gross_payroll ?? 0,
      totalDeductions: summary?.total_deductions ?? 0,
      totalTevkifat: summary?.total_tevkifat ?? 0,
      netPayment: summary?.net_payment ?? 0,
    };
  }, [dashboard?.selected_month, dashboard?.summary, selectedMonth]);

  const currentSeries = useMemo(
    () => monthlySeries.find((item) => item.month === payrollOverview.selectedMonth) ?? null,
    [monthlySeries, payrollOverview.selectedMonth],
  );

  const previousSeries = useMemo(() => {
    if (!payrollOverview.selectedMonth) {
      return null;
    }
    const index = monthlySeries.findIndex((item) => item.month === payrollOverview.selectedMonth);
    if (index <= 0) {
      return null;
    }
    return monthlySeries[index - 1];
  }, [monthlySeries, payrollOverview.selectedMonth]);

  const trendSeries = useMemo(
    () =>
      monthlySeries.map((item) => ({
        label: item.label,
        value: item.summary?.gross_payroll ?? 0,
      })),
    [monthlySeries],
  );

  const growthInsight = useMemo(() => {
    if (trendSeries.length < 2) {
      return "Hakediş trendi yeni veri geldikçe burada okunacak.";
    }
    const first = trendSeries[0]?.value ?? 0;
    const last = trendSeries[trendSeries.length - 1]?.value ?? 0;
    if (first <= 0) {
      return "Seçili dönem aralığında önceki kıyas için yeterli baz oluşmadı.";
    }
    const ratio = ((last - first) / first) * 100;
    return `Son ${trendSeries.length} ayda hakediş tutarı ${formatNumber(Math.abs(ratio), 1)}% ${ratio >= 0 ? "artış" : "daralma"} gösterdi.`;
  }, [trendSeries]);

  const costModelItems = useMemo(() => {
    const items = (dashboard?.cost_model_breakdown ?? []).map((row, index) => ({
      label: COST_MODEL_LABELS[row.cost_model] ?? displayCostModel(row.cost_model),
      value: row.net_payment,
      color: CHART_COLORS[index % CHART_COLORS.length],
      percentage:
        payrollOverview.netPayment > 0 ? (row.net_payment / payrollOverview.netPayment) * 100 : 0,
    }));
    return items.sort((left, right) => right.value - left.value);
  }, [dashboard?.cost_model_breakdown, payrollOverview.netPayment]);

  const dominantCostModel = useMemo(() => {
    const top = costModelItems[0];
    if (!top) {
      return "Model dağılımı oluştuğunda baskın hakediş yapısı burada okunacak.";
    }
    return `Hakedişin ${formatNumber(top.percentage, 0)}%'i ${top.label.toLocaleLowerCase("tr-TR")} modelinden geliyor.`;
  }, [costModelItems]);

  const productivitySeries = useMemo(() => {
    const averageValues = monthlySeries.map((item) => {
      const hours = item.summary?.total_hours ?? 0;
      const packages = item.summary?.total_packages ?? 0;
      return hours > 0 ? packages / hours : 0;
    });
    return {
      packagesPerHour: averageValues,
      packages: monthlySeries.map((item) => item.summary?.total_packages ?? 0),
      hours: monthlySeries.map((item) => item.summary?.total_hours ?? 0),
    };
  }, [monthlySeries]);

  const currentPackagesPerHour =
    payrollOverview.totalHours > 0 ? payrollOverview.totalPackages / payrollOverview.totalHours : 0;

  const previousPackagesPerHour =
    (previousSeries?.summary?.total_hours ?? 0) > 0
      ? (previousSeries?.summary?.total_packages ?? 0) / (previousSeries?.summary?.total_hours ?? 1)
      : 0;

  const highestNetPayment = useMemo(
    () =>
      [...filteredEntries]
        .sort((left, right) => right.net_payment - left.net_payment)
        .slice(0, 5)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.net_payment,
        })),
    [filteredEntries],
  );

  const highestDeduction = useMemo(
    () =>
      [...filteredEntries]
        .sort((left, right) => right.total_deductions - left.total_deductions)
        .slice(0, 5)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.total_deductions,
        })),
    [filteredEntries],
  );

  const mostEfficient = useMemo(
    () =>
      [...filteredEntries]
        .filter((entry) => entry.total_hours > 0)
        .sort(
          (left, right) =>
            right.total_packages / right.total_hours - left.total_packages / left.total_hours,
        )
        .slice(0, 5)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.total_packages / entry.total_hours,
          subValue: `${formatNumber(entry.total_packages, 0)} paket`,
        })),
    [filteredEntries],
  );

  const personTrendSeries = useMemo(() => {
    if (!selectedPersonnelId) {
      return [];
    }
    return monthlySeries.map((item) => {
      const personEntry = item.entries.find((entry) => entry.personnel_id === selectedPersonnelId);
      return {
        label: item.label,
        value: personEntry?.net_payment ?? 0,
      };
    });
  }, [monthlySeries, selectedPersonnelId]);

  const personTrendInsight = useMemo(() => {
    if (personTrendSeries.length < 2) {
      return "Seçili personelin trendi yeni aylar geldikçe burada görünecek.";
    }
    const first = personTrendSeries[0]?.value ?? 0;
    const last = personTrendSeries[personTrendSeries.length - 1]?.value ?? 0;
    if (first <= 0) {
      return "Bu kişi için geçmiş ay karşılaştırması oluşmadı.";
    }
    const ratio = ((last - first) / first) * 100;
    return `Seçili personelin net ödemesi ${personTrendSeries.length} aylık hatta ${formatNumber(
      Math.abs(ratio),
      1,
    )}% ${ratio >= 0 ? "yukarı" : "aşağı"} yönde ilerliyor.`;
  }, [personTrendSeries]);

  const selectedPersonDeductions = useMemo(() => {
    if (!selectedPersonnel) {
      return [] as DeductionListItem[];
    }
    const normalizedRows: DeductionListItem[] = deductionEntries.map((entry) => ({
      key: entry.id,
      label: entry.type_caption || entry.deduction_type || "Kesinti",
      amount: entry.amount,
    }));
    const tevkifatExists = normalizedRows.some((row) =>
      row.label.toLocaleLowerCase("tr-TR").includes("tevkifat"),
    );
    const rows = [...normalizedRows];
    if (!tevkifatExists && selectedPersonnel.tevkifat_amount > 0) {
      rows.push({
        key: "tevkifat",
        label: "Tevkifat",
        amount: selectedPersonnel.tevkifat_amount,
      });
    }
    const listedTotal = rows.reduce((total, row) => total + row.amount, 0);
    const residual = Math.max(selectedPersonnel.total_deductions - listedTotal, 0);
    if (residual > 0.01) {
      rows.push({
        key: "other",
        label: "Diğer Kesintiler",
        amount: residual,
      });
    }
    if (!rows.length && selectedPersonnel.total_deductions > 0) {
      rows.push({
        key: "summary",
        label: "Toplam Kesinti",
        amount: selectedPersonnel.total_deductions,
      });
    }
    return rows;
  }, [deductionEntries, selectedPersonnel]);

  async function handleDocumentDownload() {
    if (!selectedPersonnel) {
      setDocumentError("PDF indirmek için önce personel seçmelisin.");
      setDocumentMessage("");
      return;
    }
    const month = dashboard?.selected_month || selectedMonth;
    if (!month) {
      setDocumentError("PDF indirmek için önce dönem seçmelisin.");
      setDocumentMessage("");
      return;
    }

    setDocumentBusy(true);
    setDocumentError("");
    setDocumentMessage("");
    try {
      const params = new URLSearchParams({
        personnel_id: String(selectedPersonnel.personnel_id),
        month,
      });
      const response = await apiFetch(`/payroll/document?${params.toString()}`);
      if (!response.ok) {
        let detail = "Hakediş PDF'i indirilemedi.";
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
      const fileName =
        fileNameMatch?.[1] ||
        `hakedis_${selectedPersonnel.personnel_id}_${month}.pdf`;
      const blob = await response.blob();
      triggerBrowserDownload(blob, fileName);
      setDocumentMessage("Hakediş PDF'i indirildi.");
    } catch (nextError) {
      setDocumentError(
        nextError instanceof Error ? nextError.message : "Hakediş PDF'i indirilemedi.",
      );
    } finally {
      setDocumentBusy(false);
    }
  }

  function handleCsvDownload() {
    if (!filteredEntries.length) {
      setDocumentError("Excel indirmek için önce görünür kayıt oluşmalı.");
      setDocumentMessage("");
      return;
    }
    const headers = [
      "Personel",
      "Rol",
      "Durum",
      "Toplam Saat",
      "Toplam Paket",
      "Hakediş Tutarı",
      "Toplam Kesinti",
      "Toplam Tevkifat",
      "Net Ödenecek Tutar",
      "Şube Sayısı",
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
      String(entry.tevkifat_amount),
      String(entry.net_payment),
      String(entry.restaurant_count),
      entry.cost_model,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "hakedis";
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
    triggerBrowserDownload(blob, `catkapinda_aylik_hakedis_${month}.csv`);
    setDocumentError("");
    setDocumentMessage("Aylık hakediş tablosu indirildi.");
  }

  const kpis: Array<{
    title: string;
    value: string;
    delta: { label: string; tone: PayrollDeltaTone };
    badge: string;
    tone: "blue" | "green" | "orange" | "violet";
  }> = [
    {
      title: "Net Ödenecek Tutar",
      value: formatMoney(payrollOverview.netPayment),
      delta: buildDelta(
        payrollOverview.netPayment,
        previousSeries?.summary?.net_payment ?? 0,
        true,
      ),
      badge: "N",
      tone: "blue" as const,
    },
    {
      title: "Hakediş Tutarı",
      value: formatMoney(payrollOverview.grossPayroll),
      delta: buildDelta(
        payrollOverview.grossPayroll,
        previousSeries?.summary?.gross_payroll ?? 0,
        true,
      ),
      badge: "H",
      tone: "green" as const,
    },
    {
      title: "Toplam Kesinti",
      value: formatMoney(payrollOverview.totalDeductions),
      delta: buildDelta(
        payrollOverview.totalDeductions,
        previousSeries?.summary?.total_deductions ?? 0,
        false,
      ),
      badge: "K",
      tone: "orange" as const,
    },
    {
      title: "Toplam Tevkifat",
      value: formatMoney(payrollOverview.totalTevkifat),
      delta: buildDelta(
        payrollOverview.totalTevkifat,
        previousSeries?.summary?.total_tevkifat ?? 0,
        false,
      ),
      badge: "T",
      tone: "violet" as const,
    },
  ];

  return (
    <AppShell activeItem="Aylık Hakediş">
      <section className="payroll-page">
        <header className="page-header">
          <div className="page-copy">
            <h1>Aylık Hakediş</h1>
            <p>Kurye ödemelerini, kesintileri ve performansı tek ekranda yönetin.</p>
          </div>
          <div className="page-actions">
            <label className="field compact">
              <span>Dönem</span>
              <select
                value={selectedMonth}
                onChange={(event) => setSelectedMonth(event.target.value)}
                disabled={dashboardLoading || !dashboard?.month_options?.length}
              >
                {(dashboard?.month_options ?? []).map((month) => (
                  <option key={month} value={month}>
                    {month}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="ghost-button" onClick={handleCsvDownload}>
              Excel İndir
            </button>
          </div>
        </header>

        {dashboardLoading ? (
          <section className="surface-card loading-card">
            Hakediş verileri yükleniyor...
          </section>
        ) : !dashboard || !dashboard.summary ? (
          <section className="surface-card empty-state">
            Hakediş verileri şu an alınamadı. Bağlantı toparlandığında aylık ödeme özeti ve
            performans panelleri otomatik yenilenecek.
          </section>
        ) : (
          <>
            <section className="kpi-grid">
              {kpis.map((item) => (
                <PayrollKpiCard
                  key={item.title}
                  title={item.title}
                  value={item.value}
                  delta={item.delta}
                  badge={item.badge}
                  tone={item.tone}
                />
              ))}
            </section>

            <section className="surface-card filters-card">
              <div className="section-head compact">
                <div>
                  <h3>Filtre ve seçimler</h3>
                  <p>Hakediş görünümünü role, restorana ve personele göre daralt.</p>
                </div>
              </div>
              <div className="filters-grid">
                <label className="field">
                  <span>Rol</span>
                  <select value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)}>
                    {(dashboard.role_options ?? ["Tümü"]).map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Restoran</span>
                  <select
                    value={selectedRestaurant}
                    onChange={(event) => setSelectedRestaurant(event.target.value)}
                  >
                    {(dashboard.restaurant_options ?? ["Tümü"]).map((restaurant) => (
                      <option key={restaurant} value={restaurant}>
                        {restaurant}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field field-search">
                  <span>Personel ara</span>
                  <input
                    value={entryQuery}
                    onChange={(event) => setEntryQuery(event.target.value)}
                    placeholder="Ad, rol veya model ara"
                  />
                </label>
              </div>
            </section>

            <div className="workspace-grid">
              <div className="workspace-main">
                <div className="analytics-hero-grid">
                  <section className="surface-card trend-card">
                    <div className="section-head">
                      <div>
                        <h3>Hakediş Trendi</h3>
                        <p>Son 6 ayda toplam hakediş akışını ve ivmesini tek grafikte izle.</p>
                      </div>
                    </div>
                    <TrendChart items={trendSeries.length ? trendSeries : [{ label: "—", value: 0 }]} />
                    <div className="insight-banner">{growthInsight}</div>
                  </section>

                  <section className="surface-card donut-card">
                    <div className="section-head">
                      <div>
                        <h3>Maliyet Modeli Dağılımı</h3>
                        <p>Hakedişin hangi modelden geldiğini ve toplam yükü hızlıca gör.</p>
                      </div>
                    </div>
                    <div className="donut-layout">
                      <DonutChart items={costModelItems} total={payrollOverview.grossPayroll} />
                      <div className="donut-meta">
                        {costModelItems.length ? (
                          costModelItems.map((item) => (
                            <div key={item.label} className="legend-row">
                              <span className="legend-dot" style={{ background: item.color }} />
                              <span className="legend-label">{item.label}</span>
                              <strong>{formatMoney(item.value)}</strong>
                              <small>%{formatNumber(item.percentage, 0)}</small>
                            </div>
                          ))
                        ) : (
                          <div className="empty-state compact">Dağılım verisi oluşmadı.</div>
                        )}
                      </div>
                    </div>
                    <div className="insight-banner success">{dominantCostModel}</div>
                  </section>
                </div>

                <section className="analytics-row">
                  <div className="section-head inline">
                    <div>
                      <h3>Verimlilik Özeti</h3>
                      <p>Operasyon yükünü hız ve hacim açısından aynı seviyede okuyun.</p>
                    </div>
                  </div>
                  <div className="efficiency-grid">
                    <article className="surface-card mini-metric-card">
                      <div className="mini-metric-head">
                        <span>Ortalama Paket / Saat</span>
                        <DeltaPill
                          label={buildDelta(currentPackagesPerHour, previousPackagesPerHour, true).label}
                          tone={buildDelta(currentPackagesPerHour, previousPackagesPerHour, true).tone}
                        />
                      </div>
                      <strong>{formatNumber(currentPackagesPerHour, 1)}</strong>
                      <Sparkline values={productivitySeries.packagesPerHour} tone="blue" />
                    </article>
                    <article className="surface-card mini-metric-card">
                      <div className="mini-metric-head">
                        <span>Toplam Paket</span>
                        <DeltaPill
                          label={buildDelta(
                            payrollOverview.totalPackages,
                            previousSeries?.summary?.total_packages ?? 0,
                            true,
                          ).label}
                          tone={buildDelta(
                            payrollOverview.totalPackages,
                            previousSeries?.summary?.total_packages ?? 0,
                            true,
                          ).tone}
                        />
                      </div>
                      <strong>{formatNumber(payrollOverview.totalPackages, 0)}</strong>
                      <Sparkline values={productivitySeries.packages} tone="green" />
                    </article>
                    <article className="surface-card mini-metric-card">
                      <div className="mini-metric-head">
                        <span>Toplam Saat</span>
                        <DeltaPill
                          label={buildDelta(
                            payrollOverview.totalHours,
                            previousSeries?.summary?.total_hours ?? 0,
                            true,
                          ).label}
                          tone={buildDelta(
                            payrollOverview.totalHours,
                            previousSeries?.summary?.total_hours ?? 0,
                            true,
                          ).tone}
                        />
                      </div>
                      <strong>{formatNumber(payrollOverview.totalHours, 1)}</strong>
                      <Sparkline values={productivitySeries.hours} tone="blue" />
                    </article>
                  </div>
                </section>

                <section className="ranking-grid">
                  <RankingCard
                    title="En Yüksek Net Ödeme"
                    items={highestNetPayment}
                    formatter={formatMoney}
                    onSelect={setSelectedPersonnelId}
                    selectedId={selectedPersonnelId}
                  />
                  <RankingCard
                    title="En Yüksek Kesinti Tutarı"
                    items={highestDeduction}
                    formatter={formatMoney}
                    onSelect={setSelectedPersonnelId}
                    selectedId={selectedPersonnelId}
                  />
                  <RankingCard
                    title="En Verimli Kuryeler"
                    items={mostEfficient}
                    formatter={(value) => formatNumber(value, 1)}
                    onSelect={setSelectedPersonnelId}
                    selectedId={selectedPersonnelId}
                  />
                </section>

                <section className="surface-card roster-card">
                  <div className="section-head">
                    <div>
                      <h3>Hakediş Listesi</h3>
                      <p>Seçili dönemdeki personel özetlerinden kişiyi seçip sağ panelde detay aç.</p>
                    </div>
                    <div className="section-meta">
                      {formatNumber(filteredEntries.length, 0)} kişi
                    </div>
                  </div>

                  <div className="roster-table desktop-only">
                    <div className="roster-row roster-head">
                      <span>Personel</span>
                      <span>Rol</span>
                      <span>Net Ödeme</span>
                      <span>Kesinti</span>
                      <span>Tevkifat</span>
                      <span>Model</span>
                    </div>
                    {filteredEntries.map((entry) => (
                      <button
                        key={entry.personnel_id}
                        type="button"
                        className={`roster-row ${selectedPersonnelId === entry.personnel_id ? "is-selected" : ""}`}
                        onClick={() => setSelectedPersonnelId(entry.personnel_id)}
                      >
                        <span>
                          <strong>{entry.personnel}</strong>
                          <small>{entry.status}</small>
                        </span>
                        <span>{entry.role}</span>
                        <span>{formatMoney(entry.net_payment)}</span>
                        <span className="negative">{formatMoney(entry.total_deductions)}</span>
                        <span>{formatMoney(entry.tevkifat_amount)}</span>
                        <span>{displayCostModel(entry.cost_model)}</span>
                      </button>
                    ))}
                  </div>

                  <div className="roster-cards mobile-only">
                    {filteredEntries.map((entry) => (
                      <button
                        key={`mobile-${entry.personnel_id}`}
                        type="button"
                        className={`roster-mobile-card ${selectedPersonnelId === entry.personnel_id ? "is-selected" : ""}`}
                        onClick={() => setSelectedPersonnelId(entry.personnel_id)}
                      >
                        <div className="roster-mobile-head">
                          <strong>{entry.personnel}</strong>
                          <StatusBadge value={entry.status} />
                        </div>
                        <div className="roster-mobile-meta">
                          <span>{entry.role}</span>
                          <span>{displayCostModel(entry.cost_model)}</span>
                        </div>
                        <div className="roster-mobile-values">
                          <div>
                            <small>Net Ödeme</small>
                            <strong>{formatMoney(entry.net_payment)}</strong>
                          </div>
                          <div>
                            <small>Kesinti</small>
                            <strong className="negative">{formatMoney(entry.total_deductions)}</strong>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              </div>

              <aside className="detail-panel surface-card">
                {selectedPersonnel ? (
                  <>
                    <div className="detail-head">
                      <div className="detail-avatar">{getInitials(selectedPersonnel.personnel)}</div>
                      <div className="detail-copy">
                        <h3>{selectedPersonnel.personnel}</h3>
                        <p>{selectedPersonnel.role}</p>
                      </div>
                      <StatusBadge value={selectedPersonnel.status} />
                    </div>

                    <div className="detail-tabs" role="tablist" aria-label="Personel detay sekmeleri">
                      {[
                        { id: "finance", label: "Finans Özeti" },
                        { id: "operations", label: "Operasyon Özeti" },
                        { id: "trend", label: "Trend" },
                        { id: "pdf", label: "PDF" },
                      ].map((tab) => (
                        <button
                          key={tab.id}
                          type="button"
                          className={`detail-tab ${activeTab === tab.id ? "is-active" : ""}`}
                          onClick={() => setActiveTab(tab.id as PayrollTab)}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>

                    {activeTab === "finance" ? (
                      <div className="detail-tab-panel">
                        <div className="detail-metrics-grid">
                          <article className="detail-metric">
                            <span>Net Ödeme</span>
                            <strong>{formatMoney(selectedPersonnel.net_payment)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Hakediş Tutarı</span>
                            <strong>{formatMoney(selectedPersonnel.gross_pay)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Toplam Kesinti</span>
                            <strong>{formatMoney(selectedPersonnel.total_deductions)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Toplam Tevkifat</span>
                            <strong>{formatMoney(selectedPersonnel.tevkifat_amount)}</strong>
                          </article>
                        </div>
                        <div className="detail-list-card">
                          <div className="detail-list-head">
                            <h4>Kesinti Kalemleri</h4>
                            {deductionLoading ? <span>Yükleniyor...</span> : null}
                          </div>
                          <div className="deduction-list">
                            {selectedPersonDeductions.length ? (
                              selectedPersonDeductions.map((row) => (
                                <div className="deduction-row" key={String(row.key)}>
                                  <span>{row.label}</span>
                                  <strong className="negative">{formatMoney(row.amount)}</strong>
                                </div>
                              ))
                            ) : (
                              <div className="empty-state compact">Bu kişi için seçili ayda kesinti oluşmadı.</div>
                            )}
                          </div>
                          <div className="deduction-total-row">
                            <span>Toplam Kesinti</span>
                            <strong>{formatMoney(selectedPersonnel.total_deductions)}</strong>
                          </div>
                        </div>
                      </div>
                    ) : null}

                    {activeTab === "operations" ? (
                      <div className="detail-tab-panel">
                        <div className="detail-metrics-grid">
                          <article className="detail-metric">
                            <span>Toplam Saat</span>
                            <strong>{formatNumber(selectedPersonnel.total_hours, 1)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Toplam Paket</span>
                            <strong>{formatNumber(selectedPersonnel.total_packages, 0)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Toplam Şube</span>
                            <strong>{formatNumber(selectedPersonnel.restaurant_count, 0)}</strong>
                          </article>
                          <article className="detail-metric">
                            <span>Paket / Saat</span>
                            <strong>
                              {selectedPersonnel.total_hours > 0
                                ? formatNumber(
                                    selectedPersonnel.total_packages / selectedPersonnel.total_hours,
                                    1,
                                  )
                                : "0,0"}
                            </strong>
                          </article>
                        </div>
                        <div className="detail-copy-block">
                          <span>Maliyet modeli</span>
                          <strong>{displayCostModel(selectedPersonnel.cost_model)}</strong>
                          <p>
                            Operasyon ritmi bu ay {formatNumber(selectedPersonnel.restaurant_count, 0)} şube
                            ve {formatNumber(selectedPersonnel.total_packages, 0)} paket üzerinden okunuyor.
                          </p>
                        </div>
                      </div>
                    ) : null}

                    {activeTab === "trend" ? (
                      <div className="detail-tab-panel">
                        <div className="detail-trend-card">
                          <TrendChart items={personTrendSeries.length ? personTrendSeries : [{ label: "—", value: 0 }]} />
                        </div>
                        <div className="insight-banner">{personTrendInsight}</div>
                      </div>
                    ) : null}

                    {activeTab === "pdf" ? (
                      <div className="detail-tab-panel">
                        <div className="detail-copy-block">
                          <span>PDF</span>
                          <strong>Hakediş PDF’i İndir</strong>
                          <p>Seçili personelin aylık kurye hakediş belgesini tek tıkla dışa aktar.</p>
                        </div>
                        <button
                          type="button"
                          className="primary-button full-width"
                          onClick={handleDocumentDownload}
                          disabled={documentBusy}
                        >
                          {documentBusy ? "PDF hazırlanıyor..." : "Hakediş PDF’i İndir"}
                        </button>
                        {documentError ? <div className="form-feedback error">{documentError}</div> : null}
                        {documentMessage ? (
                          <div className="form-feedback success">{documentMessage}</div>
                        ) : null}
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="empty-state">
                    Sağ detay panelini doldurmak için listeden bir personel seçin.
                  </div>
                )}
              </aside>
            </div>
          </>
        )}
      </section>

      <style jsx>{`
        .payroll-page {
          display: grid;
          gap: 20px;
        }

        .page-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          flex-wrap: wrap;
        }

        .page-copy {
          display: grid;
          gap: 6px;
        }

        .page-copy h1 {
          margin: 0;
          font-size: clamp(1.9rem, 2.6vw, 2.6rem);
          line-height: 1;
          font-weight: 800;
          color: #0f1e36;
          letter-spacing: -0.04em;
        }

        .page-copy p {
          margin: 0;
          color: #64748b;
          font-size: 1rem;
          line-height: 1.6;
        }

        .page-actions {
          display: flex;
          align-items: end;
          gap: 12px;
          flex-wrap: wrap;
        }

        .field {
          display: grid;
          gap: 8px;
          min-width: 0;
        }

        .field.compact {
          min-width: 190px;
        }

        .field span {
          color: #64748b;
          font-size: 0.8rem;
          font-weight: 700;
        }

        .field select,
        .field input {
          width: 100%;
          min-height: 48px;
          padding: 0 14px;
          border-radius: 16px;
          border: 1px solid #e6ecf4;
          background: rgba(255, 255, 255, 0.92);
          color: #0f172a;
          font-size: 0.95rem;
          font-weight: 600;
          box-sizing: border-box;
          outline: none;
        }

        .field input::placeholder {
          color: #94a3b8;
        }

        .surface-card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 20px;
          box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
          box-sizing: border-box;
        }

        .loading-card,
        .empty-state {
          padding: 22px 24px;
          color: #64748b;
          line-height: 1.7;
        }

        .empty-state.compact {
          padding: 0;
          font-size: 0.92rem;
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
        }

        .kpi-card {
          padding: 22px;
          display: grid;
          gap: 10px;
          min-height: 154px;
        }

        .kpi-badge {
          width: 44px;
          height: 44px;
          border-radius: 16px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 0.95rem;
          font-weight: 800;
        }

        .tone-blue .kpi-badge {
          background: rgba(59, 130, 246, 0.12);
          color: #2563eb;
        }

        .tone-green .kpi-badge {
          background: rgba(34, 197, 94, 0.12);
          color: #16a34a;
        }

        .tone-orange .kpi-badge {
          background: rgba(249, 115, 22, 0.12);
          color: #ea580c;
        }

        .tone-violet .kpi-badge {
          background: rgba(139, 92, 246, 0.12);
          color: #7c3aed;
        }

        .kpi-title {
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: #64748b;
          font-weight: 800;
        }

        .kpi-value {
          font-size: clamp(1.4rem, 1.6vw, 2rem);
          font-weight: 800;
          letter-spacing: -0.04em;
          color: #0f172a;
          white-space: nowrap;
        }

        .delta-pill {
          display: inline-flex;
          align-items: center;
          width: fit-content;
          padding: 7px 10px;
          border-radius: 999px;
          font-size: 0.78rem;
          font-weight: 700;
        }

        .delta-pill--positive {
          background: rgba(34, 197, 94, 0.12);
          color: #15803d;
        }

        .delta-pill--negative {
          background: rgba(239, 68, 68, 0.12);
          color: #b91c1c;
        }

        .delta-pill--neutral {
          background: rgba(148, 163, 184, 0.12);
          color: #475569;
        }

        .filters-card {
          padding: 22px;
          display: grid;
          gap: 18px;
        }

        .section-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          flex-wrap: wrap;
        }

        .section-head.compact {
          margin-bottom: 0;
        }

        .section-head.inline {
          margin-bottom: 14px;
        }

        .section-head h3 {
          margin: 0;
          color: #0f1e36;
          font-size: 1.02rem;
          line-height: 1.2;
          font-weight: 800;
          letter-spacing: -0.02em;
        }

        .section-head p {
          margin: 6px 0 0;
          color: #64748b;
          font-size: 0.92rem;
          line-height: 1.65;
        }

        .section-meta {
          display: inline-flex;
          align-items: center;
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(37, 99, 235, 0.08);
          color: #2563eb;
          font-size: 0.8rem;
          font-weight: 800;
        }

        .filters-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }

        .field-search {
          grid-column: span 1;
        }

        .workspace-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.8fr) minmax(320px, 420px);
          gap: 20px;
          align-items: start;
        }

        .workspace-main {
          display: grid;
          gap: 20px;
          min-width: 0;
        }

        .analytics-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.45fr) minmax(320px, 1fr);
          gap: 18px;
          align-items: stretch;
        }

        .trend-card,
        .donut-card,
        .roster-card,
        .rankings-card {
          padding: 22px;
          display: grid;
          gap: 18px;
        }

        .trend-chart {
          width: 100%;
          height: auto;
          overflow: visible;
        }

        .trend-axis {
          fill: #94a3b8;
          font-size: 11px;
          font-weight: 600;
        }

        .trend-axis.bottom {
          font-size: 11px;
          fill: #64748b;
        }

        .trend-point-label {
          fill: #0f172a;
          font-size: 11px;
          font-weight: 700;
        }

        .insight-banner {
          padding: 12px 14px;
          border-radius: 14px;
          background: rgba(37, 99, 235, 0.08);
          color: #1d4ed8;
          font-size: 0.9rem;
          line-height: 1.6;
          font-weight: 600;
        }

        .insight-banner.success {
          background: rgba(34, 197, 94, 0.1);
          color: #15803d;
        }

        .donut-layout {
          display: grid;
          grid-template-columns: 220px minmax(0, 1fr);
          gap: 18px;
          align-items: center;
        }

        .donut-shell {
          position: relative;
          width: 188px;
          height: 188px;
          margin: 0 auto;
        }

        .donut-chart {
          width: 100%;
          height: 100%;
        }

        .donut-total {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          gap: 6px;
          text-align: center;
        }

        .donut-total strong {
          color: #0f172a;
          font-size: 1.3rem;
          font-weight: 800;
          letter-spacing: -0.04em;
        }

        .donut-total span {
          color: #64748b;
          font-size: 0.84rem;
          font-weight: 600;
        }

        .donut-meta {
          display: grid;
          gap: 10px;
        }

        .legend-row {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto auto;
          align-items: center;
          gap: 10px;
          color: #0f172a;
        }

        .legend-dot {
          width: 10px;
          height: 10px;
          border-radius: 999px;
        }

        .legend-label {
          font-size: 0.92rem;
          font-weight: 600;
        }

        .legend-row strong {
          font-size: 0.92rem;
          font-weight: 800;
          white-space: nowrap;
        }

        .legend-row small {
          color: #64748b;
          font-size: 0.86rem;
          font-weight: 700;
          white-space: nowrap;
        }

        .analytics-row {
          display: grid;
          gap: 14px;
        }

        .efficiency-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 18px;
        }

        .mini-metric-card {
          padding: 18px;
          display: grid;
          gap: 14px;
        }

        .mini-metric-head {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: start;
          flex-wrap: wrap;
        }

        .mini-metric-head span {
          color: #64748b;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-weight: 800;
        }

        .mini-metric-card strong {
          color: #0f172a;
          font-size: 1.7rem;
          font-weight: 800;
          letter-spacing: -0.04em;
        }

        .sparkline {
          width: 100%;
          height: 52px;
        }

        .ranking-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 18px;
        }

        .ranking-list {
          display: grid;
          gap: 10px;
        }

        .ranking-item {
          width: 100%;
          display: grid;
          grid-template-columns: 36px minmax(0, 1fr) auto;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border-radius: 16px;
          border: 1px solid rgba(229, 231, 235, 0.9);
          background: rgba(248, 250, 252, 0.72);
          text-align: left;
          cursor: pointer;
          transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
        }

        .ranking-item:hover,
        .ranking-item.is-selected {
          border-color: rgba(37, 99, 235, 0.26);
          background: rgba(239, 246, 255, 0.82);
          transform: translateY(-1px);
        }

        .ranking-index {
          width: 36px;
          height: 36px;
          border-radius: 14px;
          background: rgba(37, 99, 235, 0.08);
          color: #1d4ed8;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 0.9rem;
          font-weight: 800;
        }

        .ranking-copy {
          display: grid;
          gap: 4px;
          min-width: 0;
        }

        .ranking-copy strong {
          color: #0f172a;
          font-size: 0.95rem;
          font-weight: 800;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .ranking-copy small {
          color: #64748b;
          font-size: 0.84rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .ranking-value {
          color: #0f172a;
          font-size: 0.95rem;
          font-weight: 800;
          white-space: nowrap;
        }

        .roster-table {
          display: grid;
          border-top: 1px solid #edf2f8;
        }

        .roster-row {
          width: 100%;
          display: grid;
          grid-template-columns: minmax(0, 1.4fr) minmax(120px, 0.8fr) repeat(3, minmax(110px, 0.8fr)) minmax(130px, 0.9fr);
          align-items: center;
          gap: 12px;
          padding: 14px 0;
          border-bottom: 1px solid #edf2f8;
          background: transparent;
          border-left: 0;
          border-right: 0;
          border-top: 0;
          text-align: left;
          cursor: pointer;
        }

        .roster-head {
          color: #64748b;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-weight: 800;
          cursor: default;
        }

        .roster-row:not(.roster-head):hover,
        .roster-row.is-selected {
          background: rgba(248, 250, 252, 0.86);
        }

        .roster-row span {
          display: grid;
          gap: 3px;
          min-width: 0;
          color: #0f172a;
          font-size: 0.92rem;
          font-weight: 600;
        }

        .roster-row span strong {
          font-size: 0.96rem;
          font-weight: 800;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .roster-row span small {
          color: #94a3b8;
          font-size: 0.78rem;
          font-weight: 700;
        }

        .negative {
          color: #dc2626 !important;
        }

        .detail-panel {
          position: sticky;
          top: 24px;
          padding: 22px;
          display: grid;
          gap: 18px;
        }

        .detail-head {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          align-items: center;
          gap: 14px;
        }

        .detail-avatar {
          width: 56px;
          height: 56px;
          border-radius: 20px;
          background: linear-gradient(135deg, rgba(37, 99, 235, 0.16), rgba(22, 163, 74, 0.12));
          color: #1d4ed8;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 1rem;
          font-weight: 800;
        }

        .detail-copy {
          display: grid;
          gap: 4px;
          min-width: 0;
        }

        .detail-copy h3 {
          margin: 0;
          color: #0f172a;
          font-size: 1.24rem;
          font-weight: 800;
          letter-spacing: -0.03em;
        }

        .detail-copy p {
          margin: 0;
          color: #64748b;
          font-size: 0.92rem;
          line-height: 1.5;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 34px;
          padding: 0 12px;
          border-radius: 999px;
          font-size: 0.84rem;
          font-weight: 800;
          white-space: nowrap;
        }

        .status-badge--active {
          background: rgba(34, 197, 94, 0.12);
          color: #15803d;
        }

        .status-badge--muted {
          background: rgba(148, 163, 184, 0.12);
          color: #475569;
        }

        .status-badge--neutral {
          background: rgba(59, 130, 246, 0.08);
          color: #1d4ed8;
        }

        .detail-tabs {
          display: flex;
          align-items: center;
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 4px;
        }

        .detail-tab {
          min-height: 40px;
          padding: 0 14px;
          border-radius: 999px;
          border: 1px solid #e8eef6;
          background: rgba(248, 250, 252, 0.9);
          color: #64748b;
          font-size: 0.85rem;
          font-weight: 800;
          white-space: nowrap;
          cursor: pointer;
          transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
        }

        .detail-tab.is-active {
          background: rgba(37, 99, 235, 0.1);
          border-color: rgba(37, 99, 235, 0.18);
          color: #1d4ed8;
        }

        .detail-tab-panel {
          display: grid;
          gap: 16px;
        }

        .detail-metrics-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .detail-metric {
          padding: 14px;
          border-radius: 16px;
          background: rgba(248, 250, 252, 0.82);
          border: 1px solid #edf2f8;
          display: grid;
          gap: 8px;
        }

        .detail-metric span {
          color: #64748b;
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-weight: 800;
        }

        .detail-metric strong {
          color: #0f172a;
          font-size: 1.18rem;
          font-weight: 800;
          letter-spacing: -0.04em;
          white-space: nowrap;
        }

        .detail-list-card {
          padding: 16px;
          border-radius: 18px;
          background: rgba(248, 250, 252, 0.78);
          border: 1px solid #edf2f8;
          display: grid;
          gap: 14px;
        }

        .detail-list-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .detail-list-head h4 {
          margin: 0;
          color: #0f1e36;
          font-size: 0.96rem;
          font-weight: 800;
        }

        .detail-list-head span {
          color: #94a3b8;
          font-size: 0.82rem;
          font-weight: 700;
        }

        .deduction-list {
          display: grid;
          gap: 10px;
        }

        .deduction-row,
        .deduction-total-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 10px 0;
          border-bottom: 1px solid #edf2f8;
        }

        .deduction-total-row {
          border-bottom: none;
          padding-bottom: 0;
        }

        .deduction-row span,
        .deduction-total-row span {
          color: #475569;
          font-size: 0.92rem;
        }

        .deduction-row strong,
        .deduction-total-row strong {
          color: #0f172a;
          font-size: 0.96rem;
          font-weight: 800;
          white-space: nowrap;
        }

        .detail-copy-block {
          padding: 16px;
          border-radius: 18px;
          background: rgba(248, 250, 252, 0.78);
          border: 1px solid #edf2f8;
          display: grid;
          gap: 8px;
        }

        .detail-copy-block span {
          color: #64748b;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-weight: 800;
        }

        .detail-copy-block strong {
          color: #0f172a;
          font-size: 1.02rem;
          font-weight: 800;
        }

        .detail-copy-block p {
          margin: 0;
          color: #64748b;
          font-size: 0.9rem;
          line-height: 1.65;
        }

        .detail-trend-card {
          padding: 8px 0 0;
        }

        .primary-button,
        .ghost-button {
          min-height: 48px;
          padding: 0 18px;
          border-radius: 16px;
          font-size: 0.95rem;
          font-weight: 800;
          cursor: pointer;
          transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
        }

        .primary-button {
          border: none;
          background: linear-gradient(135deg, #0f5fd7, #1d4ed8);
          color: #ffffff;
          box-shadow: 0 18px 34px rgba(29, 78, 216, 0.18);
        }

        .primary-button:hover,
        .ghost-button:hover {
          transform: translateY(-1px);
        }

        .primary-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .ghost-button {
          border: 1px solid rgba(37, 99, 235, 0.14);
          background: rgba(255, 255, 255, 0.92);
          color: #0f1e36;
        }

        .full-width {
          width: 100%;
        }

        .form-feedback {
          padding: 12px 14px;
          border-radius: 14px;
          font-size: 0.9rem;
          font-weight: 700;
        }

        .form-feedback.error {
          background: rgba(239, 68, 68, 0.1);
          color: #b91c1c;
        }

        .form-feedback.success {
          background: rgba(34, 197, 94, 0.1);
          color: #15803d;
        }

        .desktop-only {
          display: grid;
        }

        .mobile-only {
          display: none;
        }

        @media (max-width: 1280px) {
          .kpi-grid,
          .ranking-grid,
          .efficiency-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .analytics-hero-grid {
            grid-template-columns: minmax(0, 1fr);
          }

          .workspace-grid {
            grid-template-columns: minmax(0, 1fr);
          }

          .detail-panel {
            position: static;
          }
        }

        @media (max-width: 1024px) {
          .filters-grid,
          .donut-layout,
          .detail-metrics-grid,
          .efficiency-grid,
          .ranking-grid {
            grid-template-columns: minmax(0, 1fr);
          }

          .donut-shell {
            width: 168px;
            height: 168px;
          }
        }

        @media (max-width: 640px) {
          .payroll-page {
            gap: 16px;
          }

          .page-header {
            gap: 14px;
          }

          .page-actions {
            width: 100%;
            display: grid;
            grid-template-columns: minmax(0, 1fr);
          }

          .field.compact,
          .ghost-button,
          .primary-button {
            width: 100%;
          }

          .kpi-grid {
            grid-template-columns: 1fr;
          }

          .kpi-card {
            min-height: 0;
          }

          .filters-card,
          .trend-card,
          .donut-card,
          .roster-card,
          .rankings-card,
          .detail-panel {
            padding: 18px;
          }

          .page-copy h1 {
            font-size: 1.8rem;
          }

          .detail-head {
            grid-template-columns: auto 1fr;
          }

          .detail-head .status-badge {
            grid-column: 1 / -1;
            justify-self: start;
          }

          .roster-table.desktop-only {
            display: none;
          }

          .mobile-only {
            display: grid;
            gap: 12px;
          }

          .roster-mobile-card {
            width: 100%;
            padding: 14px;
            border-radius: 18px;
            border: 1px solid #e8eef6;
            background: rgba(248, 250, 252, 0.82);
            display: grid;
            gap: 10px;
            text-align: left;
            cursor: pointer;
          }

          .roster-mobile-card.is-selected {
            border-color: rgba(37, 99, 235, 0.24);
            background: rgba(239, 246, 255, 0.86);
          }

          .roster-mobile-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
          }

          .roster-mobile-head strong {
            color: #0f172a;
            font-size: 0.98rem;
            font-weight: 800;
          }

          .roster-mobile-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            color: #64748b;
            font-size: 0.84rem;
            font-weight: 700;
          }

          .roster-mobile-values {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }

          .roster-mobile-values small {
            color: #64748b;
            font-size: 0.78rem;
          }

          .roster-mobile-values strong {
            display: block;
            margin-top: 4px;
            color: #0f172a;
            font-size: 0.98rem;
            font-weight: 800;
          }
        }
      `}</style>
    </AppShell>
  );
}

function displayCostModel(value: string) {
  return COST_MODEL_LABELS[value] ?? value;
}
